"""Run the 4-die stress workload mechanism-validation experiment."""

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
from src.model.thermal import RCThermalModel, ThermalConfig
from src.model.voltage import EquivalentPdnModel, VoltageConfig
from src.scheduler.base import ScheduleResult
from src.scheduler.greedy import BandwidthGreedyScheduler
from src.scheduler.ptv_aware import PTVAwareScheduler
from src.scheduler.serial import SerialScheduler
from src.visualize.comparison import plot_basic_comparisons
from src.visualize.curves import plot_ir_drop_curve, plot_temperature_curve
from src.visualize.gantt import plot_gantt


CONFIG_PATH = ROOT / "configs" / "case_4die_stress.yaml"
RESULT_DIR = ROOT / "results" / "case_4die_stress"
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
    """Load a YAML mapping."""

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"YAML file must contain a mapping: {path}")
    return data


def write_dict_rows(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    """Write a list of dictionaries as CSV."""

    if not rows:
        raise ValueError("cannot write an empty CSV")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames or list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def summary_row(result: ScheduleResult) -> dict:
    """Return a scheduler metrics row with stable comparison columns."""

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
    """Write schedule, metrics, Gantt, temperature, and IR-drop files."""

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
    """Build the serial baseline scheduler."""

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
    """Build the bandwidth-greedy scheduler."""

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
    """Build the PTV-aware scheduler with stress-case control parameters."""

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


def validate_case(stack: DieStack, access: AccessConfig, tasks: Sequence[TestTask]) -> None:
    """Validate the stress case shape before scheduling."""

    if len(stack.dies) != 4:
        raise ValueError("case_4die_stress must contain exactly four dies")
    if len(tasks) < 16:
        raise ValueError("case_4die_stress must contain at least sixteen tasks")
    for task in tasks:
        stack.get_die(task.die_id)
        if not task.dwr_segment:
            access.dwr_for_die(task.die_id)


def run() -> dict[str, Path]:
    """Run serial, bandwidth-greedy, and PTV-aware schedulers on the stress workload."""

    case = load_yaml(CONFIG_PATH)
    stack = DieStack.from_config(case["stack"])
    access = AccessConfig.from_config(case["access"])
    tasks = build_tasks(case["tasks"])
    thermal_config = ThermalConfig.from_config(case["thermal"])
    voltage_config = VoltageConfig.from_config(case["voltage"])
    scheduler_config = case.get("scheduler", {})
    time_step_s = float(case["simulation"]["time_step_s"])
    clock_hz = float(case["simulation"]["clock_hz"])

    validate_case(stack, access, tasks)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

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
    outputs: dict[str, Path] = {}
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
    print("4-die stress workload mechanism-validation experiment completed.")
    for name, path in outputs.items():
        print(f"{name}: {path.relative_to(ROOT)}")
