from __future__ import annotations

from functools import lru_cache

from src.evaluators import (
    evaluate_schedule_thermal,
    read_schedule_csv,
    write_hotspots_csv,
    write_temperature_trace_csv,
    write_thermal_report_markdown,
    write_thermal_summary_csv,
)
from src.model import load_system_model
from src.recipes import RecipeGenerator, pareto_prune, rows_from_recipes
from src.schedulers import run_alns, write_alns_schedule_csv


CASE_PATH = "configs/cases/3d_stack_m1_example.json"


@lru_cache(maxsize=1)
def _alns_schedule():
    model = load_system_model(CASE_PATH)
    rows = pareto_prune(rows_from_recipes(RecipeGenerator(model).generate_all())).kept_rows
    result = run_alns(model, rows, iterations=2, repair_time_limit_s=2.0)
    return model, result


def test_thermal_evaluation_produces_region_samples(tmp_path) -> None:
    model, schedule_result = _alns_schedule()
    schedule_path = tmp_path / "schedule.csv"
    write_alns_schedule_csv(schedule_result, schedule_path)
    phases = read_schedule_csv(schedule_path)
    result = evaluate_schedule_thermal(model, phases, "unit")

    assert result.samples
    assert result.hotspots
    assert result.peak_temperature_c >= float(model.raw["package"]["ambient_temperature_c"])
    assert {row.thermal_region for row in result.hotspots} == set(model.thermal_regions_by_id)


def test_thermal_outputs_are_writable(tmp_path) -> None:
    model, schedule_result = _alns_schedule()
    result = evaluate_schedule_thermal(model, schedule_result.best.phases, "unit")
    trace_output = tmp_path / "trace.csv"
    hotspot_output = tmp_path / "hotspots.csv"
    summary_output = tmp_path / "summary.csv"
    report_output = tmp_path / "report.md"

    write_temperature_trace_csv([result], trace_output)
    write_hotspots_csv([result], hotspot_output)
    write_thermal_summary_csv([result], summary_output)
    write_thermal_report_markdown([result], report_output)

    assert trace_output.read_text(encoding="utf-8").startswith("schedule_id,time_s")
    assert hotspot_output.read_text(encoding="utf-8").startswith("schedule_id,thermal_region")
    assert summary_output.read_text(encoding="utf-8").startswith("schedule_id,makespan_s")
    assert "M7 Thermal Proxy Report" in report_output.read_text(encoding="utf-8")
