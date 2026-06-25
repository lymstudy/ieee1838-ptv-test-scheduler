from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an M14 paper-style experiment chapter draft from existing results.")
    parser.add_argument("--m10-table", default="results/tables/m10_benchmark_sweep.csv")
    parser.add_argument("--m11-table", default="results/tables/m11_algorithm_comparison.csv")
    parser.add_argument("--m12b-table", default="results/tables/m12_hotspot_validation_summary.csv")
    parser.add_argument("--m13-index", default="results/tables/m13_figure_index.csv")
    parser.add_argument("--output", default="results/reports/m14_experiment_chapter_draft.md")
    parser.add_argument("--table-index-output", default="results/tables/m14_experiment_artifact_index.csv")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    m10_rows = read_csv(Path(args.m10_table))
    m11_rows = read_csv(Path(args.m11_table))
    m12b_rows = read_csv(Path(args.m12b_table))
    figure_rows = read_csv(Path(args.m13_index))

    m10 = summarize_m10(m10_rows)
    m11 = summarize_m11(m11_rows)
    m12b = summarize_m12b(m12b_rows)

    write_chapter(
        output_path=Path(args.output),
        m10=m10,
        m11=m11,
        m12b=m12b,
        figure_rows=figure_rows,
        sources={
            "m10": args.m10_table,
            "m11": args.m11_table,
            "m12b": args.m12b_table,
            "m13": args.m13_index,
        },
    )
    write_artifact_index(Path(args.table_index_output), args, figure_rows)
    print(f"output={args.output}")
    print(f"table_index_output={args.table_index_output}")


def summarize_m10(rows: list[dict[str, str]]) -> dict[str, Any]:
    ok_rows = [row for row in rows if row.get("status") == "ok"]
    cases = {row["case_id"] for row in ok_rows}
    scales = sorted({row.get("scale", "") for row in ok_rows}, key=scale_order)
    topologies = sorted({row.get("topology_type", "") for row in ok_rows}, key=topology_order)
    workloads = sorted({row.get("source_soc", "") for row in ok_rows})
    m4_nominal_lane8 = [
        row
        for row in ok_rows
        if row.get("method_id") == "m4_greedy" and row.get("power_profile") == "nominal" and row.get("lane_count") == "8"
    ]

    topology_stats = []
    for topology in topologies:
        group = [row for row in ok_rows if row.get("topology_type") == topology and row.get("method_id") == "m4_greedy"]
        topology_stats.append(
            {
                "topology": topology,
                "rows": len(group),
                "avg_norm": mean([to_float(row["normalized_makespan"]) for row in group]),
                "avg_speedup": mean([to_float(row["speedup_vs_serial"]) for row in group]),
            }
        )

    best_by_scale = []
    for scale in scales:
        group = [row for row in ok_rows if row.get("scale") == scale and row.get("method_id") == "m4_greedy"]
        if not group:
            continue
        best = min(group, key=lambda row: to_float(row["normalized_makespan"]))
        best_by_scale.append(best)

    return {
        "total_rows": len(rows),
        "ok_rows": len(ok_rows),
        "case_count": len(cases),
        "scales": scales,
        "topologies": topologies,
        "workloads": workloads,
        "nominal_lane8_rows": len(m4_nominal_lane8),
        "nominal_lane8_avg_speedup": mean([to_float(row["speedup_vs_serial"]) for row in m4_nominal_lane8]),
        "nominal_lane8_avg_norm": mean([to_float(row["normalized_makespan"]) for row in m4_nominal_lane8]),
        "topology_stats": topology_stats,
        "best_by_scale": best_by_scale,
    }


def summarize_m11(rows: list[dict[str, str]]) -> dict[str, Any]:
    ok_rows = [row for row in rows if row.get("status") == "ok"]
    non_ok_rows = [row for row in rows if row.get("status") != "ok"]
    by_method: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in ok_rows:
        by_method[row["method_id"]].append(row)

    method_order = ["pure_serial", "fixed_fastest", "tam_like", "low_power", "m4_all_recipes", "m4_greedy", "m5_cpsat", "m6_alns"]
    method_stats = []
    for method in method_order:
        group = by_method.get(method, [])
        if not group:
            continue
        method_stats.append(
            {
                "method": method,
                "family": group[0].get("method_family", ""),
                "rows": len(group),
                "avg_norm": mean([to_float(row["normalized_makespan"]) for row in group]),
                "avg_speedup": mean([to_float(row["speedup_vs_serial"]) for row in group]),
            }
        )

    best_by_case = []
    for case_id in sorted({row["case_id"] for row in ok_rows}):
        group = [row for row in ok_rows if row["case_id"] == case_id]
        best_by_case.append(min(group, key=lambda row: to_float(row["normalized_makespan"])))

    return {
        "total_rows": len(rows),
        "ok_rows": len(ok_rows),
        "non_ok_rows": len(non_ok_rows),
        "case_count": len({row["case_id"] for row in rows}),
        "method_count": len({row["method_id"] for row in rows}),
        "method_stats": method_stats,
        "best_by_case": best_by_case,
        "non_ok_details": non_ok_rows,
    }


def summarize_m12b(rows: list[dict[str, str]]) -> dict[str, Any]:
    ok_rows = [row for row in rows if row.get("status") == "ok"]
    cases = sorted({row["case_id"] for row in rows})
    ranking_matches = []
    for case_id in cases:
        group = [row for row in ok_rows if row["case_id"] == case_id]
        if not group:
            continue
        proxy_best = min(group, key=lambda row: to_float(row["proxy_peak_temperature_c"]))
        hotspot_best = min(group, key=lambda row: to_float(row["hotspot_peak_temperature_c"]))
        ranking_matches.append(
            {
                "case_id": case_id,
                "proxy_best": proxy_best["schedule_id"],
                "hotspot_best": hotspot_best["schedule_id"],
                "match": proxy_best["schedule_id"] == hotspot_best["schedule_id"],
            }
        )
    return {
        "total_rows": len(rows),
        "ok_rows": len(ok_rows),
        "case_count": len(cases),
        "hotspot_min": min([to_float(row["hotspot_peak_temperature_c"]) for row in ok_rows], default=0.0),
        "hotspot_max": max([to_float(row["hotspot_peak_temperature_c"]) for row in ok_rows], default=0.0),
        "ranking_matches": ranking_matches,
        "ranking_match_count": sum(1 for item in ranking_matches if item["match"]),
    }


def write_chapter(
    output_path: Path,
    m10: dict[str, Any],
    m11: dict[str, Any],
    m12b: dict[str, Any],
    figure_rows: list[dict[str, str]],
    sources: dict[str, str],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# M14 Experiment Chapter Draft",
        "",
        "## 1. Experimental Setup",
        "",
        "The evaluation uses the computable IEEE 1838 model and generated Test Access Recipes from the previous stages.",
        f"The M10 benchmark suite contains {m10['case_count']} cases, {len(m10['workloads'])} ITC'02-derived workloads "
        f"({', '.join(m10['workloads'])}), {len(m10['scales'])} scale levels ({', '.join(m10['scales'])}), and "
        f"{len(m10['topologies'])} package topologies ({', '.join(m10['topologies'])}).",
        f"The M10 sweep produced {m10['total_rows']} schedule rows, of which {m10['ok_rows']} were successful.",
        "",
        "The algorithm comparison in M11 evaluates baseline and proposed schedulers on representative small and medium cases.",
        f"It contains {m11['case_count']} cases, {m11['method_count']} methods, and {m11['ok_rows']} successful rows out of {m11['total_rows']}.",
        "",
        "Thermal validation is split into two levels: a fast thermal proxy for broad sweeps and an offline HotSpot check for a representative subset.",
        f"M12b contains {m12b['ok_rows']} successful HotSpot executions across {m12b['case_count']} representative cases.",
        "",
        "## 2. Benchmark Scale and Topology Coverage",
        "",
        "M10 is used to show that the recipe generation and greedy scheduler scale across package organizations rather than only one hand-written stack.",
        f"For the nominal 8-lane setting, M4 greedy averages {m10['nominal_lane8_avg_speedup']:.2f}x speedup over pure serial "
        f"with mean normalized makespan {m10['nominal_lane8_avg_norm']:.4f}.",
        "",
        "| topology | M4 rows | avg normalized makespan | avg speedup |",
        "| --- | ---: | ---: | ---: |",
    ]
    for stat in m10["topology_stats"]:
        lines.append(f"| {stat['topology']} | {stat['rows']} | {stat['avg_norm']:.4f} | {stat['avg_speedup']:.2f} |")

    lines.extend(
        [
            "",
            "The best M4 row in each scale level is:",
            "",
            "| scale | case | lanes | power profile | normalized makespan | speedup |",
            "| --- | --- | ---: | --- | ---: | ---: |",
        ]
    )
    for row in m10["best_by_scale"]:
        lines.append(
            f"| {row['scale']} | {row['case_id']} | {row['lane_count']} | {row['power_profile']} | "
            f"{to_float(row['normalized_makespan']):.4f} | {to_float(row['speedup_vs_serial']):.2f} |"
        )

    lines.extend(
        [
            "",
            "## 3. Algorithm Comparison",
            "",
            "M11 separates path-selection effects from scheduler effects by comparing serial, fixed-path, TAM-like, power-aware, M4, M5, and M6 variants.",
            "The CP-SAT rows are feasible schedules under the modeled constraints; they should not be described as globally optimal unless the solver status proves optimality.",
            "",
            "| method | family | successful rows | avg normalized makespan | avg speedup |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
    )
    for stat in m11["method_stats"]:
        lines.append(f"| {stat['method']} | {stat['family']} | {stat['rows']} | {stat['avg_norm']:.4f} | {stat['avg_speedup']:.2f} |")

    if m11["non_ok_details"]:
        lines.extend(["", "M11 skipped or bounded rows are reported explicitly:", "", "| case | method | status | reason |", "| --- | --- | --- | --- |"])
        for row in m11["non_ok_details"]:
            lines.append(f"| {row['case_id']} | {row['method_id']} | {row['status']} | {row.get('error', '')} |")

    lines.extend(
        [
            "",
            "## 4. Thermal Proxy and HotSpot Validation",
            "",
            "The thermal proxy is used during scheduling and broad evaluation because it is fast enough to apply across many cases.",
            "HotSpot is used only as representative offline validation, not as an inner-loop solver.",
            f"The M12b HotSpot peak range is {m12b['hotspot_min']:.2f} C to {m12b['hotspot_max']:.2f} C.",
            f"The proxy-best and HotSpot-best schedule rankings agree in {m12b['ranking_match_count']} out of {len(m12b['ranking_matches'])} representative cases.",
            "",
            "| case | proxy-best schedule | HotSpot-best schedule | ranking match |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in m12b["ranking_matches"]:
        lines.append(f"| {item['case_id']} | {item['proxy_best']} | {item['hotspot_best']} | {item['match']} |")

    lines.extend(
        [
            "",
            "This result supports using the proxy for trend guidance, but it does not make the proxy a replacement for detailed thermal simulation.",
            "The current HotSpot export is block-level and simplified, so the wording should remain representative validation rather than signoff-grade thermal analysis.",
            "",
            "## 5. Figure and Table Usage",
            "",
            "| figure id | recommended role in paper |",
            "| --- | --- |",
        ]
    )
    for row in figure_rows:
        lines.append(f"| {row['figure_id']} | {row['notes']} |")

    lines.extend(
        [
            "",
            "Recommended table usage:",
            "",
            f"- M10 benchmark coverage and sensitivity: `{sources['m10']}`.",
            f"- M11 algorithm comparison: `{sources['m11']}`.",
            f"- M12b HotSpot validation summary: `{sources['m12b']}`.",
            f"- M13 figure index: `{sources['m13']}`.",
            "",
            "## 6. Limitations",
            "",
            "- The benchmark cases are derived from public ITC'02-style workload information and synthetic package mappings.",
            "- M10 emphasizes scalable benchmark coverage; only selected methods are used in the broad sweep.",
            "- M11 gives a richer algorithm comparison, but currently focuses on small and medium representative cases.",
            "- M12b validates representative schedules offline with HotSpot; it is not a full-chip industrial thermal signoff flow.",
            "- CP-SAT feasible results should be described as feasible refined schedules unless optimal status is explicitly available.",
            "",
            "## 7. Draft Conclusion",
            "",
            "The experimental results indicate that IEEE 1838-aware recipe generation and resource-constrained scheduling can substantially reduce test time compared with pure serial access while keeping the access-path constraints explicit.",
            "Across the M10 benchmark suite, the method scales across 2.5D interposer, 3D stack, and 5.5D multi-tower organizations.",
            "M11 shows that the proposed M4/M5 scheduling flow is competitive with fixed-path and TAM-like baselines under the modeled constraints.",
            "M12b further shows that the thermal proxy preserves the representative method ranking under offline HotSpot validation, although the thermal conclusion should be stated as trend validation rather than signoff.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_artifact_index(output_path: Path, args: argparse.Namespace, figure_rows: list[dict[str, str]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {"artifact": "m10_benchmark_sweep", "path": args.m10_table, "role": "benchmark coverage and M4 scale sweep"},
        {"artifact": "m11_algorithm_comparison", "path": args.m11_table, "role": "algorithm comparison table"},
        {"artifact": "m12b_hotspot_validation", "path": args.m12b_table, "role": "representative HotSpot validation"},
        {"artifact": "m13_figure_index", "path": args.m13_index, "role": "figure list for paper drafting"},
    ]
    for row in figure_rows:
        rows.append({"artifact": row["figure_id"], "path": row["path"], "role": row["notes"]})
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["artifact", "path", "role"])
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"missing input table: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def to_float(value: str | float | int) -> float:
    return float(value)


def scale_order(scale: str) -> int:
    return {"small": 0, "medium": 1, "large": 2, "xlarge": 3}.get(scale, 99)


def topology_order(topology: str) -> int:
    return {"2_5d_interposer": 0, "3d_stack": 1, "5_5d_multi_tower": 2}.get(topology, 99)


if __name__ == "__main__":
    main()
