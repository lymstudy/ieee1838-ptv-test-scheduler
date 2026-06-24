from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.model import load_system_model
from src.recipes import read_recipe_rows_csv
from src.schedulers import greedy_schedule, write_schedule_csv, write_schedule_report_markdown


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run M4 greedy scheduling for Pareto-pruned Test Access Recipes.")
    parser.add_argument(
        "--case",
        default="configs/cases/3d_stack_m1_example.json",
        help="Path to an M1 system model JSON file.",
    )
    parser.add_argument(
        "--recipes",
        default="results/tables/m3_recipe_pareto.csv",
        help="Path to Pareto-pruned recipe CSV from M3.",
    )
    parser.add_argument(
        "--schedule-output",
        default="results/schedules/m4_greedy_schedule.csv",
        help="Output CSV path for scheduled phases.",
    )
    parser.add_argument(
        "--report-output",
        default="results/reports/m4_greedy_schedule_report.md",
        help="Output Markdown path for schedule summary and Gantt preview.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model = load_system_model(args.case)
    recipe_rows = read_recipe_rows_csv(args.recipes)
    result = greedy_schedule(model, recipe_rows)

    write_schedule_csv(result, args.schedule_output)
    write_schedule_report_markdown(result, args.report_output)

    print(f"case_id={model.case_id}")
    print(f"selected_recipes={len(result.selected_rows)}")
    print(f"scheduled_phases={len(result.phases)}")
    print(f"makespan_s={result.makespan_s:.9f}")
    print(f"peak_power_w={result.peak_power_w:.6f}")
    print(f"max_fpp_lanes_used={result.max_fpp_lanes_used}")
    print(f"schedule_output={args.schedule_output}")
    print(f"report_output={args.report_output}")


if __name__ == "__main__":
    main()
