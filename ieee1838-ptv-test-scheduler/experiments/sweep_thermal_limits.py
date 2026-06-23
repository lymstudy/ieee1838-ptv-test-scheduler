"""Sweep thermal limit on the 4-die stress workload."""

from __future__ import annotations

import copy
import csv
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.model.access import AccessConfig
from src.model.stack import DieStack
from src.model.task import build_tasks
from src.model.thermal import RCThermalModel, ThermalConfig
from src.model.voltage import EquivalentPdnModel, VoltageConfig
from src.scheduler.base import ScheduleResult
from src.scheduler.greedy import BandwidthGreedyScheduler
from src.scheduler.ptv_aware import PTVAwareScheduler
from src.scheduler.serial import SerialScheduler
from src.visualize.sweep import plot_thermal_limit_sweep


CONFIG_PATH = ROOT / "configs" / "case_4die_stress.yaml"
RESULT_DIR = ROOT / "results" / "sweeps" / "thermal_limits"
THERMAL_LIMITS = (25.5, 26.0, 26.5, 27.0, 28.0)
SUMMARY_COLUMNS = [
    "thermal_limit",
    "scheduler_name",
    "tat",
    "peak_temperature",
    "peak_ir_drop",
    "temperature_violation_count",
    "voltage_violation_count",
    "average_parallelism",
    "max_parallelism",
    "fpp_lane_utilization_average",
    "dummy_cycle_count",
    "dummy_time_total",
    "capture_staggering_applied",
    "constraints_were_binding",
    "over_constrained",
]


def load_yaml(path: Path) -> dict:
    """Load a YAML mapping."""

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"YAML file must contain a mapping: {path}")
    return data


def write_dict_rows(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    """Write dictionaries to CSV with a stable column order."""

    if not rows:
        raise ValueError("cannot write an empty CSV")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def summary_row(thermal_limit: float, result: ScheduleResult, over_constrained: bool) -> dict:
    """Return one thermal-limit sweep row."""

    return {
        "thermal_limit": thermal_limit,
        "scheduler_name": result.scheduler_name,
        "tat": result.tat,
        "peak_temperature": result.peak_temperature,
        "peak_ir_drop": result.peak_ir_drop,
        "temperature_violation_count": result.metrics["temperature_violation_count"],
        "voltage_violation_count": result.metrics["voltage_violation_count"],
        "average_parallelism": result.metrics.get("average_parallelism", 0.0),
        "max_parallelism": result.metrics.get("max_parallelism", 0),
        "fpp_lane_utilization_average": result.metrics.get("fpp_lane_utilization_average", 0.0),
        "dummy_cycle_count": result.metrics.get("dummy_cycle_count", 0),
        "dummy_time_total": result.metrics.get("dummy_time_total", 0.0),
        "capture_staggering_applied": result.metrics.get("capture_staggering_applied", False),
        "constraints_were_binding": result.metrics.get("constraints_were_binding", False),
        "over_constrained": over_constrained,
    }


def build_results(case: dict) -> list[ScheduleResult]:
    """Run all three schedulers for one thermal limit setting."""

    stack = DieStack.from_config(case["stack"])
    access = AccessConfig.from_config(case["access"])
    tasks = build_tasks(case["tasks"])
    thermal_config = ThermalConfig.from_config(case["thermal"])
    voltage_config = VoltageConfig.from_config(case["voltage"])
    scheduler_config = case.get("scheduler", {})
    time_step_s = float(case["simulation"]["time_step_s"])
    clock_hz = float(case["simulation"]["clock_hz"])

    serial = SerialScheduler(
        stack=stack,
        access=access,
        thermal_model=RCThermalModel(thermal_config),
        voltage_model=EquivalentPdnModel(voltage_config),
        clock_hz=clock_hz,
        time_step_s=time_step_s,
    )
    greedy = BandwidthGreedyScheduler(
        stack=stack,
        access=access,
        thermal_model=RCThermalModel(thermal_config),
        voltage_model=EquivalentPdnModel(voltage_config),
        clock_hz=clock_hz,
        time_step_s=time_step_s,
    )
    ptv = PTVAwareScheduler(
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
    return [serial.schedule(tasks), greedy.schedule(tasks), ptv.schedule(tasks)]


def case_with_thermal_limit(base_case: dict, thermal_limit: float) -> dict:
    """Return a deep-copied stress case with a modified thermal limit."""

    ambient = float(base_case["thermal"]["ambient_temp_c"])
    if thermal_limit <= ambient:
        raise ValueError("thermal_limit must exceed ambient temperature")
    case = copy.deepcopy(base_case)
    case["thermal"]["max_temp_c"] = float(thermal_limit)
    return case


def is_over_constrained(results: list[ScheduleResult]) -> bool:
    """Return true when PTV-aware cannot avoid thermal violations at this limit."""

    for result in results:
        if result.scheduler_name == "ptv_aware":
            return int(result.metrics["temperature_violation_count"]) > 0
    raise ValueError("missing ptv_aware result")


def run(thermal_limits: tuple[float, ...] = THERMAL_LIMITS) -> dict[str, Path]:
    """Run the thermal-limit sweep and write summary CSV and SVG plots."""

    base_case = load_yaml(CONFIG_PATH)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    for thermal_limit in thermal_limits:
        case = case_with_thermal_limit(base_case, thermal_limit)
        results = build_results(case)
        over_constrained = is_over_constrained(results)
        for result in results:
            rows.append(summary_row(thermal_limit, result, over_constrained))

    summary_path = RESULT_DIR / "thermal_limit_sweep_summary.csv"
    write_dict_rows(summary_path, rows, SUMMARY_COLUMNS)
    outputs = {"thermal_limit_sweep_summary": summary_path}
    outputs.update(plot_thermal_limit_sweep(rows, RESULT_DIR))
    return outputs


if __name__ == "__main__":
    outputs = run()
    print("Thermal limit sweep completed.")
    for name, path in outputs.items():
        print(f"{name}: {path.relative_to(ROOT)}")
