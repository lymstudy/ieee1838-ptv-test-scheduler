from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from src.model import ModelValidationError, load_system_model
from src.recipes import RecipeGenerator, write_recipe_phases_csv, write_recipes_csv


CASE_PATH = Path("configs/cases/3d_stack_m1_example.json")


def _recipes():
    model = load_system_model(CASE_PATH)
    return RecipeGenerator(model).generate_all()


def _recipe(recipe_id: str):
    return next(recipe for recipe in _recipes() if recipe.recipe_id == recipe_id)


def _phases(recipe_id: str) -> list[dict[str, object]]:
    return json.loads(_recipe(recipe_id).phase_resources)


def test_m1_example_loads_and_validates() -> None:
    model = load_system_model(CASE_PATH)

    assert model.case_id == "3d_stack_m1_example"
    assert model.primary_die_id == "die0"
    assert model.die_path_to("die3") == ["die0", "die1", "die2", "die3"]
    assert model.layer_conduction_factor("thermal_die2") > 1.0


def test_access_setup_cost_increases_for_deeper_die() -> None:
    model = load_system_model(CASE_PATH)

    assert model.access_setup_bits("die3") > model.access_setup_bits("die2")
    assert model.access_setup_bits("die2") > model.access_setup_bits("die1")
    assert model.access_setup_bits("die1") > model.access_setup_bits("die0")


def test_recipe_generator_emits_expected_recipe_types() -> None:
    recipes = _recipes()
    recipe_types = {recipe.recipe_type for recipe in recipes}

    assert {"S", "F", "B", "H", "I"} <= recipe_types
    assert any(recipe.target_id == "mem_die2_sram" and recipe.recipe_type == "B" for recipe in recipes)
    assert any(recipe.target_kind == "interconnect" and recipe.recipe_type == "I" for recipe in recipes)


def test_scannable_objects_have_multiple_candidates() -> None:
    recipes = _recipes()
    by_target: dict[str, set[str]] = {}
    for recipe in recipes:
        if recipe.target_kind in {"core", "memory"}:
            by_target.setdefault(recipe.target_id, set()).add(recipe.recipe_type)

    assert by_target["core_die0_logic"] >= {"S", "F", "H"}
    assert by_target["core_die1_cpu"] >= {"S", "F", "H"}
    assert by_target["mem_die2_sram"] >= {"S", "F", "B", "H"}
    assert by_target["core_die3_accel"] >= {"S", "F", "B", "H"}


def test_fpp_variants_are_faster_than_serial_for_large_scan() -> None:
    recipes = _recipes()
    accel_recipes = [recipe for recipe in recipes if recipe.target_id == "core_die3_accel"]
    serial_time = next(recipe.total_time_s for recipe in accel_recipes if recipe.recipe_type == "S")
    fpp_best = min(recipe.total_time_s for recipe in accel_recipes if recipe.recipe_type == "F")

    assert fpp_best < serial_time


def test_generated_csv_is_writable_and_parseable(tmp_path: Path) -> None:
    recipes = _recipes()
    output = tmp_path / "m2_recipe_summary.csv"
    phase_output = tmp_path / "m2_recipe_phase_summary.csv"

    write_recipes_csv(recipes, output)
    write_recipe_phases_csv(recipes, phase_output)

    with output.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    with phase_output.open("r", encoding="utf-8", newline="") as handle:
        phase_rows = list(csv.DictReader(handle))

    assert len(rows) == len(recipes)
    assert {"recipe_id", "recipe_type", "total_time_s", "thermal_risk", "thermal_load", "lane_occupancy", "phase_resources"} <= set(rows[0])
    assert len(phase_rows) > len(recipes)
    assert {"phase_name", "duration_s", "serial_required", "fpp_lanes_required"} <= set(phase_rows[0])


def test_f_recipe_has_phase_level_serial_and_fpp_semantics() -> None:
    recipe = _recipe("F_core_die0_logic_lane1")
    phases = _phases(recipe.recipe_id)
    by_name = {phase["phase_name"]: phase for phase in phases}
    config_names = {"CONFIG_ACCESS_PATH", "CONFIG_FPP", "CONFIG_SCAN_OR_DWR_MODE"}

    assert recipe.test_method == "ATPG_SCAN"
    assert recipe.access_mechanism == "FPP_PARALLEL"
    assert recipe.test_endpoint == "internal_scan"
    assert recipe.fpp_time_s > 0
    assert recipe.lane_occupancy == pytest.approx(recipe.fpp_time_s * recipe.max_fpp_lanes_required)
    assert recipe.serial_time_s == pytest.approx(
        sum(float(phase["duration_s"]) for phase in phases if phase["phase_name"] in config_names)
    )
    assert by_name["FPP_SHIFT_IN"]["serial_required"] is False
    assert by_name["FPP_SHIFT_OUT"]["serial_required"] is False
    assert by_name["FPP_SHIFT_IN"]["fpp_lanes_required"] == 1
    assert by_name["FPP_SHIFT_OUT"]["fpp_lanes_required"] == 1


def test_b_recipe_distinguishes_lbist_and_mbist_phase_resources() -> None:
    memory_recipe = _recipe("B_mem_die2_sram_local_bist")
    core_recipe = _recipe("B_core_die3_accel_local_bist")
    model = load_system_model(CASE_PATH)
    memory_phases = {phase["phase_name"]: phase for phase in _phases(memory_recipe.recipe_id)}
    setup_bits = model.access_setup_bits("die2")
    readout_bits = 128

    assert memory_recipe.test_method == "MBIST"
    assert memory_recipe.bist_type == "MBIST"
    assert core_recipe.test_method == "LBIST"
    assert core_recipe.bist_type == "LBIST"
    assert memory_phases["CONFIG_BIST"]["serial_required"] is True
    assert memory_phases["LOCAL_BIST_RUN"]["serial_required"] is False
    assert memory_phases["LOCAL_BIST_RUN"]["fpp_lanes_required"] == 0
    assert memory_phases["READ_BIST_RESULT"]["serial_required"] is True
    assert memory_recipe.readback_time_s == pytest.approx(model.serial_time_s(setup_bits * 0.5 + readout_bits))


def test_h_recipe_adds_serial_status_readback() -> None:
    f_recipe = _recipe("F_core_die0_logic_lane1")
    h_recipe = _recipe("H_core_die0_logic_lane1")

    assert "SERIAL_STATUS_READBACK" not in f_recipe.phases
    assert "SERIAL_STATUS_READBACK" in h_recipe.phases
    assert h_recipe.serial_time_s > f_recipe.serial_time_s


def test_i_recipe_keeps_dwr_extest_semantics() -> None:
    recipe = _recipe("I_link_die1_die2_serial_extest")
    phases = {phase["phase_name"]: phase for phase in _phases(recipe.recipe_id)}

    assert recipe.test_method == "EXTEST"
    assert recipe.access_mechanism == "DWR_EXTEST"
    assert recipe.test_endpoint == "interconnect_extest"
    assert phases["DWR_SHIFT_IN"]["serial_required"] is True
    assert phases["DWR_CAPTURE"]["serial_required"] is False
    assert phases["DWR_SHIFT_OUT"]["serial_required"] is True


def test_validation_rejects_bad_primary_reference(tmp_path: Path) -> None:
    bad_case = tmp_path / "bad_case.json"
    text = CASE_PATH.read_text(encoding="utf-8")
    text = text.replace('"primary_entry_die": "die0"', '"primary_entry_die": "die_missing"')
    bad_case.write_text(text, encoding="utf-8")

    with pytest.raises(ModelValidationError):
        load_system_model(bad_case)
