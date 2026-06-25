from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.run_m11_algorithm_study import _fastest_recipe_rows, _filter_recipe_types, _tam_like_rows
from src.evaluators.comparison import build_comparison_rows
from src.model import SystemModel, load_system_model
from src.recipes import RecipeGenerator, pareto_prune, rows_from_recipes
from src.schedulers import CpSatUnavailableError, ScheduleResult, SchedulingError, greedy_schedule, solve_cpsat_schedule


FIELDS = [
    "case_id",
    "topology_type",
    "die_count",
    "target_count",
    "recipe_count",
    "pareto_recipe_count",
    "method_id",
    "method_family",
    "status",
    "error",
    "makespan_s",
    "normalized_makespan",
    "speedup_vs_serial",
    "gain_vs_fixed_fastest_percent",
    "peak_power_w",
    "peak_temperature_c",
    "fpp_utilization",
    "selected_recipe_types",
    "selected_b_count",
    "selected_f_count",
    "selected_h_count",
    "selected_s_count",
    "solver_status",
    "solver_wall_time_s",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run M18 resource-pressure study.")
    parser.add_argument("--case-dir", default="configs/cases/m18", help="Directory containing M18 pressure cases.")
    parser.add_argument("--time-limit-s", type=float, default=10.0, help="CP-SAT time limit per pressure case.")
    parser.add_argument("--output", default="results/tables/m18_pressure_study.csv", help="Output CSV path.")
    parser.add_argument("--report-output", default="results/reports/m18_pressure_study_report.md", help="Output report path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    case_paths = sorted(Path(args.case_dir).glob("*.json"))
    if not case_paths:
        raise FileNotFoundError(f"no M18 cases found in {args.case_dir}; run generate_m18_pressure_cases.py first")
    rows = []
    for case_path in case_paths:
        rows.extend(run_case(load_system_model(case_path), time_limit_s=args.time_limit_s))
    write_rows(rows, Path(args.output))
    write_report(rows, Path(args.report_output))
    print(f"cases={len(case_paths)}")
    print(f"rows={len(rows)}")
    print(f"output={args.output}")
    print(f"report_output={args.report_output}")


def run_case(model: SystemModel, time_limit_s: float = 10.0) -> list[dict[str, Any]]:
    all_rows = rows_from_recipes(RecipeGenerator(model).generate_all())
    pareto_rows = pareto_prune(all_rows).kept_rows
    schedules: list[tuple[str, str, ScheduleResult]] = []
    meta: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []

    specs = [
        ("pure_serial", "Pure serial IEEE 1838", "baseline", lambda: greedy_schedule(model, _filter_recipe_types(all_rows, {"S"}))),
        ("fixed_fastest", "Fixed fastest per target", "fixed_path", lambda: greedy_schedule(model, _fastest_recipe_rows(pareto_rows))),
        ("tam_like", "TAM-like FPP preference", "fixed_path", lambda: greedy_schedule(model, _tam_like_rows(pareto_rows))),
        ("m4_greedy", "M4 joint greedy", "joint", lambda: greedy_schedule(model, pareto_rows)),
    ]
    for method_id, label, family, schedule_fn in specs:
        try:
            schedules.append((method_id, label, schedule_fn()))
            meta[method_id] = {"family": family, "solver_status": "greedy", "solver_wall_time_s": 0.0}
        except (SchedulingError, ValueError, RuntimeError) as exc:
            failures.append(_failure_row(model, len(all_rows), len(pareto_rows), method_id, family, str(exc)))

    try:
        cpsat_schedule, info = solve_cpsat_schedule(model, pareto_rows, time_limit_s=time_limit_s)
    except (CpSatUnavailableError, RuntimeError, ValueError) as exc:
        failures.append(_failure_row(model, len(all_rows), len(pareto_rows), "m5_cpsat", "joint", str(exc)))
    else:
        schedules.append(("m5_cpsat", "M5 CP-SAT joint selection", cpsat_schedule))
        meta["m5_cpsat"] = {"family": "joint", "solver_status": info.status_name, "solver_wall_time_s": info.wall_time_s}

    output_rows = []
    fixed_makespan = None
    if schedules:
        comparisons, _thermal = build_comparison_rows(model, schedules, reference_method_id="pure_serial")
        fixed = [row for row in comparisons if row.method_id == "fixed_fastest"]
        fixed_makespan = fixed[0].makespan_s if fixed else None
        for comparison in comparisons:
            output_rows.append(
                _success_row(
                    model=model,
                    recipe_count=len(all_rows),
                    pareto_recipe_count=len(pareto_rows),
                    comparison=comparison,
                    family=meta[comparison.method_id]["family"],
                    solver_status=meta[comparison.method_id]["solver_status"],
                    solver_wall_time_s=meta[comparison.method_id]["solver_wall_time_s"],
                    fixed_makespan=fixed_makespan,
                )
            )
    output_rows.extend(failures)
    return output_rows


def selected_type_counts(selected_recipe_types: str) -> dict[str, int]:
    tokens = [token.strip() for token in selected_recipe_types.split(";") if token.strip()]
    counts = {recipe_type: 0 for recipe_type in ["B", "F", "H", "S"]}
    for token in tokens:
        if ":" in token:
            recipe_type, count = token.split(":", 1)
            recipe_type = recipe_type.strip()
            if recipe_type in counts:
                counts[recipe_type] += int(count)
        elif token in counts:
            counts[token] += 1
    return counts


def best_joint_gain(rows: list[dict[str, Any]]) -> float:
    ok_rows = [row for row in rows if row["status"] == "ok"]
    joint = [row for row in ok_rows if row["method_family"] == "joint"]
    if not joint:
        return 0.0
    return max(float(row.get("gain_vs_fixed_fastest_percent", 0.0) or 0.0) for row in joint)


def write_rows(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})


def write_report(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ok_rows = [row for row in rows if row["status"] == "ok"]
    lines = [
        "# M18 Resource-Pressure Study Report",
        "",
        f"- Total rows: {len(rows)}",
        f"- Successful rows: {len(ok_rows)}",
        f"- Best joint gain: {best_joint_gain(rows):.2f}%",
        "",
        "## Claim Impact",
        "",
        "M18 upgrades path-schedule joint optimization from a weak general-sweep claim to a supported controlled-ablation claim.",
        "The correct wording is still limited: the current evidence shows value under explicit shared-resource pressure, not universal dominance on all M10 cases.",
        "",
        "## Best Joint Gain Per Case",
        "",
        "| case | topology | targets | fixed_fastest_s | best_joint | best_joint_s | gain_vs_fixed_fastest | recipe mix |",
        "| --- | --- | ---: | ---: | --- | ---: | ---: | --- |",
    ]
    for case_id in sorted({str(row["case_id"]) for row in ok_rows}):
        case_rows = [row for row in ok_rows if row["case_id"] == case_id]
        fixed = next(row for row in case_rows if row["method_id"] == "fixed_fastest")
        joint_rows = [row for row in case_rows if row["method_family"] == "joint"]
        best = max(joint_rows, key=lambda row: float(row["gain_vs_fixed_fastest_percent"]))
        lines.append(
            "| {case_id} | {topology_type} | {target_count} | {fixed_s:.9f} | {method_id} | {makespan_s:.9f} | {gain:.2f}% | {mix} |".format(
                case_id=case_id,
                topology_type=best["topology_type"],
                target_count=best["target_count"],
                fixed_s=float(fixed["makespan_s"]),
                method_id=best["method_id"],
                makespan_s=float(best["makespan_s"]),
                gain=float(best["gain_vs_fixed_fastest_percent"]),
                mix=best["selected_recipe_types"],
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "M18 intentionally stresses the case where the individually fastest recipe is a shared BIST path.",
            "A fixed fastest-path policy serializes all targets on the shared BIST engine.",
            "Joint recipe selection can mix BIST and FPP paths, using otherwise idle package lanes while the shared BIST engine is busy.",
            "These cases are controlled ablations, not public industrial chip measurements.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _success_row(
    model: SystemModel,
    recipe_count: int,
    pareto_recipe_count: int,
    comparison: Any,
    family: str,
    solver_status: str,
    solver_wall_time_s: float,
    fixed_makespan: float | None,
) -> dict[str, Any]:
    gain = ""
    if fixed_makespan and fixed_makespan > 0:
        gain = (fixed_makespan - float(comparison.makespan_s)) / fixed_makespan * 100.0
    counts = selected_type_counts(str(comparison.selected_recipe_types))
    payload = _base_row(model, recipe_count, pareto_recipe_count, comparison.method_id, family, "ok", "")
    payload.update(
        {
            "makespan_s": comparison.makespan_s,
            "normalized_makespan": comparison.normalized_makespan,
            "speedup_vs_serial": 1.0 / comparison.normalized_makespan if comparison.normalized_makespan else 0.0,
            "gain_vs_fixed_fastest_percent": gain,
            "peak_power_w": comparison.peak_power_w,
            "peak_temperature_c": comparison.peak_temperature_c,
            "fpp_utilization": comparison.fpp_utilization,
            "selected_recipe_types": comparison.selected_recipe_types,
            "selected_b_count": counts["B"],
            "selected_f_count": counts["F"],
            "selected_h_count": counts["H"],
            "selected_s_count": counts["S"],
            "solver_status": solver_status,
            "solver_wall_time_s": solver_wall_time_s,
        }
    )
    return {field: payload.get(field, "") for field in FIELDS}


def _failure_row(
    model: SystemModel,
    recipe_count: int,
    pareto_recipe_count: int,
    method_id: str,
    family: str,
    error: str,
) -> dict[str, Any]:
    return _base_row(model, recipe_count, pareto_recipe_count, method_id, family, "failed", error)


def _base_row(
    model: SystemModel,
    recipe_count: int,
    pareto_recipe_count: int,
    method_id: str,
    family: str,
    status: str,
    error: str,
) -> dict[str, Any]:
    return {
        "case_id": model.case_id,
        "topology_type": model.raw["package"].get("topology_type", ""),
        "die_count": len(model.dies),
        "target_count": len(model.test_objects) + len(model.interconnects),
        "recipe_count": recipe_count,
        "pareto_recipe_count": pareto_recipe_count,
        "method_id": method_id,
        "method_family": family,
        "status": status,
        "error": error,
    }


if __name__ == "__main__":
    main()
