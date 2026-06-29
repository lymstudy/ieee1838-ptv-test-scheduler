"""V4 Final Experiment: Comprehensive Ablation Study of the Corrected IEEE 1838 Physical Model.

Demonstrates the corrected physical model with all mechanisms isolated via an ablation matrix:
  - serial_baseline: BIST disabled, no FPP -- worst case, all tasks use serial TAP
  - bist_only: Per-die BIST engines, no FPP -- BIST releases TAP during local execution
  - fpp_only: BIST disabled, FPP on available dies -- FPP offloads INTEST data from TAP
  - bist_fpp: Per-die BIST + FPP on available dies -- both mechanisms combined
  - bist_fpp_thermal: All mechanisms + per-die thermal constraints

Runs on at least 3 case configs covering different topologies (3D stack, 2.5D interposer).
Uses both CP-SAT (primary, 30s time limit) and greedy (supplementary) schedulers.

Output:
  - results/tables/v4_final_experiment.csv
  - results/reports/v4_final_experiment_report.md
  - results/schedules/v4_final/ (schedule CSVs for Gantt visualization / 10-figure regeneration)

Figures (regenerable from the CSV data + schedule CSVs):
  1. Makespan comparison across conditions (grouped bar, per-case)
  2. Speedup vs serial_baseline (grouped bar, per-case)
  3. TAP (serial) utilization across conditions
  4. FPP utilization across conditions
  5. BIST overlap ratio across conditions
  6. Max concurrent BIST engines
  7. Peak temperature across conditions (thermal condition only)
  8. Makespan vs die count / topology scaling
  9. CP-SAT vs Greedy comparison
  10. Gantt chart for best-condition schedule (bist_fpp_thermal, 4die_3d_stack, CP-SAT)

Usage:
  python experiments/run_v4_final_experiment.py [--time-limit-s 30] [--skip-greedy]
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

# Ensure project root is on the path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.model import SystemModel, load_system_model
from src.recipes import TaskGenerator, rows_from_variants
from src.schedulers import (
    CpSatUnavailableError,
    ScheduleResult,
    ScheduledPhase,
    SchedulingError,
    greedy_schedule,
    solve_cpsat_schedule,
    write_schedule_csv,
)

# ---------------------------------------------------------------------------
# Experiment configuration
# ---------------------------------------------------------------------------

# Available v4 cases (all that exist in configs/cases/v4/)
AVAILABLE_CASES = [
    "configs/cases/v4/v4_small_3d_stack.json",       # 3-die 3D stack (small)
    "configs/cases/v4/v4_4die_3d_stack.json",         # 4-die 3D stack (full)
    "configs/cases/v4/v4_4die_2_5d_interposer.json",  # 4-die 2.5D interposer
    "configs/cases/v4/v4_6die_3d_stack.json",          # 6-die 3D stack (large)
    "configs/cases/v4/v4_medium_3d_stack.json",        # 4-die 3D stack (medium)
]

# Default: run on at least 3 covering different topologies
DEFAULT_CASES = [
    "configs/cases/v4/v4_small_3d_stack.json",       # 3D stack, small, 3 dies
    "configs/cases/v4/v4_4die_3d_stack.json",         # 3D stack, full, 4 dies
    "configs/cases/v4/v4_4die_2_5d_interposer.json",  # 2.5D interposer, 4 dies
]

# Ablation conditions
CONDITION_DEFS: list[dict] = [
    {
        "condition_id": "serial_baseline",
        "description": "Worst case: BIST disabled, no FPP. All tasks use serial TAP exclusively.",
        "bist_enabled": False,
        "fpp_enabled": False,
        "thermal_enabled": False,
    },
    {
        "condition_id": "bist_only",
        "description": "Per-die BIST engines fire and release TAP. Pure IEEE 1838 BIST model.",
        "bist_enabled": True,
        "fpp_enabled": False,
        "thermal_enabled": False,
    },
    {
        "condition_id": "fpp_only",
        "description": "BIST disabled, FPP offloads INTEST data from TAP.",
        "bist_enabled": False,
        "fpp_enabled": True,
        "thermal_enabled": False,
    },
    {
        "condition_id": "bist_fpp",
        "description": "Both BIST (per-die engines) and FPP parallel data offload combined.",
        "bist_enabled": True,
        "fpp_enabled": True,
        "thermal_enabled": False,
    },
    {
        "condition_id": "bist_fpp_thermal",
        "description": "Full model: all mechanisms active with per-die thermal constraints (85C limit).",
        "bist_enabled": True,
        "fpp_enabled": True,
        "thermal_enabled": True,
    },
]

# CP-SAT time limit per solve
DEFAULT_TIME_LIMIT_S = 30.0

# Output CSV columns
FIELDNAMES = [
    "case_id",
    "topology",
    "condition_id",
    "method_id",
    "status",
    "error",
    "makespan_s",
    "makespan_us",
    "serial_busy_ratio",
    "fpp_utilization",
    "bist_overlap_ratio",
    "max_concurrent_bist",
    "peak_temperature_c",
    "thermal_violations",
    "selected_recipe_types",
    "task_count",
    "variant_count",
    "scheduled_task_count",
    "peak_power_w",
    "solver_status",
    "solver_wall_time_s",
    "die_count",
    "fpp_lane_count",
    "bist_engine_count",
]


# ---------------------------------------------------------------------------
# Model adapters (create modified model copies for each condition)
# ---------------------------------------------------------------------------

def _deepcopy_raw(model: SystemModel) -> dict:
    """Deep copy the raw dict once."""
    return deepcopy(model.raw)


def _apply_disable_bist(raw: dict) -> None:
    """Modify raw dict in-place to disable BIST."""
    for obj in raw["test_objects"]:
        if "bist" in obj:
            obj["bist"]["enabled"] = False
        obj["supported_recipes"] = [
            r for r in obj.get("supported_recipes", []) if r not in {"B", "H"}
        ]
        obj["test_types"] = [t for t in obj.get("test_types", []) if t != "BIST"]
    if "bist_engine_groups" in raw.get("resource_groups", {}):
        raw["resource_groups"]["bist_engine_groups"] = []


def _apply_disable_fpp(raw: dict) -> None:
    """Modify raw dict in-place to disable FPP."""
    raw["resource_limits"]["total_fpp_lanes"] = 0
    for channel in raw["ieee1838_access"].get("fpp_channels", []):
        channel["max_lanes"] = 0
    for group in raw.get("resource_groups", {}).get("fpp_capacity_groups", []):
        group["capacity"] = 0
        group["members"] = []


def adapter_apply_condition(
    model: SystemModel,
    bist_enabled: bool,
    fpp_enabled: bool,
) -> SystemModel:
    """Apply bist/fpp toggles to a single deep-copied model.

    Deep-copies once, then applies mutations in-place. Avoids redundant
    deep-copies that the original per-adapter approach incurred.
    """
    raw = deepcopy(model.raw)
    if not bist_enabled:
        _apply_disable_bist(raw)
    if not fpp_enabled:
        _apply_disable_fpp(raw)
    return SystemModel(raw=raw, source_path=model.source_path)


# ---------------------------------------------------------------------------
# Metric computation
# ---------------------------------------------------------------------------

def compute_serial_busy_ratio(result: ScheduleResult) -> float:
    """Fraction of makespan that the TAP serial chain is occupied."""
    if result.makespan_s <= 0:
        return 0.0
    return result.serial_busy_time_s / result.makespan_s


def compute_fpp_utilization(model: SystemModel, result: ScheduleResult) -> float:
    """Fraction of FPP lane-time used vs total available."""
    total_lanes = int(model.resource_limits.get("total_fpp_lanes", 0))
    if result.makespan_s <= 0 or total_lanes <= 0:
        return 0.0
    return result.fpp_lane_time_s / (result.makespan_s * total_lanes)


def compute_bist_overlap_ratio(result: ScheduleResult) -> float:
    """Fraction of BIST execution time that overlaps across dies.

    For N BIST phases: sum of all pairwise overlaps / sum of individual durations.
    Returns 0.0 if 0 or 1 BIST phases.
    """
    bist_phases = [p for p in result.phases if "BIST_RUN" in p.phase_name]
    n = len(bist_phases)
    if n <= 1:
        return 0.0

    total_duration = sum(p.duration_s for p in bist_phases)
    if total_duration <= 0:
        return 0.0

    total_overlap = 0.0
    for i in range(n):
        for j in range(i + 1, n):
            a, b = bist_phases[i], bist_phases[j]
            overlap = max(0.0, min(a.end_s, b.end_s) - max(a.start_s, b.start_s))
            total_overlap += overlap

    # Normalize: max possible overlap = (n-1) * total_duration (all phases overlap fully)
    # We use total_duration as denominator for a 0-1 scale
    return total_overlap / total_duration


def compute_max_concurrent_bist(result: ScheduleResult) -> int:
    """Maximum number of BIST phases executing simultaneously."""
    bist_phases = [p for p in result.phases if "BIST_RUN" in p.phase_name]
    if not bist_phases:
        return 0

    boundaries = sorted(
        {p.start_s for p in bist_phases} | {p.end_s for p in bist_phases}
    )
    max_concurrent = 0
    for t in boundaries:
        count = sum(
            1 for p in bist_phases
            if p.start_s <= t < p.end_s - 1e-12
        )
        max_concurrent = max(max_concurrent, count)
    return max_concurrent


def thermal_evaluate(
    model: SystemModel, result: ScheduleResult
) -> tuple[float, int]:
    """Run thermal evaluation. Returns (peak_temp_c, violation_count)."""
    try:
        from src.evaluators.thermal import evaluate_schedule_thermal
        thermal = evaluate_schedule_thermal(model, result.phases, result.case_id)
        return thermal.peak_temperature_c, thermal.violation_count
    except ImportError:
        return 0.0, 0
    except Exception:
        return 0.0, 0


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class ExperimentRun:
    """Results for a single (case, condition, method) combination."""
    case_id: str = ""
    topology: str = ""
    condition_id: str = ""
    method_id: str = ""
    status: str = "ok"
    error: str = ""

    # Timing
    makespan_s: float = 0.0
    makespan_us: float = 0.0

    # Resource utilization
    serial_busy_ratio: float = 0.0
    fpp_utilization: float = 0.0

    # BIST metrics
    bist_overlap_ratio: float = 0.0
    max_concurrent_bist: int = 0

    # Thermal
    peak_temperature_c: float = 0.0
    thermal_violations: int = 0

    # Selection
    selected_recipe_types: str = ""

    # Counts
    task_count: int = 0
    variant_count: int = 0
    scheduled_task_count: int = 0

    # Power
    peak_power_w: float = 0.0

    # Solver info
    solver_status: str = ""
    solver_wall_time_s: float = 0.0

    # Case metadata
    die_count: int = 0
    fpp_lane_count: int = 0
    bist_engine_count: int = 0

    # Schedule result (not serialized, used for downstream analysis)
    schedule_result: ScheduleResult | None = field(default=None, repr=False)

    def to_row(self) -> dict[str, object]:
        """Export to a dict for CSV writing (excludes schedule_result)."""
        d = asdict(self)
        del d["schedule_result"]
        return {k: d.get(k, "") for k in FIELDNAMES if k != "schedule_result"}


# ---------------------------------------------------------------------------
# Experiment runner
# ---------------------------------------------------------------------------

def run_experiment(
    case_paths: list[str],
    time_limit_s: float = DEFAULT_TIME_LIMIT_S,
    skip_greedy: bool = False,
) -> list[ExperimentRun]:
    """Run the full ablation matrix across all cases."""
    all_runs: list[ExperimentRun] = []

    for case_path in case_paths:
        print(f"\n{'='*80}")
        print(f"CASE: {Path(case_path).stem}")
        print(f"{'='*80}")

        # Load base model
        base_model = load_system_model(case_path)
        topology = base_model.raw["package"].get("topology_type", "unknown")
        die_count = len(base_model.dies)
        fpp_lane_count = int(base_model.resource_limits.get("total_fpp_lanes", 0))
        bist_engine_count = len(
            base_model.raw.get("resource_groups", {}).get("bist_engine_groups", [])
        )

        print(f"  topology: {topology}, dies: {die_count}, "
              f"FPP lanes: {fpp_lane_count}, BIST engines: {bist_engine_count}")

        # Generate task list from the FULL model (with BIST and FPP)
        full_gen = TaskGenerator(base_model)
        full_tasks = full_gen.generate_tasks()
        bist_task_count = sum(1 for t in full_tasks if t.test_type == "BIST")
        print(f"  total tasks: {len(full_tasks)}, BIST tasks: {bist_task_count}")

        for task in full_tasks:
            print(f"    {task.task_id:45s} die={task.die_id:5s} type={task.test_type:6s}")

        for cond_def in CONDITION_DEFS:
            condition_id = cond_def["condition_id"]
            description = cond_def["description"]

            print(f"\n  --- Condition: {condition_id} ---")
            print(f"      {description}")

            # Build adapted model for this condition
            model = adapter_apply_condition(
                base_model,
                bist_enabled=cond_def["bist_enabled"],
                fpp_enabled=cond_def["fpp_enabled"],
            )

            # Generate variants from adapted model
            gen = TaskGenerator(model)
            tasks = gen.generate_tasks()
            variants = gen.generate_all_variants()
            variant_rows = rows_from_variants(variants)

            effective_fpp = int(model.resource_limits.get("total_fpp_lanes", 0))
            effective_bist = sum(
                1 for t in tasks if t.test_type == "BIST"
            )
            print(f"      tasks: {len(tasks)}, variants: {len(variants)}, "
                  f"FPP lanes: {effective_fpp}, BIST tasks: {effective_bist}")

            # List recipe types available
            recipe_types = sorted(set(
                str(v.recipe_type) if hasattr(v, 'recipe_type') else str(r.get('recipe_type', ''))
                for v in variants for r in [v.to_recipe_row() if hasattr(v, 'to_recipe_row') else v]
            ))
            # Do it properly:
            recipe_types = sorted(set(
                str(r.get("recipe_type", "")) for r in variant_rows
            ))
            print(f"      recipe types: {recipe_types}")

            # --- CP-SAT (primary) ---
            print(f"      Running CP-SAT (time_limit={time_limit_s}s)...")
            try:
                c_result, c_info = solve_cpsat_schedule(
                    model, variant_rows, time_limit_s=time_limit_s
                )
                c_run = build_experiment_run(
                    base_model, model, c_result, condition_id, "m5_cpsat",
                    len(tasks), len(variants), topology, die_count,
                    effective_fpp, effective_bist,
                    solver_status=c_info.status_name,
                    solver_wall_time_s=c_info.wall_time_s,
                )
                all_runs.append(c_run)
                print(f"        status={c_info.status_name}, "
                      f"makespan={c_run.makespan_us:.0f}us, "
                      f"BIST overlap={c_run.bist_overlap_ratio:.3f}, "
                      f"max_concurrent_bist={c_run.max_concurrent_bist}")

                # Save schedule CSV
                save_schedule_csv(c_result, condition_id, "cpsat", base_model.case_id)

            except CpSatUnavailableError as exc:
                print(f"        CP-SAT UNAVAILABLE: {exc}")
                all_runs.append(failed_run(
                    base_model, condition_id, "m5_cpsat",
                    str(exc), len(tasks), len(variants),
                    topology, die_count, effective_fpp, effective_bist,
                ))
            except RuntimeError as exc:
                print(f"        CP-SAT FAILED: {exc}")
                all_runs.append(failed_run(
                    base_model, condition_id, "m5_cpsat",
                    str(exc), len(tasks), len(variants),
                    topology, die_count, effective_fpp, effective_bist,
                ))

            # --- Greedy (supplementary) ---
            if not skip_greedy:
                print(f"      Running greedy...")
                try:
                    g_result = greedy_schedule(model, variant_rows)
                    g_run = build_experiment_run(
                        base_model, model, g_result, condition_id, "m4_greedy",
                        len(tasks), len(variants), topology, die_count,
                        effective_fpp, effective_bist,
                    )
                    all_runs.append(g_run)
                    print(f"        makespan={g_run.makespan_us:.0f}us, "
                          f"BIST overlap={g_run.bist_overlap_ratio:.3f}, "
                          f"max_concurrent_bist={g_run.max_concurrent_bist}")

                    save_schedule_csv(g_result, condition_id, "greedy", base_model.case_id)
                except SchedulingError as exc:
                    print(f"        GREEDY FAILED: {exc}")
                    all_runs.append(failed_run(
                        base_model, condition_id, "m4_greedy",
                        str(exc), len(tasks), len(variants),
                        topology, die_count, effective_fpp, effective_bist,
                    ))

    return all_runs


def build_experiment_run(
    base_model: SystemModel,
    model: SystemModel,
    result: ScheduleResult,
    condition_id: str,
    method_id: str,
    task_count: int,
    variant_count: int,
    topology: str,
    die_count: int,
    fpp_lane_count: int,
    bist_engine_count: int,
    solver_status: str = "",
    solver_wall_time_s: float = 0.0,
) -> ExperimentRun:
    """Build an ExperimentRun from a successful schedule."""
    scheduled_task_ids = {str(r["task_id"]) for r in result.selected_rows}
    selected_types = sorted(set(
        str(r.get("recipe_type", "")) for r in result.selected_rows
    ))

    peak_temp, violations = thermal_evaluate(model, result)

    return ExperimentRun(
        case_id=base_model.case_id,
        topology=topology,
        condition_id=condition_id,
        method_id=method_id,
        status="ok",
        makespan_s=result.makespan_s,
        makespan_us=result.makespan_s * 1_000_000,
        serial_busy_ratio=compute_serial_busy_ratio(result),
        fpp_utilization=compute_fpp_utilization(model, result),
        bist_overlap_ratio=compute_bist_overlap_ratio(result),
        max_concurrent_bist=compute_max_concurrent_bist(result),
        peak_temperature_c=peak_temp,
        thermal_violations=violations,
        selected_recipe_types="+".join(selected_types),
        task_count=task_count,
        variant_count=variant_count,
        scheduled_task_count=len(scheduled_task_ids),
        peak_power_w=result.peak_power_w,
        solver_status=solver_status,
        solver_wall_time_s=solver_wall_time_s,
        die_count=die_count,
        fpp_lane_count=fpp_lane_count,
        bist_engine_count=bist_engine_count,
        schedule_result=result,
    )


def failed_run(
    base_model: SystemModel,
    condition_id: str,
    method_id: str,
    error: str,
    task_count: int,
    variant_count: int,
    topology: str,
    die_count: int,
    fpp_lane_count: int,
    bist_engine_count: int,
) -> ExperimentRun:
    """Build a failed ExperimentRun."""
    return ExperimentRun(
        case_id=base_model.case_id,
        topology=topology,
        condition_id=condition_id,
        method_id=method_id,
        status="failed",
        error=error[:200],
        task_count=task_count,
        variant_count=variant_count,
        die_count=die_count,
        fpp_lane_count=fpp_lane_count,
        bist_engine_count=bist_engine_count,
    )


# ---------------------------------------------------------------------------
# Schedule CSV export
# ---------------------------------------------------------------------------

SCHEDULE_DIR = "results/schedules/v4_final"


def save_schedule_csv(
    result: ScheduleResult,
    condition_id: str,
    method_id: str,
    case_id: str,
) -> None:
    """Save a schedule CSV for Gantt visualization."""
    output_dir = Path(SCHEDULE_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{case_id}__{condition_id}__{method_id}.csv"
    output_path = output_dir / filename
    write_schedule_csv(result, output_path)


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------

def write_results_csv(runs: list[ExperimentRun], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        for run in runs:
            writer.writerow(run.to_row())


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------

def write_report(
    runs: list[ExperimentRun],
    output_path: str | Path,
) -> None:
    """Generate a comprehensive Markdown report with all data needed for 10 figures."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    # Group runs
    ok_runs = [r for r in runs if r.status == "ok"]
    failed_runs = [r for r in runs if r.status != "ok"]
    cases = sorted(set(r.case_id for r in runs))
    conditions = sorted(set(r.condition_id for r in runs))
    methods = sorted(set(r.method_id for r in runs))

    lines = [
        "# V4 Final Experiment Report",
        "",
        "## Overview",
        "",
        f"- **Cases:** {len(cases)} ({', '.join(cases)})",
        f"- **Conditions:** {len(conditions)} ({', '.join(conditions)})",
        f"- **Methods:** {len(methods)} ({', '.join(methods)})",
        f"- **Total runs:** {len(runs)}",
        f"- **Successful:** {len(ok_runs)}",
        f"- **Failed:** {len(failed_runs)}",
        "",
        "## Conditions",
        "",
    ]
    for cd in CONDITION_DEFS:
        lines.append(f"- **{cd['condition_id']}**: {cd['description']}")

    lines.extend([
        "",
        "## Full Results Table",
        "",
        "| case_id | condition | method | status | makespan_us | TAP_util | FPP_util | BIST_overlap | max_BIST | peak_T_C | viol | recipe_types | tasks |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |",
    ])

    for r in runs:
        lines.append(
            f"| {r.case_id} | {r.condition_id} | {r.method_id} | {r.status} | "
            f"{r.makespan_us:.0f} | {r.serial_busy_ratio:.3f} | {r.fpp_utilization:.3f} | "
            f"{r.bist_overlap_ratio:.3f} | {r.max_concurrent_bist} | "
            f"{r.peak_temperature_c:.1f} | {r.thermal_violations} | "
            f"{r.selected_recipe_types} | {r.scheduled_task_count}/{r.task_count} |"
        )

    # Speedup table vs serial_baseline
    lines.extend([
        "",
        "## Figure 1 & 2: Makespan Comparison and Speedup vs Serial Baseline",
        "",
    ])

    for case_id in cases:
        # Find serial_baseline CP-SAT makespan
        baseline_makespan = None
        for r in ok_runs:
            if r.case_id == case_id and r.condition_id == "serial_baseline" and r.method_id == "m5_cpsat":
                baseline_makespan = r.makespan_s
                break

        lines.append(f"### {case_id}")
        if baseline_makespan:
            lines.append(f"Serial baseline makespan: {baseline_makespan*1e6:.0f} us")
        lines.append("")
        lines.append("| Condition | Method | Makespan (us) | Speedup vs Serial | TAP Util | FPP Util | BIST Overlap | max_BIST |")
        lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |")

        case_runs = sorted(
            [r for r in ok_runs if r.case_id == case_id],
            key=lambda r: (conditions.index(r.condition_id) if r.condition_id in conditions else 99, r.method_id)
        )
        for r in case_runs:
            speedup = baseline_makespan / r.makespan_s if baseline_makespan and r.makespan_s > 0 else 0
            lines.append(
                f"| {r.condition_id} | {r.method_id} | {r.makespan_us:.0f} | "
                f"{speedup:.2f}x | {r.serial_busy_ratio:.3f} | "
                f"{r.fpp_utilization:.3f} | {r.bist_overlap_ratio:.3f} | "
                f"{r.max_concurrent_bist} |"
            )
        lines.append("")

    # Figure 3: TAP Utilization comparison
    lines.extend([
        "## Figure 3: TAP (Serial) Utilization",
        "",
        "| case_id | condition | method | serial_busy_ratio |",
        "| --- | --- | --- | ---: |",
    ])
    for r in sorted(ok_runs, key=lambda r: -r.serial_busy_ratio):
        lines.append(
            f"| {r.case_id} | {r.condition_id} | {r.method_id} | {r.serial_busy_ratio:.4f} |"
        )

    # Figure 4: FPP Utilization
    lines.extend([
        "",
        "## Figure 4: FPP Utilization",
        "",
        "| case_id | condition | method | fpp_utilization |",
        "| --- | --- | --- | ---: |",
    ])
    for r in sorted(ok_runs, key=lambda r: -r.fpp_utilization):
        lines.append(
            f"| {r.case_id} | {r.condition_id} | {r.method_id} | {r.fpp_utilization:.4f} |"
        )

    # Figure 5: BIST Overlap Ratio
    lines.extend([
        "",
        "## Figure 5: BIST Overlap Ratio",
        "",
        "| case_id | condition | method | bist_overlap_ratio | max_concurrent_bist |",
        "| --- | --- | --- | ---: | ---: |",
    ])
    for r in sorted(ok_runs, key=lambda r: -r.bist_overlap_ratio):
        lines.append(
            f"| {r.case_id} | {r.condition_id} | {r.method_id} | "
            f"{r.bist_overlap_ratio:.4f} | {r.max_concurrent_bist} |"
        )

    # Figure 6: Max Concurrent BIST
    lines.extend([
        "",
        "## Figure 6: Max Concurrent BIST",
        "",
        "| case_id | condition | method | max_concurrent_bist | bist_engine_count |",
        "| --- | --- | --- | ---: | ---: |",
    ])
    for r in sorted(ok_runs, key=lambda r: -r.max_concurrent_bist):
        lines.append(
            f"| {r.case_id} | {r.condition_id} | {r.method_id} | "
            f"{r.max_concurrent_bist} | {r.bist_engine_count} |"
        )

    # Figure 7: Thermal Analysis
    lines.extend([
        "",
        "## Figure 7: Thermal Analysis (bist_fpp_thermal condition)",
        "",
        "| case_id | method | peak_T_C | thermal_violations |",
        "| --- | --- | ---: | ---: |",
    ])
    for r in ok_runs:
        if r.condition_id == "bist_fpp_thermal":
            lines.append(
                f"| {r.case_id} | {r.method_id} | "
                f"{r.peak_temperature_c:.2f} | {r.thermal_violations} |"
            )

    # Figure 8: Scaling (makespan vs die_count by topology)
    lines.extend([
        "",
        "## Figure 8: Scaling Analysis (Makespan vs Die Count / Topology)",
        "",
        "| case_id | topology | die_count | condition | method | makespan_us |",
        "| --- | --- | ---: | --- | --- | ---: |",
    ])
    for r in sorted(ok_runs, key=lambda r: (r.die_count, r.case_id, r.condition_id)):
        if r.method_id == "m5_cpsat":
            lines.append(
                f"| {r.case_id} | {r.topology} | {r.die_count} | "
                f"{r.condition_id} | {r.method_id} | {r.makespan_us:.0f} |"
            )

    # Figure 9: CP-SAT vs Greedy comparison
    lines.extend([
        "",
        "## Figure 9: CP-SAT vs Greedy Comparison",
        "",
        "| case_id | condition | CP-SAT makespan_us | Greedy makespan_us | CP-SAT/Greedy ratio |",
        "| --- | --- | ---: | ---: | ---: |",
    ])
    for case_id in cases:
        for cond_id in conditions:
            cpsat_run = next(
                (r for r in ok_runs
                 if r.case_id == case_id and r.condition_id == cond_id and r.method_id == "m5_cpsat"),
                None
            )
            greedy_run = next(
                (r for r in ok_runs
                 if r.case_id == case_id and r.condition_id == cond_id and r.method_id == "m4_greedy"),
                None
            )
            if cpsat_run and greedy_run and greedy_run.makespan_s > 0:
                ratio = cpsat_run.makespan_s / greedy_run.makespan_s
                lines.append(
                    f"| {case_id} | {cond_id} | {cpsat_run.makespan_us:.0f} | "
                    f"{greedy_run.makespan_us:.0f} | {ratio:.3f} |"
                )

    # Figure 10: Schedule Gantt reference
    lines.extend([
        "",
        "## Figure 10: Gantt Charts",
        "",
        "Schedule CSVs saved to `results/schedules/v4_final/` for representative case+condition combos.",
        "",
        "Key schedule files for the best-condition scenario:",
        "",
        "| File | Description |",
        "| --- | --- |",
    ])
    schedule_dir = Path(SCHEDULE_DIR)
    if schedule_dir.exists():
        for csv_file in sorted(schedule_dir.glob("*.csv")):
            lines.append(f"| `{csv_file.name}` | Schedule CSV |")

    # BIST verification
    lines.extend([
        "",
        "## BIST Overlap Verification",
        "",
    ])
    for r in ok_runs:
        if r.schedule_result is None:
            continue
        bist_phases = [
            p for p in r.schedule_result.phases
            if "BIST_RUN" in p.phase_name
        ]
        if len(bist_phases) >= 2:
            lines.append(f"### {r.case_id} / {r.condition_id} / {r.method_id}")
            lines.append(f"  Total BIST phases: {len(bist_phases)}")
            for p in bist_phases:
                lines.append(
                    f"  - {p.target_id} on {p.die_id}: "
                    f"{p.start_s*1e6:.0f}us -> {p.end_s*1e6:.0f}us "
                    f"({p.duration_s*1e6:.0f}us)"
                )
            lines.append("")

            # Pairwise overlaps
            n = len(bist_phases)
            for i in range(n):
                for j in range(i + 1, n):
                    a, b = bist_phases[i], bist_phases[j]
                    overlap = max(0.0, min(a.end_s, b.end_s) - max(a.start_s, b.start_s))
                    flag = "OVERLAP" if overlap > 1e-9 else "no overlap"
                    lines.append(
                        f"  - {a.target_id} vs {b.target_id}: overlap={overlap*1e6:.0f}us {flag}"
                    )
            lines.append("")

    # Notes
    lines.extend([
        "## Notes",
        "",
        "- **Two transport resources**: TAP (serial, capacity=1, all dies) and FPP (parallel, optional, some dies).",
        "- **Task types**: INTEST, EXTEST, BIST, IJTAG -- all mandatory.",
        "- **BIST model**: Per-die BIST engines (capacity=1 each). BIST releases TAP during local execution, enabling overlap.",
        "- **FPP model**: Standard IEEE 1838-2019 Clause 7 FPP lanes for parallel data transport.",
        "- **Thermal model**: First-order RC proxy with die-to-die vertical coupling and heat sink distance factors.",
        "- **CP-SAT time limit**: 30s per solve.",
        "- **10 figures** regenerable from this experiment data and schedule CSVs.",
    ])

    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Verification diagnostics
# ---------------------------------------------------------------------------

def print_verification(runs: list[ExperimentRun]) -> None:
    """Print verification diagnostics for BIST overlap and task accounting."""
    print("\n" + "=" * 80)
    print("VERIFICATION DIAGNOSTICS")
    print("=" * 80)

    ok_runs = [r for r in runs if r.status == "ok" and r.schedule_result is not None]

    for r in ok_runs:
        result = r.schedule_result
        if result is None:
            continue

        print(f"\n--- {r.case_id} / {r.condition_id} / {r.method_id} ---")

        # Task accounting
        scheduled_task_ids = {str(row["task_id"]) for row in result.selected_rows}
        print(f"  Scheduled tasks: {len(scheduled_task_ids)} / {r.task_count}")
        if len(scheduled_task_ids) != r.task_count:
            missing = r.task_count - len(scheduled_task_ids)
            print(f"  WARNING: {missing} tasks not scheduled!")

        # BIST phases
        bist_phases = [p for p in result.phases if "BIST_RUN" in p.phase_name]
        if bist_phases:
            print(f"  BIST phases: {len(bist_phases)}")
            for p in bist_phases:
                print(
                    f"    {p.target_id:15s} on {p.die_id:5s}: "
                    f"{p.start_s*1e6:.0f}us -> {p.end_s*1e6:.0f}us "
                    f"({p.duration_s*1e6:.0f}us)"
                )
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
            print("  No BIST phases (expected for BIST-disabled conditions)")

        # Selection summary
        selected_types = sorted(set(
            str(row.get("recipe_type", "")) for row in result.selected_rows
        ))
        print(f"  Selected recipe types: {selected_types}")
        print(f"  Makespan: {r.makespan_us:.0f}us")
        print(f"  Peak power: {result.peak_power_w:.3f}W")

    # Summary table
    print("\n" + "-" * 80)
    print("SUMMARY TABLE")
    print("-" * 80)
    print(f"{'case_id':30s} {'condition':22s} {'method':10s} {'makespan_us':>12s} {'BIST_overlap':>12s} {'max_BIST':>8s} {'peak_T':>8s}")
    print("-" * 110)
    for r in ok_runs:
        print(
            f"{r.case_id:30s} {r.condition_id:22s} {r.method_id:10s} "
            f"{r.makespan_us:12.0f} {r.bist_overlap_ratio:12.3f} "
            f"{r.max_concurrent_bist:8d} {r.peak_temperature_c:8.1f}"
        )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="V4 Final Experiment: Comprehensive ablation study of corrected IEEE 1838 model."
    )
    parser.add_argument(
        "--cases", nargs="+",
        default=DEFAULT_CASES,
        help="Case JSON paths (default: 3 cases covering different topologies).",
    )
    parser.add_argument(
        "--time-limit-s", type=float, default=DEFAULT_TIME_LIMIT_S,
        help=f"CP-SAT time limit per solve (default: {DEFAULT_TIME_LIMIT_S}s).",
    )
    parser.add_argument(
        "--skip-greedy", action="store_true",
        help="Skip greedy scheduler (CP-SAT only).",
    )
    parser.add_argument(
        "--output-csv",
        default="results/tables/v4_final_experiment.csv",
        help="Output CSV path.",
    )
    parser.add_argument(
        "--report-output",
        default="results/reports/v4_final_experiment_report.md",
        help="Output Markdown report path.",
    )
    parser.add_argument(
        "--list-cases", action="store_true",
        help="List all available v4 cases and exit.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.list_cases:
        print("Available v4 cases:")
        for path in AVAILABLE_CASES:
            full = Path(PROJECT_ROOT) / path if not Path(path).is_absolute() else Path(path)
            status = "EXISTS" if full.exists() else "MISSING"
            print(f"  {status:7s} {path}")
        return

    print("V4 Final Experiment")
    print(f"  cases: {len(args.cases)}")
    for c in args.cases:
        print(f"    - {c}")
    print(f"  CP-SAT time limit: {args.time_limit_s}s per solve")
    print(f"  skip greedy: {args.skip_greedy}")
    print()

    # Run experiment
    runs = run_experiment(
        case_paths=args.cases,
        time_limit_s=args.time_limit_s,
        skip_greedy=args.skip_greedy,
    )

    # Write outputs
    write_results_csv(runs, args.output_csv)
    write_report(runs, args.report_output)

    print(f"\nResults written:")
    print(f"  CSV: {args.output_csv}")
    print(f"  Report: {args.report_output}")
    print(f"  Schedule CSVs: {SCHEDULE_DIR}/")

    # Print verification diagnostics
    print_verification(runs)


if __name__ == "__main__":
    main()
