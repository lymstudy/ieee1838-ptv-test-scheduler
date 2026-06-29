# --- NEW physically correct model ---
from .generator import (
    CompilationVariant,
    TaskGenerator,
    TestTask,
    rows_from_variants,
)

# --- OLD deprecated model (backward compat) ---
from .generator import RecipeGenerator, RecipePhase, TestAccessRecipe, write_recipe_phases_csv, write_recipes_csv
from .pruning import (
    ParetoPruningResult,
    dominates,
    pareto_prune,
    read_recipe_rows_csv,
    rows_from_recipes,
    write_pruning_summary_csv,
    write_pruning_report_markdown,
    write_recipe_rows_csv,
)

__all__ = [
    # NEW
    "CompilationVariant",
    "TaskGenerator",
    "TestTask",
    "rows_from_variants",
    # OLD (deprecated, backward compat)
    "ParetoPruningResult",
    "RecipeGenerator",
    "RecipePhase",
    "TestAccessRecipe",
    "dominates",
    "pareto_prune",
    "read_recipe_rows_csv",
    "rows_from_recipes",
    "write_pruning_summary_csv",
    "write_pruning_report_markdown",
    "write_recipe_phases_csv",
    "write_recipe_rows_csv",
    "write_recipes_csv",
]
