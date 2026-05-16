"""Run the manually specified realistic UART statistics workload."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.run_example_benchmark_workload import (
    SUMMARY_COLUMNS,
    TASK_SUMMARY_COLUMNS,
    build_results,
    summary_row,
    task_summary_row,
    write_dict_rows,
)
from src.scheduler.base import ScheduleResult
from src.visualize.comparison import plot_basic_comparisons
from src.visualize.gantt import plot_gantt
from src.workload.benchmark_adapter import generate_case_from_benchmark, load_benchmark_stats


STATS_PATH = ROOT / "benchmarks" / "realistic_uart_stats.yaml"
RESULT_DIR = ROOT / "results" / "benchmarks" / "realistic_uart"


def write_scheduler_outputs(result: ScheduleResult, prefix: str) -> dict[str, Path]:
    """Write schedule CSV and Gantt chart for one scheduler."""

    schedule_path = RESULT_DIR / f"{prefix}_schedule.csv"
    write_dict_rows(schedule_path, [entry.to_row() for entry in result.entries])

    gantt_path = RESULT_DIR / f"{prefix}_gantt.svg"
    plot_gantt(result, gantt_path)
    return {f"{prefix}_schedule": schedule_path, f"{prefix}_gantt": gantt_path}


def run() -> dict[str, Path]:
    """Run the realistic UART statistics workload and write outputs."""

    stats = load_benchmark_stats(STATS_PATH)
    case = generate_case_from_benchmark(stats)
    tasks, results = build_results(case)
    clock_hz = float(case["simulation"]["clock_hz"])

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, Path] = {}

    task_summary_path = RESULT_DIR / "benchmark_task_summary.csv"
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
        outputs.update(write_scheduler_outputs(result, prefix_by_scheduler[result.scheduler_name]))

    summary_path = RESULT_DIR / "scheduler_metrics_summary.csv"
    write_dict_rows(summary_path, [summary_row(result) for result in results], fieldnames=SUMMARY_COLUMNS)
    outputs["scheduler_metrics_summary"] = summary_path
    outputs.update(plot_basic_comparisons(results, RESULT_DIR))
    return outputs


if __name__ == "__main__":
    outputs = run()
    print("Realistic UART statistics workload experiment completed.")
    for name, path in outputs.items():
        print(f"{name}: {path.relative_to(ROOT)}")
