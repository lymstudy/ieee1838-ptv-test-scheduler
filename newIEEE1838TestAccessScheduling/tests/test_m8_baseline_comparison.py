from __future__ import annotations

from src.evaluators.comparison import build_comparison_rows, write_comparison_csv, write_comparison_report_markdown
from src.model import load_system_model
from src.recipes import RecipeGenerator, pareto_prune, rows_from_recipes
from src.schedulers import greedy_schedule, solve_cpsat_schedule


CASE_PATH = "configs/cases/3d_stack_m1_example.json"


def test_comparison_rows_include_normalized_metrics() -> None:
    model = load_system_model(CASE_PATH)
    rows = pareto_prune(rows_from_recipes(RecipeGenerator(model).generate_all())).kept_rows
    greedy = greedy_schedule(model, rows)
    cpsat, _info = solve_cpsat_schedule(model, rows, time_limit_s=10.0)

    comparison, thermal = build_comparison_rows(
        model,
        [
            ("m4", "M4", greedy),
            ("m5", "M5", cpsat),
        ],
        reference_method_id="m4",
    )

    assert len(comparison) == 2
    assert len(thermal) == 2
    assert comparison[0].normalized_makespan == 1.0
    assert comparison[1].makespan_s <= comparison[0].makespan_s
    assert comparison[1].peak_temperature_c >= 25.0


def test_comparison_outputs_are_writable(tmp_path) -> None:
    model = load_system_model(CASE_PATH)
    rows = pareto_prune(rows_from_recipes(RecipeGenerator(model).generate_all())).kept_rows
    schedule = greedy_schedule(model, rows)
    comparison, _thermal = build_comparison_rows(model, [("m4", "M4", schedule)])
    csv_output = tmp_path / "comparison.csv"
    report_output = tmp_path / "comparison.md"

    write_comparison_csv(comparison, csv_output)
    write_comparison_report_markdown(comparison, report_output)

    assert csv_output.read_text(encoding="utf-8").startswith("case_id,method_id")
    assert "M8 Baseline Comparison Report" in report_output.read_text(encoding="utf-8")
