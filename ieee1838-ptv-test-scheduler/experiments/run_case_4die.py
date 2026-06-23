"""Run the 4-die scaffold sanity checks and scheduler baselines."""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Sequence

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.model.access import AccessConfig
from src.model.stack import DieStack
from src.model.task import TestTask, build_tasks
from src.model.thermal import RCThermalModel, TemperatureState, ThermalConfig
from src.model.voltage import EquivalentPdnModel, VoltageConfig
from src.scheduler.base import ScheduleResult
from src.scheduler.greedy import BandwidthGreedyScheduler
from src.scheduler.ptv_aware import PTVAwareScheduler
from src.scheduler.serial import SerialScheduler
from src.visualize.comparison import plot_basic_comparisons
from src.visualize.curves import plot_ir_drop_curve, plot_temperature_curve, plot_trace_curve
from src.visualize.gantt import plot_gantt


CONFIG_DIR = ROOT / "configs"
RESULT_DIR = ROOT / "results" / "case_4die"
SUMMARY_COLUMNS = [
    "scheduler_name",
    "tat",
    "peak_temperature",
    "peak_ir_drop",
    "temperature_violation_count",
    "voltage_violation_count",
    "num_tasks",
    "average_parallelism",
    "max_parallelism",
    "fpp_lane_utilization_average",
    "dummy_cycle_count",
    "dummy_time_total",
    "capture_staggering_applied",
    "constraints_were_binding",
]


def load_yaml(path: Path) -> dict:
    """Load a YAML file into a mapping."""

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"YAML file must contain a mapping: {path}")
    return data


def write_dict_rows(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    """Write a list of dictionaries as a CSV file."""

    if not rows:
        raise ValueError("cannot write an empty CSV")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames or list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def trace_row(time_s: float, values_by_die: dict[int, float], peak_key: str) -> dict[str, float]:
    """Build a trace row with per-die values and a peak column."""

    row = {"time": time_s}
    row.update({f"die_{die_id}": value for die_id, value in sorted(values_by_die.items())})
    row[peak_key] = max(values_by_die.values())
    return row


def write_sanity_outputs(
    stack: DieStack,
    access: AccessConfig,
    tasks: Sequence[TestTask],
    thermal_model: RCThermalModel,
    voltage_model: EquivalentPdnModel,
    time_step_s: float,
) -> dict[str, Path]:
    """Write the original scaffold sanity CSV and SVG outputs."""

    model_summary_path = RESULT_DIR / "model_summary.csv"
    write_dict_rows(
        model_summary_path,
        [
            {
                "die_id": die.id,
                "die_name": die.name,
                "layer_index": die.layer_index,
                "area_mm2": die.area_mm2,
                "initial_temp_c": die.initial_temp_c,
                "nominal_power_w": die.nominal_power_w,
                "dwr_length_bits": access.dwr_for_die(die.id).length_bits,
            }
            for die in stack.dies
        ],
    )

    power_by_die_w = {die.id: 0.0 for die in stack.dies}
    for task in tasks:
        power_by_die_w[task.die_id] = task.power_w

    initial_state = TemperatureState({die.id: die.initial_temp_c for die in stack.dies})
    next_state = thermal_model.step(initial_state, power_by_die_w, time_step_s)
    thermal_path = RESULT_DIR / "thermal_sanity.csv"
    write_dict_rows(
        thermal_path,
        [
            {
                "die_id": die_id,
                "initial_temp_c": initial_state.by_die_id[die_id],
                "next_temp_c": next_state.by_die_id[die_id],
                "time_step_s": time_step_s,
            }
            for die_id in stack.die_ids()
        ],
    )

    temperature_curve_path = RESULT_DIR / "temperature_curve.svg"
    plot_trace_curve(
        (
            trace_row(0.0, initial_state.by_die_id, "peak_temperature"),
            trace_row(time_step_s, next_state.by_die_id, "peak_temperature"),
        ),
        temperature_curve_path,
        title="Scaffold sanity temperature trace",
        ylabel="temperature (C)",
        peak_key="peak_temperature",
    )

    voltage_state = voltage_model.estimate(power_by_die_w)
    voltage_path = RESULT_DIR / "voltage_sanity.csv"
    write_dict_rows(
        voltage_path,
        [
            {
                "die_id": die_id,
                "power_w": power_by_die_w[die_id],
                "ir_drop_v": voltage_state.ir_drop_by_die_v[die_id],
            }
            for die_id in stack.die_ids()
        ],
    )

    zero_ir_drop = {die.id: 0.0 for die in stack.dies}
    ir_drop_curve_path = RESULT_DIR / "ir_drop_curve.svg"
    plot_trace_curve(
        (
            trace_row(0.0, zero_ir_drop, "peak_ir_drop"),
            trace_row(time_step_s, voltage_state.ir_drop_by_die_v, "peak_ir_drop"),
        ),
        ir_drop_curve_path,
        title="Scaffold sanity IR-drop trace",
        ylabel="IR drop (V)",
        peak_key="peak_ir_drop",
    )

    return {
        "model_summary": model_summary_path,
        "thermal_sanity": thermal_path,
        "temperature_curve": temperature_curve_path,
        "voltage_sanity": voltage_path,
        "ir_drop_curve": ir_drop_curve_path,
    }


def summary_row(result: ScheduleResult) -> dict:
    """Return a scheduler metrics row with comparison-safe columns."""

    tat = result.tat
    average_parallelism = result.metrics.get("average_parallelism")
    if average_parallelism is None:
        average_parallelism = sum(entry.duration for entry in result.entries) / tat if tat > 0 else 0.0
    max_parallelism = result.metrics.get("max_parallelism")
    if max_parallelism is None:
        max_parallelism = 1 if result.entries else 0
    return {
        "scheduler_name": result.scheduler_name,
        "tat": tat,
        "peak_temperature": result.peak_temperature,
        "peak_ir_drop": result.peak_ir_drop,
        "temperature_violation_count": result.metrics["temperature_violation_count"],
        "voltage_violation_count": result.metrics["voltage_violation_count"],
        "num_tasks": len(result.entries),
        "average_parallelism": average_parallelism,
        "max_parallelism": max_parallelism,
        "fpp_lane_utilization_average": result.metrics.get("fpp_lane_utilization_average", 0.0),
        "dummy_cycle_count": result.metrics.get("dummy_cycle_count", 0),
        "dummy_time_total": result.metrics.get("dummy_time_total", 0.0),
        "capture_staggering_applied": result.metrics.get("capture_staggering_applied", False),
        "constraints_were_binding": result.metrics.get("constraints_were_binding", False),
    }


def write_scheduler_outputs(result: ScheduleResult, prefix: str) -> dict[str, Path]:
    """Write schedule, metrics, Gantt, temperature, and IR-drop outputs."""

    schedule_path = RESULT_DIR / f"{prefix}_schedule.csv"
    write_dict_rows(schedule_path, [entry.to_row() for entry in result.entries])

    metrics_path = RESULT_DIR / f"{prefix}_metrics.csv"
    write_dict_rows(metrics_path, [summary_row(result)], fieldnames=SUMMARY_COLUMNS)

    gantt_path = RESULT_DIR / f"{prefix}_gantt.svg"
    temperature_curve_path = RESULT_DIR / f"{prefix}_temperature_curve.svg"
    ir_drop_curve_path = RESULT_DIR / f"{prefix}_ir_drop_curve.svg"
    plot_gantt(result, gantt_path)
    plot_temperature_curve(result, temperature_curve_path)
    plot_ir_drop_curve(result, ir_drop_curve_path)

    return {
        f"{prefix}_schedule": schedule_path,
        f"{prefix}_metrics": metrics_path,
        f"{prefix}_gantt": gantt_path,
        f"{prefix}_temperature_curve": temperature_curve_path,
        f"{prefix}_ir_drop_curve": ir_drop_curve_path,
    }


def build_serial_scheduler(
    stack: DieStack,
    access: AccessConfig,
    thermal_config: ThermalConfig,
    voltage_config: VoltageConfig,
    clock_hz: float,
    time_step_s: float,
) -> SerialScheduler:
    """Build a serial baseline scheduler."""

    return SerialScheduler(
        stack=stack,
        access=access,
        thermal_model=RCThermalModel(thermal_config),
        voltage_model=EquivalentPdnModel(voltage_config),
        clock_hz=clock_hz,
        time_step_s=time_step_s,
    )


def build_greedy_scheduler(
    stack: DieStack,
    access: AccessConfig,
    thermal_config: ThermalConfig,
    voltage_config: VoltageConfig,
    clock_hz: float,
    time_step_s: float,
) -> BandwidthGreedyScheduler:
    """Build a bandwidth-greedy baseline scheduler."""

    return BandwidthGreedyScheduler(
        stack=stack,
        access=access,
        thermal_model=RCThermalModel(thermal_config),
        voltage_model=EquivalentPdnModel(voltage_config),
        clock_hz=clock_hz,
        time_step_s=time_step_s,
    )


def build_ptv_scheduler(
    stack: DieStack,
    access: AccessConfig,
    thermal_config: ThermalConfig,
    voltage_config: VoltageConfig,
    clock_hz: float,
    time_step_s: float,
    scheduler_config: dict,
) -> PTVAwareScheduler:
    """Build a PTV-aware scheduler."""

    return PTVAwareScheduler(
        stack=stack,
        access=access,
        thermal_model=RCThermalModel(thermal_config),
        voltage_model=EquivalentPdnModel(voltage_config),
        clock_hz=clock_hz,
        time_step_s=time_step_s,
        max_concurrent_capture=int(scheduler_config.get("max_concurrent_capture", 1)),
        dummy_cycle_duration_s=float(scheduler_config.get("dummy_cycle_duration_s", 0.0001)),
        max_dummy_cycles_per_block=int(scheduler_config.get("max_dummy_cycles_per_block", 10)),
    )


def run() -> dict[str, Path]:
    """Run sanity checks plus serial, bandwidth-greedy, and PTV-aware schedulers."""

    defaults = load_yaml(CONFIG_DIR / "default_params.yaml")
    case = load_yaml(CONFIG_DIR / "case_4die.yaml")

    stack = DieStack.from_config(case["stack"])
    access = AccessConfig.from_config(case["access"])
    tasks = build_tasks(case["tasks"])
    thermal_config = ThermalConfig.from_config(defaults["thermal"])
    voltage_config = VoltageConfig.from_config(defaults["voltage"])
    scheduler_config = defaults.get("scheduler", {})
    time_step_s = float(defaults["simulation"]["time_step_s"])
    clock_hz = float(defaults["simulation"]["clock_hz"])

    if len(stack.dies) != 4:
        raise ValueError("case_4die must contain exactly four dies")
    for task in tasks:
        stack.get_die(task.die_id)
        access.dwr_for_die(task.die_id)

    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    outputs = write_sanity_outputs(
        stack,
        access,
        tasks,
        RCThermalModel(thermal_config),
        EquivalentPdnModel(voltage_config),
        time_step_s,
    )

    serial_result = build_serial_scheduler(stack, access, thermal_config, voltage_config, clock_hz, time_step_s).schedule(tasks)
    greedy_result = build_greedy_scheduler(stack, access, thermal_config, voltage_config, clock_hz, time_step_s).schedule(tasks)
    ptv_result = build_ptv_scheduler(
        stack,
        access,
        thermal_config,
        voltage_config,
        clock_hz,
        time_step_s,
        scheduler_config,
    ).schedule(tasks)

    results = [serial_result, greedy_result, ptv_result]
    outputs.update(write_scheduler_outputs(serial_result, "serial"))
    outputs.update(write_scheduler_outputs(greedy_result, "greedy"))
    outputs.update(write_scheduler_outputs(ptv_result, "ptv"))

    summary_path = RESULT_DIR / "scheduler_metrics_summary.csv"
    write_dict_rows(summary_path, [summary_row(result) for result in results], fieldnames=SUMMARY_COLUMNS)
    outputs["scheduler_metrics_summary"] = summary_path
    outputs.update(plot_basic_comparisons(results, RESULT_DIR))
    return outputs


if __name__ == "__main__":
    outputs = run()
    print("4-die sanity, serial, bandwidth-greedy, and PTV-aware experiments completed.")
    for name, path in outputs.items():
        print(f"{name}: {path.relative_to(ROOT)}")

