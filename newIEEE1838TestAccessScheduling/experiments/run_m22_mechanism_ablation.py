from __future__ import annotations

import argparse
import csv
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.generate_m21_innovation_pressure_suite import build_pressure_case
from experiments.run_m21_innovation_pressure_suite import DETAIL_FIELDS, best_joint_row, method_row, run_case
from src.model import SystemModel, load_system_model


ABLATIONS = [
    {
        "ablation_id": "m10_original_control",
        "ablation_label": "Original M10 model without imposed shared-resource pressure",
        "interpretation": "Coverage control: ordinary M10 cases should not be used to claim path-schedule joint gains.",
    },
    {
        "ablation_id": "bist_private_control",
        "ablation_label": "Pressure workload with private BIST engines",
        "interpretation": "Resource control: when BIST engines are private, fixed-fastest and joint scheduling should converge.",
    },
    {
        "ablation_id": "shared_bist_no_parallel_escape",
        "ablation_label": "Shared BIST pressure without FPP/hybrid escape paths",
        "interpretation": "Path-diversity control: a bottleneck alone is insufficient if all schedulers must use the same path.",
    },
    {
        "ablation_id": "shared_bist_with_parallel_escape",
        "ablation_label": "Shared BIST pressure with FPP/hybrid alternatives",
        "interpretation": "Mechanism case: joint recipe scheduling can mix BIST and FPP/hybrid paths to relieve serialization.",
    },
]

DETAIL_OUTPUT_FIELDS = ["ablation_id", "ablation_label"] + DETAIL_FIELDS
SUMMARY_FIELDS = [
    "ablation_id",
    "ablation_label",
    "case_count",
    "avg_best_joint_gain_percent",
    "min_best_joint_gain_percent",
    "max_best_joint_gain_percent",
    "avg_fixed_makespan_s",
    "avg_best_joint_makespan_s",
    "avg_fixed_tap_access_time_s",
    "avg_joint_tap_access_time_s",
    "avg_joint_fpp_data_time_s",
    "avg_joint_exclusive_test_time_s",
    "avg_fixed_b_count",
    "avg_joint_b_count",
    "avg_joint_f_count",
    "avg_joint_h_count",
    "avg_temperature_spread_c",
    "interpretation",
]
TOPOLOGY_FIELDS = [
    "ablation_id",
    "topology_type",
    "case_count",
    "avg_best_joint_gain_percent",
    "min_best_joint_gain_percent",
    "max_best_joint_gain_percent",
    "avg_joint_f_count",
    "avg_joint_h_count",
    "avg_temperature_spread_c",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run M22 mechanism ablation for path-schedule joint optimization.")
    parser.add_argument("--case-dir", default="configs/cases/m10", help="Directory containing M10 source cases.")
    parser.add_argument("--include-cpsat", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--max-cpsat-targets", type=int, default=22)
    parser.add_argument("--time-limit-s", type=float, default=3.0)
    parser.add_argument("--detail-output", default="results/tables/m22_mechanism_ablation_detail.csv")
    parser.add_argument("--summary-output", default="results/tables/m22_mechanism_ablation_summary.csv")
    parser.add_argument("--topology-output", default="results/tables/m22_topology_ablation_summary.csv")
    parser.add_argument("--report-output", default="results/reports/m22_mechanism_ablation_report.md")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    case_paths = sorted(Path(args.case_dir).glob("*.json"))
    if not case_paths:
        raise FileNotFoundError(f"no M10 cases found in {args.case_dir}; run generate_m10_benchmark_suite.py first")

    detail_rows: list[dict[str, Any]] = []
    for case_path in case_paths:
        source_model = load_system_model(case_path)
        for payload in build_ablation_payloads(source_model):
            ablation_id = payload["experimental_controls"]["m22_ablation_id"]
            ablation_label = payload["experimental_controls"]["m22_ablation_label"]
            model = SystemModel(raw=payload, source_path=source_model.source_path)
            model.validate()
            for row in run_case(
                model,
                include_cpsat=args.include_cpsat,
                max_cpsat_targets=args.max_cpsat_targets,
                time_limit_s=args.time_limit_s,
            ):
                output_row = {"ablation_id": ablation_id, "ablation_label": ablation_label}
                output_row.update(row)
                detail_rows.append({field: output_row.get(field, "") for field in DETAIL_OUTPUT_FIELDS})

    summary_rows = summarize_ablation_rows(detail_rows)
    topology_rows = summarize_topology_rows(detail_rows)
    write_rows(detail_rows, Path(args.detail_output), DETAIL_OUTPUT_FIELDS)
    write_rows(summary_rows, Path(args.summary_output), SUMMARY_FIELDS)
    write_rows(topology_rows, Path(args.topology_output), TOPOLOGY_FIELDS)
    write_report(detail_rows, summary_rows, topology_rows, Path(args.report_output))

    print(f"source_cases={len(case_paths)}")
    print(f"detail_rows={len(detail_rows)}")
    print(f"summary_output={args.summary_output}")
    print(f"report_output={args.report_output}")


def build_ablation_payloads(source_model: SystemModel) -> list[dict[str, Any]]:
    return [
        tag_payload(deepcopy(source_model.raw), source_model, "m10_original_control"),
        tag_payload(make_private_bist_control(build_pressure_case(source_model)), source_model, "bist_private_control"),
        tag_payload(remove_parallel_escape_paths(build_pressure_case(source_model)), source_model, "shared_bist_no_parallel_escape"),
        tag_payload(build_pressure_case(source_model), source_model, "shared_bist_with_parallel_escape"),
    ]


def tag_payload(payload: dict[str, Any], source_model: SystemModel, ablation_id: str) -> dict[str, Any]:
    ablation = next(item for item in ABLATIONS if item["ablation_id"] == ablation_id)
    payload["case_id"] = f"m22_{ablation_id}_{source_model.case_id.removeprefix('m10_')}"
    source = dict(payload.get("benchmark_source", {}))
    source.update(
        {
            "milestone": "M22",
            "source": "ITC02_SOC_MECHANISM_ABLATION",
            "source_case_id": source_model.case_id,
        }
    )
    payload["benchmark_source"] = source
    controls = dict(payload.get("experimental_controls", {}))
    controls.update(
        {
            "m22_ablation_id": ablation_id,
            "m22_ablation_label": ablation["ablation_label"],
            "m22_interpretation": ablation["interpretation"],
            "shared_bist_group_count": count_bist_groups(payload),
        }
    )
    payload["experimental_controls"] = controls
    payload["description"] = f"M22 mechanism ablation: {ablation['ablation_label']}."
    return payload


def make_private_bist_control(payload: dict[str, Any]) -> dict[str, Any]:
    groups = []
    for obj in payload["test_objects"]:
        if obj.get("object_type") == "instrument":
            continue
        obj.setdefault("supported_recipes", [])
        if "B" not in obj["supported_recipes"]:
            obj["supported_recipes"].append("B")
        engine_id = f"m22_private_bist_{obj['object_id']}"
        obj.setdefault("bist", {})
        obj["bist"]["enabled"] = True
        obj["bist"]["engine_id"] = engine_id
        obj.setdefault("required_resources", {})["bist_engine"] = engine_id
        groups.append({"group_id": engine_id, "capacity": 1, "members": [obj["object_id"]]})
    payload.setdefault("resource_groups", {})["bist_engine_groups"] = groups
    return payload


def remove_parallel_escape_paths(payload: dict[str, Any]) -> dict[str, Any]:
    for obj in payload["test_objects"]:
        if obj.get("object_type") == "instrument":
            continue
        obj["supported_recipes"] = [recipe for recipe in obj.get("supported_recipes", []) if recipe not in {"F", "H"}]
    return payload


def count_bist_groups(payload: dict[str, Any]) -> int:
    return len(payload.get("resource_groups", {}).get("bist_engine_groups", []))


def summarize_ablation_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ok_rows = [row for row in rows if row["status"] == "ok"]
    output = []
    for ablation in ABLATIONS:
        ablation_id = ablation["ablation_id"]
        subset = [row for row in ok_rows if row["ablation_id"] == ablation_id]
        case_ids = sorted({row["source_case_id"] for row in subset})
        case_metrics = [case_metric([row for row in subset if row["source_case_id"] == case_id]) for case_id in case_ids]
        output.append(
            {
                "ablation_id": ablation_id,
                "ablation_label": ablation["ablation_label"],
                "case_count": len(case_metrics),
                "avg_best_joint_gain_percent": avg([item["gain"] for item in case_metrics]),
                "min_best_joint_gain_percent": min([item["gain"] for item in case_metrics], default=0.0),
                "max_best_joint_gain_percent": max([item["gain"] for item in case_metrics], default=0.0),
                "avg_fixed_makespan_s": avg([item["fixed_makespan"] for item in case_metrics]),
                "avg_best_joint_makespan_s": avg([item["joint_makespan"] for item in case_metrics]),
                "avg_fixed_tap_access_time_s": avg([item["fixed_tap_access_time"] for item in case_metrics]),
                "avg_joint_tap_access_time_s": avg([item["joint_tap_access_time"] for item in case_metrics]),
                "avg_joint_fpp_data_time_s": avg([item["joint_fpp_data_time"] for item in case_metrics]),
                "avg_joint_exclusive_test_time_s": avg([item["joint_exclusive_test_time"] for item in case_metrics]),
                "avg_fixed_b_count": avg([item["fixed_b"] for item in case_metrics]),
                "avg_joint_b_count": avg([item["joint_b"] for item in case_metrics]),
                "avg_joint_f_count": avg([item["joint_f"] for item in case_metrics]),
                "avg_joint_h_count": avg([item["joint_h"] for item in case_metrics]),
                "avg_temperature_spread_c": avg([item["temperature_spread"] for item in case_metrics]),
                "interpretation": ablation["interpretation"],
            }
        )
    return output


def summarize_topology_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ok_rows = [row for row in rows if row["status"] == "ok"]
    output = []
    for ablation in ABLATIONS:
        subset = [row for row in ok_rows if row["ablation_id"] == ablation["ablation_id"]]
        for topology in sorted({row["topology_type"] for row in subset}):
            topology_rows = [row for row in subset if row["topology_type"] == topology]
            case_ids = sorted({row["source_case_id"] for row in topology_rows})
            metrics = [case_metric([row for row in topology_rows if row["source_case_id"] == case_id]) for case_id in case_ids]
            output.append(
                {
                    "ablation_id": ablation["ablation_id"],
                    "topology_type": topology,
                    "case_count": len(metrics),
                    "avg_best_joint_gain_percent": avg([item["gain"] for item in metrics]),
                    "min_best_joint_gain_percent": min([item["gain"] for item in metrics], default=0.0),
                    "max_best_joint_gain_percent": max([item["gain"] for item in metrics], default=0.0),
                    "avg_joint_f_count": avg([item["joint_f"] for item in metrics]),
                    "avg_joint_h_count": avg([item["joint_h"] for item in metrics]),
                    "avg_temperature_spread_c": avg([item["temperature_spread"] for item in metrics]),
                }
            )
    return output


def case_metric(case_rows: list[dict[str, Any]]) -> dict[str, float]:
    fixed = method_row(case_rows, "fixed_fastest")
    joint = best_joint_row(case_rows)
    temperatures = [float(row["peak_temperature_c"]) for row in case_rows if row.get("peak_temperature_c") not in {"", None}]
    return {
        "gain": float(joint["gain_vs_fixed_fastest_percent"] or 0.0),
        "fixed_makespan": float(fixed["makespan_s"]),
        "joint_makespan": float(joint["makespan_s"]),
        "fixed_tap_access_time": float(fixed.get("tap_access_time_s", 0.0) or 0.0),
        "joint_tap_access_time": float(joint.get("tap_access_time_s", 0.0) or 0.0),
        "joint_fpp_data_time": float(joint.get("fpp_data_time_s", 0.0) or 0.0),
        "joint_exclusive_test_time": float(joint.get("exclusive_test_time_s", 0.0) or 0.0),
        "fixed_b": float(fixed["selected_b_count"] or 0),
        "joint_b": float(joint["selected_b_count"] or 0),
        "joint_f": float(joint["selected_f_count"] or 0),
        "joint_h": float(joint["selected_h_count"] or 0),
        "temperature_spread": max(temperatures) - min(temperatures) if temperatures else 0.0,
    }


def write_rows(rows: list[dict[str, Any]], output_path: Path, fieldnames: list[str]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_report(
    detail_rows: list[dict[str, Any]],
    summary_rows: list[dict[str, Any]],
    topology_rows: list[dict[str, Any]],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ok_rows = [row for row in detail_rows if row["status"] == "ok"]
    lines = [
        "# M22 Mechanism Ablation Report",
        "",
        "M22 is an experiment fix, not a paper-writing patch. It separates benchmark coverage from the mechanism claim.",
        "",
        f"- Successful schedule rows: {len(ok_rows)}",
        f"- Source cases: {len({row['source_case_id'] for row in ok_rows})}",
        f"- Ablation settings: {len(ABLATIONS)}",
        "",
        "## Main Ablation",
        "",
        "| ablation | cases | avg gain vs fixed-fastest | gain range | fixed/joint TAP time | joint FPP data time | joint exclusive test time | avg joint B/F/H | interpretation |",
        "| --- | ---: | ---: | --- | --- | ---: | ---: | --- | --- |",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['ablation_id']} | {row['case_count']} | {float(row['avg_best_joint_gain_percent']):.2f}% | "
            f"{float(row['min_best_joint_gain_percent']):.2f}% - {float(row['max_best_joint_gain_percent']):.2f}% | "
            f"{float(row['avg_fixed_tap_access_time_s']):.6f}/{float(row['avg_joint_tap_access_time_s']):.6f} s | "
            f"{float(row['avg_joint_fpp_data_time_s']):.6f} s | "
            f"{float(row['avg_joint_exclusive_test_time_s']):.6f} s | "
            f"{float(row['avg_joint_b_count']):.2f}/{float(row['avg_joint_f_count']):.2f}/{float(row['avg_joint_h_count']):.2f} | "
            f"{row['interpretation']} |"
        )

    lines.extend(
        [
            "",
            "## Topology Split",
            "",
            "| ablation | topology | cases | avg gain | gain range | avg joint F/H | avg temp spread |",
            "| --- | --- | ---: | ---: | --- | --- | ---: |",
        ]
    )
    for row in topology_rows:
        lines.append(
            f"| {row['ablation_id']} | {row['topology_type']} | {row['case_count']} | "
            f"{float(row['avg_best_joint_gain_percent']):.2f}% | "
            f"{float(row['min_best_joint_gain_percent']):.2f}% - {float(row['max_best_joint_gain_percent']):.2f}% | "
            f"{float(row['avg_joint_f_count']):.2f}/{float(row['avg_joint_h_count']):.2f} | "
            f"{float(row['avg_temperature_spread_c']):.2f} C |"
        )

    lines.extend(
        [
            "",
            "## What This Proves",
            "",
            "- If there is no shared bottleneck, fixing the fastest path is already enough.",
            "- If there is a bottleneck but no alternative path, joint scheduling cannot create meaningful path diversity.",
            "- FPP is a data-transfer channel after TAP configuration, not an independent task launcher.",
            "- Scan/FPP/capture/BIST execution phases use exclusive test-session resources, so non-parallelizable work is not freely overlapped.",
            "- When shared BIST pressure and FPP/hybrid data-transfer alternatives coexist, joint recipe selection reduces serialization under those constraints.",
            "- The result should be written as a controlled ITC'02-derived mechanism experiment, not as a claim over every ordinary benchmark.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


if __name__ == "__main__":
    main()
