from __future__ import annotations

from experiments.generate_m18_pressure_cases import build_shared_bist_pressure_case
from experiments.run_m18_pressure_study import best_joint_gain, run_case, selected_type_counts
from src.model import SystemModel


def test_m18_generated_case_uses_one_shared_bist_engine() -> None:
    payload = build_shared_bist_pressure_case("unit_m18_pressure", "3d_stack", 8)
    model = SystemModel(payload)
    model.validate()

    groups = payload["resource_groups"]["bist_engine_groups"]

    assert len(groups) == 1
    assert groups[0]["group_id"] == "shared_m18_bist_engine"
    assert groups[0]["capacity"] == 1
    assert len(groups[0]["members"]) == 8
    assert all(obj["required_resources"]["bist_engine"] == "shared_m18_bist_engine" for obj in payload["test_objects"])


def test_m18_pressure_case_gives_joint_selection_clear_gain() -> None:
    payload = build_shared_bist_pressure_case("unit_m18_pressure", "3d_stack", 8)
    model = SystemModel(payload)
    model.validate()

    rows = run_case(model, time_limit_s=3.0)
    fixed = next(row for row in rows if row["method_id"] == "fixed_fastest")
    best_gain = best_joint_gain(rows)

    assert fixed["selected_recipe_types"] == "B:8"
    assert best_gain > 40.0
    assert any(row["method_family"] == "joint" and row["selected_recipe_types"] == "B:4;F:4" for row in rows)


def test_m18_selected_type_counts_parses_recipe_mix() -> None:
    counts = selected_type_counts("B:4;F:3;H:1")

    assert counts == {"B": 4, "F": 3, "H": 1, "S": 0}
