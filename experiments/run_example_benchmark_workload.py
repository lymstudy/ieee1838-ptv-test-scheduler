"""Run the schema-level example benchmark-derived workload."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

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
from src.visualize.gantt import plot_gantt
from src.workload.benchmark_adapter import generate_case_from_benchmark, load_benchmark_stats


STATS_PATH = ROOT / "benchmarks" / "example_benchmark_stats.yaml"
DEFAULT_RESULT_DIR = ROOT / "results" / "benchmarks" / "example"
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
TASK_SUMMARY_COLUMNS = [
    "task_id",
    "task_type",
    "die_id",
    "duration_cycles",
    "duration_s",
    "power_w",
    "fpp_lanes_required",
    "dwr_segment",
    "is_capture_phase",
    "dependencies",
]


def prepare_output_dir(output_dir: Path | str) -> Path:
    """Create and return the output directory, raising a clear error on failure."""

    path = Path(output_dir)
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RuntimeError(f"failed to create output directory '{path}': {exc}") from exc
    return path


def write_dict_rows(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    """Write dictionaries to CSV with a stable column order."""

    if not rows:
        raise ValueError("cannot write an empty CSV")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames or list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def summary_row(result: ScheduleResult) -> dict:
    """Return one scheduler metric row."""

    return {
        "scheduler_name": result.scheduler_name,
        "tat": result.tat,
        "peak_temperature": result.peak_temperature,
        "peak_ir_drop": result.peak_ir_drop,
        "temperature_violation_count": result.metrics["temperature_violation_count"],
        "voltage_violation_count": result.metrics["voltage_violation_count"],
        "num_tasks": len(result.entries),
        "average_parallelism": result.metrics.get("average_parallelism", 0.0),
        "max_parallelism": result.metrics.get("max_parallelism", 0),
        "fpp_lane_utilization_average": result.metrics.get("fpp_lane_utilization_average", 0.0),
        "dummy_cycle_count": result.metrics.get("dummy_cycle_count", 0),
        "dummy_time_total": result.metrics.get("dummy_time_total", 0.0),
        "capture_staggering_applied": result.metrics.get("capture_staggering_applied", False),
        "constraints_were_binding": result.metrics.get("constraints_were_binding", False),
    }


def task_summary_row(task: TestTask, clock_hz: float) -> dict:
    """Return one generated benchmark task summary row."""

    return {
        "task_id": task.id,
        "task_type": task.task_type.value,
        "die_id": task.die_id,
        "duration_cycles": task.duration_cycles,
        "duration_s": task.duration_s(clock_hz),
        "power_w": task.power_w,
        "fpp_lanes_required": task.fpp_lanes_required if task.fpp_lanes_required is not None else "",
        "dwr_segment": task.dwr_segment or "",
        "is_capture_phase": task.is_capture_phase,
        "dependencies": ";".join(task.dependencies),
    }


def build_results(case: dict) -> tuple[tuple[TestTask, ...], list[ScheduleResult]]:
    """Build model objects and run the three schedulers."""

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
    return tasks, [serial.schedule(tasks), greedy.schedule(tasks), ptv.schedule(tasks)]


def write_scheduler_outputs(result: ScheduleResult, prefix: str, result_dir: Path) -> dict[str, Path]:
    """Write schedule CSV and Gantt chart for one scheduler."""

    schedule_path = result_dir / f"{prefix}_schedule.csv"
    write_dict_rows(schedule_path, [entry.to_row() for entry in result.entries])

    gantt_path = result_dir / f"{prefix}_gantt.svg"
    plot_gantt(result, gantt_path)
    return {f"{prefix}_schedule": schedule_path, f"{prefix}_gantt": gantt_path}


def run(output_dir: Path | str = DEFAULT_RESULT_DIR) -> dict[str, Path]:
    """Run the example benchmark-statistics workload and write outputs."""

    stats = load_benchmark_stats(STATS_PATH)
    case = generate_case_from_benchmark(stats)
    tasks, results = build_results(case)
    clock_hz = float(case["simulation"]["clock_hz"])

    result_dir = prepare_output_dir(output_dir)
    outputs: dict[str, Path] = {}

    task_summary_path = result_dir / "benchmark_task_summary.csv"
    write_dict_rows(
        task_summary_path,
        [task_summary_row(task, clock_hz) for task in tasks],
        fieldnames=TASK_SUMMARY_COLUMNS,
    )
    outputs["benchmark_task_summary"] = task_summary_path

    prefix_by_scheduler = {
        "serial_ieee1838_style": "serial",
        "bandwidth_greedy": "greedy",
        "ptv_aware": "ptv",
    }
    for result in results:
        outputs.update(
            write_scheduler_outputs(result, prefix_by_scheduler[result.scheduler_name], result_dir)
        )

    summary_path = result_dir / "scheduler_metrics_summary.csv"
    write_dict_rows(summary_path, [summary_row(result) for result in results], fieldnames=SUMMARY_COLUMNS)
    outputs["scheduler_metrics_summary"] = summary_path
    outputs.update(plot_basic_comparisons(results, result_dir))
    return outputs


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_RESULT_DIR,
        help=f"directory for benchmark outputs (default: {DEFAULT_RESULT_DIR})",
    )
    return parser.parse_args(argv)


def display_path(path: Path) -> str:
    """Return a readable path relative to the repo when possible."""

    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def main(argv: list[str] | None = None) -> None:
    """Run the example benchmark workload from the command line."""

    args = parse_args(argv)
    outputs = run(args.output_dir)
    print("Example benchmark-derived workload experiment completed.")
    for name, path in outputs.items():
        print(f"{name}: {display_path(path)}")


if __name__ == "__main__":
    main()
