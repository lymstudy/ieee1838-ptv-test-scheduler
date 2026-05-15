"""Sweep deterministic synthetic workload scale."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

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
from src.visualize.sweep import plot_workload_scale_sweep
from src.workload.synthetic import DENSITY_ORDER, expected_task_count, generate_synthetic_case


RESULT_DIR = ROOT / "results" / "sweeps" / "workload_scale"
DIE_COUNTS = (4, 8, 12)
TASK_DENSITIES = DENSITY_ORDER
SUMMARY_COLUMNS = [
    "die_count",
    "task_density",
    "num_tasks",
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


def write_dict_rows(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    """Write dictionaries to CSV with a stable column order."""

    if not rows:
        raise ValueError("cannot write an empty CSV")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_results(case: dict) -> list[ScheduleResult]:
    """Run all three schedulers for one generated workload."""

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


def is_over_constrained(results: list[ScheduleResult]) -> bool:
    """Return true when PTV-aware cannot avoid thermal violations for this workload."""

    for result in results:
        if result.scheduler_name == "ptv_aware":
            return int(result.metrics["temperature_violation_count"]) > 0
    raise ValueError("missing ptv_aware result")


def summary_row(
    die_count: int,
    task_density: str,
    num_tasks: int,
    result: ScheduleResult,
    over_constrained: bool,
) -> dict:
    """Return one workload-scale sweep row."""

    return {
        "die_count": die_count,
        "task_density": task_density,
        "num_tasks": num_tasks,
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


def run(
    die_counts: tuple[int, ...] = DIE_COUNTS,
    task_densities: tuple[str, ...] = TASK_DENSITIES,
) -> dict[str, Path]:
    """Run the workload-scale sweep and write summary CSV and SVG plots."""

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for die_count in die_counts:
        for task_density in task_densities:
            case = generate_synthetic_case(die_count, task_density)
            num_tasks = expected_task_count(die_count, task_density)
            if len(case["tasks"]) != num_tasks:
                raise ValueError("generated task count does not match expected count")
            results = build_results(case)
            over_constrained = is_over_constrained(results)
            for result in results:
                rows.append(summary_row(die_count, task_density, num_tasks, result, over_constrained))

    summary_path = RESULT_DIR / "workload_scale_summary.csv"
    write_dict_rows(summary_path, rows, SUMMARY_COLUMNS)
    outputs = {"workload_scale_summary": summary_path}
    outputs.update(plot_workload_scale_sweep(rows, RESULT_DIR))
    return outputs


if __name__ == "__main__":
    outputs = run()
    print("Workload scale sweep completed.")
    for name, path in outputs.items():
        print(f"{name}: {path.relative_to(ROOT)}")
