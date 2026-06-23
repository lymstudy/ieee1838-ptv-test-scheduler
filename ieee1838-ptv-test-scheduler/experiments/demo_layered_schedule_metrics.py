"""Demonstrate B3.1.5 layered schedule metrics evaluation."""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.demo_access_time_scheduler import create_demo_config, expand_demo_phases
from src.layered import AccessTimeAwareScheduler, LayeredScheduleEvaluator, LayeredScheduleMetrics


DEFAULT_RESULT_DIR = ROOT / "results" / "layered_schedule_metrics"


def prepare_output_dir(output_dir: Path | str) -> Path:
    """Create and return the output directory, raising a clear error on failure."""

    path = Path(output_dir)
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RuntimeError(f"failed to create output directory '{path}': {exc}") from exc
    return path


def metric_rows(metrics: LayeredScheduleMetrics) -> list[dict[str, str | float | int]]:
    """Flatten metrics into name/value CSV rows."""

    data = asdict(metrics)
    rows: list[dict[str, str | float | int]] = []
    for key, value in data.items():
        if isinstance(value, dict):
            continue
        rows.append({"metric": key, "value": value})
    for key, value in metrics.resource_busy_time.items():
        rows.append({"metric": f"resource_busy_time.{key}", "value": value})
    for key, value in metrics.phase_type_time.items():
        rows.append({"metric": f"phase_type_time.{key}", "value": value})
    return rows


def write_csv(path: Path, rows: list[dict[str, str | float | int]]) -> None:
    """Write metrics rows to CSV."""

    if not rows:
        raise ValueError("cannot write empty metrics summary")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["metric", "value"])
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, metrics: LayeredScheduleMetrics) -> None:
    """Write a Markdown summary for layered schedule metrics."""

    lines = [
        "# Layered Schedule Metrics Summary",
        "",
        "This B3.1.5 demo evaluates phase-level access/resource behavior only.",
        "It does not implement thermal or voltage prediction and is not a complete IEEE 1838 framework.",
        "",
        "## Scalar Metrics",
        "",
        "| metric | value |",
        "| --- | ---: |",
    ]
    for row in metric_rows(metrics):
        lines.append(f"| {row['metric']} | {row['value']} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_metrics(metrics: LayeredScheduleMetrics) -> None:
    """Print a compact metrics summary."""

    print("Layered schedule metrics")
    print(f"  total_time: {metrics.total_time:.9g}")
    print(f"  phase_count: {metrics.phase_count}")
    print(f"  ptap_utilization: {metrics.ptap_utilization:.4f}")
    print(f"  fpp_utilization: {metrics.fpp_utilization:.4f}")
    print(f"  access_overhead_ratio: {metrics.access_overhead_ratio:.4f}")
    print(f"  max_parallel_phases: {metrics.max_parallel_phases}")
    print(f"  average_parallelism: {metrics.average_parallelism:.4f}")


def run(output_dir: Path | str = DEFAULT_RESULT_DIR) -> dict[str, Path]:
    """Run the layered schedule metrics demo and write summary files."""

    result_dir = prepare_output_dir(output_dir)
    config = create_demo_config()
    phases = expand_demo_phases(config)
    scheduler = AccessTimeAwareScheduler(total_fpp_lanes=config.fpp_lane_count)
    schedule = scheduler.schedule(phases)
    metrics = LayeredScheduleEvaluator.evaluate(schedule, total_fpp_lanes=config.fpp_lane_count)

    csv_path = result_dir / "metrics_summary.csv"
    markdown_path = result_dir / "metrics_summary.md"
    write_csv(csv_path, metric_rows(metrics))
    write_markdown(markdown_path, metrics)
    print_metrics(metrics)

    return {
        "metrics_summary_csv": csv_path,
        "metrics_summary_md": markdown_path,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_RESULT_DIR,
        help=f"directory for demo outputs (default: {DEFAULT_RESULT_DIR})",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Run the demo from the command line."""

    args = parse_args(argv)
    outputs = run(args.output_dir)
    for output_path in outputs.values():
        print(output_path)


if __name__ == "__main__":
    main()
