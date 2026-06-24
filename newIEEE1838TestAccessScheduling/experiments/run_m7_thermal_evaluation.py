from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluators import (
    evaluate_schedule_thermal,
    read_schedule_csv,
    write_hotspots_csv,
    write_temperature_trace_csv,
    write_thermal_report_markdown,
    write_thermal_summary_csv,
)
from src.model import load_system_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run M7 thermal proxy evaluation for schedule CSV files.")
    parser.add_argument(
        "--case",
        default="configs/cases/3d_stack_m1_example.json",
        help="Path to an M1 system model JSON file.",
    )
    parser.add_argument(
        "--schedule",
        action="append",
        nargs=2,
        metavar=("ID", "CSV"),
        help="Schedule ID and CSV path. Can be repeated.",
    )
    parser.add_argument(
        "--temperature-output",
        default="results/tables/m7_temperature_trace.csv",
        help="Output CSV path for temperature samples.",
    )
    parser.add_argument(
        "--hotspot-output",
        default="results/tables/m7_hotspots.csv",
        help="Output CSV path for hotspot summary.",
    )
    parser.add_argument(
        "--summary-output",
        default="results/tables/m7_thermal_summary.csv",
        help="Output CSV path for per-schedule thermal summary.",
    )
    parser.add_argument(
        "--report-output",
        default="results/reports/m7_thermal_report.md",
        help="Output Markdown path for M7 thermal report.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model = load_system_model(args.case)
    schedules = args.schedule or [
        ("m4_greedy", "results/schedules/m4_greedy_schedule.csv"),
        ("m5_cpsat", "results/schedules/m5_refined_schedule.csv"),
        ("m6_alns", "results/schedules/m6_alns_schedule.csv"),
    ]

    results = []
    for schedule_id, schedule_path in schedules:
        phases = read_schedule_csv(schedule_path)
        results.append(evaluate_schedule_thermal(model, phases, schedule_id))

    write_temperature_trace_csv(results, args.temperature_output)
    write_hotspots_csv(results, args.hotspot_output)
    write_thermal_summary_csv(results, args.summary_output)
    write_thermal_report_markdown(results, args.report_output)

    print(f"case_id={model.case_id}")
    for result in results:
        print(
            f"schedule={result.schedule_id},makespan_s={result.makespan_s:.9f},"
            f"peak_temperature_c={result.peak_temperature_c:.6f},peak_region={result.peak_region}"
        )
    print(f"temperature_output={args.temperature_output}")
    print(f"hotspot_output={args.hotspot_output}")
    print(f"summary_output={args.summary_output}")
    print(f"report_output={args.report_output}")


if __name__ == "__main__":
    main()
