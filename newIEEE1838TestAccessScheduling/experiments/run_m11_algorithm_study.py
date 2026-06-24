from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.run_m10_benchmark_sweep import resource_variant
from src.evaluators.comparison import build_comparison_rows
from src.model import SystemModel, load_system_model
from src.recipes import RecipeGenerator, pareto_prune, rows_from_recipes
from src.schedulers import (
    CpSatUnavailableError,
    ScheduleResult,
    SchedulingError,
    greedy_schedule,
    run_alns,
    solve_cpsat_schedule,
)


DEFAULT_CASES = [
    "configs/cases/m10/m10_small_d695_3d_stack.json",
    "configs/cases/m10/m10_small_d695_2_5d_interposer.json",
    "configs/cases/m10/m10_small_d695_5_5d_multi_tower.json",
    "configs/cases/m10/m10_medium_p22810_3d_stack.json",
    "configs/cases/m10/m10_medium_p22810_2_5d_interposer.json",
    "configs/cases/m10/m10_medium_p22810_5_5d_multi_tower.json",
]

FIELDNAMES = [
    "case_id",
    "source_soc",
    "scale",
    "topology_type",
    "die_count",
    "tower_count",
    "target_count",
    "recipe_count",
    "pareto_recipe_count",
    "lane_count",
    "power_profile",
    "method_id",
    "method_label",
    "method_family",
    "status",
    "error",
    "makespan_s",
    "normalized_makespan",
    "speedup_vs_serial",
    "peak_power_w",
    "peak_temperature_c",
    "peak_thermal_region",
    "fpp_utilization",
    "serial_busy_ratio",
    "selected_recipe_types",
    "thermal_violations",
    "solver_status",
    "solver_wall_time_s",
    "alns_iterations",
    "alns_improvement_percent",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run M11 algorithm comparison and ablation study.")
    parser.add_argument("--cases", nargs="*", default=DEFAULT_CASES, help="Case JSONs to compare.")
    parser.add_argument("--lane-count", type=int, default=8, help="FPP lane count for all compared cases.")
    parser.add_argument(
        "--power-profile",
        default="nominal",
        choices=["tight", "nominal", "relaxed"],
        help="Power profile from the M10 sweep settings.",
    )
    parser.add_argument("--time-limit-s", type=float, default=5.0, help="CP-SAT time limit per case.")
    parser.add_argument("--alns-iterations", type=int, default=4, help="ALNS iterations for eligible cases.")
    parser.add_argument("--alns-repair-time-limit-s", type=float, default=1.5, help="CP-SAT repair limit inside ALNS.")
    parser.add_argument("--max-alns-targets", type=int, default=16, help="Maximum target count for ALNS rows.")
    parser.add_argument(
        "--output",
        default="results/tables/m11_algorithm_comparison.csv",
        help="Output CSV path.",
    )
    parser.add_argument(
        "--report-output",
        default="results/reports/m11_algorithm_study_report.md",
        help="Output Markdown report path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = []
    for case in args.cases:
        base_model = load_system_model(case)
        model = resource_variant(base_model, lane_count=args.lane_count, power_profile=args.power_profile)
        rows.extend(
            run_case(
                model,
                lane_count=args.lane_count,
                power_profile=args.power_profile,
                time_limit_s=args.time_limit_s,
                alns_iterations=args.alns_iterations,
                alns_repair_time_limit_s=args.alns_repair_time_limit_s,
                max_alns_targets=args.max_alns_targets,
            )
        )

    write_rows(rows, args.output)
    write_report(rows, args.report_output)

    print(f"cases={len(args.cases)}")
    print(f"rows={len(rows)}")
    print(f"output={args.output}")
    print(f"report_output={args.report_output}")


def run_case(
    model: SystemModel,
    lane_count: int = 8,
    power_profile: str = "nominal",
    time_limit_s: float = 5.0,
    alns_iterations: int = 4,
    alns_repair_time_limit_s: float = 1.5,
    max_alns_targets: int = 16,
) -> list[dict[str, Any]]:
    all_rows = rows_from_recipes(RecipeGenerator(model).generate_all())
    pareto_rows = pareto_prune(all_rows).kept_rows
    target_count = len({str(row["target_id"]) for row in all_rows})
    schedules: list[tuple[str, str, ScheduleResult]] = []
    method_meta: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []

    method_specs: list[tuple[str, str, str, Callable[[], ScheduleResult]]] = [
        ("pure_serial", "Pure serial IEEE 1838", "baseline", lambda: greedy_schedule(model, _filter_recipe_types(all_rows, {"S", "I"}))),
        ("fixed_fastest", "Fixed fastest recipe", "baseline", lambda: greedy_schedule(model, _fastest_recipe_rows(pareto_rows))),
        ("tam_like", "Simplified TAM/FPP packing", "baseline", lambda: greedy_schedule(model, _tam_like_rows(pareto_rows))),
        ("low_power", "Power-aware fixed recipe", "baseline", lambda: greedy_schedule(model, _lowest_power_rows(pareto_rows))),
        ("m4_all_recipes", "M4 greedy without Pareto pruning", "ablation", lambda: greedy_schedule(model, all_rows)),
        ("m4_greedy", "M4 greedy recipe scheduling", "proposed", lambda: greedy_schedule(model, pareto_rows)),
    ]

    for method_id, label, family, schedule_fn in method_specs:
        try:
            schedules.append((method_id, label, schedule_fn()))
            method_meta[method_id] = {"family": family, "solver_status": "greedy", "solver_wall_time_s": 0.0}
        except (SchedulingError, ValueError, RuntimeError) as exc:
            failures.append(
                _status_row(
                    model,
                    lane_count,
                    power_profile,
                    method_id,
                    label,
                    family,
                    "failed",
                    str(exc),
                    len(all_rows),
                    len(pareto_rows),
                )
            )

    try:
        cpsat_schedule, info = solve_cpsat_schedule(model, pareto_rows, time_limit_s=time_limit_s)
    except CpSatUnavailableError as exc:
        failures.append(
            _status_row(model, lane_count, power_profile, "m5_cpsat", "M5 CP-SAT", "proposed", "failed", str(exc), len(all_rows), len(pareto_rows))
        )
    except RuntimeError as exc:
        failures.append(
            _status_row(model, lane_count, power_profile, "m5_cpsat", "M5 CP-SAT", "proposed", "failed", str(exc), len(all_rows), len(pareto_rows))
        )
    else:
        schedules.append(("m5_cpsat", "M5 CP-SAT", cpsat_schedule))
        method_meta["m5_cpsat"] = {
            "family": "proposed",
            "solver_status": info.status_name,
            "solver_wall_time_s": info.wall_time_s,
        }

    if target_count <= max_alns_targets:
        try:
            alns = run_alns(
                model,
                pareto_rows,
                iterations=alns_iterations,
                repair_time_limit_s=alns_repair_time_limit_s,
                backend="ortools",
            )
        except (CpSatUnavailableError, RuntimeError, ValueError) as exc:
            failures.append(
                _status_row(
                    model,
                    lane_count,
                    power_profile,
                    "m6_alns",
                    "M6 CP-SAT-ALNS",
                    "proposed",
                    "failed",
                    str(exc),
                    len(all_rows),
                    len(pareto_rows),
                )
            )
        else:
            schedules.append(("m6_alns", "M6 CP-SAT-ALNS", alns.best))
            method_meta["m6_alns"] = {
                "family": "proposed",
                "solver_status": alns.backend,
                "solver_wall_time_s": "",
                "alns_iterations": len(alns.iterations),
                "alns_improvement_percent": alns.improvement_percent,
            }
    else:
        failures.append(
            _status_row(
                model,
                lane_count,
                power_profile,
                "m6_alns",
                "M6 CP-SAT-ALNS",
                "proposed",
                "skipped",
                f"target_count={target_count} exceeds max_alns_targets={max_alns_targets}",
                len(all_rows),
                len(pareto_rows),
            )
        )

    output_rows = []
    if schedules:
        comparison_rows, _thermal = build_comparison_rows(model, schedules, reference_method_id="pure_serial")
        for comparison in comparison_rows:
            output_rows.append(
                _success_row(
                    model,
                    lane_count,
                    power_profile,
                    comparison,
                    len(all_rows),
                    len(pareto_rows),
                    method_meta.get(comparison.method_id, {}),
                )
            )
    output_rows.extend(failures)
    return output_rows


def write_rows(rows: list[dict[str, Any]], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_report(rows: list[dict[str, Any]], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    ok_rows = [row for row in rows if row["status"] == "ok"]
    non_ok = [row for row in rows if row["status"] != "ok"]
    lines = [
        "# M11 Algorithm Study Report",
        "",
        f"- Total rows: {len(rows)}",
        f"- Successful rows: {len(ok_rows)}",
        f"- Non-success rows: {len(non_ok)}",
        "",
        "## Average Normalized Makespan",
        "",
        "| method | family | rows | avg_norm_vs_serial | avg_speedup |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for method_id in _ordered_methods(ok_rows):
        subset = [row for row in ok_rows if row["method_id"] == method_id]
        avg_norm = sum(float(row["normalized_makespan"]) for row in subset) / len(subset)
        avg_speedup = sum(float(row["speedup_vs_serial"]) for row in subset) / len(subset)
        lines.append(f"| {method_id} | {subset[0]['method_family']} | {len(subset)} | {avg_norm:.4f} | {avg_speedup:.2f} |")

    lines.extend(["", "## Best Method Per Case", "", "| case | topology | best method | makespan_s | norm | solver |", "| --- | --- | --- | ---: | ---: | --- |"])
    for case_id in sorted({str(row["case_id"]) for row in ok_rows}):
        case_rows = [row for row in ok_rows if row["case_id"] == case_id]
        best = min(case_rows, key=lambda row: float(row["makespan_s"]))
        lines.append(
            "| {case_id} | {topology_type} | {method_id} | {makespan_s:.9f} | {normalized_makespan:.4f} | {solver_status} |".format(
                **best
            )
        )

    if non_ok:
        lines.extend(["", "## Skipped Or Failed Rows", "", "| case | method | status | reason |", "| --- | --- | --- | --- |"])
        for row in non_ok:
            lines.append(f"| {row['case_id']} | {row['method_id']} | {row['status']} | {row['error']} |")

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- M11 compares algorithms on the selected small/medium cases at 8 FPP lanes and nominal power by default.",
            "- CP-SAT `FEASIBLE` rows are valid schedules, not optimality proofs.",
            "- M6 ALNS is bounded by `--max-alns-targets` to avoid turning this comparison into an uncontrolled long run.",
            "- Thermal values remain M7 proxy estimates; HotSpot-level validation belongs to M12.",
        ]
    )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _success_row(
    model: SystemModel,
    lane_count: int,
    power_profile: str,
    comparison: Any,
    recipe_count: int,
    pareto_recipe_count: int,
    meta: dict[str, Any],
) -> dict[str, Any]:
    row = asdict(comparison)
    speedup = 1.0 / float(row["normalized_makespan"]) if float(row["normalized_makespan"]) > 0 else 0.0
    payload = _base_row(model, lane_count, power_profile, recipe_count, pareto_recipe_count)
    payload.update(
        {
            "method_id": row["method_id"],
            "method_label": row["method_label"],
            "method_family": meta.get("family", ""),
            "status": "ok",
            "error": "",
            "makespan_s": row["makespan_s"],
            "normalized_makespan": row["normalized_makespan"],
            "speedup_vs_serial": speedup,
            "peak_power_w": row["peak_power_w"],
            "peak_temperature_c": row["peak_temperature_c"],
            "peak_thermal_region": row["peak_thermal_region"],
            "fpp_utilization": row["fpp_utilization"],
            "serial_busy_ratio": row["serial_busy_ratio"],
            "selected_recipe_types": row["selected_recipe_types"],
            "thermal_violations": row["thermal_violations"],
            "solver_status": meta.get("solver_status", ""),
            "solver_wall_time_s": meta.get("solver_wall_time_s", ""),
            "alns_iterations": meta.get("alns_iterations", ""),
            "alns_improvement_percent": meta.get("alns_improvement_percent", ""),
        }
    )
    return {field: payload.get(field, "") for field in FIELDNAMES}


def _status_row(
    model: SystemModel,
    lane_count: int,
    power_profile: str,
    method_id: str,
    method_label: str,
    family: str,
    status: str,
    error: str,
    recipe_count: int,
    pareto_recipe_count: int,
) -> dict[str, Any]:
    payload = _base_row(model, lane_count, power_profile, recipe_count, pareto_recipe_count)
    payload.update(
        {
            "method_id": method_id,
            "method_label": method_label,
            "method_family": family,
            "status": status,
            "error": error,
        }
    )
    return {field: payload.get(field, "") for field in FIELDNAMES}


def _base_row(
    model: SystemModel,
    lane_count: int,
    power_profile: str,
    recipe_count: int,
    pareto_recipe_count: int,
) -> dict[str, Any]:
    source = model.raw.get("benchmark_source", {})
    return {
        "case_id": model.case_id,
        "source_soc": source.get("soc_name", ""),
        "scale": source.get("scale", ""),
        "topology_type": model.raw["package"].get("topology_type", ""),
        "die_count": len(model.dies),
        "tower_count": int(model.raw["package"].get("tower_count", 0)),
        "target_count": len(model.test_objects) + len(model.interconnects),
        "recipe_count": recipe_count,
        "pareto_recipe_count": pareto_recipe_count,
        "lane_count": lane_count,
        "power_profile": power_profile,
    }


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


def _ordered_methods(rows: list[dict[str, Any]]) -> list[str]:
    order = [
        "pure_serial",
        "fixed_fastest",
        "tam_like",
        "low_power",
        "m4_all_recipes",
        "m4_greedy",
        "m5_cpsat",
        "m6_alns",
    ]
    present = {str(row["method_id"]) for row in rows}
    return [method for method in order if method in present] + sorted(present - set(order))


if __name__ == "__main__":
    main()
