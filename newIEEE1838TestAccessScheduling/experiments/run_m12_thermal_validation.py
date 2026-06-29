from __future__ import annotations

import argparse
import csv
import sys
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.run_m10_benchmark_sweep import resource_variant
from src.evaluators import (
    HotSpotExportRow,
    evaluate_schedule_thermal,
    write_hotspot_export_manifest,
    write_hotspot_floorplan,
    write_hotspot_power_trace,
    write_hotspots_csv,
    write_temperature_trace_csv,
)
from src.model import SystemModel, load_system_model
from src.recipes import RecipeGenerator, pareto_prune, rows_from_recipes
from src.schedulers import ScheduleResult, greedy_schedule, solve_cpsat_schedule


DEFAULT_CASES = [
    "configs/cases/m10/m10_small_d695_5_5d_multi_tower.json",
    "configs/cases/m10/m10_medium_p22810_3d_stack.json",
    "configs/cases/m10/m10_medium_p22810_5_5d_multi_tower.json",
]

SUMMARY_FIELDS = [
    "case_id",
    "source_soc",
    "scale",
    "topology_type",
    "thermal_profile",
    "method_id",
    "method_label",
    "makespan_s",
    "peak_power_w",
    "peak_temperature_c",
    "temperature_rise_c",
    "peak_region",
    "peak_time_s",
    "over_limit_duration_s",
    "violation_count",
    "selected_recipe_types",
    "solver_status",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run M12 thermal stress evaluation and HotSpot export.")
    parser.add_argument("--cases", nargs="*", default=DEFAULT_CASES, help="Case JSONs to evaluate.")
    parser.add_argument("--lane-count", type=int, default=8, help="FPP lane count used for schedule generation.")
    parser.add_argument(
        "--power-profile",
        default="nominal",
        choices=["tight", "nominal", "relaxed"],
        help="M10 power profile used for schedule generation.",
    )
    parser.add_argument("--time-limit-s", type=float, default=5.0, help="CP-SAT time limit per case.")
    parser.add_argument("--skip-cpsat", action="store_true", help="Skip M5 CP-SAT schedule generation.")
    parser.add_argument(
        "--summary-output",
        default="results/tables/m12_thermal_validation_summary.csv",
        help="Output CSV path for thermal validation summary.",
    )
    parser.add_argument(
        "--hotspot-output",
        default="results/tables/m12_thermal_hotspots.csv",
        help="Output CSV path for hotspot rows.",
    )
    parser.add_argument(
        "--temperature-output",
        default="results/tables/m12_temperature_trace.csv",
        help="Output CSV path for temperature trace rows.",
    )
    parser.add_argument(
        "--report-output",
        default="results/reports/m12_thermal_validation_report.md",
        help="Output Markdown report path.",
    )
    parser.add_argument(
        "--hotspot-dir",
        default="results/hotspot/m12",
        help="Directory for representative HotSpot-compatible .flp/.ptrace exports.",
    )
    parser.add_argument(
        "--hotspot-manifest",
        default="results/hotspot/m12_hotspot_export_manifest.csv",
        help="Output CSV manifest for HotSpot exports.",
    )
    parser.add_argument(
        "--hotspot-case-index",
        type=int,
        default=-1,
        help="Index of case to export for HotSpot input. Negative exports every evaluated case.",
    )
    parser.add_argument("--hotspot-sample-period-s", type=float, default=0.00001, help="Power trace sample period.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary_rows: list[dict[str, Any]] = []
    thermal_results = []
    export_rows: list[HotSpotExportRow] = []

    export_every_case = args.hotspot_case_index < 0
    export_case_index = max(0, min(args.hotspot_case_index, len(args.cases) - 1))
    for index, case_path in enumerate(args.cases):
        base_model = load_system_model(case_path)
        schedule_model = resource_variant(base_model, lane_count=args.lane_count, power_profile=args.power_profile)
        schedules, solver_status = build_schedules(schedule_model, time_limit_s=args.time_limit_s, include_cpsat=not args.skip_cpsat)

        for profile in ("nominal_proxy", "stress_proxy"):
            eval_model = thermal_profile_variant(schedule_model, profile)
            for method_id, method_label, schedule in schedules:
                schedule_id = f"{eval_model.case_id}::{profile}::{method_id}"
                result = evaluate_schedule_thermal(eval_model, schedule.phases, schedule_id)
                thermal_results.append(result)
                summary_rows.append(_summary_row(eval_model, profile, method_id, method_label, schedule, result, solver_status.get(method_id, "")))

        if export_every_case or index == export_case_index:
            export_rows.extend(
                export_hotspot_inputs(
                    schedule_model,
                    schedules,
                    output_dir=Path(args.hotspot_dir),
                    sample_period_s=args.hotspot_sample_period_s,
                    method_filter={"m4_greedy", "thermal_min_risk"},
                )
            )

    write_summary_csv(summary_rows, args.summary_output)
    write_hotspots_csv(thermal_results, args.hotspot_output)
    write_temperature_trace_csv(thermal_results, args.temperature_output)
    write_report(summary_rows, export_rows, args.report_output)
    write_hotspot_export_manifest(export_rows, args.hotspot_manifest)

    print(f"cases={len(args.cases)}")
    print(f"summary_rows={len(summary_rows)}")
    print(f"hotspot_exports={len(export_rows)}")
    print(f"summary_output={args.summary_output}")
    print(f"report_output={args.report_output}")


def build_schedules(
    model: SystemModel,
    time_limit_s: float = 5.0,
    include_cpsat: bool = True,
) -> tuple[list[tuple[str, str, ScheduleResult]], dict[str, str]]:
    all_rows = rows_from_recipes(RecipeGenerator(model).generate_all())
    pareto_rows = pareto_prune(all_rows).kept_rows
    schedules = [
        ("fixed_fastest", "Fixed fastest recipe", greedy_schedule(model, _fastest_recipe_rows(pareto_rows))),
        ("low_power", "Power-aware fixed recipe", greedy_schedule(model, _lowest_power_rows(pareto_rows))),
        ("thermal_min_risk", "Thermal-risk-min fixed recipe", greedy_schedule(model, _lowest_thermal_risk_rows(pareto_rows))),
        ("m4_greedy", "M4 greedy recipe scheduling", greedy_schedule(model, pareto_rows)),
    ]
    solver_status = {method_id: "greedy" for method_id, _label, _schedule in schedules}
    if include_cpsat:
        cpsat_schedule, info = solve_cpsat_schedule(model, pareto_rows, time_limit_s=time_limit_s)
        schedules.append(("m5_cpsat", "M5 CP-SAT", cpsat_schedule))
        solver_status["m5_cpsat"] = info.status_name
    return schedules, solver_status


def thermal_profile_variant(model: SystemModel, profile: str) -> SystemModel:
    if profile == "nominal_proxy":
        return model
    if profile != "stress_proxy":
        raise ValueError(f"unknown thermal profile: {profile}")

    raw = deepcopy(model.raw)
    raw["thermal_model"]["vertical_coupling_weight"] = float(raw["thermal_model"].get("vertical_coupling_weight", 0.35)) * 3.0
    raw["thermal_model"]["horizontal_coupling_weight"] = float(raw["thermal_model"].get("horizontal_coupling_weight", 0.2)) * 3.0
    # Prevent double-scaling: stress_proxy applies 40x R and 50x C reduction at the model
    # level, so set proxy_resistance_multiplier=1 to avoid additional scaling in thermal.py
    raw["thermal_model"]["proxy_resistance_multiplier"] = 1.0
    raw["thermal_model"]["proxy_capacitance_divider"] = 1.0
    for die in raw["dies"]:
        thermal = die["thermal"]
        thermal["thermal_resistance_c_per_w"] = float(thermal.get("thermal_resistance_c_per_w", 1.0)) * 40.0
        thermal["thermal_capacitance_j_per_c"] = max(0.001, float(thermal.get("thermal_capacitance_j_per_c", 1.0)) * 0.02)
    variant = SystemModel(raw=raw, source_path=model.source_path)
    variant.validate()
    return variant


def export_hotspot_inputs(
    model: SystemModel,
    schedules: list[tuple[str, str, ScheduleResult]],
    output_dir: Path,
    sample_period_s: float,
    method_filter: set[str],
) -> list[HotSpotExportRow]:
    output_dir.mkdir(parents=True, exist_ok=True)
    floorplan = output_dir / f"{model.case_id}.flp"
    write_hotspot_floorplan(model, floorplan)

    rows = []
    for method_id, _label, schedule in schedules:
        if method_id not in method_filter:
            continue
        trace = output_dir / f"{model.case_id}__{method_id}.ptrace"
        sample_count = write_hotspot_power_trace(model, schedule.phases, trace, sample_period_s=sample_period_s)
        rows.append(
            HotSpotExportRow(
                case_id=model.case_id,
                schedule_id=method_id,
                floorplan_path=floorplan.as_posix(),
                power_trace_path=trace.as_posix(),
                sample_period_s=sample_period_s,
                sample_count=sample_count,
                region_count=len(model.dies),
                notes="Generated HotSpot-compatible input; HotSpot has not been executed by this script.",
            )
        )
    return rows


def write_summary_csv(rows: list[dict[str, Any]], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_report(rows: list[dict[str, Any]], export_rows: list[HotSpotExportRow], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# M12 Thermal Validation Report",
        "",
        "This report uses the M7 first-order RC proxy and exports HotSpot-compatible inputs. It is not a HotSpot execution report.",
        "",
        f"- Summary rows: {len(rows)}",
        f"- HotSpot export rows: {len(export_rows)}",
        "",
        "## Peak Temperature By Profile",
        "",
        "| profile | method | rows | avg_peak_temp_c | max_peak_temp_c | avg_rise_c |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for profile in sorted({row["thermal_profile"] for row in rows}):
        for method in _ordered_methods(rows):
            subset = [row for row in rows if row["thermal_profile"] == profile and row["method_id"] == method]
            if not subset:
                continue
            avg_peak = sum(float(row["peak_temperature_c"]) for row in subset) / len(subset)
            max_peak = max(float(row["peak_temperature_c"]) for row in subset)
            avg_rise = sum(float(row["temperature_rise_c"]) for row in subset) / len(subset)
            lines.append(f"| {profile} | {method} | {len(subset)} | {avg_peak:.6f} | {max_peak:.6f} | {avg_rise:.6f} |")

    lines.extend(["", "## Best Stress-Profile Method Per Case", "", "| case | topology | best method | peak_temp_c | rise_c | makespan_s |", "| --- | --- | --- | ---: | ---: | ---: |"])
    for case_id in sorted({row["case_id"] for row in rows}):
        subset = [row for row in rows if row["case_id"] == case_id and row["thermal_profile"] == "stress_proxy"]
        if not subset:
            continue
        best = min(subset, key=lambda row: float(row["peak_temperature_c"]))
        lines.append(
            "| {case_id} | {topology_type} | {method_id} | {peak_temperature_c:.6f} | {temperature_rise_c:.6f} | {makespan_s:.9f} |".format(
                **best
            )
        )

    if export_rows:
        lines.extend(["", "## HotSpot Input Export", "", "| case | schedule | floorplan | ptrace | samples |", "| --- | --- | --- | --- | ---: |"])
        for row in export_rows:
            lines.append(f"| {row.case_id} | {row.schedule_id} | `{row.floorplan_path}` | `{row.power_trace_path}` | {row.sample_count} |")

    lines.extend(
        [
            "",
            "## Interpretation Notes",
            "",
            "- `stress_proxy` is an intentionally amplified sensitivity profile, not measured silicon data.",
            "- `.flp` and `.ptrace` files are generated HotSpot inputs only.",
            "- Physical thermal claims require running HotSpot or another validated thermal simulator in M13/M12 follow-up.",
        ]
    )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _summary_row(
    model: SystemModel,
    thermal_profile: str,
    method_id: str,
    method_label: str,
    schedule: ScheduleResult,
    result: Any,
    solver_status: str,
) -> dict[str, Any]:
    source = model.raw.get("benchmark_source", {})
    ambient = float(model.raw["package"].get("ambient_temperature_c", 25.0))
    recipe_counts = _recipe_type_counts(schedule)
    return {
        "case_id": model.case_id,
        "source_soc": source.get("soc_name", ""),
        "scale": source.get("scale", ""),
        "topology_type": model.raw["package"].get("topology_type", ""),
        "thermal_profile": thermal_profile,
        "method_id": method_id,
        "method_label": method_label,
        "makespan_s": schedule.makespan_s,
        "peak_power_w": schedule.peak_power_w,
        "peak_temperature_c": result.peak_temperature_c,
        "temperature_rise_c": result.peak_temperature_c - ambient,
        "peak_region": result.peak_region,
        "peak_time_s": result.peak_time_s,
        "over_limit_duration_s": result.over_limit_duration_s,
        "violation_count": result.violation_count,
        "selected_recipe_types": recipe_counts,
        "solver_status": solver_status,
    }


def _fastest_recipe_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return _select_one_per_target(rows, lambda row: (float(row.get("total_time_s", 0.0)), float(row.get("peak_power_w", 0.0)), str(row["recipe_id"])))


def _lowest_power_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return _select_one_per_target(rows, lambda row: (float(row.get("peak_power_w", 0.0)), float(row.get("thermal_risk", 0.0)), float(row.get("total_time_s", 0.0)), str(row["recipe_id"])))


def _lowest_thermal_risk_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return _select_one_per_target(rows, lambda row: (float(row.get("thermal_risk", 0.0)), float(row.get("peak_power_w", 0.0)), float(row.get("total_time_s", 0.0)), str(row["recipe_id"])))


def _select_one_per_target(rows: list[dict[str, object]], key_fn: Any) -> list[dict[str, object]]:
    selected: dict[str, tuple[Any, dict[str, object]]] = {}
    for row in rows:
        target_id = str(row["target_id"])
        key = key_fn(row)
        if target_id not in selected or key < selected[target_id][0]:
            selected[target_id] = (key, row)
    return [item[1] for item in selected.values()]


def _recipe_type_counts(schedule: ScheduleResult) -> str:
    counts: dict[str, int] = {}
    for row in schedule.selected_rows:
        recipe_type = str(row.get("recipe_type", ""))
        counts[recipe_type] = counts.get(recipe_type, 0) + 1
    return ";".join(f"{key}:{counts[key]}" for key in sorted(counts))


def _ordered_methods(rows: list[dict[str, Any]]) -> list[str]:
    order = ["fixed_fastest", "low_power", "thermal_min_risk", "m4_greedy", "m5_cpsat"]
    present = {str(row["method_id"]) for row in rows}
    return [method for method in order if method in present] + sorted(present - set(order))


if __name__ == "__main__":
    main()
