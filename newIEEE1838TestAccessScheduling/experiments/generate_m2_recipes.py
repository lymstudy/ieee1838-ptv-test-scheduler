from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.model import load_system_model
from src.recipes import RecipeGenerator, write_recipe_phases_csv, write_recipes_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate M2 Test Access Recipe candidates.")
    parser.add_argument(
        "--case",
        default="configs/cases/3d_stack_m1_example.json",
        help="Path to an M1 system model JSON file.",
    )
    parser.add_argument(
        "--output",
        default="results/tables/m2_recipe_summary_refined.csv",
        help="Output CSV path for refined generated recipes.",
    )
    parser.add_argument(
        "--phase-output",
        default="results/tables/m2_recipe_phase_summary.csv",
        help="Output CSV path for per-phase resource summary.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model = load_system_model(args.case)
    recipes = RecipeGenerator(model).generate_all()
    write_recipes_csv(recipes, args.output)
    write_recipe_phases_csv(recipes, args.phase_output)

    counts = Counter(recipe.recipe_type for recipe in recipes)
    output = Path(args.output)
    print(f"case_id={model.case_id}")
    print(f"recipes={len(recipes)}")
    print("recipe_type_counts=" + ",".join(f"{key}:{counts[key]}" for key in sorted(counts)))
    print(f"output={output}")
    print(f"phase_output={Path(args.phase_output)}")


if __name__ == "__main__":
    main()
