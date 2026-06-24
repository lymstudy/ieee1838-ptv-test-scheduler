from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.model import load_system_model
from src.recipes import (
    RecipeGenerator,
    pareto_prune,
    rows_from_recipes,
    write_pruning_summary_csv,
    write_pruning_report_markdown,
    write_recipe_rows_csv,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run M3 Pareto pruning for Test Access Recipes.")
    parser.add_argument(
        "--case",
        default="configs/cases/3d_stack_m1_example.json",
        help="Path to an M1 system model JSON file.",
    )
    parser.add_argument(
        "--pruned-output",
        default="results/tables/m3_recipe_pareto.csv",
        help="Output CSV path for Pareto-pruned recipes.",
    )
    parser.add_argument(
        "--summary-output",
        default="results/reports/m3_pruning_summary.csv",
        help="Output CSV path for per-target pruning summary.",
    )
    parser.add_argument(
        "--report-output",
        default="results/reports/m3_pruning_report.md",
        help="Output Markdown path for the pruning report.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model = load_system_model(args.case)
    recipe_rows = rows_from_recipes(RecipeGenerator(model).generate_all())
    result = pareto_prune(recipe_rows)

    write_recipe_rows_csv(result.kept_rows, args.pruned_output)
    write_pruning_summary_csv(result.summary_rows, args.summary_output)
    write_pruning_report_markdown(result, args.report_output)

    before_counts = Counter(str(row["recipe_type"]) for row in recipe_rows)
    after_counts = Counter(str(row["recipe_type"]) for row in result.kept_rows)
    print(f"case_id={model.case_id}")
    print(f"recipes_before={len(recipe_rows)}")
    print(f"recipes_after={len(result.kept_rows)}")
    print(f"recipes_removed={len(result.removed_rows)}")
    print("before_type_counts=" + ",".join(f"{key}:{before_counts[key]}" for key in sorted(before_counts)))
    print("after_type_counts=" + ",".join(f"{key}:{after_counts[key]}" for key in sorted(after_counts)))
    print(f"pruned_output={args.pruned_output}")
    print(f"summary_output={args.summary_output}")
    print(f"report_output={args.report_output}")


if __name__ == "__main__":
    main()
