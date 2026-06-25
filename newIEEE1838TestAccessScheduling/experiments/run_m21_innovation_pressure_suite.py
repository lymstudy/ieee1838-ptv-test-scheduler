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
from src.evaluators.thermal import evaluate_schedule_thermal
from src.model import SystemModel, load_system_model
from src.recipes import RecipeGenerator, pareto_prune, rows_from_recipes
from src.schedulers import CpSatUnavailableError, ScheduleResult, SchedulingError, greedy_schedule, solve_cpsat_schedule


DETAIL_FIELDS = [
    "case_id",
    "source_case_id",
    "source_soc",
    "scale",
    "topology_type",
    "die_count",
    "tower_count",
    "target_count",
    "recipe_count",
    "pareto_recipe_count",
    "shared_bist_group_count",
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
    "temperature_rise_c",
    "peak_thermal_region",
    "fpp_utilization",
    "serial_busy_ratio",
    "tap_access_phase_count",
    "tap_access_time_s",
    "fpp_data_time_s",
    "exclusive_test_time_s",
    "selected_recipe_types",
    "selected_b_count",
    "selected_f_count",
    "selected_h_count",
    "selected_s_count",
    "solver_status",
]

TOPOLOGY_FIELDS = [
    "topology_type",
    "case_count",
    "avg_joint_gain_percent",
    "min_joint_gain_percent",
    "max_joint_gain_percent",
    "avg_fixed_b_count",
    "avg_joint_b_count",
    "avg_joint_f_count",
    "avg_temperature_spread_c",
    "avg_shared_bist_group_count",
]

CLAIM_FIELDS = ["claim_id", "support_status", "evidence", "recommended_wording", "remaining_gap"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run M21 innovation pressure suite.")
    parser.add_argument("--case-dir", default="configs/cases/m21", help="Directory containing M21 cases.")
    parser.add_argument("--include-cpsat", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--max-cpsat-targets", type=int, default=22)
    parser.add_argument("--time-limit-s", type=float, default=5.0)
    parser.add_argument("--detail-output", default="results/tables/m21_innovation_pressure_detail.csv")
    parser.add_argument("--topology-output", default="results/tables/m21_topology_pressure_summary.csv")
    parser.add_argument("--claim-output", default="results/tables/m21_claim_support.csv")
    parser.add_argument("--report-output", default="results/reports/m21_innovation_pressure_report.md")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    case_paths = sorted(Path(args.case_dir).glob("*.json"))
    if not case_paths:
        raise FileNotFoundError(f"no M21 cases found in {args.case_dir}; run generate_m21_innovation_pressure_suite.py first")

    rows = []
    for case_path in case_paths:
        rows.extend(
            run_case(
                load_system_model(case_path),
                include_cpsat=args.include_cpsat,
                max_cpsat_targets=args.max_cpsat_targets,
                time_limit_s=args.time_limit_s,
            )
        )

    topology_rows = topology_summary(rows)
    claim_rows = claim_support(rows, topology_rows)
    write_rows(rows, Path(args.detail_output), DETAIL_FIELDS)
    write_rows(topology_rows, Path(args.topology_output), TOPOLOGY_FIELDS)
    write_rows(claim_rows, Path(args.claim_output), CLAIM_FIELDS)
    write_report(rows, topology_rows, claim_rows, Path(args.report_output))

    print(f"cases={len(case_paths)}")
    print(f"detail_rows={len(rows)}")
    print(f"detail_output={args.detail_output}")
    print(f"report_output={args.report_output}")


def run_case(model: SystemModel, include_cpsat: bool, max_cpsat_targets: int, time_limit_s: float) -> list[dict[str, Any]]:
    all_rows = rows_from_recipes(RecipeGenerator(model).generate_all())
    pareto_rows = pareto_prune(all_rows).kept_rows
    schedules: list[tuple[str, str, ScheduleResult]] = []
    meta: dict[str, dict[str, str]] = {}
    failures: list[dict[str, Any]] = []

    specs = [
        ("pure_serial", "Pure serial IEEE 1838", "baseline", lambda: greedy_schedule(model, _filter_recipe_types(all_rows, {"S", "I"}))),
        ("fixed_fastest", "Fixed fastest per target", "fixed_path", lambda: greedy_schedule(model, _fastest_recipe_rows(pareto_rows))),
        ("tam_like", "TAM-like FPP preference", "fixed_path", lambda: greedy_schedule(model, _tam_like_rows(pareto_rows))),
        ("m4_greedy", "M4 joint greedy recipe scheduling", "joint", lambda: greedy_schedule(model, pareto_rows)),
    ]
    for method_id, label, family, schedule_fn in specs:
        try:
            schedules.append((method_id, label, schedule_fn()))
            meta[method_id] = {"family": family, "solver_status": "greedy"}
        except (SchedulingError, ValueError, RuntimeError) as exc:
            failures.append(base_row(model, len(all_rows), len(pareto_rows), method_id, family, "failed", str(exc)))

    target_count = len(model.test_objects) + len(model.interconnects)
    if include_cpsat and target_count <= max_cpsat_targets:
        try:
            schedule, info = solve_cpsat_schedule(model, pareto_rows, time_limit_s=time_limit_s)
        except (CpSatUnavailableError, RuntimeError, ValueError) as exc:
            failures.append(base_row(model, len(all_rows), len(pareto_rows), "m5_cpsat", "joint", "failed", str(exc)))
        else:
            schedules.append(("m5_cpsat", "M5 CP-SAT joint scheduling", schedule))
            meta["m5_cpsat"] = {"family": "joint", "solver_status": info.status_name}

    output = []
    fixed_makespan = None
    if schedules:
        comparison_rows, _thermal = build_comparison_rows(model, schedules, reference_method_id="pure_serial")
        fixed = [row for row in comparison_rows if row.method_id == "fixed_fastest"]
        fixed_makespan = fixed[0].makespan_s if fixed else None
        thermal_by_method = {
            method_id: evaluate_schedule_thermal(model, schedule.phases, method_id)
            for method_id, _label, schedule in schedules
        }
        for comparison in comparison_rows:
            output.append(
                success_row(
                    model=model,
                    recipe_count=len(all_rows),
                    pareto_recipe_count=len(pareto_rows),
                    comparison=comparison,
                    family=meta[comparison.method_id]["family"],
                    solver_status=meta[comparison.method_id]["solver_status"],
                    fixed_makespan=fixed_makespan,
                    thermal=thermal_by_method[comparison.method_id],
                    phase_stats=schedule_phase_stats(next(schedule for method_id, _label, schedule in schedules if method_id == comparison.method_id).phases),
                )
            )
    output.extend(failures)
    return output


def topology_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ok_rows = [row for row in rows if row["status"] == "ok"]
    output = []
    for topology in sorted({row["topology_type"] for row in ok_rows}):
        case_ids = sorted({row["case_id"] for row in ok_rows if row["topology_type"] == topology})
        gains = []
        fixed_b = []
        joint_b = []
        joint_f = []
        temp_spreads = []
        groups = []
        for case_id in case_ids:
            case_rows = [row for row in ok_rows if row["case_id"] == case_id]
            best_joint = best_joint_row(case_rows)
            fixed = method_row(case_rows, "fixed_fastest")
            gains.append(float(best_joint["gain_vs_fixed_fastest_percent"]))
            fixed_b.append(int(fixed["selected_b_count"]))
            joint_b.append(int(best_joint["selected_b_count"]))
            joint_f.append(int(best_joint["selected_f_count"]))
            temps = [float(row["peak_temperature_c"]) for row in case_rows]
            temp_spreads.append(max(temps) - min(temps))
            groups.append(int(best_joint["shared_bist_group_count"]))
        output.append(
            {
                "topology_type": topology,
                "case_count": len(case_ids),
                "avg_joint_gain_percent": avg(gains),
                "min_joint_gain_percent": min(gains),
                "max_joint_gain_percent": max(gains),
                "avg_fixed_b_count": avg(fixed_b),
                "avg_joint_b_count": avg(joint_b),
                "avg_joint_f_count": avg(joint_f),
                "avg_temperature_spread_c": avg(temp_spreads),
                "avg_shared_bist_group_count": avg(groups),
            }
        )
    return output


def claim_support(rows: list[dict[str, Any]], topology_rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    ok_rows = [row for row in rows if row["status"] == "ok"]
    case_ids = sorted({row["case_id"] for row in ok_rows})
    best_gains = [float(best_joint_row([row for row in ok_rows if row["case_id"] == case_id])["gain_vs_fixed_fastest_percent"]) for case_id in case_ids]
    topology_gain_spread = max(float(row["avg_joint_gain_percent"]) for row in topology_rows) - min(
        float(row["avg_joint_gain_percent"]) for row in topology_rows
    )
    temp_spreads = [float(row["avg_temperature_spread_c"]) for row in topology_rows]
    cpsat_rows = [row for row in ok_rows if row["method_id"] == "m5_cpsat"]
    m4_rows = [row for row in ok_rows if row["method_id"] == "m4_greedy"]
    cpsat_better = 0
    for row in cpsat_rows:
        case_m4 = [m4 for m4 in m4_rows if m4["case_id"] == row["case_id"]]
        if case_m4 and float(row["makespan_s"]) <= float(case_m4[0]["makespan_s"]):
            cpsat_better += 1

    return [
        {
            "claim_id": "test_access_recipe_model",
            "support_status": "supported",
            "evidence": f"{len(case_ids)} pressure cases, avg candidate recipes={avg([int(row['recipe_count']) for row in ok_rows if row['method_id']=='fixed_fastest']):.1f}",
            "recommended_wording": "Test Access Recipe can express serial, FPP, BIST, hybrid and interconnect access choices as schedulable alternatives.",
            "remaining_gap": "Still a research model, not automatic DFT extraction from industrial design databases.",
        },
        {
            "claim_id": "path_schedule_joint_optimization",
            "support_status": "supported" if min(best_gains) > 5.0 else "partial",
            "evidence": f"cases={len(case_ids)}, avg_gain={avg(best_gains):.2f}%, min_gain={min(best_gains):.2f}%, max_gain={max(best_gains):.2f}%",
            "recommended_wording": "Under shared-resource pressure, every task is still TAP-enabled first; joint selection mixes BIST local execution and FPP data-transfer paths under explicit test-session constraints.",
            "remaining_gap": "Do not claim this gain on ordinary M10 sweep; it is a pressure-suite result.",
        },
        {
            "claim_id": "unified_2_5d_3d_5_5d_model",
            "support_status": "supported" if topology_gain_spread > 5.0 else "partial",
            "evidence": f"topologies={len(topology_rows)}, avg_gain_spread={topology_gain_spread:.2f}%, group_counts={[row['avg_shared_bist_group_count'] for row in topology_rows]}",
            "recommended_wording": "The unified model can encode topology-dependent resource bottlenecks, not just rename the same workload.",
            "remaining_gap": "Topology pressure parameters remain modeling assumptions and must be stated as such.",
        },
        {
            "claim_id": "thermal_aware_validation",
            "support_status": "partial" if max(temp_spreads) > 1.0 else "weak",
            "evidence": f"avg_temperature_spread_by_topology={[round(value, 3) for value in temp_spreads]} C",
            "recommended_wording": "Thermal proxy now produces visible stress differentiation and can be used for risk analysis; HotSpot remains offline validation.",
            "remaining_gap": "Still not a closed HotSpot-in-the-loop optimizer.",
        },
        {
            "claim_id": "cpsat_alns_hybrid",
            "support_status": "partial" if cpsat_rows and cpsat_better >= max(1, len(cpsat_rows) // 2) else "weak",
            "evidence": f"m5_rows={len(cpsat_rows)}, m5_not_worse_than_m4={cpsat_better}; ALNS not promoted in M21",
            "recommended_wording": "CP-SAT is a useful exact/feasible refinement backend on small and medium pressure cases; ALNS remains an extension prototype.",
            "remaining_gap": "ALNS still needs a stronger implementation before becoming a core contribution.",
        },
    ]


def success_row(
    model: SystemModel,
    recipe_count: int,
    pareto_recipe_count: int,
    comparison: Any,
    family: str,
    solver_status: str,
    fixed_makespan: float | None,
    thermal: Any,
    phase_stats: dict[str, Any],
) -> dict[str, Any]:
    counts = selected_type_counts(str(comparison.selected_recipe_types))
    gain = ""
    if fixed_makespan and fixed_makespan > 0:
        gain = (fixed_makespan - float(comparison.makespan_s)) / fixed_makespan * 100.0
    payload = base_row(model, recipe_count, pareto_recipe_count, comparison.method_id, family, "ok", "")
    payload.update(
        {
            "makespan_s": comparison.makespan_s,
            "normalized_makespan": comparison.normalized_makespan,
            "speedup_vs_serial": 1.0 / comparison.normalized_makespan if comparison.normalized_makespan else 0.0,
            "gain_vs_fixed_fastest_percent": gain,
            "peak_power_w": comparison.peak_power_w,
            "peak_temperature_c": thermal.peak_temperature_c,
            "temperature_rise_c": thermal.peak_temperature_c - float(model.raw["package"].get("ambient_temperature_c", 25.0)),
            "peak_thermal_region": thermal.peak_region,
            "fpp_utilization": comparison.fpp_utilization,
            "serial_busy_ratio": comparison.serial_busy_ratio,
            "tap_access_phase_count": phase_stats["tap_access_phase_count"],
            "tap_access_time_s": phase_stats["tap_access_time_s"],
            "fpp_data_time_s": phase_stats["fpp_data_time_s"],
            "exclusive_test_time_s": phase_stats["exclusive_test_time_s"],
            "selected_recipe_types": comparison.selected_recipe_types,
            "selected_b_count": counts["B"],
            "selected_f_count": counts["F"],
            "selected_h_count": counts["H"],
            "selected_s_count": counts["S"],
            "solver_status": solver_status,
        }
    )
    return {field: payload.get(field, "") for field in DETAIL_FIELDS}


def schedule_phase_stats(phases: list[Any]) -> dict[str, Any]:
    tap_phases = [phase for phase in phases if phase.serial_required]
    fpp_data_phases = [phase for phase in phases if phase.phase_name.startswith("FPP_")]
    exclusive_phases = [phase for phase in phases if getattr(phase, "exclusive_resource", "")]
    return {
        "tap_access_phase_count": len(tap_phases),
        "tap_access_time_s": sum(float(phase.duration_s) for phase in tap_phases),
        "fpp_data_time_s": sum(float(phase.duration_s) for phase in fpp_data_phases),
        "exclusive_test_time_s": sum(float(phase.duration_s) for phase in exclusive_phases),
    }


def base_row(
    model: SystemModel,
    recipe_count: int,
    pareto_recipe_count: int,
    method_id: str,
    family: str,
    status: str,
    error: str,
) -> dict[str, Any]:
    source = model.raw.get("benchmark_source", {})
    return {
        "case_id": model.case_id,
        "source_case_id": source.get("source_case_id", ""),
        "source_soc": source.get("soc_name", ""),
        "scale": source.get("scale", ""),
        "topology_type": model.raw["package"].get("topology_type", ""),
        "die_count": len(model.dies),
        "tower_count": int(model.raw["package"].get("tower_count", 0)),
        "target_count": len(model.test_objects) + len(model.interconnects),
        "recipe_count": recipe_count,
        "pareto_recipe_count": pareto_recipe_count,
        "shared_bist_group_count": int(model.raw.get("experimental_controls", {}).get("shared_bist_group_count", 0)),
        "method_id": method_id,
        "method_family": family,
        "status": status,
        "error": error,
    }


def selected_type_counts(selected_recipe_types: str) -> dict[str, int]:
    counts = {key: 0 for key in ["B", "F", "H", "S"]}
    for token in [item.strip() for item in selected_recipe_types.split(";") if item.strip()]:
        if ":" not in token:
            continue
        key, value = token.split(":", 1)
        if key in counts:
            counts[key] += int(value)
    return counts


def best_joint_row(rows: list[dict[str, Any]]) -> dict[str, Any]:
    joint = [row for row in rows if row["method_family"] == "joint" and row["status"] == "ok"]
    return max(joint, key=lambda row: float(row.get("gain_vs_fixed_fastest_percent", 0.0) or 0.0))


def method_row(rows: list[dict[str, Any]], method_id: str) -> dict[str, Any]:
    return next(row for row in rows if row["method_id"] == method_id and row["status"] == "ok")


def avg(values: list[float | int]) -> float:
    return sum(float(value) for value in values) / len(values) if values else 0.0


def write_rows(rows: list[dict[str, Any]], output_path: Path, fieldnames: list[str]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def write_report(
    rows: list[dict[str, Any]],
    topology_rows: list[dict[str, Any]],
    claim_rows: list[dict[str, str]],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ok_rows = [row for row in rows if row["status"] == "ok"]
    best_gains = [
        float(best_joint_row([row for row in ok_rows if row["case_id"] == case_id])["gain_vs_fixed_fastest_percent"])
        for case_id in sorted({row["case_id"] for row in ok_rows})
    ]
    lines = [
        "# M21 Innovation Pressure Suite Report",
        "",
        "M21 replaces the weak ordinary-sweep evidence with an ITC'02-derived pressure suite.",
        "",
        f"- Successful detail rows: {len(ok_rows)}",
        f"- Pressure cases: {len(set(row['case_id'] for row in ok_rows))}",
        f"- Best-joint average gain vs fixed-fastest: {avg(best_gains):.2f}%",
        f"- Best-joint minimum gain vs fixed-fastest: {min(best_gains):.2f}%",
        "",
        "## Claim Support",
        "",
        "| claim | status | evidence | recommended wording | gap |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in claim_rows:
        lines.append(f"| {row['claim_id']} | {row['support_status']} | {row['evidence']} | {row['recommended_wording']} | {row['remaining_gap']} |")
    lines.extend(
        [
            "",
            "## Topology Pressure Summary",
            "",
            "| topology | cases | avg gain | gain range | avg BIST groups | avg temp spread |",
            "| --- | ---: | ---: | --- | ---: | ---: |",
        ]
    )
    for row in topology_rows:
        lines.append(
            f"| {row['topology_type']} | {row['case_count']} | {float(row['avg_joint_gain_percent']):.2f}% | "
            f"{float(row['min_joint_gain_percent']):.2f}% - {float(row['max_joint_gain_percent']):.2f}% | "
            f"{float(row['avg_shared_bist_group_count']):.2f} | {float(row['avg_temperature_spread_c']):.3f} C |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- M21 is not a new industrial dataset; it is an ITC'02-derived controlled pressure suite.",
            "- It is designed to expose the mechanism that ordinary M10 sweep hides: fixed fastest-path selection can create shared-resource serialization.",
            "- FPP is modeled as a post-TAP data-transfer channel, not as an independent task launcher.",
            "- Scan/FPP/capture/BIST execution phases use exclusive test-session resources; non-parallelizable work is not freely overlapped.",
            "- Thermal numbers are more differentiated than M10/M12 nominal proxy values, but they remain proxy estimates.",
            "- ALNS is intentionally not upgraded here; CP-SAT is treated as the reliable refinement backend.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
