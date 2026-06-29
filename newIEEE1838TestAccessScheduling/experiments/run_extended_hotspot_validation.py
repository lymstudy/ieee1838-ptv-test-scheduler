"""Expanded HotSpot validation covering 3 topologies x 3 scales x 2-3 methods.

Generates .flp and .ptrace files for each case+method combination, saves to
results/hotspot/expanded/, and produces:
  - results/tables/expanded_hotspot_validation.csv   (summary table)
  - results/reports/expanded_hotspot_report.md       (Markdown report)

If the HotSpot simulator is not available (requires SSH to Linux VM), this
script generates all .flp/.ptrace files ready for later HotSpot execution.
The report includes clear instructions for how to run HotSpot later.

Coverage:
  - 3 topologies: 2.5D, 3D, 5.5D
  - 3 scales: small (d695), medium (p22810), large (p34392)
  - 2-3 methods per case: fixed_fastest, m4_greedy, m5_cpsat (if available)
  - Total: 3 x 3 x 3 = 27 target runs (some may skip CP-SAT on large cases)

Optional: --run-cpsat to include CP-SAT scheduling (takes longer).
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluators import (
    HotSpotExportRow,
    evaluate_schedule_thermal,
    write_hotspot_export_manifest,
    write_hotspot_floorplan,
    write_hotspot_power_trace,
)
from src.model import SystemModel, load_system_model
from src.recipes import RecipeGenerator, pareto_prune, rows_from_recipes
from src.schedulers import ScheduleResult, greedy_schedule, solve_cpsat_schedule


CASES = {
    ("2.5D", "small"): "configs/cases/m10/m10_small_d695_2_5d_interposer.json",
    ("2.5D", "medium"): "configs/cases/m10/m10_medium_p22810_2_5d_interposer.json",
    ("2.5D", "large"): "configs/cases/m10/m10_large_p34392_2_5d_interposer.json",
    ("3D", "small"): "configs/cases/m10/m10_small_d695_3d_stack.json",
    ("3D", "medium"): "configs/cases/m10/m10_medium_p22810_3d_stack.json",
    ("3D", "large"): "configs/cases/m10/m10_large_p34392_3d_stack.json",
    ("5.5D", "small"): "configs/cases/m10/m10_small_d695_5_5d_multi_tower.json",
    ("5.5D", "medium"): "configs/cases/m10/m10_medium_p22810_5_5d_multi_tower.json",
    ("5.5D", "large"): "configs/cases/m10/m10_large_p34392_5_5d_multi_tower.json",
}

HOTSPOT_OUTPUT_DIR = "results/hotspot/expanded"
SUMMARY_TABLE = "results/tables/expanded_hotspot_validation.csv"
REPORT_OUTPUT = "results/reports/expanded_hotspot_report.md"
MANIFEST_OUTPUT = "results/hotspot/expanded_hotspot_manifest.csv"
SAMPLE_PERIOD_S = 0.00001  # 10us sample period for HotSpot power trace

SUMMARY_FIELDS = [
    "topology",
    "scale",
    "case_id",
    "method_id",
    "makespan_s",
    "peak_power_w",
    "proxy_peak_temperature_c",
    "proxy_peak_region",
    "proxy_peak_die",
    "die_count",
    "flp_path",
    "ptrace_path",
    "sample_count",
    "solver_status",
    "notes",
]


@dataclass
class CaseResult:
    topology: str
    scale: str
    case_id: str
    method_id: str
    makespan_s: float
    peak_power_w: float
    proxy_peak_temperature_c: float
    proxy_peak_region: str
    proxy_peak_die: str
    die_count: int
    flp_path: str
    ptrace_path: str
    sample_count: int
    solver_status: str
    notes: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Expanded HotSpot validation: 3 topologies x 3 scales x 2-3 methods."
    )
    parser.add_argument("--lane-count", type=int, default=8, help="FPP lane count.")
    parser.add_argument(
        "--power-profile",
        default="nominal",
        choices=["tight", "nominal", "relaxed"],
        help="Power budget profile.",
    )
    parser.add_argument(
        "--run-cpsat",
        action="store_true",
        help="Include M5 CP-SAT scheduling (adds ~5s per case).",
    )
    parser.add_argument("--time-limit-s", type=float, default=10.0, help="CP-SAT time limit per case.")
    parser.add_argument(
        "--sample-period-s",
        type=float,
        default=SAMPLE_PERIOD_S,
        help="HotSpot power trace sample period.",
    )
    parser.add_argument(
        "--output-dir",
        default=HOTSPOT_OUTPUT_DIR,
        help="Output directory for .flp/.ptrace files.",
    )
    parser.add_argument(
        "--summary-output",
        default=SUMMARY_TABLE,
        help="Output CSV path for summary table.",
    )
    parser.add_argument(
        "--report-output",
        default=REPORT_OUTPUT,
        help="Output Markdown report path.",
    )
    parser.add_argument(
        "--manifest-output",
        default=MANIFEST_OUTPUT,
        help="Output HotSpot manifest CSV path.",
    )
    parser.add_argument(
        "--skip-cpsat",
        action="store_true",
        help="Skip CP-SAT entirely (overrides --run-cpsat).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    include_cpsat = args.run_cpsat and not args.skip_cpsat

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results: list[CaseResult] = []
    export_rows: list[HotSpotExportRow] = []

    total = len(CASES)
    for idx, ((topology, scale), case_path) in enumerate(sorted(CASES.items()), 1):
        print(f"\n[{idx}/{total}] {topology} {scale}: {case_path}")
        model = load_system_model(case_path)

        case_results, case_exports = process_case(
            model=model,
            topology=topology,
            scale=scale,
            output_dir=output_dir,
            include_cpsat=include_cpsat,
            time_limit_s=args.time_limit_s,
            sample_period_s=args.sample_period_s,
            lane_count=args.lane_count,
        )
        results.extend(case_results)
        export_rows.extend(case_exports)

    # Write outputs
    write_summary_csv(results, args.summary_output)
    write_report(results, export_rows, args.report_output)
    write_hotspot_export_manifest(export_rows, args.manifest_output)

    # Print summary
    print("\n" + "=" * 72)
    print(f"Total cases processed: {total}")
    print(f"Total method results: {len(results)}")
    print(f"Total HotSpot exports: {len(export_rows)}")
    print(f"Summary table: {args.summary_output}")
    print(f"Report: {args.report_output}")
    print(f"Manifest: {args.manifest_output}")
    print(f"HotSpot inputs: {output_dir}/")

    # Quick validation
    print("\n## Quick Validation")
    by_topology: dict[str, list[CaseResult]] = {}
    for r in results:
        by_topology.setdefault(r.topology, []).append(r)

    for topology in ["2.5D", "3D", "5.5D"]:
        case_results = by_topology.get(topology, [])
        if not case_results:
            continue
        peaks = [r.proxy_peak_temperature_c for r in case_results]
        methods = sorted(set(r.method_id for r in case_results))
        print(f"  {topology}: {len(case_results)} results, {len(methods)} methods, "
              f"temps {min(peaks):.1f}-{max(peaks):.1f}C, "
              f"methods: {methods}")


def process_case(
    model: SystemModel,
    topology: str,
    scale: str,
    output_dir: Path,
    include_cpsat: bool,
    time_limit_s: float,
    sample_period_s: float,
    lane_count: int,
) -> tuple[list[CaseResult], list[HotSpotExportRow]]:
    from experiments.run_m10_benchmark_sweep import resource_variant

    schedule_model = resource_variant(model, lane_count=lane_count, power_profile="nominal")

    all_rows = rows_from_recipes(RecipeGenerator(schedule_model).generate_all())
    pareto_rows = pareto_prune(all_rows).kept_rows

    # Select fastest recipe per target
    fastest_rows = _select_fastest_per_target(pareto_rows)

    schedules: list[tuple[str, str, ScheduleResult]] = [
        ("fixed_fastest", "Fixed fastest recipe", greedy_schedule(schedule_model, fastest_rows)),
        ("m4_greedy", "M4 greedy recipe scheduling", greedy_schedule(schedule_model, pareto_rows)),
    ]
    solver_info: dict[str, str] = {
        "fixed_fastest": "greedy",
        "m4_greedy": "greedy",
    }

    if include_cpsat:
        try:
            cpsat_schedule, info = solve_cpsat_schedule(
                schedule_model, pareto_rows, time_limit_s=time_limit_s
            )
            schedules.append(("m5_cpsat", "M5 CP-SAT", cpsat_schedule))
            solver_info["m5_cpsat"] = info.status_name
        except Exception:
            print(f"  [SKIP] CP-SAT unavailable or failed for {model.case_id}")

    # Write floorplan (one per case, shared across methods)
    flp_path = output_dir / f"{model.case_id}.flp"
    write_hotspot_floorplan(schedule_model, flp_path)

    results: list[CaseResult] = []
    export_rows: list[HotSpotExportRow] = []

    for method_id, method_label, schedule in schedules:
        schedule_id = f"{model.case_id}::{method_id}"

        # Thermal proxy evaluation
        thermal_result = evaluate_schedule_thermal(schedule_model, schedule.phases, schedule_id)
        peak_die = _peak_die_from_hotspots(thermal_result.hotspots)

        # Write HotSpot power trace
        ptrace_path = output_dir / f"{model.case_id}__{method_id}.ptrace"
        sample_count = write_hotspot_power_trace(
            schedule_model, schedule.phases, ptrace_path,
            sample_period_s=sample_period_s,
        )

        results.append(CaseResult(
            topology=topology,
            scale=scale,
            case_id=model.case_id,
            method_id=method_id,
            makespan_s=schedule.makespan_s,
            peak_power_w=schedule.peak_power_w,
            proxy_peak_temperature_c=thermal_result.peak_temperature_c,
            proxy_peak_region=thermal_result.peak_region,
            proxy_peak_die=peak_die,
            die_count=len(model.dies),
            flp_path=flp_path.as_posix(),
            ptrace_path=ptrace_path.as_posix(),
            sample_count=sample_count,
            solver_status=solver_info.get(method_id, ""),
            notes="",
        ))

        export_rows.append(HotSpotExportRow(
            case_id=model.case_id,
            schedule_id=method_id,
            floorplan_path=flp_path.as_posix(),
            power_trace_path=ptrace_path.as_posix(),
            sample_period_s=sample_period_s,
            sample_count=sample_count,
            region_count=len(model.dies),
            notes="Expanded HotSpot validation input. Run HotSpot on Linux VM to validate.",
        ))

        print(f"  {method_id}: makespan={schedule.makespan_s:.6f}s, "
              f"peak_temp={thermal_result.peak_temperature_c:.2f}C, "
              f"peak_die={peak_die}, samples={sample_count}")

    return results, export_rows


def _select_fastest_per_target(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    selected: dict[str, tuple[float, dict[str, object]]] = {}
    for row in rows:
        target_id = str(row["target_id"])
        time_s = float(row.get("total_time_s", 0.0))
        if target_id not in selected or time_s < selected[target_id][0]:
            selected[target_id] = (time_s, row)
    return [item[1] for item in selected.values()]


def _peak_die_from_hotspots(hotspots: list[Any]) -> str:
    if not hotspots:
        return "N/A"
    peak = max(hotspots, key=lambda h: h.peak_temperature_c)
    return peak.die_id


def write_summary_csv(results: list[CaseResult], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        for result in results:
            writer.writerow(asdict(result))


def write_report(
    results: list[CaseResult],
    export_rows: list[HotSpotExportRow],
    output_path: str | Path,
) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Expanded HotSpot Validation Report",
        "",
        "This report covers 3 topologies x 3 scales x 2-3 scheduling methods.",
        "HotSpot-compatible .flp and .ptrace files have been generated.",
        "Actual HotSpot execution requires a Linux VM with the HotSpot simulator installed.",
        "",
        f"- Total method results: {len(results)}",
        f"- Total HotSpot export files: {len(export_rows)}",
        "",
        "## Summary Table",
        "",
        "| topology | scale | case_id | method | makespan_s | peak_power_w | proxy_peak_c | proxy_peak_die |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for r in results:
        lines.append(
            f"| {r.topology} | {r.scale} | {r.case_id} | {r.method_id} | "
            f"{r.makespan_s:.9f} | {r.peak_power_w:.3f} | "
            f"{r.proxy_peak_temperature_c:.2f} | {r.proxy_peak_die} |"
        )

    # Per-topology summary
    lines.extend(["", "## Per-Topology Summary", ""])
    for topology in ["2.5D", "3D", "5.5D"]:
        case_results = [r for r in results if r.topology == topology]
        if not case_results:
            continue
        peaks = [r.proxy_peak_temperature_c for r in case_results]
        methods = sorted(set(r.method_id for r in case_results))
        scales = sorted(set(r.scale for r in case_results))
        lines.append(f"### {topology}")
        lines.append(f"- Methods: {', '.join(methods)}")
        lines.append(f"- Scales: {', '.join(scales)}")
        lines.append(f"- Results: {len(case_results)}")
        lines.append(f"- Temperature range: {min(peaks):.2f}C - {max(peaks):.2f}C")
        lines.append("")

    # Per-method comparison
    lines.extend(["## Per-Method Temperature Comparison", ""])
    for method_id in sorted(set(r.method_id for r in results)):
        method_results = [r for r in results if r.method_id == method_id]
        if not method_results:
            continue
        peaks = [r.proxy_peak_temperature_c for r in method_results]
        lines.append(f"- **{method_id}**: {len(method_results)} runs, "
                     f"avg peak {sum(peaks)/len(peaks):.2f}C, "
                     f"range {min(peaks):.2f}-{max(peaks):.2f}C")

    # HotSpot export summary
    lines.extend([
        "",
        "## HotSpot Export Files",
        "",
        f"All .flp and .ptrace files are in `results/hotspot/expanded/`.",
        "",
        "| case_id | schedule_id | floorplan | ptrace | samples | regions |",
        "| --- | --- | --- | --- | ---: | ---: |",
    ])
    for row in export_rows:
        flp_name = Path(row.floorplan_path).name
        ptrace_name = Path(row.power_trace_path).name
        lines.append(
            f"| {row.case_id} | {row.schedule_id} | `{flp_name}` | "
            f"`{ptrace_name}` | {row.sample_count} | {row.region_count} |"
        )

    # Instructions for running HotSpot
    lines.extend([
        "",
        "## How to Run HotSpot Later",
        "",
        "HotSpot is a C++ thermal simulator that must be compiled and run on Linux.",
        "If the Linux VM with HotSpot is not currently available, follow these steps:",
        "",
        "### Prerequisites",
        "",
        "1. Linux VM with `hotspot` installed (e.g., Ubuntu 20.04+)",
        "2. HotSpot binary compiled from: https://github.com/uvahotspot/HotSpot",
        "",
        "### Running HotSpot",
        "",
        "```bash",
        "# On the Linux VM, copy the entire expanded/ directory",
        "scp -r results/hotspot/expanded/ user@linux-vm:~/hotspot_inputs/",
        "",
        "# SSH into the VM and run HotSpot for each case",
        "ssh user@linux-vm",
        "cd ~/hotspot_inputs/",
        "",
        "# Example: run HotSpot for one case+method combination",
        "hotspot -c hotspot.config -f m10_small_d695_3d_stack.flp \\",
        "  -p m10_small_d695_3d_stack__m4_greedy.ptrace \\",
        "  -o m10_small_d695_3d_stack__m4_greedy.ttrace",
        "",
        "# Batch process all .ptrace files",
        "for ptrace in *.ptrace; do",
        "  base=\"${ptrace%.ptrace}\"",
        "  flp=\"${base%__*}.flp\"",
        "  hotspot -c hotspot.config -f \"$flp\" -p \"$ptrace\" -o \"${base}.ttrace\"",
        "done",
        "```",
        "",
        "### Interpreting Results",
        "",
        "- HotSpot outputs `.ttrace` files with per-block temperature traces",
        "- Compare HotSpot peak temperatures with the proxy peak temperatures in this report",
        "- The proxy should preserve the temperature ordering across methods even if absolute values differ",
        "",
        "### Alternative: Automated Remote Execution",
        "",
        "If the Linux VM is available and configured with SSH key access, use:",
        "",
        "```bash",
        "python experiments/run_m12_hotspot_remote_validation.py \\",
        "  --manifest results/hotspot/expanded_hotspot_manifest.csv \\",
        "  --ssh-user <user> --ssh-host <host> --ssh-key <path>",
        "```",
        "",
        "---",
        f"*Report generated by run_extended_hotspot_validation.py*",
    ])

    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
