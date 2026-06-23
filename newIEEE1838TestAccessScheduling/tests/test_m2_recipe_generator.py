from __future__ import annotations

import csv
from pathlib import Path

import pytest

from src.model import ModelValidationError, load_system_model
from src.recipes import RecipeGenerator, write_recipes_csv


CASE_PATH = Path("configs/cases/3d_stack_m1_example.json")


def test_m1_example_loads_and_validates() -> None:
    model = load_system_model(CASE_PATH)

    assert model.case_id == "3d_stack_m1_example"
    assert model.primary_die_id == "die0"
    assert model.die_path_to("die3") == ["die0", "die1", "die2", "die3"]


def test_access_setup_cost_increases_for_deeper_die() -> None:
    model = load_system_model(CASE_PATH)

    assert model.access_setup_bits("die3") > model.access_setup_bits("die2")
    assert model.access_setup_bits("die2") > model.access_setup_bits("die1")
    assert model.access_setup_bits("die1") > model.access_setup_bits("die0")


def test_recipe_generator_emits_expected_recipe_types() -> None:
    model = load_system_model(CASE_PATH)
    recipes = RecipeGenerator(model).generate_all()
    recipe_types = {recipe.recipe_type for recipe in recipes}

    assert {"S", "F", "B", "H", "I"} <= recipe_types
    assert any(recipe.target_id == "mem_die2_sram" and recipe.recipe_type == "B" for recipe in recipes)
    assert any(recipe.target_kind == "interconnect" and recipe.recipe_type == "I" for recipe in recipes)


def test_scannable_objects_have_multiple_candidates() -> None:
    model = load_system_model(CASE_PATH)
    recipes = RecipeGenerator(model).generate_all()
    by_target: dict[str, set[str]] = {}
    for recipe in recipes:
        if recipe.target_kind in {"core", "memory"}:
            by_target.setdefault(recipe.target_id, set()).add(recipe.recipe_type)

    assert by_target["core_die0_logic"] >= {"S", "F", "H"}
    assert by_target["core_die1_cpu"] >= {"S", "F", "H"}
    assert by_target["mem_die2_sram"] >= {"S", "F", "B", "H"}
    assert by_target["core_die3_accel"] >= {"S", "F", "B", "H"}


def test_fpp_variants_are_faster_than_serial_for_large_scan() -> None:
    model = load_system_model(CASE_PATH)
    recipes = RecipeGenerator(model).generate_all()
    accel_recipes = [recipe for recipe in recipes if recipe.target_id == "core_die3_accel"]
    serial_time = next(recipe.total_time_s for recipe in accel_recipes if recipe.recipe_type == "S")
    fpp_best = min(recipe.total_time_s for recipe in accel_recipes if recipe.recipe_type == "F")

    assert fpp_best < serial_time


def test_generated_csv_is_writable_and_parseable(tmp_path: Path) -> None:
    model = load_system_model(CASE_PATH)
    recipes = RecipeGenerator(model).generate_all()
    output = tmp_path / "m2_recipe_summary.csv"

    write_recipes_csv(recipes, output)

    with output.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == len(recipes)
    assert {"recipe_id", "recipe_type", "total_time_s", "thermal_risk"} <= set(rows[0])


def test_validation_rejects_bad_primary_reference(tmp_path: Path) -> None:
    bad_case = tmp_path / "bad_case.json"
    text = CASE_PATH.read_text(encoding="utf-8")
    text = text.replace('"primary_entry_die": "die0"', '"primary_entry_die": "die_missing"')
    bad_case.write_text(text, encoding="utf-8")

    with pytest.raises(ModelValidationError):
        load_system_model(bad_case)
