"""Audit schedule consistency for the realistic UART statistics workload."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.audit_example_benchmark_schedule import AuditSummary, audit_schedule, read_schedule
from experiments.run_realistic_uart_workload import run as run_realistic_uart
from src.workload.benchmark_adapter import load_benchmark_stats


RESULT_DIR = ROOT / "results" / "benchmarks" / "realistic_uart"
AUDIT_DIR = RESULT_DIR / "audit"
STATS_PATH = ROOT / "benchmarks" / "realistic_uart_stats.yaml"
SUMMARY_PATH = RESULT_DIR / "scheduler_metrics_summary.csv"
SCHEDULE_PATHS = {
    "bandwidth_greedy": RESULT_DIR / "greedy_schedule.csv",
    "ptv_aware": RESULT_DIR / "ptv_schedule.csv",
}


def read_metrics() -> dict[str, dict[str, str]]:
    """Read realistic UART scheduler metrics by scheduler name."""

    with SUMMARY_PATH.open(newline="", encoding="utf-8") as handle:
        return {row["scheduler_name"]: row for row in csv.DictReader(handle)}


def write_markdown_summary(summaries: dict[str, AuditSummary], metrics: dict[str, dict[str, str]]) -> Path:
    """Write a realistic UART schedule audit summary."""

    greedy = summaries["bandwidth_greedy"]
    ptv = summaries["ptv_aware"]
    greedy_metrics = metrics["bandwidth_greedy"]
    ptv_metrics = metrics["ptv_aware"]
    tat_delta = ptv.tat - greedy.tat
    bug_statement = "No scheduler bug was found in this audit."
    if greedy.fpp_capacity_violation_count or greedy.dwr_overlap_violation_count:
        bug_statement = "Potential greedy resource violation found; inspect audit CSVs."
    if ptv.fpp_capacity_violation_count or ptv.dwr_overlap_violation_count:
        bug_statement = "Potential PTV-aware resource violation found; inspect audit CSVs."

    if ptv.tat <= greedy.tat:
        tat_interpretation = (
            "PTV-aware TAT is less than or equal to bandwidth-greedy TAT in this manually specified UART statistics case. "
            "The audit attributes this to heuristic task ordering and lower FPP idle lane-seconds, not to a general dominance claim."
        )
    else:
        tat_interpretation = (
            "PTV-aware TAT is greater than bandwidth-greedy TAT in this manually specified UART statistics case. "
            "This is the expected constrained-scheduling tradeoff when PTV-aware limits physical-risk concurrency."
        )

    path = AUDIT_DIR / "schedule_comparison_audit.md"
    lines = [
        "# Realistic UART Schedule Audit",
        "",
        "This audit covers a manually specified realistic statistics case. It is not RTL-extracted benchmark validation.",
        "",
        "## Summary",
        "",
        bug_statement,
        "",
        tat_interpretation,
        "",
        "## Scheduler Metrics",
        "",
        "| scheduler | TAT | final finishing task | peak temperature | peak IR-drop | temperature violations | voltage violations | max parallelism |",
        "|---|---:|---|---:|---:|---:|---:|---:|",
    ]
    for name in ("bandwidth_greedy", "ptv_aware"):
        summary = summaries[name]
        metric = metrics[name]
        lines.append(
            f"| {name} | {summary.tat:.12g} | {', '.join(summary.final_finishing_tasks)} | "
            f"{float(metric['peak_temperature']):.12g} | {float(metric['peak_ir_drop']):.12g} | "
            f"{metric['temperature_violation_count']} | {metric['voltage_violation_count']} | {summary.max_parallelism} |"
        )
    lines.extend(
        [
            "",
            "## Resource Checks",
            "",
            "| scheduler | FPP capacity violation intervals | DWR overlap violation intervals | global idle time | FPP idle lane-seconds | first scan-shift start |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for name in ("bandwidth_greedy", "ptv_aware"):
        summary = summaries[name]
        first_scan = "" if summary.first_scan_shift_start is None else f"{summary.first_scan_shift_start:.12g}"
        lines.append(
            f"| {name} | {summary.fpp_capacity_violation_count} | {summary.dwr_overlap_violation_count} | "
            f"{summary.global_idle_time:.12g} | {summary.fpp_idle_lane_seconds:.12g} | {first_scan} |"
        )
    lines.extend(
        [
            "",
            "## Violation Comparison",
            "",
            f"- Bandwidth-greedy voltage violations: {greedy_metrics['voltage_violation_count']}.",
            f"- PTV-aware voltage violations: {ptv_metrics['voltage_violation_count']}.",
            f"- Bandwidth-greedy temperature violations: {greedy_metrics['temperature_violation_count']}.",
            f"- PTV-aware temperature violations: {ptv_metrics['temperature_violation_count']}.",
            f"- TAT delta, PTV-aware - bandwidth-greedy: {tat_delta:.12g} s.",
            "",
            "## Interpretation",
            "",
            "The realistic UART statistics workload is manually specified from circuit-level estimates. The audit should be used to check consistency of the generated schedules and resource usage, not to claim real chip validation.",
            "",
            "If PTV-aware is close to or faster than bandwidth-greedy in this case, the explanation is heuristic ordering and reduced resource blocking. If PTV-aware is slower, the explanation is physical-risk-aware throttling. In either case, the result should not be generalized beyond this workload without additional benchmark-derived data.",
            "",
            "## FPP Task Order",
            "",
            "Bandwidth-greedy FPP task order:",
            "",
            "```text",
            " -> ".join(greedy.fpp_task_order),
            "```",
            "",
            "PTV-aware FPP task order:",
            "",
            "```text",
            " -> ".join(ptv.fpp_task_order),
            "```",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run() -> dict[str, Path]:
    """Run the realistic UART schedule audit."""

    if not all(path.exists() for path in SCHEDULE_PATHS.values()) or not SUMMARY_PATH.exists():
        run_realistic_uart()

    stats = load_benchmark_stats(STATS_PATH)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    summaries: dict[str, AuditSummary] = {}
    outputs: dict[str, Path] = {}
    for scheduler_name, schedule_path in SCHEDULE_PATHS.items():
        entries = read_schedule(schedule_path)
        output_name = "greedy_schedule_audit.csv" if scheduler_name == "bandwidth_greedy" else "ptv_schedule_audit.csv"
        output_path = AUDIT_DIR / output_name
        summaries[scheduler_name] = audit_schedule(
            scheduler_name=scheduler_name,
            entries=entries,
            fpp_lane_capacity=stats.fpp_lanes,
            vdd=stats.power_model.vdd,
            shared_resistance=stats.power_model.shared_resistance,
            output_path=output_path,
        )
        outputs[output_name.removesuffix(".csv")] = output_path

    outputs["schedule_comparison_audit"] = write_markdown_summary(summaries, read_metrics())
    return outputs


if __name__ == "__main__":
    outputs = run()
    print("Realistic UART schedule audit completed.")
    for name, path in outputs.items():
        print(f"{name}: {path.relative_to(ROOT)}")
