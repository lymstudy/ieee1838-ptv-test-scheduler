from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluators import (
    write_hotspots_csv,
    write_temperature_trace_csv,
    write_thermal_summary_csv,
)
from src.evaluators.comparison import (
    build_comparison_rows,
    write_comparison_csv,
    write_comparison_report_markdown,
)
from src.model import load_system_model
from src.recipes import RecipeGenerator, pareto_prune, rows_from_recipes
from src.schedulers import greedy_schedule, run_alns, solve_cpsat_schedule, write_schedule_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run M8 baseline comparison on one case.")
    parser.add_argument(
        "--case",
        default="configs/cases/3d_stack_m1_example.json",
        help="Path to an M1 system model JSON file.",
    )
    parser.add_argument(
        "--output",
        default="results/tables/m8_baseline_comparison.csv",
        help="Output CSV path for baseline comparison table.",
    )
    parser.add_argument(
        "--report-output",
        default="results/reports/m8_baseline_comparison_report.md",
        help="Output Markdown path for baseline comparison report.",
    )
    parser.add_argument(
        "--schedule-dir",
        default="results/schedules",
        help="Directory for per-baseline schedule CSV files.",
    )
    parser.add_argument(
        "--temperature-output",
        default="results/tables/m8_temperature_trace.csv",
        help="Output CSV path for thermal trace of compared methods.",
    )
    parser.add_argument(
        "--hotspot-output",
        default="results/tables/m8_hotspots.csv",
        help="Output CSV path for hotspot table of compared methods.",
    )
    parser.add_argument(
        "--thermal-summary-output",
        default="results/tables/m8_thermal_summary.csv",
        help="Output CSV path for thermal summary of compared methods.",
    )
    parser.add_argument("--time-limit-s", type=float, default=10.0, help="CP-SAT time limit for exact methods.")
    parser.add_argument("--alns-iterations", type=int, default=20, help="ALNS iteration count.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model = load_system_model(args.case)
    all_rows = rows_from_recipes(RecipeGenerator(model).generate_all())
    pareto_rows = pareto_prune(all_rows).kept_rows

    schedules = [
        ("pure_serial", "Pure serial IEEE 1838", greedy_schedule(model, _filter_recipe_types(all_rows, {"S", "I"}))),
        ("fixed_fastest", "Fixed fastest recipe", greedy_schedule(model, _fastest_recipe_rows(pareto_rows))),
        ("tam_like", "Simplified TAM/FPP packing", greedy_schedule(model, _tam_like_rows(pareto_rows))),
        ("low_power", "Power-aware fixed recipe", greedy_schedule(model, _lowest_power_rows(pareto_rows))),
        ("m4_greedy", "M4 greedy recipe scheduling", greedy_schedule(model, pareto_rows)),
    ]

    cpsat_schedule, _info = solve_cpsat_schedule(model, pareto_rows, time_limit_s=args.time_limit_s)
    schedules.append(("m5_cpsat", "M5 CP-SAT", cpsat_schedule))

    alns_result = run_alns(model, pareto_rows, iterations=args.alns_iterations, repair_time_limit_s=2.0)
    schedules.append(("m6_alns", "M6 CP-SAT-ALNS", alns_result.best))

    schedule_dir = Path(args.schedule_dir)
    for method_id, _label, schedule in schedules:
        write_schedule_csv(schedule, schedule_dir / f"m8_{method_id}_schedule.csv")

    comparison_rows, thermal_results = build_comparison_rows(model, schedules, reference_method_id="pure_serial")
    write_comparison_csv(comparison_rows, args.output)
    write_comparison_report_markdown(comparison_rows, args.report_output)
    write_temperature_trace_csv(thermal_results, args.temperature_output)
    write_hotspots_csv(thermal_results, args.hotspot_output)
    write_thermal_summary_csv(thermal_results, args.thermal_summary_output)

    print(f"case_id={model.case_id}")
    for row in comparison_rows:
        print(
            f"method={row.method_id},makespan_s={row.makespan_s:.9f},"
            f"normalized={row.normalized_makespan:.4f},peak_temp_c={row.peak_temperature_c:.6f}"
        )
    print(f"comparison_output={args.output}")
    print(f"report_output={args.report_output}")


def _filter_recipe_types(rows: list[dict[str, object]], recipe_types: set[str]) -> list[dict[str, object]]:
    filtered = [row for row in rows if str(row.get("recipe_type", "")) in recipe_types]
    target_ids = {str(row["target_id"]) for row in rows}
    covered = {str(row["target_id"]) for row in filtered}
    missing = sorted(target_ids - covered)
    if missing:
        raise ValueError(f"baseline cannot cover targets with recipe types {recipe_types}: {missing}")
    return filtered


def _fastest_recipe_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    selected = {}
    for row in rows:
        target_id = str(row["target_id"])
        key = (float(row.get("total_time_s", 0.0)), float(row.get("peak_power_w", 0.0)), str(row["recipe_id"]))
        if target_id not in selected or key < selected[target_id][0]:
            selected[target_id] = (key, row)
    return [item[1] for item in selected.values()]


def _tam_like_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    selected = {}
    for row in rows:
        target_id = str(row["target_id"])
        recipe_type = str(row.get("recipe_type", ""))
        type_rank = 0 if recipe_type == "F" else 1
        key = (
            type_rank,
            float(row.get("total_time_s", 0.0)),
            float(row.get("max_fpp_lanes_required", 0.0)),
            str(row["recipe_id"]),
        )
        if target_id not in selected or key < selected[target_id][0]:
            selected[target_id] = (key, row)
    return [item[1] for item in selected.values()]


def _lowest_power_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    selected = {}
    for row in rows:
        target_id = str(row["target_id"])
        key = (
            float(row.get("peak_power_w", 0.0)),
            float(row.get("thermal_risk", 0.0)),
            float(row.get("total_time_s", 0.0)),
            str(row["recipe_id"]),
        )
        if target_id not in selected or key < selected[target_id][0]:
            selected[target_id] = (key, row)
    return [item[1] for item in selected.values()]


if __name__ == "__main__":
    main()
