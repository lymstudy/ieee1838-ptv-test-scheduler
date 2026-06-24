from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.model import load_system_model
from src.recipes import read_recipe_rows_csv
from src.schedulers import refine_schedule, write_refined_schedule_csv, write_refinement_report_markdown


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run M5 constrained schedule refinement.")
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
        default="results/schedules/m5_refined_schedule.csv",
        help="Output CSV path for the refined scheduled phases.",
    )
    parser.add_argument(
        "--report-output",
        default="results/reports/m5_refinement_report.md",
        help="Output Markdown path for M5 refinement summary.",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=20,
        help="Maximum number of accepted local refinement moves.",
    )
    parser.add_argument(
        "--enable-recipe-moves",
        action="store_true",
        help="Also try single-target recipe replacement moves after order refinement.",
    )
    parser.add_argument(
        "--backend",
        choices=["auto", "ortools", "local"],
        default="auto",
        help="M5 backend. auto uses OR-Tools when installed, otherwise local refinement.",
    )
    parser.add_argument(
        "--time-limit-s",
        type=float,
        default=10.0,
        help="OR-Tools CP-SAT solver time limit in seconds.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="OR-Tools CP-SAT worker count.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model = load_system_model(args.case)
    recipe_rows = read_recipe_rows_csv(args.recipes)
    result = refine_schedule(
        model,
        recipe_rows,
        max_iterations=args.max_iterations,
        enable_recipe_moves=args.enable_recipe_moves,
        backend=args.backend,
        time_limit_s=args.time_limit_s,
        workers=args.workers,
    )

    write_refined_schedule_csv(result, args.schedule_output)
    write_refinement_report_markdown(result, args.report_output)

    print(f"case_id={model.case_id}")
    print(f"baseline_m4_makespan_s={result.baseline.makespan_s:.9f}")
    print(f"refined_m5_makespan_s={result.refined.makespan_s:.9f}")
    print(f"improvement_s={result.improvement_s:.9f}")
    print(f"improvement_percent={result.improvement_percent:.2f}")
    print(f"accepted_moves={len(result.moves)}")
    print(f"backend={result.backend}")
    if result.solve_info is not None:
        print(f"cp_sat_status={result.solve_info.status_name}")
        print(f"cp_sat_wall_time_s={result.solve_info.wall_time_s:.6f}")
    print(f"schedule_output={args.schedule_output}")
    print(f"report_output={args.report_output}")


if __name__ == "__main__":
    main()
