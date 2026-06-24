from __future__ import annotations

from functools import lru_cache

import pytest

from src.model import load_system_model
from src.recipes import RecipeGenerator, pareto_prune, rows_from_recipes
from src.schedulers import refine_schedule, solve_cpsat_schedule, write_refined_schedule_csv, write_refinement_report_markdown


CASE_PATH = "configs/cases/3d_stack_m1_example.json"


def _m3_rows():
    model = load_system_model(CASE_PATH)
    rows = rows_from_recipes(RecipeGenerator(model).generate_all())
    return model, pareto_prune(rows).kept_rows


@lru_cache(maxsize=1)
def _m5_result():
    model, rows = _m3_rows()
    return model, rows, refine_schedule(model, rows)


def test_refinement_improves_default_case_makespan() -> None:
    _model, _rows, result = _m5_result()

    assert result.refined.makespan_s < result.baseline.makespan_s
    assert result.improvement_percent > 0
    assert len(result.moves) > 0


def test_refinement_selects_one_recipe_per_target() -> None:
    _model, rows, result = _m5_result()

    target_ids = {str(row["target_id"]) for row in rows}
    assert {str(row["target_id"]) for row in result.refined.selected_rows} == target_ids
    assert len(result.refined.selected_rows) == len(target_ids)


def test_refinement_respects_core_resource_limits() -> None:
    model, _rows, result = _m5_result()
    boundaries = sorted({time for phase in result.refined.phases for time in (phase.start_s, phase.end_s)})

    for left, right in zip(boundaries, boundaries[1:]):
        if right - left <= 1e-12:
            continue
        active = [phase for phase in result.refined.phases if phase.start_s < right - 1e-12 and left < phase.end_s - 1e-12]
        assert sum(int(phase.serial_required) for phase in active) <= int(model.resource_limits["ptap_ports"])
        assert sum(phase.fpp_lanes_required for phase in active) <= int(model.resource_limits["total_fpp_lanes"])
        assert sum(phase.power_w for phase in active) <= float(model.resource_limits["max_total_power_w"]) + 1e-12


def test_refinement_writers_create_outputs(tmp_path) -> None:
    _model, _rows, result = _m5_result()
    schedule_output = tmp_path / "m5.csv"
    report_output = tmp_path / "m5.md"

    write_refined_schedule_csv(result, schedule_output)
    write_refinement_report_markdown(result, report_output)

    assert schedule_output.read_text(encoding="utf-8").startswith("case_id,target_id")
    report = report_output.read_text(encoding="utf-8")
    assert "M5 Schedule Refinement Report" in report
    assert "Improvement" in report


def test_ortools_backend_when_installed() -> None:
    pytest.importorskip("ortools")
    model, rows = _m3_rows()
    result, info = solve_cpsat_schedule(model, rows, time_limit_s=10.0)

    assert info.status_name in {"OPTIMAL", "FEASIBLE"}
    assert result.makespan_s > 0
    assert result.makespan_s <= refine_schedule(model, rows, backend="local").baseline.makespan_s
