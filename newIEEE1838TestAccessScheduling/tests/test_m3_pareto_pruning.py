from __future__ import annotations

import csv
from pathlib import Path

from src.model import load_system_model
from src.recipes import (
    RecipeGenerator,
    dominates,
    pareto_prune,
    rows_from_recipes,
    write_pruning_summary_csv,
    write_recipe_rows_csv,
)


CASE_PATH = Path("configs/cases/3d_stack_m1_example.json")


def _m2_rows() -> list[dict[str, object]]:
    model = load_system_model(CASE_PATH)
    return rows_from_recipes(RecipeGenerator(model).generate_all())


def test_pareto_pruning_reduces_candidate_count() -> None:
    rows = _m2_rows()
    result = pareto_prune(rows)

    assert len(rows) == 32
    assert len(result.kept_rows) < len(rows)
    assert len(result.removed_rows) == len(rows) - len(result.kept_rows)


def test_each_target_keeps_at_least_one_recipe() -> None:
    rows = _m2_rows()
    result = pareto_prune(rows)
    before_targets = {row["target_id"] for row in rows}
    after_targets = {row["target_id"] for row in result.kept_rows}

    assert before_targets == after_targets


def test_no_kept_recipe_is_dominated() -> None:
    result = pareto_prune(_m2_rows())

    for candidate in result.kept_rows:
        same_target = [row for row in result.kept_rows if row["target_id"] == candidate["target_id"]]
        assert not any(dominates(other, candidate) for other in same_target)


def test_pareto_keeps_resource_tradeoffs() -> None:
    result = pareto_prune(_m2_rows())
    core0 = [row for row in result.kept_rows if row["target_id"] == "core_die0_logic"]
    recipe_ids = {row["recipe_id"] for row in core0}

    assert "S_core_die0_logic_serial" in recipe_ids
    assert "F_core_die0_logic_lane1" in recipe_ids
    assert "F_core_die0_logic_lane2" in recipe_ids


def test_dominated_hybrid_variant_is_removed_with_reason() -> None:
    result = pareto_prune(_m2_rows())
    removed_by_id = {row["recipe_id"]: row for row in result.removed_rows}

    removed = removed_by_id["H_core_die0_logic_lane1"]
    assert removed["dominated_by"] == "F_core_die0_logic_lane1"
    assert "total_time_s" in str(removed["dominance_reason"])


def test_custom_dominance_uses_serial_resource_time() -> None:
    rows = [
        {
            "recipe_id": "a",
            "target_id": "target",
            "target_kind": "core",
            "recipe_type": "S",
            "total_time_s": 10.0,
            "access_time_s": 3.0,
            "data_time_s": 2.0,
            "readback_time_s": 0.0,
            "peak_power_w": 1.0,
            "thermal_risk": 1.0,
            "serial_access_required": True,
            "fpp_lanes_required": 0,
        },
        {
            "recipe_id": "b",
            "target_id": "target",
            "target_kind": "core",
            "recipe_type": "S",
            "total_time_s": 10.0,
            "access_time_s": 4.0,
            "data_time_s": 2.0,
            "readback_time_s": 0.0,
            "peak_power_w": 1.0,
            "thermal_risk": 1.0,
            "serial_access_required": True,
            "fpp_lanes_required": 0,
        },
    ]

    result = pareto_prune(rows)

    assert [row["recipe_id"] for row in result.kept_rows] == ["a"]
    assert result.removed_rows[0]["dominated_by"] == "a"


def test_m3_outputs_are_writable_and_parseable(tmp_path: Path) -> None:
    result = pareto_prune(_m2_rows())
    pruned_output = tmp_path / "m3_recipe_pruned.csv"
    summary_output = tmp_path / "m3_pruning_summary.csv"

    write_recipe_rows_csv(result.kept_rows, pruned_output)
    write_pruning_summary_csv(result.summary_rows, summary_output)

    with pruned_output.open("r", encoding="utf-8", newline="") as handle:
        pruned_rows = list(csv.DictReader(handle))
    with summary_output.open("r", encoding="utf-8", newline="") as handle:
        summary_rows = list(csv.DictReader(handle))

    assert len(pruned_rows) == len(result.kept_rows)
    assert len(summary_rows) == len({row["target_id"] for row in _m2_rows()})
    assert "serial_resource_time_s" in pruned_rows[0]
