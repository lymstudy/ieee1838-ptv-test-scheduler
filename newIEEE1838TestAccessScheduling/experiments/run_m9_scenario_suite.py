from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluators.comparison import ComparisonRow, build_comparison_rows
from src.model import SystemModel, load_system_model
from src.recipes import RecipeGenerator, pareto_prune, rows_from_recipes
from src.schedulers import CpSatUnavailableError, ScheduleResult, greedy_schedule, solve_cpsat_schedule, write_schedule_csv


DEFAULT_CASES = [
    "configs/cases/3d_stack_m1_example.json",
    "configs/cases/2_5d_interposer_m9_public.json",
    "configs/cases/5_5d_multi_tower_m9_public.json",
]

FIELDNAMES = [
    "case_id",
    "topology_type",
    "die_count",
    "tower_count",
    "test_object_count",
    "interconnect_count",
    "target_count",
    "recipe_count",
    "pareto_recipe_count",
    "method_id",
    "method_label",
    "makespan_s",
    "normalized_makespan",
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run M9 scenario expansion comparison across package topologies.")
    parser.add_argument(
        "--cases",
        nargs="*",
        default=DEFAULT_CASES,
        help="Case JSON files to compare.",
    )
    parser.add_argument(
        "--output",
        default="results/tables/m9_scenario_comparison.csv",
        help="Output CSV path for M9 scenario comparison.",
    )
    parser.add_argument(
        "--report-output",
        default="results/reports/m9_scenario_expansion_report.md",
        help="Output Markdown report path.",
    )
    parser.add_argument(
        "--schedule-dir",
        default="",
        help="Optional directory for per-method schedule CSVs. Empty means do not write schedules.",
    )
    parser.add_argument("--time-limit-s", type=float, default=10.0, help="CP-SAT time limit per case.")
    parser.add_argument("--skip-cpsat", action="store_true", help="Skip M5 CP-SAT in large smoke runs.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows: list[dict[str, Any]] = []
    schedule_dir = Path(args.schedule_dir) if args.schedule_dir else None

    for case_path in args.cases:
        case_rows = run_case(
            case_path,
            time_limit_s=args.time_limit_s,
            include_cpsat=not args.skip_cpsat,
            schedule_dir=schedule_dir,
        )
        rows.extend(case_rows)

    write_m9_csv(rows, args.output)
    write_m9_report(rows, args.report_output)

    for row in rows:
        print(
            "case={case_id},topology={topology_type},method={method_id},"
            "makespan_s={makespan_s:.9f},norm={normalized_makespan:.4f},"
            "peak_temp_c={peak_temperature_c:.6f}".format(**row)
        )
    print(f"comparison_output={args.output}")
    print(f"report_output={args.report_output}")


def run_case(
    case_path: str | Path,
    time_limit_s: float = 10.0,
    include_cpsat: bool = True,
    schedule_dir: Path | None = None,
) -> list[dict[str, Any]]:
    model = load_system_model(case_path)
    all_rows = rows_from_recipes(RecipeGenerator(model).generate_all())
    pareto_rows = pareto_prune(all_rows).kept_rows

    schedules: list[tuple[str, str, ScheduleResult]] = [
        ("pure_serial", "Pure serial IEEE 1838", greedy_schedule(model, _filter_recipe_types(all_rows, {"S", "I"}))),
        ("m4_greedy", "M4 greedy recipe scheduling", greedy_schedule(model, pareto_rows)),
    ]
    solver_info: dict[str, tuple[str, float]] = {
        "pure_serial": ("greedy", 0.0),
        "m4_greedy": ("greedy", 0.0),
    }

    if include_cpsat:
        try:
            cpsat_schedule, info = solve_cpsat_schedule(model, pareto_rows, time_limit_s=time_limit_s)
        except CpSatUnavailableError:
            solver_info["m5_cpsat"] = ("unavailable", 0.0)
        else:
            schedules.append(("m5_cpsat", "M5 CP-SAT", cpsat_schedule))
            solver_info["m5_cpsat"] = (info.status_name, info.wall_time_s)

    if schedule_dir is not None:
        schedule_dir.mkdir(parents=True, exist_ok=True)
        for method_id, _label, schedule in schedules:
            write_schedule_csv(schedule, schedule_dir / f"m9_{model.case_id}_{method_id}_schedule.csv")

    comparison_rows, _thermal = build_comparison_rows(model, schedules, reference_method_id="pure_serial")
    return [
        _m9_row(model, row, len(all_rows), len(pareto_rows), solver_info.get(row.method_id, ("", 0.0)))
        for row in comparison_rows
    ]


def write_m9_csv(rows: list[dict[str, Any]], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_m9_report(rows: list[dict[str, Any]], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# M9 Scenario Expansion Report",
        "",
        "This report compares the same scheduling flow across the original 3D stack, a 2.5D interposer case, and a 5.5D multi-tower case.",
        "",
        "| case | topology | dies | targets | recipes | method | makespan_s | norm_serial | peak_temp_c | recipes |",
        "| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            "| {case_id} | {topology_type} | {die_count} | {target_count} | {pareto_recipe_count}/{recipe_count} | "
            "{method_label} | {makespan_s:.9f} | {normalized_makespan:.4f} | "
            "{peak_temperature_c:.6f} | {selected_recipe_types} |".format(**row)
        )

    lines.extend(["", "## Best Makespan Per Case", ""])
    for case_id in sorted({str(row["case_id"]) for row in rows}):
        case_rows = [row for row in rows if row["case_id"] == case_id]
        best = min(case_rows, key=lambda row: float(row["makespan_s"]))
        lines.append(
            "- `{case_id}`: `{method_id}` at {makespan_s:.9f} s "
            "(normalized {normalized_makespan:.4f}).".format(**best)
        )

    lines.extend(
        [
            "",
            "## Data Notes",
            "",
            "- ITC'02 `.soc` files provide public benchmark scan-chain lengths and pattern counts for generated M9 test objects.",
            "- UCIe/Open3DBench values are used as public package-link and topology references.",
            "- IEEE 1838 controller bit widths, DWR sizing, per-phase power, and thermal RC coefficients remain labeled model assumptions.",
            "- Thermal values are first-order RC proxy results, not HotSpot outputs.",
        ]
    )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _m9_row(
    model: SystemModel,
    row: ComparisonRow,
    recipe_count: int,
    pareto_recipe_count: int,
    solver_info: tuple[str, float],
) -> dict[str, Any]:
    payload = asdict(row)
    payload.update(
        {
            "topology_type": str(model.raw["package"].get("topology_type", "")),
            "die_count": len(model.dies),
            "tower_count": int(model.raw["package"].get("tower_count", 0)),
            "test_object_count": len(model.test_objects),
            "interconnect_count": len(model.interconnects),
            "target_count": len(model.test_objects) + len(model.interconnects),
            "recipe_count": recipe_count,
            "pareto_recipe_count": pareto_recipe_count,
            "solver_status": solver_info[0],
            "solver_wall_time_s": solver_info[1],
        }
    )
    return {field: payload.get(field, "") for field in FIELDNAMES}


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
