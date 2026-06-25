from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.run_m10_benchmark_sweep import resource_variant
from experiments.run_m11_algorithm_study import (
    _fastest_recipe_rows,
    _filter_recipe_types,
    _lowest_power_rows,
    _tam_like_rows,
)
from src.evaluators.comparison import build_comparison_rows
from src.model import SystemModel, load_system_model
from src.recipes import RecipeGenerator, pareto_prune, rows_from_recipes
from src.schedulers import CpSatUnavailableError, ScheduleResult, SchedulingError, greedy_schedule, solve_cpsat_schedule


ABLATION_FIELDS = [
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
]

SUPPORT_FIELDS = ["innovation_id", "support_status", "evidence", "recommended_wording", "remaining_gap"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run M17 innovation-support experiments and evidence audit.")
    parser.add_argument("--case-dir", default="configs/cases/m10", help="M10 case directory.")
    parser.add_argument("--lane-count", type=int, default=8, help="Lane count for path/schedule ablation.")
    parser.add_argument("--power-profile", default="nominal", choices=["tight", "nominal", "relaxed"])
    parser.add_argument("--include-cpsat", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--max-cpsat-targets", type=int, default=22)
    parser.add_argument("--time-limit-s", type=float, default=3.0)
    parser.add_argument("--m10-table", default="results/tables/m10_benchmark_sweep.csv")
    parser.add_argument("--m11-table", default="results/tables/m11_algorithm_comparison.csv")
    parser.add_argument("--m12b-table", default="results/tables/m12_hotspot_validation_summary.csv")
    parser.add_argument("--m18-table", default="results/tables/m18_pressure_study.csv")
    parser.add_argument("--ablation-output", default="results/tables/m17_path_schedule_ablation.csv")
    parser.add_argument("--support-output", default="results/tables/m17_innovation_support_matrix.csv")
    parser.add_argument("--report-output", default="results/reports/m17_innovation_support_report.md")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    case_paths = sorted(Path(args.case_dir).glob("*.json"))
    if not case_paths:
        raise FileNotFoundError(f"no M10 case JSONs found: {args.case_dir}")

    ablation_rows = []
    for case_path in case_paths:
        base_model = load_system_model(case_path)
        model = resource_variant(base_model, lane_count=args.lane_count, power_profile=args.power_profile)
        ablation_rows.extend(
            run_ablation_case(
                model,
                lane_count=args.lane_count,
                power_profile=args.power_profile,
                include_cpsat=args.include_cpsat,
                max_cpsat_targets=args.max_cpsat_targets,
                time_limit_s=args.time_limit_s,
            )
        )

    support_rows = build_support_matrix(
        ablation_rows=ablation_rows,
        m10_rows=read_csv(Path(args.m10_table)),
        m11_rows=read_csv(Path(args.m11_table)),
        m12b_rows=read_csv(Path(args.m12b_table)),
        m18_rows=read_optional_csv(Path(args.m18_table)),
    )
    write_rows(ablation_rows, Path(args.ablation_output), ABLATION_FIELDS)
    write_rows(support_rows, Path(args.support_output), SUPPORT_FIELDS)
    write_report(Path(args.report_output), ablation_rows, support_rows)

    print(f"ablation_rows={len(ablation_rows)}")
    print(f"support_rows={len(support_rows)}")
    print(f"ablation_output={args.ablation_output}")
    print(f"support_output={args.support_output}")
    print(f"report_output={args.report_output}")


def run_ablation_case(
    model: SystemModel,
    lane_count: int,
    power_profile: str,
    include_cpsat: bool,
    max_cpsat_targets: int,
    time_limit_s: float,
) -> list[dict[str, Any]]:
    all_rows = rows_from_recipes(RecipeGenerator(model).generate_all())
    pareto_rows = pareto_prune(all_rows).kept_rows
    schedules: list[tuple[str, str, ScheduleResult]] = []
    meta: dict[str, dict[str, str]] = {}
    failures: list[dict[str, Any]] = []

    method_specs = [
        ("pure_serial", "Pure serial IEEE 1838", "baseline", lambda: greedy_schedule(model, _filter_recipe_types(all_rows, {"S", "I"}))),
        ("fixed_fastest", "Fixed fastest path", "fixed_path", lambda: greedy_schedule(model, _fastest_recipe_rows(pareto_rows))),
        ("fixed_low_power", "Fixed lowest-power path", "fixed_path", lambda: greedy_schedule(model, _lowest_power_rows(pareto_rows))),
        ("fixed_thermal_min", "Fixed lowest thermal-risk path", "fixed_path", lambda: greedy_schedule(model, _lowest_thermal_risk_rows(pareto_rows))),
        ("tam_like", "TAM-like FPP preference", "fixed_path", lambda: greedy_schedule(model, _tam_like_rows(pareto_rows))),
        ("joint_m4_greedy", "Joint recipe selection + greedy scheduling", "joint", lambda: greedy_schedule(model, pareto_rows)),
    ]
    for method_id, label, family, schedule_fn in method_specs:
        try:
            schedule = schedule_fn()
        except (SchedulingError, ValueError, RuntimeError) as exc:
            failures.append(_base_row(model, lane_count, power_profile, len(all_rows), len(pareto_rows), method_id, family, "failed", str(exc)))
        else:
            schedules.append((method_id, label, schedule))
            meta[method_id] = {"method_family": family, "solver_status": "greedy"}

    target_count = len(model.test_objects) + len(model.interconnects)
    if include_cpsat and target_count <= max_cpsat_targets:
        try:
            cpsat_schedule, info = solve_cpsat_schedule(model, pareto_rows, time_limit_s=time_limit_s)
        except (CpSatUnavailableError, RuntimeError) as exc:
            failures.append(_base_row(model, lane_count, power_profile, len(all_rows), len(pareto_rows), "m5_cpsat", "joint", "failed", str(exc)))
        else:
            schedules.append(("m5_cpsat", "M5 CP-SAT joint refinement", cpsat_schedule))
            meta["m5_cpsat"] = {"method_family": "joint", "solver_status": info.status_name}

    output_rows = []
    if schedules:
        comparison_rows, _thermal = build_comparison_rows(model, schedules, reference_method_id="pure_serial")
        for row in comparison_rows:
            output_rows.append(
                _success_row(
                    model=model,
                    lane_count=lane_count,
                    power_profile=power_profile,
                    recipe_count=len(all_rows),
                    pareto_recipe_count=len(pareto_rows),
                    comparison=row,
                    family=meta[row.method_id]["method_family"],
                    solver_status=meta[row.method_id]["solver_status"],
                )
            )
    output_rows.extend(failures)
    return output_rows


def build_support_matrix(
    ablation_rows: list[dict[str, Any]],
    m10_rows: list[dict[str, str]],
    m11_rows: list[dict[str, str]],
    m12b_rows: list[dict[str, str]],
    m18_rows: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    ok_ablation = [row for row in ablation_rows if row["status"] == "ok"]
    path_gain = path_joint_gain_summary(ok_ablation)
    if m18_rows:
        path_gain = merge_m18_pressure_support(path_gain, m18_rows)
    coverage = benchmark_coverage_summary(m10_rows)
    topology = topology_difference_summary(m10_rows)
    thermal = thermal_validation_summary(m12b_rows)
    cpsat_alns = cpsat_alns_summary(m11_rows)
    recipe = recipe_model_summary(m10_rows)

    return [
        {
            "innovation_id": "test_access_recipe_model",
            "support_status": "supported",
            "evidence": recipe,
            "recommended_wording": "提出 Test Access Recipe 抽象，将 S/F/B/I 等 IEEE 1838 访问方式统一为可调度候选路径。",
            "remaining_gap": "需要在正文中强调这是建模贡献，不是工业 DFT 自动抽取工具。",
        },
        {
            "innovation_id": "path_schedule_joint_optimization",
            "support_status": path_gain["status"],
            "evidence": path_gain["evidence"],
            "recommended_wording": path_gain["wording"],
            "remaining_gap": path_gain["gap"],
        },
        {
            "innovation_id": "unified_2_5d_3d_5_5d_model",
            "support_status": "partial" if topology["speedup_spread"] < 0.15 else "supported",
            "evidence": f"{coverage}; topology avg speedup spread={topology['speedup_spread']:.3f}",
            "recommended_wording": "构建覆盖 2.5D/3D/5.5D 的统一 benchmark 建模与实验框架。",
            "remaining_gap": "还需要在模型章节明确三类拓扑的资源差异，而不只报告同一 workload 的不同命名。",
        },
        {
            "innovation_id": "thermal_aware_validation",
            "support_status": thermal["status"],
            "evidence": thermal["evidence"],
            "recommended_wording": thermal["wording"],
            "remaining_gap": thermal["gap"],
        },
        {
            "innovation_id": "cpsat_alns_hybrid",
            "support_status": cpsat_alns["status"],
            "evidence": cpsat_alns["evidence"],
            "recommended_wording": cpsat_alns["wording"],
            "remaining_gap": cpsat_alns["gap"],
        },
    ]


def path_joint_gain_summary(rows: list[dict[str, Any]]) -> dict[str, str]:
    fixed_methods = {"fixed_fastest", "fixed_low_power", "fixed_thermal_min", "tam_like"}
    joint_methods = {"joint_m4_greedy", "m5_cpsat"}
    gains = []
    cases = sorted({row["case_id"] for row in rows})
    for case_id in cases:
        fixed = [row for row in rows if row["case_id"] == case_id and row["method_id"] in fixed_methods]
        joint = [row for row in rows if row["case_id"] == case_id and row["method_id"] in joint_methods]
        if not fixed or not joint:
            continue
        best_fixed = min(fixed, key=lambda row: float(row["makespan_s"]))
        best_joint = min(joint, key=lambda row: float(row["makespan_s"]))
        gain = (float(best_fixed["makespan_s"]) - float(best_joint["makespan_s"])) / float(best_fixed["makespan_s"]) * 100.0
        gains.append(gain)
    positive = [gain for gain in gains if gain > 1.0]
    avg_gain = sum(gains) / len(gains) if gains else 0.0
    if avg_gain > 0.5 and len(positive) >= max(2, len(gains) // 3):
        status = "supported"
        wording = "实验显示联合 recipe 选择与调度相对于固定路径基线带来可测的测试时间收益。"
        gap = "可继续补充更强资源受限/热受限场景扩大差距。"
    elif avg_gain > 0.0 and any(gain > 0.1 for gain in gains):
        status = "partial"
        wording = "联合选择在部分场景有小幅收益，更适合作为框架能力而非压倒性性能优势表述。"
        gap = "当前固定最快路径与 M4 结果接近，需要更强 ablation 或更复杂资源冲突场景。"
    else:
        status = "weak"
        wording = "当前结果不足以证明路径-调度联合优化的必要性，只能说明框架支持联合建模。"
        gap = "需要设计 fixed-path 明显受限的 case，或引入更强全局优化目标。"
    return {
        "status": status,
        "evidence": f"cases={len(gains)}, avg_joint_gain_vs_best_fixed={avg_gain:.3f}%, cases_gain_gt_1pct={len(positive)}",
        "wording": wording,
        "gap": gap,
    }


def merge_m18_pressure_support(path_gain: dict[str, str], rows: list[dict[str, str]]) -> dict[str, str]:
    ok_rows = [row for row in rows if row.get("status") == "ok"]
    pressure_cases = sorted({row["case_id"] for row in ok_rows})
    joint_rows = [row for row in ok_rows if row.get("method_family") == "joint"]
    gains = [float(row.get("gain_vs_fixed_fastest_percent", 0.0) or 0.0) for row in joint_rows]
    best_gain = max(gains) if gains else 0.0
    supported_cases = {
        row["case_id"]
        for row in joint_rows
        if float(row.get("gain_vs_fixed_fastest_percent", 0.0) or 0.0) >= 20.0
    }
    if len(supported_cases) >= 2 and best_gain >= 20.0:
        return {
            "status": "supported",
            "evidence": (
                f"{path_gain['evidence']}; M18 pressure cases={len(pressure_cases)}, "
                f"cases_gain_ge_20pct={len(supported_cases)}, best_joint_gain={best_gain:.2f}%"
            ),
            "wording": (
                "普通 sweep 中联合优化优势不稳定；但在共享 BIST engine 与 FPP lane 并存的资源压力场景中，"
                "联合 recipe 选择与调度能通过混合 BIST/FPP 路径显著缩短测试时间。"
            ),
            "gap": "需要把 M18 明确写成受控资源压力消融，不要泛化为所有 benchmark 上的压倒性优势。",
        }
    return {
        **path_gain,
        "evidence": f"{path_gain['evidence']}; M18 pressure best_joint_gain={best_gain:.2f}%",
    }


def benchmark_coverage_summary(rows: list[dict[str, str]]) -> str:
    ok_rows = [row for row in rows if row.get("status") == "ok"]
    cases = {row["case_id"] for row in ok_rows}
    die_counts = sorted({int(row["die_count"]) for row in ok_rows})
    targets = sorted({int(row["target_count"]) for row in ok_rows})
    recipes = sorted({int(row["recipe_count"]) for row in ok_rows})
    topologies = sorted({row["topology_type"] for row in ok_rows})
    return f"{len(cases)} cases; dies={die_counts}; targets={targets}; recipes={recipes}; topologies={topologies}"


def topology_difference_summary(rows: list[dict[str, str]]) -> dict[str, float]:
    ok_m4 = [row for row in rows if row.get("status") == "ok" and row.get("method_id") == "m4_greedy"]
    by_topology: dict[str, list[float]] = {}
    for row in ok_m4:
        by_topology.setdefault(row["topology_type"], []).append(float(row["speedup_vs_serial"]))
    avgs = [sum(values) / len(values) for values in by_topology.values() if values]
    spread = (max(avgs) - min(avgs)) / max(avgs) if avgs and max(avgs) else 0.0
    return {"speedup_spread": spread}


def thermal_validation_summary(rows: list[dict[str, str]]) -> dict[str, str]:
    ok_rows = [row for row in rows if row.get("status") == "ok"]
    cases = sorted({row["case_id"] for row in ok_rows})
    matches = 0
    for case_id in cases:
        group = [row for row in ok_rows if row["case_id"] == case_id]
        if not group:
            continue
        proxy_best = min(group, key=lambda row: float(row["proxy_peak_temperature_c"]))
        hotspot_best = min(group, key=lambda row: float(row["hotspot_peak_temperature_c"]))
        matches += int(proxy_best["schedule_id"] == hotspot_best["schedule_id"])
    if len(ok_rows) >= 6 and matches == len(cases):
        status = "partial"
        wording = "支持热感知评估与代表性 HotSpot 离线验证，不建议表述为完整电热闭环优化。"
        gap = "HotSpot 样本仍少，且尚未把 HotSpot 反馈重新加入调度器。"
    else:
        status = "weak"
        wording = "只能作为热代理结果的补充检查。"
        gap = "需要更多 HotSpot case 或闭环重调度实验。"
    return {
        "status": status,
        "evidence": f"hotspot_ok_rows={len(ok_rows)}, cases={len(cases)}, ranking_matches={matches}/{len(cases)}",
        "wording": wording,
        "gap": gap,
    }


def cpsat_alns_summary(rows: list[dict[str, str]]) -> dict[str, str]:
    ok_rows = [row for row in rows if row.get("status") == "ok"]
    m5 = [row for row in ok_rows if row["method_id"] == "m5_cpsat"]
    m6 = [row for row in ok_rows if row["method_id"] == "m6_alns"]
    skipped_m6 = [row for row in rows if row.get("method_id") == "m6_alns" and row.get("status") != "ok"]
    if len(m6) >= len(m5) and m6:
        status = "partial"
    else:
        status = "weak"
    return {
        "status": status,
        "evidence": f"m5_ok={len(m5)}, m6_ok={len(m6)}, m6_non_ok={len(skipped_m6)}",
        "wording": "CP-SAT 可作为精修求解器；ALNS 当前应作为扩展原型，暂不作为核心实验创新点。",
        "gap": "需要让 ALNS 在 medium/large case 上稳定运行并优于或快于单独 CP-SAT，才能作为强创新点。",
    }


def recipe_model_summary(rows: list[dict[str, str]]) -> str:
    ok_rows = [row for row in rows if row.get("status") == "ok"]
    cases = {}
    for row in ok_rows:
        cases.setdefault(row["case_id"], row)
    total_targets = sum(int(row["target_count"]) for row in cases.values())
    total_recipes = sum(int(row["recipe_count"]) for row in cases.values())
    ratio = total_recipes / total_targets if total_targets else 0.0
    return f"{len(cases)} cases, total_targets={total_targets}, total_candidate_recipes={total_recipes}, recipes_per_target={ratio:.2f}"


def _lowest_thermal_risk_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    selected = {}
    for row in rows:
        target_id = str(row["target_id"])
        key = (
            float(row.get("thermal_risk", 0.0)),
            float(row.get("peak_power_w", 0.0)),
            float(row.get("total_time_s", 0.0)),
            str(row["recipe_id"]),
        )
        if target_id not in selected or key < selected[target_id][0]:
            selected[target_id] = (key, row)
    return [item[1] for item in selected.values()]


def _success_row(
    model: SystemModel,
    lane_count: int,
    power_profile: str,
    recipe_count: int,
    pareto_recipe_count: int,
    comparison: Any,
    family: str,
    solver_status: str,
) -> dict[str, Any]:
    payload = _base_row(model, lane_count, power_profile, recipe_count, pareto_recipe_count, comparison.method_id, family, "ok", "")
    payload.update(
        {
            "makespan_s": comparison.makespan_s,
            "normalized_makespan": comparison.normalized_makespan,
            "speedup_vs_serial": 1.0 / comparison.normalized_makespan if comparison.normalized_makespan else 0.0,
            "peak_power_w": comparison.peak_power_w,
            "peak_temperature_c": comparison.peak_temperature_c,
            "peak_thermal_region": comparison.peak_thermal_region,
            "fpp_utilization": comparison.fpp_utilization,
            "serial_busy_ratio": comparison.serial_busy_ratio,
            "selected_recipe_types": comparison.selected_recipe_types,
            "thermal_violations": comparison.thermal_violations,
            "solver_status": solver_status,
        }
    )
    return {field: payload.get(field, "") for field in ABLATION_FIELDS}


def _base_row(
    model: SystemModel,
    lane_count: int,
    power_profile: str,
    recipe_count: int,
    pareto_recipe_count: int,
    method_id: str,
    family: str,
    status: str,
    error: str,
) -> dict[str, Any]:
    source = model.raw.get("benchmark_source", {})
    payload = {
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
        "method_id": method_id,
        "method_family": family,
        "status": status,
        "error": error,
    }
    return {field: payload.get(field, "") for field in ABLATION_FIELDS}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"missing input table: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_optional_csv(path: Path) -> list[dict[str, str]] | None:
    if not path.exists():
        return None
    return read_csv(path)


def write_rows(rows: list[dict[str, Any]], output_path: Path, fieldnames: list[str]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def write_report(output_path: Path, ablation_rows: list[dict[str, Any]], support_rows: list[dict[str, str]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ok_rows = [row for row in ablation_rows if row["status"] == "ok"]
    lines = [
        "# M17 Innovation Support Report",
        "",
        "M17 audits whether the current experiments support the claimed innovation points.",
        "",
        f"- Ablation rows: {len(ablation_rows)}",
        f"- Successful ablation rows: {len(ok_rows)}",
        "",
        "## Innovation Support Matrix",
        "",
        "| innovation | status | evidence | recommended wording | remaining gap |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in support_rows:
        lines.append(
            f"| {row['innovation_id']} | {row['support_status']} | {row['evidence']} | {row['recommended_wording']} | {row['remaining_gap']} |"
        )
    lines.extend(
        [
            "",
            "## Method",
            "",
            "The path/schedule ablation reruns all M10 cases at a fixed lane/power setting and compares fixed-path baselines against joint recipe-selection schedules.",
            "The support matrix intentionally reports weak or partial support when the current data do not justify a strong claim.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
