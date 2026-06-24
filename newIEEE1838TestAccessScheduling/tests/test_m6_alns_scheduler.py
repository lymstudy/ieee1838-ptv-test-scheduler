from __future__ import annotations

from functools import lru_cache

from src.model import load_system_model
from src.recipes import RecipeGenerator, pareto_prune, rows_from_recipes
from src.schedulers import (
    run_alns,
    write_alns_convergence_csv,
    write_alns_report_markdown,
    write_alns_schedule_csv,
)


CASE_PATH = "configs/cases/3d_stack_m1_example.json"


def _m3_rows():
    model = load_system_model(CASE_PATH)
    rows = rows_from_recipes(RecipeGenerator(model).generate_all())
    return model, pareto_prune(rows).kept_rows


@lru_cache(maxsize=1)
def _alns_result():
    model, rows = _m3_rows()
    return model, rows, run_alns(model, rows, iterations=6, repair_time_limit_s=2.0)


def test_alns_runs_iterations_and_keeps_feasible_schedule() -> None:
    model, rows, result = _alns_result()

    assert len(result.iterations) == 6
    assert result.best.makespan_s <= result.initial.makespan_s + 1e-12
    assert len(result.best.selected_rows) == len({str(row["target_id"]) for row in rows})
    assert result.best.peak_power_w <= float(model.resource_limits["max_total_power_w"]) + 1e-12
    assert result.best.max_fpp_lanes_used <= int(model.resource_limits["total_fpp_lanes"])


def test_alns_convergence_is_monotonic_for_best_value() -> None:
    _model, _rows, result = _alns_result()
    best_values = [row.best_makespan_s for row in result.iterations]

    assert best_values == sorted(best_values, reverse=True)


def test_alns_writers_create_outputs(tmp_path) -> None:
    _model, _rows, result = _alns_result()
    schedule_output = tmp_path / "m6_schedule.csv"
    convergence_output = tmp_path / "m6_convergence.csv"
    report_output = tmp_path / "m6_report.md"

    write_alns_schedule_csv(result, schedule_output)
    write_alns_convergence_csv(result, convergence_output)
    write_alns_report_markdown(result, report_output)

    assert schedule_output.read_text(encoding="utf-8").startswith("case_id,target_id")
    assert convergence_output.read_text(encoding="utf-8").startswith("iteration,destroy_operator")
    assert "M6 ALNS Schedule Report" in report_output.read_text(encoding="utf-8")
