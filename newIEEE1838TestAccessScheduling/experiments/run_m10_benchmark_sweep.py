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

from src.evaluators.comparison import build_comparison_rows
from src.model import SystemModel, load_system_model
from src.recipes import RecipeGenerator, pareto_prune, rows_from_recipes
from src.schedulers import CpSatUnavailableError, ScheduleResult, SchedulingError, greedy_schedule, solve_cpsat_schedule


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
    "max_power_w",
    "method_id",
    "method_label",
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
]

POWER_PROFILE_FACTORS = {
    "tight": 0.45,
    "nominal": 1.0,
    "relaxed": 1.5,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run M10 benchmark lane/power sensitivity sweep.")
    parser.add_argument("--case-dir", default="configs/cases/m10", help="Directory containing M10 case JSONs.")
    parser.add_argument(
        "--output",
        default="results/tables/m10_benchmark_sweep.csv",
        help="Output CSV path.",
    )
    parser.add_argument(
        "--report-output",
        default="results/reports/m10_benchmark_sweep_report.md",
        help="Output Markdown report path.",
    )
    parser.add_argument("--lane-options", type=int, nargs="*", default=[2, 8, 16], help="FPP lane counts to sweep.")
    parser.add_argument(
        "--power-profiles",
        nargs="*",
        default=["tight", "nominal", "relaxed"],
        choices=sorted(POWER_PROFILE_FACTORS),
        help="Power budget profiles to sweep.",
    )
    parser.add_argument("--include-cpsat", action="store_true", help="Include CP-SAT on cases below --max-cpsat-targets.")
    parser.add_argument("--max-cpsat-targets", type=int, default=12, help="Maximum targets for optional CP-SAT rows.")
    parser.add_argument("--time-limit-s", type=float, default=5.0, help="Optional CP-SAT time limit per variant.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    case_paths = sorted(Path(args.case_dir).glob("*.json"))
    if not case_paths:
        raise FileNotFoundError(f"no M10 cases found in {args.case_dir}; run generate_m10_benchmark_suite.py first")

    rows = run_sweep(
        case_paths=case_paths,
        lane_options=args.lane_options,
        power_profiles=args.power_profiles,
        include_cpsat=args.include_cpsat,
        max_cpsat_targets=args.max_cpsat_targets,
        time_limit_s=args.time_limit_s,
    )
    write_rows(rows, args.output)
    write_report(rows, args.report_output)

    print(f"cases={len(case_paths)}")
    print(f"rows={len(rows)}")
    print(f"output={args.output}")
    print(f"report_output={args.report_output}")


def run_sweep(
    case_paths: list[Path],
    lane_options: list[int],
    power_profiles: list[str],
    include_cpsat: bool = False,
    max_cpsat_targets: int = 12,
    time_limit_s: float = 5.0,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case_path in case_paths:
        base_model = load_system_model(case_path)
        for lane_count in lane_options:
            for power_profile in power_profiles:
                model = resource_variant(base_model, lane_count=lane_count, power_profile=power_profile)
                rows.extend(
                    run_variant(
                        model,
                        lane_count=lane_count,
                        power_profile=power_profile,
                        include_cpsat=include_cpsat,
                        max_cpsat_targets=max_cpsat_targets,
                        time_limit_s=time_limit_s,
                    )
                )
    return rows


def resource_variant(model: SystemModel, lane_count: int, power_profile: str) -> SystemModel:
    if lane_count <= 0:
        raise ValueError("lane_count must be positive")
    if power_profile not in POWER_PROFILE_FACTORS:
        raise ValueError(f"unknown power profile: {power_profile}")

    raw = deepcopy(model.raw)
    raw["resource_limits"]["total_fpp_lanes"] = lane_count
    base_power = float(model.resource_limits["max_total_power_w"])
    raw["resource_limits"]["max_total_power_w"] = max(2.5, round(base_power * POWER_PROFILE_FACTORS[power_profile], 6))

    for channel in raw["ieee1838_access"].get("fpp_channels", []):
        channel["max_lanes"] = lane_count
    for group in raw.get("resource_groups", {}).get("fpp_capacity_groups", []):
        group["capacity"] = lane_count
        group["members"] = list(group.get("members", []))[:lane_count]
    for domain in raw.get("resource_groups", {}).get("power_domains", []):
        domain["max_power_w"] = raw["resource_limits"]["max_total_power_w"]

    variant = SystemModel(raw=raw, source_path=model.source_path)
    variant.validate()
    return variant


def run_variant(
    model: SystemModel,
    lane_count: int,
    power_profile: str,
    include_cpsat: bool = False,
    max_cpsat_targets: int = 12,
    time_limit_s: float = 5.0,
) -> list[dict[str, Any]]:
    all_rows = rows_from_recipes(RecipeGenerator(model).generate_all())
    pareto_rows = pareto_prune(all_rows).kept_rows
    target_count = len({str(row["target_id"]) for row in all_rows})
    schedules: list[tuple[str, str, ScheduleResult]] = []
    solver_info: dict[str, tuple[str, float]] = {}
    failures: list[dict[str, Any]] = []

    method_specs = [
        ("pure_serial", "Pure serial IEEE 1838", lambda: greedy_schedule(model, _filter_recipe_types(all_rows, {"S", "I"})), "greedy"),
        ("m4_greedy", "M4 greedy recipe scheduling", lambda: greedy_schedule(model, pareto_rows), "greedy"),
    ]
    for method_id, label, schedule_fn, solver_status in method_specs:
        try:
            schedules.append((method_id, label, schedule_fn()))
            solver_info[method_id] = (solver_status, 0.0)
        except (SchedulingError, ValueError, RuntimeError) as exc:
            failures.append(_failure_row(model, lane_count, power_profile, method_id, label, str(exc), len(all_rows), len(pareto_rows)))

    if include_cpsat and target_count <= max_cpsat_targets:
        try:
            cpsat_schedule, info = solve_cpsat_schedule(model, pareto_rows, time_limit_s=time_limit_s)
        except CpSatUnavailableError as exc:
            failures.append(_failure_row(model, lane_count, power_profile, "m5_cpsat", "M5 CP-SAT", str(exc), len(all_rows), len(pareto_rows)))
        except RuntimeError as exc:
            failures.append(_failure_row(model, lane_count, power_profile, "m5_cpsat", "M5 CP-SAT", str(exc), len(all_rows), len(pareto_rows)))
        else:
            schedules.append(("m5_cpsat", "M5 CP-SAT", cpsat_schedule))
            solver_info["m5_cpsat"] = (info.status_name, info.wall_time_s)

    rows = []
    if schedules:
        comparisons, _thermal = build_comparison_rows(model, schedules, reference_method_id="pure_serial")
        rows.extend(
            _success_row(model, lane_count, power_profile, row, len(all_rows), len(pareto_rows), solver_info.get(row.method_id, ("", 0.0)))
            for row in comparisons
        )
    rows.extend(failures)
    return rows


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
    success_rows = [row for row in rows if row["status"] == "ok"]
    failed_rows = [row for row in rows if row["status"] != "ok"]
    lines = [
        "# M10 Benchmark Sweep Report",
        "",
        f"- Total rows: {len(rows)}",
        f"- Successful schedule rows: {len(success_rows)}",
        f"- Failed rows: {len(failed_rows)}",
        "",
        "## M4 Greedy Average Normalized Makespan",
        "",
        "| topology | rows | avg_norm_vs_serial | avg_speedup |",
        "| --- | ---: | ---: | ---: |",
    ]
    for topology in sorted({str(row["topology_type"]) for row in success_rows}):
        subset = [row for row in success_rows if row["topology_type"] == topology and row["method_id"] == "m4_greedy"]
        if not subset:
            continue
        avg_norm = sum(float(row["normalized_makespan"]) for row in subset) / len(subset)
        avg_speedup = sum(float(row["speedup_vs_serial"]) for row in subset) / len(subset)
        lines.append(f"| {topology} | {len(subset)} | {avg_norm:.4f} | {avg_speedup:.2f} |")

    lines.extend(["", "## Best M4 Row Per Scale", "", "| scale | case | lanes | power | norm | speedup |", "| --- | --- | ---: | --- | ---: | ---: |"])
    for scale in sorted({str(row["scale"]) for row in success_rows}):
        subset = [row for row in success_rows if row["scale"] == scale and row["method_id"] == "m4_greedy"]
        if not subset:
            continue
        best = min(subset, key=lambda row: float(row["normalized_makespan"]))
        lines.append(
            "| {scale} | {case_id} | {lane_count} | {power_profile} | {normalized_makespan:.4f} | {speedup_vs_serial:.2f} |".format(
                **best
            )
        )

    if failed_rows:
        lines.extend(["", "## Failed Rows", "", "| case | lanes | power | method | error |", "| --- | ---: | --- | --- | --- |"])
        for row in failed_rows[:20]:
            lines.append(
                f"| {row['case_id']} | {row['lane_count']} | {row['power_profile']} | {row['method_id']} | {row['error']} |"
            )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- M10 defaults to pure serial and M4 greedy because this milestone measures scale and sensitivity.",
            "- CP-SAT can be enabled for selected small cases with `--include-cpsat`.",
            "- These rows are not global optimality claims.",
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
    solver_info: tuple[str, float],
) -> dict[str, Any]:
    payload = _base_row(model, lane_count, power_profile, recipe_count, pareto_recipe_count)
    row = asdict(comparison)
    speedup = 1.0 / float(row["normalized_makespan"]) if float(row["normalized_makespan"]) > 0 else 0.0
    payload.update(
        {
            "method_id": row["method_id"],
            "method_label": row["method_label"],
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
            "solver_status": solver_info[0],
            "solver_wall_time_s": solver_info[1],
        }
    )
    return {field: payload.get(field, "") for field in FIELDNAMES}


def _failure_row(
    model: SystemModel,
    lane_count: int,
    power_profile: str,
    method_id: str,
    method_label: str,
    error: str,
    recipe_count: int,
    pareto_recipe_count: int,
) -> dict[str, Any]:
    payload = _base_row(model, lane_count, power_profile, recipe_count, pareto_recipe_count)
    payload.update({"method_id": method_id, "method_label": method_label, "status": "failed", "error": error})
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
        "max_power_w": float(model.resource_limits["max_total_power_w"]),
    }


def _filter_recipe_types(rows: list[dict[str, object]], recipe_types: set[str]) -> list[dict[str, object]]:
    filtered = [row for row in rows if str(row.get("recipe_type", "")) in recipe_types]
    target_ids = {str(row["target_id"]) for row in rows}
    covered = {str(row["target_id"]) for row in filtered}
    missing = sorted(target_ids - covered)
    if missing:
        raise ValueError(f"baseline cannot cover targets with recipe types {recipe_types}: {missing}")
    return filtered


if __name__ == "__main__":
    main()
