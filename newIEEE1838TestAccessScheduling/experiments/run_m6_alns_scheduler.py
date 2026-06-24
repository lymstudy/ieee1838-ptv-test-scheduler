from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.model import load_system_model
from src.recipes import read_recipe_rows_csv
from src.schedulers import (
    run_alns,
    write_alns_convergence_csv,
    write_alns_report_markdown,
    write_alns_schedule_csv,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run M6 ALNS scheduling with local repair.")
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
        default="results/schedules/m6_alns_schedule.csv",
        help="Output CSV path for the best ALNS schedule.",
    )
    parser.add_argument(
        "--convergence-output",
        default="results/tables/m6_alns_convergence.csv",
        help="Output CSV path for ALNS convergence history.",
    )
    parser.add_argument(
        "--report-output",
        default="results/reports/m6_alns_report.md",
        help="Output Markdown path for ALNS summary.",
    )
    parser.add_argument("--iterations", type=int, default=20, help="Number of ALNS iterations.")
    parser.add_argument("--destroy-fraction", type=float, default=0.35, help="Fraction of targets destroyed per iteration.")
    parser.add_argument("--seed", type=int, default=1838, help="Deterministic random seed.")
    parser.add_argument("--repair-time-limit-s", type=float, default=2.0, help="CP-SAT repair time limit per iteration.")
    parser.add_argument("--workers", type=int, default=8, help="CP-SAT worker count.")
    parser.add_argument(
        "--backend",
        choices=["ortools", "greedy"],
        default="ortools",
        help="Repair backend for local ALNS neighborhoods.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model = load_system_model(args.case)
    recipe_rows = read_recipe_rows_csv(args.recipes)
    result = run_alns(
        model,
        recipe_rows,
        iterations=args.iterations,
        destroy_fraction=args.destroy_fraction,
        seed=args.seed,
        repair_time_limit_s=args.repair_time_limit_s,
        workers=args.workers,
        backend=args.backend,
    )

    write_alns_schedule_csv(result, args.schedule_output)
    write_alns_convergence_csv(result, args.convergence_output)
    write_alns_report_markdown(result, args.report_output)

    print(f"case_id={model.case_id}")
    print(f"iterations={len(result.iterations)}")
    print(f"initial_makespan_s={result.initial.makespan_s:.9f}")
    print(f"best_makespan_s={result.best.makespan_s:.9f}")
    print(f"improvement_s={result.improvement_s:.9f}")
    print(f"improvement_percent={result.improvement_percent:.2f}")
    print(f"schedule_output={args.schedule_output}")
    print(f"convergence_output={args.convergence_output}")
    print(f"report_output={args.report_output}")


if __name__ == "__main__":
    main()
