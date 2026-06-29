"""V4 Core Experiment: TAP Time-Multiplexed Scheduling with Mandatory Tasks.

Section 0.4 of the paper revision plan: demonstrates that the scheduling
framework correctly schedules ALL mandatory test tasks (not one per target),
and that BIST execution phases from different dies overlap in time.

Key departure from pre-v4 experiments:
  - Uses TaskGenerator (NOT RecipeGenerator)
  - Each die has MULTIPLE mandatory tasks (e.g. 2 INTEST cores + 1 BIST + 1 EXTEST)
  - Schedulers run in "task mode" (AddExactlyOne per task_id)
  - Ablation conditions isolate: serial-only, BIST parallelism, FPP, thermal

Usage:
  python experiments/run_v4_core_experiment.py [--case PATH] [--time-limit-s 10]
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.model import SystemModel, load_system_model
from src.recipes import TaskGenerator, rows_from_variants
from src.schedulers import (
    CpSatUnavailableError,
    ScheduleResult,
    SchedulingError,
    greedy_schedule,
    solve_cpsat_schedule,
    write_schedule_csv,
)

# ---------------------------------------------------------------------------
# Experiment configuration
# ---------------------------------------------------------------------------

DEFAULT_CASE = "configs/cases/v4/v4_core_4die_task.json"

FIELDNAMES = [
    "case_id",
    "condition",
    "condition_label",
    "scheduler",
    "status",
    "error",
    "makespan_s",
    "task_count",
    "scheduled_task_count",
    "bist_task_count",
    "bist_overlap_ratio",
    "tap_utilization",
    "fpp_utilization",
    "peak_power_w",
    "peak_temperature_c",
    "peak_thermal_region",
    "thermal_violations",
    "solver_status",
    "solver_wall_time_s",
]


@dataclass
class ConditionResult:
    """Aggregated metrics for one ablation condition."""
    case_id: str
    condition: str
    condition_label: str
    scheduler: str
    status: str = "ok"
    error: str = ""
    makespan_s: float = 0.0
    task_count: int = 0
    scheduled_task_count: int = 0
    bist_task_count: int = 0
    bist_overlap_ratio: float = 0.0
    tap_utilization: float = 0.0
    fpp_utilization: float = 0.0
    peak_power_w: float = 0.0
    peak_temperature_c: float = 0.0
    peak_thermal_region: str = ""
    thermal_violations: int = 0
    solver_status: str = ""
    solver_wall_time_s: float = 0.0
    schedule_result: ScheduleResult | None = field(default=None, repr=False)


# ---------------------------------------------------------------------------
# Model builders for each ablation condition
# ---------------------------------------------------------------------------

def disable_fpp(model: SystemModel) -> SystemModel:
    """Return a model copy with FPP effectively disabled (0 lanes)."""
    raw = deepcopy(model.raw)
    raw["resource_limits"]["total_fpp_lanes"] = 0
    for channel in raw["ieee1838_access"].get("fpp_channels", []):
        channel["max_lanes"] = 0
    for group in raw.get("resource_groups", {}).get("fpp_capacity_groups", []):
        group["capacity"] = 0
        group["members"] = []
    variant = SystemModel(raw=raw, source_path=model.source_path)
    return variant


def set_fpp_lanes(model: SystemModel, lane_count: int) -> SystemModel:
    """Return a model copy with the specified number of FPP lanes."""
    raw = deepcopy(model.raw)
    raw["resource_limits"]["total_fpp_lanes"] = lane_count
    lane_objects = raw["ieee1838_access"].get("fpp_lanes", [])
    capped_members = [lane["lane_id"] for lane in lane_objects[:lane_count]]
    for channel in raw["ieee1838_access"].get("fpp_channels", []):
        channel["max_lanes"] = lane_count
    for group in raw.get("resource_groups", {}).get("fpp_capacity_groups", []):
        group["capacity"] = lane_count
        group["members"] = [m for m in group.get("members", []) if m in capped_members]
    variant = SystemModel(raw=raw, source_path=model.source_path)
    return variant


def raise_power_limit(model: SystemModel, power_w: float) -> SystemModel:
    """Return a model copy with increased power limit to avoid thermal throttling."""
    raw = deepcopy(model.raw)
    raw["resource_limits"]["max_total_power_w"] = power_w
    for domain in raw.get("resource_groups", {}).get("power_domains", []):
        domain["max_power_w"] = power_w
    variant = SystemModel(raw=raw, source_path=model.source_path)
    return variant


def disable_bist(model: SystemModel) -> SystemModel:
    """Return a model copy where BIST is disabled (for pure_serial baseline)."""
    raw = deepcopy(model.raw)
    for obj in raw["test_objects"]:
        if "bist" in obj and obj["bist"].get("enabled", False):
            obj["bist"]["enabled"] = False
        # Remove B and H from supported_recipes if present
        supported = obj.get("supported_recipes", [])
        obj["supported_recipes"] = [r for r in supported if r not in {"B", "H"}]
    variant = SystemModel(raw=raw, source_path=model.source_path)
    return variant


# ---------------------------------------------------------------------------
# Metric computation
# ---------------------------------------------------------------------------

def compute_bist_overlap_ratio(result: ScheduleResult) -> float:
    """Fraction of BIST phases that are overlapped with other BIST phases.

    Returns 0.0 if there are 1 or fewer BIST phases.
    For 2 BIST phases: overlap_time / min(phase1_duration, phase2_duration).
    For >2: sum of pairwise overlaps / total BIST duration.
    """
    bist_phases = [p for p in result.phases if "BIST_RUN" in p.phase_name]
    if len(bist_phases) <= 1:
        return 0.0
    total_overlap = 0.0
    total_duration = sum(p.duration_s for p in bist_phases)
    if total_duration <= 0:
        return 0.0
    n = len(bist_phases)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = bist_phases[i], bist_phases[j]
            overlap = max(0.0, min(a.end_s, b.end_s) - max(a.start_s, b.start_s))
            total_overlap += overlap
    return total_overlap / total_duration


def compute_tap_utilization(result: ScheduleResult) -> float:
    """Fraction of makespan that the TAP serial chain is busy."""
    if result.makespan_s <= 0:
        return 0.0
    return result.serial_busy_time_s / result.makespan_s


def compute_fpp_utilization(model: SystemModel, result: ScheduleResult) -> float:
    """Fraction of FPP lane-time used vs available."""
    total_lanes = int(model.resource_limits.get("total_fpp_lanes", 0))
    if result.makespan_s <= 0 or total_lanes <= 0:
        return 0.0
    return result.fpp_lane_time_s / (result.makespan_s * total_lanes)


def thermal_evaluate(model: SystemModel, result: ScheduleResult) -> tuple[float, str, int]:
    """Run thermal evaluation on the schedule. Returns (peak_temp_c, peak_region, violations)."""
    try:
        from src.evaluators.thermal import evaluate_schedule_thermal
        thermal = evaluate_schedule_thermal(model, result.phases, result.case_id)
        return thermal.peak_temperature_c, thermal.peak_region, thermal.violation_count
    except ImportError:
        return 0.0, "", 0


# ---------------------------------------------------------------------------
# Parse args
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="V4 Core Experiment: TAP time-multiplexed scheduling with mandatory tasks."
    )
    parser.add_argument(
        "--case", default=DEFAULT_CASE,
        help="Case JSON path.",
    )
    parser.add_argument(
        "--time-limit-s", type=float, default=10.0,
        help="CP-SAT time limit per solver invocation.",
    )
    parser.add_argument(
        "--output-csv",
        default="results/tables/v4_core_experiment.csv",
        help="Output CSV path.",
    )
    parser.add_argument(
        "--report-output",
        default="results/reports/v4_core_experiment_report.md",
        help="Output Markdown report path.",
    )
    parser.add_argument(
        "--schedule-dir",
        default="results/schedules/v4",
        help="Directory for per-condition schedule CSVs.",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main experiment
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()
    base_model = load_system_model(args.case)
    print(f"V4 Core Experiment")
    print(f"  case: {base_model.case_id}")
    print(f"  dies: {len(base_model.dies)}")
    print(f"  test_objects: {len(base_model.test_objects)}")
    print(f"  interconnects: {len(base_model.interconnects)}")

    # Generate tasks and variants ONCE (from the base model with FPP available)
    # Each ablation condition uses adapted model copies to change resource limits
    gen = TaskGenerator(base_model)
    tasks = gen.generate_tasks()
    bist_tasks = [t for t in tasks if t.test_type == "BIST"]
    print(f"  total tasks: {len(tasks)}")
    print(f"  BIST tasks: {len(bist_tasks)}")
    print()

    # Show task breakdown
    for t in tasks:
        print(f"    {t.task_id:40s} die={t.die_id:5s} type={t.test_type:6s}")

    all_results: list[ConditionResult] = []

    # --- Condition 1: pure_serial ---
    run_condition(
        base_model, "pure_serial", "Pure Serial (no BIST, no FPP)",
        lambda m: disable_bist(disable_fpp(m)),
        tasks, all_results, args,
    )

    # --- Condition 2: bist_parallel ---
    run_condition(
        base_model, "bist_parallel", "BIST Parallel (per-die engines, no FPP)",
        lambda m: disable_fpp(m),
        tasks, all_results, args,
    )

    # --- Condition 3: bist_fpp ---
    run_condition(
        base_model, "bist_fpp", "BIST+FPP (per-die engines, 8 FPP lanes)",
        lambda m: set_fpp_lanes(m, 8),
        tasks, all_results, args,
    )

    # --- Condition 4: bist_fpp_thermal ---
    def _bist_fpp_thermal(m: SystemModel) -> SystemModel:
        m2 = set_fpp_lanes(m, 8)
        return raise_power_limit(m2, 8.0)
    run_condition(
        base_model, "bist_fpp_thermal", "BIST+FPP+Thermal (all mechanisms, thermal monitoring)",
        _bist_fpp_thermal,
        tasks, all_results, args,
    )

    # --- Write outputs ---
    write_csv(all_results, args.output_csv)
    write_report(all_results, args.report_output, base_model.case_id)

    print(f"\nResults written:")
    print(f"  CSV: {args.output_csv}")
    print(f"  Report: {args.report_output}")
    print(f"  Schedule CSVs: {args.schedule_dir}/")

    # --- Verification diagnostics ---
    print("\n" + "=" * 70)
    print("VERIFICATION DIAGNOSTICS")
    print("=" * 70)
    for cr in all_results:
        if cr.schedule_result is None:
            continue
        print(f"\n--- {cr.condition_label} ({cr.scheduler}) ---")
        bist_phases = [p for p in cr.schedule_result.phases if "BIST_RUN" in p.phase_name]
        if bist_phases:
            print(f"  BIST phases: {len(bist_phases)}")
            for p in bist_phases:
                print(f"    {p.target_id:15s} on {p.die_id:5s}: {p.start_s*1e6:.0f}us -> {p.end_s*1e6:.0f}us")
            if len(bist_phases) >= 2:
                print("  Pairwise BIST overlaps:")
                for i, a in enumerate(bist_phases):
                    for j, b in enumerate(bist_phases):
                        if i >= j:
                            continue
                        overlap = max(0.0, min(a.end_s, b.end_s) - max(a.start_s, b.start_s))
                        status = "OVERLAP" if overlap > 1e-9 else "no overlap"
                        print(f"    {a.target_id} vs {b.target_id}: {overlap*1e6:.0f}us {status}")
        else:
            print("  No BIST phases (expected for pure_serial)")

        # Task accounting
        scheduled_task_ids = {str(r["task_id"]) for r in cr.schedule_result.selected_rows}
        print(f"  Scheduled tasks: {len(scheduled_task_ids)} / {cr.task_count}")


def run_condition(
    base_model: SystemModel,
    condition: str,
    condition_label: str,
    model_adapter,
    tasks: list,
    all_results: list[ConditionResult],
    args: argparse.Namespace,
) -> None:
    """Run one ablation condition with both greedy and CP-SAT schedulers."""
    print(f"\n{'='*60}")
    print(f"Condition: {condition_label}")
    print(f"{'='*60}")

    model = model_adapter(base_model)
    gen = TaskGenerator(model)
    variants = gen.generate_all_variants()
    variant_rows = rows_from_variants(variants)

    print(f"  Variants generated: {len(variants)}")
    print(f"  FPP lanes: {model.resource_limits.get('total_fpp_lanes', 0)}")
    print(f"  BIST tasks in model: {sum(1 for t in gen.generate_tasks() if t.test_type == 'BIST')}")

    bist_task_count = sum(1 for t in gen.generate_tasks() if t.test_type == "BIST")
    task_count = len(gen.generate_tasks())

    # --- Greedy ---
    print("  Running greedy scheduler ...")
    try:
        g_result = greedy_schedule(model, variant_rows)
        g_cr = make_condition_result(
            model, g_result, condition, condition_label, "greedy", task_count, bist_task_count
        )
        all_results.append(g_cr)
        write_schedule_for_condition(g_result, condition, "greedy", args.schedule_dir)
        print(f"    makespan: {g_result.makespan_s:.9f} s, tasks: {g_cr.scheduled_task_count}")
    except SchedulingError as exc:
        print(f"    GREEDY FAILED: {exc}")
        all_results.append(failed_result(model.case_id, condition, condition_label, "greedy", str(exc), task_count, bist_task_count))

    # --- CP-SAT ---
    print("  Running CP-SAT solver ...")
    try:
        c_result, c_info = solve_cpsat_schedule(model, variant_rows, time_limit_s=args.time_limit_s)
        c_cr = make_condition_result(
            model, c_result, condition, condition_label, "cpsat", task_count, bist_task_count,
            solver_status=c_info.status_name, solver_wall_time_s=c_info.wall_time_s,
        )
        all_results.append(c_cr)
        write_schedule_for_condition(c_result, condition, "cpsat", args.schedule_dir)
        print(f"    status={c_info.status_name}, makespan: {c_result.makespan_s:.9f} s, tasks: {c_cr.scheduled_task_count}")
    except CpSatUnavailableError as exc:
        print(f"    CP-SAT UNAVAILABLE: {exc}")
        all_results.append(failed_result(model.case_id, condition, condition_label, "cpsat", str(exc), task_count, bist_task_count))
    except RuntimeError as exc:
        print(f"    CP-SAT FAILED: {exc}")
        all_results.append(failed_result(model.case_id, condition, condition_label, "cpsat", str(exc), task_count, bist_task_count))


def make_condition_result(
    model: SystemModel,
    result: ScheduleResult,
    condition: str,
    condition_label: str,
    scheduler: str,
    task_count: int,
    bist_task_count: int,
    solver_status: str = "",
    solver_wall_time_s: float = 0.0,
) -> ConditionResult:
    scheduled_task_ids = {str(r["task_id"]) for r in result.selected_rows}
    peak_temp, peak_region, violations = thermal_evaluate(model, result)
    return ConditionResult(
        case_id=model.case_id,
        condition=condition,
        condition_label=condition_label,
        scheduler=scheduler,
        status="ok",
        error="",
        makespan_s=result.makespan_s,
        task_count=task_count,
        scheduled_task_count=len(scheduled_task_ids),
        bist_task_count=bist_task_count,
        bist_overlap_ratio=compute_bist_overlap_ratio(result),
        tap_utilization=compute_tap_utilization(result),
        fpp_utilization=compute_fpp_utilization(model, result),
        peak_power_w=result.peak_power_w,
        peak_temperature_c=peak_temp,
        peak_thermal_region=peak_region,
        thermal_violations=violations,
        solver_status=solver_status,
        solver_wall_time_s=solver_wall_time_s,
        schedule_result=result,
    )


def failed_result(
    case_id: str,
    condition: str,
    condition_label: str,
    scheduler: str,
    error: str,
    task_count: int,
    bist_task_count: int,
) -> ConditionResult:
    return ConditionResult(
        case_id=case_id,
        condition=condition,
        condition_label=condition_label,
        scheduler=scheduler,
        status="failed",
        error=error,
        task_count=task_count,
        bist_task_count=bist_task_count,
    )


def write_schedule_for_condition(
    result: ScheduleResult,
    condition: str,
    scheduler: str,
    schedule_dir: str | Path,
) -> None:
    """Write a schedule CSV for Gantt visualization."""
    output = Path(schedule_dir) / f"{condition}_{scheduler}.csv"
    write_schedule_csv(result, output)


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------

def write_csv(results: list[ConditionResult], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        for cr in results:
            row = asdict(cr)
            del row["schedule_result"]  # not serializable
            # Ensure all fields are present
            clean = {}
            for field in FIELDNAMES:
                clean[field] = row.get(field, "")
            writer.writerow(clean)


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------

def write_report(results: list[ConditionResult], output_path: str | Path, case_id: str) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# V4 Core Experiment Report",
        "",
        f"- Case: `{case_id}`",
        f"- Description: Section 0.4 task-multiplexed scheduling with mandatory tasks",
        f"- Total conditions: {len(set(r.condition for r in results))}",
        f"- Total runs: {len(results)}",
        "",
        "## Conditions",
        "",
        "| Condition | Scheduler | Status | Makespan (s) | Tasks Scheduled | BIST Overlap | TAP Util | FPP Util | Peak Power (W) | Peak Temp (C) |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for cr in results:
        lines.append(
            f"| {cr.condition_label} | {cr.scheduler} | {cr.status} | "
            f"{cr.makespan_s:.9f} | {cr.scheduled_task_count}/{cr.task_count} | "
            f"{cr.bist_overlap_ratio:.4f} | {cr.tap_utilization:.4f} | "
            f"{cr.fpp_utilization:.4f} | {cr.peak_power_w:.4f} | "
            f"{cr.peak_temperature_c:.2f} |"
        )

    # Speedup summary
    lines.extend(["", "## Speedup vs Pure Serial", ""])
    # Find pure_serial greedy baseline
    baseline = None
    for cr in results:
        if cr.condition == "pure_serial" and cr.scheduler == "greedy" and cr.status == "ok":
            baseline = cr
            break
    if baseline and baseline.makespan_s > 0:
        lines.append("| Condition | Scheduler | Makespan (s) | Speedup vs Pure Serial |")
        lines.append("| --- | --- | ---: | ---: |")
        for cr in results:
            if cr.status == "ok":
                speedup = baseline.makespan_s / cr.makespan_s if cr.makespan_s > 0 else 0
                lines.append(
                    f"| {cr.condition_label} | {cr.scheduler} | "
                    f"{cr.makespan_s:.9f} | {speedup:.2f}x |"
                )

    # BIST overlap details
    lines.extend(["", "## BIST Overlap Analysis", ""])
    lines.append("| Condition | Scheduler | BIST Tasks | Overlap Ratio |")
    lines.append("| --- | --- | ---: | ---: |")
    for cr in results:
        if cr.status == "ok":
            lines.append(
                f"| {cr.condition_label} | {cr.scheduler} | "
                f"{cr.bist_task_count} | {cr.bist_overlap_ratio:.4f} |"
            )

    lines.extend([
        "",
        "## Notes",
        "",
        "- All tasks are mandatory (unlike pre-v4 where recipes were alternatives per target).",
        "- Task mode: AddExactlyOne constraint per task_id (one variant per task).",
        "- BIST engines are per-die (capacity=1 each), so BIST on die0 and die1 can overlap.",
        "- TAP is released during LOCAL_BIST_RUN, enabling parallel BIST execution.",
        "- FPP data offload uses standard-defined FPP lanes (IEEE 1838-2019 Clause 7).",
        "- Thermal evaluation uses first-order RC proxy model.",
    ])

    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
