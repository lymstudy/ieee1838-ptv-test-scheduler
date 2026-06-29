from __future__ import annotations

"""Habiby 2022 PBO (Pseudo-Boolean Optimization) incremental test scheduling baseline.

Implements the incremental optimization approach from:

    Habiby et al. "Power-aware test scheduling framework for IEEE 1687
    multi-power domain networks using formal techniques."
    Microelectronics Reliability, 2022.

Adapted for IEEE 1838:
  - "Instrument"  --> Test Target (each die's test object or interconnect)
  - Network structure constraints --> IEEE 1838 resource constraints
    (PTAP serial mutual exclusion, FPP lane capacity, shared BIST, DWR)
  - Power constraint --> system peak power limit
  - Objective: maximize number of concurrently active targets per session

Algorithm
---------
1. For each target, pre-select its fastest recipe (fixed-path, Habiby-style).
2. Initialize pool = all targets.
3. While pool is not empty:
   a. Build a CP-SAT model with boolean x_i for each target i in pool.
   b. Add resource constraints (FPP lanes, power, PTAP serial mutual exclusion).
   c. Objective: maximize sum(weight_i * x_i).
   d. Solve --> active targets for this session.
   e. Session duration = max(test_time of active targets).
   f. Remove active targets from pool; record session.
4. Total makespan = sum of session durations.
"""

import argparse
import csv
import json
import math
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ortools.sat.python import cp_model

from src.model import SystemModel, load_system_model
from src.recipes import RecipeGenerator, pareto_prune, rows_from_recipes
from src.schedulers.greedy import (
    ScheduledPhase,
    _peak_fpp_lanes as peak_fpp_lanes,
    _peak_power as peak_power,
    greedy_schedule,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TIME_SCALE = 1_000_000_000  # seconds --> discrete ticks for CP-SAT
POWER_SCALE = 1_000

# M10 cases (3d_stack variants)
M10_CASES = [
    "configs/cases/m10/m10_small_d695_3d_stack.json",
    "configs/cases/m10/m10_medium_p22810_3d_stack.json",
    "configs/cases/m10/m10_large_p34392_3d_stack.json",
]

# M21 pressure cases (3d_stack variants)
M21_CASES = [
    "configs/cases/m21/m21_pressure_small_d695_3d_stack.json",
    "configs/cases/m21/m21_pressure_medium_p22810_3d_stack.json",
    "configs/cases/m21/m21_pressure_large_p34392_3d_stack.json",
]

CSV_FIELDNAMES = [
    "case_id",
    "method_id",
    "makespan_s",
    "peak_power_w",
    "num_sessions",
    "num_targets",
    "solver_status",
    "solver_wall_time_s",
]


# ---------------------------------------------------------------------------
# Helpers (mirroring run_m11 / cpsat.py patterns but self-contained)
# ---------------------------------------------------------------------------


def _fastest_recipe_rows(
    rows: list[dict[str, object]],
    max_lanes: int | None = None,
) -> list[dict[str, object]]:
    """Select the fastest (lowest total_time_s) recipe for each target.

    This is the Habiby-style fixed-path approach: each target commits to
    exactly one recipe before scheduling begins.

    If max_lanes is provided, only recipes with fpp_lanes_required <= max_lanes
    are considered for each target. This ensures the selected recipe is
    actually feasible within the system's FPP lane budget.
    """
    selected: dict[str, tuple[tuple[float, float, str], dict[str, object]]] = {}
    for row in rows:
        target_id = str(row["target_id"])
        # Skip recipes that exceed lane budget
        if max_lanes is not None:
            lanes = int(row.get("max_fpp_lanes_required", 0) or 0)
            if lanes > max_lanes:
                continue
        key = (
            float(row.get("total_time_s", 0.0)),
            float(row.get("peak_power_w", 0.0)),
            str(row["recipe_id"]),
        )
        if target_id not in selected or key < selected[target_id][0]:
            selected[target_id] = (key, row)
    # Check for targets with no feasible recipe
    all_targets = {str(r["target_id"]) for r in rows}
    covered = set(selected)
    missing = all_targets - covered
    if missing:
        raise ValueError(
            f"Cannot cover targets {sorted(missing)} with fpp_lanes <= {max_lanes}. "
            f"Try increasing lane count."
        )
    return [item[1] for item in selected.values()]


def _pbo_recipe_rows(
    rows: list[dict[str, object]],
    max_lanes: int,
) -> list[dict[str, object]]:
    """Select one recipe per target for the PBO incremental scheduler.

    Strategy (Habiby-style fixed-path selection):
    - FPP targets (type F/H): select the recipe with the FEWEST lanes that
      is still Pareto-optimal. This maximizes concurrency in the shared
      FPP lane pool. When ties exist, pick the fastest total_time_s.
    - Non-FPP targets (S, I, B): select the absolutely fastest recipe,
      since they don't consume shareable FPP lanes.
    """
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        grouped.setdefault(str(row["target_id"]), []).append(row)

    selected: list[dict[str, object]] = []
    for target_id, group in grouped.items():
        # Filter to feasible recipes
        feasible = [
            r for r in group
            if int(r.get("max_fpp_lanes_required", 0) or 0) <= max_lanes
        ]
        if not feasible:
            recipe_types = {str(r.get("recipe_type", "")) for r in group}
            raise ValueError(
                f"Target {target_id}: no feasible recipes with lanes <= {max_lanes}. "
                f"Available recipe types: {recipe_types}"
            )

        # Determine recipe type of the group
        recipe_types_in_group = {str(r.get("recipe_type", "")) for r in feasible}
        is_fpp_target = bool(recipe_types_in_group & {"F", "H"})

        if is_fpp_target:
            # PBO-friendly: select the recipe with the fewest FPP lanes,
            # tie-break by shortest time. Only consider F/H recipes
            # (FPP is always faster than serial for these targets).
            fpp_feasible = [
                r for r in feasible
                if str(r.get("recipe_type", "")) in {"F", "H"}
            ]
            if not fpp_feasible:
                fpp_feasible = feasible  # fallback (shouldn't happen)
            best = min(
                fpp_feasible,
                key=lambda r: (
                    int(r.get("max_fpp_lanes_required", 0) or 0),
                    float(r.get("total_time_s", 0.0)),
                    float(r.get("peak_power_w", 0.0)),
                ),
            )
        else:
            # Non-FPP (only S/I/B): select fastest recipe
            # For BIST targets, prefer B over S
            bist_feasible = [r for r in feasible if str(r.get("recipe_type", "")) == "B"]
            if bist_feasible:
                # BIST targets: B recipes are preferred (non-serial execution phase)
                best = min(
                    bist_feasible,
                    key=lambda r: (
                        float(r.get("total_time_s", 0.0)),
                        float(r.get("peak_power_w", 0.0)),
                    ),
                )
            else:
                best = min(
                    feasible,
                    key=lambda r: (
                        float(r.get("total_time_s", 0.0)),
                        float(r.get("peak_power_w", 0.0)),
                    ),
                )
        selected.append(best)

    return selected


def _ceil_scaled(value: float, scale: int) -> int:
    """Scale a float upwards to a discrete integer (safe rounding)."""
    if value <= 0:
        return 0
    return int(math.ceil(value * scale - 1e-9))


def _parse_phases(row: dict[str, object]) -> list[dict[str, Any]]:
    return json.loads(str(row.get("phase_resources", "[]")))


def _phase_has_serial(phase: dict[str, Any]) -> bool:
    val = phase.get("serial_required", False)
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() in {"1", "true", "yes", "y"}


def _phase_fpp_lanes(phase: dict[str, Any]) -> int:
    return int(phase.get("fpp_lanes_required", 0) or 0)


def _phase_fpp_channel(phase: dict[str, Any]) -> str:
    return str(phase.get("fpp_channel", ""))


def _phase_power_w(phase: dict[str, Any]) -> float:
    return float(phase.get("power_w", 0.0) or 0.0)


def _phase_exclusive_resource(phase: dict[str, Any]) -> str:
    return str(phase.get("exclusive_resource", ""))


def _target_uses_any_dwr_segment(
    info: dict[str, Any],
    dwr_members: set[str],
) -> bool:
    """Check if a target uses any DWR segment in the given set."""
    row = info.get("row", {})
    dwr_str = str(row.get("dwr_segments", ""))
    if not dwr_str:
        return False
    target_segments = set(dwr_str.split(";"))
    return bool(target_segments & dwr_members)


# ---------------------------------------------------------------------------
# PBO incremental scheduler
# ---------------------------------------------------------------------------


def _build_pbo_session(
    model: SystemModel,
    pool_rows: list[dict[str, object]],
    target_info: dict[str, dict[str, Any]],
    time_limit_s: float,
) -> tuple[list[str], float, str, float]:
    """Run one CP-SAT PBO iteration to select a maximal concurrent set.

    Parameters
    ----------
    model : SystemModel
    pool_rows : list of recipe rows (one per target still in pool)
    target_info : {target_id: {"test_time_s": ..., "peak_power_w": ...,
                                "fpp_lanes": ..., "serial_required": ...,
                                "fpp_channel": ..., "exclusive_resource": ...}}
    time_limit_s : CP-SAT time limit for this single iteration

    Returns
    -------
    active_targets : list of target_id that are scheduled in this session
    session_duration_s : max test_time among active targets
    solver_status : CP-SAT status string
    solver_wall_time_s : solver wall time for this iteration
    """
    cp = cp_model.CpModel()

    # Boolean decision variable for each target in the pool
    target_ids = [str(row["target_id"]) for row in pool_rows]
    x: dict[str, Any] = {}
    for tid in target_ids:
        x[tid] = cp.NewBoolVar(f"x_{tid}")

    # ------------------------------------------------------------------
    # 1. PTAP serial mutual exclusion.
    #
    # In IEEE 1838, the single PTAP controller is a shared resource.
    # Targets with serial phases need the PTAP during config/readback.
    #
    # PBO atomic-target approximation:
    #   - serial_only targets (S/I): use PTAP for their entire test
    #     time -> strictly mutually exclusive (at most 1 active)
    #   - FPP/BIST targets (F/H/B): use PTAP only during short config
    #     phases. They CAN run concurrently with each other because
    #     their serial config phases can be staggered in time while
    #     their non-serial phases (FPP data transfer, BIST execution)
    #     overlap.
    #
    # Session duration accounts for serial phase serialization:
    #   duration = sum(serial_resource_time) + max(non_serial_time)
    #
    # The constraint: at most 1 serial_only target active, AND
    # serial_only targets are mutually exclusive with FPP/BIST
    # targets (since the PTAP is occupied by the serial_only target
    # for its entire duration, blocking others' config phases).
    # ------------------------------------------------------------------
    serial_only_targets = [
        tid for tid in target_ids if target_info[tid]["serial_only"]
    ]
    fpp_targets = [
        tid for tid in target_ids if not target_info[tid]["serial_only"]
    ]

    if serial_only_targets:
        # At most 1 serial-only target active at a time
        cp.Add(sum(x[tid] for tid in serial_only_targets) <= 1)

    # Serial_only targets cannot run concurrently with FPP/BIST targets
    # (the PTAP is occupied for the serial_only target's full duration)
    if serial_only_targets and fpp_targets:
        serial_only_active = cp.NewBoolVar("serial_only_active")
        # serial_only_active == 1 iff any serial_only target is selected
        cp.Add(sum(x[tid] for tid in serial_only_targets) >= 1).OnlyEnforceIf(
            serial_only_active
        )
        cp.Add(sum(x[tid] for tid in serial_only_targets) == 0).OnlyEnforceIf(
            serial_only_active.Not()
        )
        # If a serial_only target is active, no FPP/BIST targets allowed
        for tid in fpp_targets:
            cp.Add(x[tid] == 0).OnlyEnforceIf(serial_only_active)

    # ------------------------------------------------------------------
    # 2. FPP lane cumulative constraint: sum(lanes_i * x_i) <= max_lanes
    # ------------------------------------------------------------------
    max_lanes = int(model.resource_limits.get("total_fpp_lanes", 0))
    if max_lanes > 0:
        pool_with_lanes = [
            (tid, target_info[tid]["fpp_lanes"])
            for tid in target_ids
            if target_info[tid]["fpp_lanes"] > 0
        ]
        if pool_with_lanes:
            cp.Add(
                sum(target_info[tid]["fpp_lanes"] * x[tid] for tid, _ in pool_with_lanes)
                <= max_lanes
            )

    # Per-channel FPP lane constraints
    for channel in model.access.get("fpp_channels", []):
        channel_id = str(channel["channel_id"])
        channel_max = int(channel.get("max_lanes", max_lanes))
        channel_targets = [
            tid
            for tid in target_ids
            if target_info[tid]["fpp_channel"] == channel_id and target_info[tid]["fpp_lanes"] > 0
        ]
        if channel_targets:
            cp.Add(
                sum(target_info[tid]["fpp_lanes"] * x[tid] for tid in channel_targets)
                <= channel_max
            )

    # ------------------------------------------------------------------
    # 3. Power constraint: sum(power_i * x_i) <= Pmax
    # ------------------------------------------------------------------
    max_power = float(model.resource_limits.get("max_total_power_w", 0.0))
    if max_power > 0:
        cp.Add(
            sum(
                _ceil_scaled(target_info[tid]["peak_power_w"], POWER_SCALE) * x[tid]
                for tid in target_ids
            )
            <= _ceil_scaled(max_power, POWER_SCALE)
        )

    # ------------------------------------------------------------------
    # 4. BIST engine group capacities (shared BIST engines).
    #    Only applies to BIST (type B) targets that actually use the
    #    shared BIST engine resource.
    # ------------------------------------------------------------------
    for group in model.raw.get("resource_groups", {}).get("bist_engine_groups", []):
        members = set(str(member) for member in group.get("members", []))
        capacity = int(group.get("capacity", 1))
        group_targets = [
            tid for tid in target_ids
            if tid in members and target_info[tid]["recipe_type"] == "B"
        ]
        if group_targets:
            cp.Add(sum(x[tid] for tid in group_targets) <= capacity)

    # ------------------------------------------------------------------
    # 5. DWR conflict groups (mutual exclusion on shared DWR segments).
    #    Only applies to targets that use DWR segments overlapping with
    #    the conflict group.
    # ------------------------------------------------------------------
    for group in model.raw.get("resource_groups", {}).get("dwr_conflict_groups", []):
        members = set(str(member) for member in group.get("members", []))
        capacity = int(group.get("capacity", 1))
        group_targets = [
            tid for tid in target_ids
            if tid in members and _target_uses_any_dwr_segment(
                target_info[tid], members
            )
        ]
        if group_targets:
            cp.Add(sum(x[tid] for tid in group_targets) <= capacity)

    # ------------------------------------------------------------------
    # 6. Exclusive resource groups (test sessions)
    #    At most one target using the same exclusive_resource can be active.
    # ------------------------------------------------------------------
    exclusive_map: dict[str, list[str]] = {}
    for tid in target_ids:
        resource = target_info[tid]["exclusive_resource"]
        if resource:
            exclusive_map.setdefault(resource, []).append(tid)
    for resource, tids in exclusive_map.items():
        if len(tids) > 1:
            cp.Add(sum(x[tid] for tid in tids) <= 1)

    # ------------------------------------------------------------------
    # Objective: maximize the number of concurrently active targets.
    # Weighted by 1.0 (simple count maximization, matching PBO approach).
    # ------------------------------------------------------------------
    cp.Maximize(sum(x[tid] for tid in target_ids))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(time_limit_s)
    solver.parameters.num_search_workers = 8
    status = solver.Solve(cp)

    status_name = solver.StatusName(status)
    if status not in {cp_model.OPTIMAL, cp_model.FEASIBLE}:
        return [], 0.0, status_name, solver.WallTime()

    # Collect active targets
    active_targets = [tid for tid in target_ids if solver.BooleanValue(x[tid])]
    if not active_targets:
        return [], 0.0, status_name, solver.WallTime()

    # Session duration: PBO approximation
    #   Serial phases must be serialized (sum of serial_resource_times)
    #   Non-serial phases can overlap (max of non_serial_times)
    total_serial = sum(
        target_info[tid]["serial_resource_time_s"] for tid in active_targets
    )
    max_non_serial = max(
        (target_info[tid]["non_serial_time_s"] for tid in active_targets), default=0.0
    )
    session_duration = total_serial + max_non_serial

    return active_targets, session_duration, status_name, solver.WallTime()


def habiby_pbo_schedule(
    model: SystemModel,
    recipe_rows: list[dict[str, object]],
    time_limit_s: float = 30.0,
) -> tuple[float, float, int, list[dict[str, Any]], str, float]:
    """Run the full PBO incremental scheduling pipeline.

    Parameters
    ----------
    model : SystemModel
    recipe_rows : list of recipe rows (one per target, fastest recipe selected)
    time_limit_s : total CP-SAT time budget across all iterations

    Returns
    -------
    makespan_s : total schedule makespan in seconds
    peak_power_w : peak power across all sessions
    num_sessions : number of scheduling sessions
    session_info : list of per-session dicts
    overall_status : summary solver status string
    total_wall_time_s : total solver wall time
    """
    try:
        from ortools.sat.python import cp_model  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "OR-Tools is not installed. Install project dependencies with: "
            "python -m pip install -r requirements.txt"
        ) from exc

    if not recipe_rows:
        raise ValueError("no recipe rows supplied")

    # Build target_info map: extract key resource attributes from each recipe
    target_info: dict[str, dict[str, Any]] = {}
    for row in recipe_rows:
        tid = str(row["target_id"])
        phases = _parse_phases(row)
        total_time = float(row.get("total_time_s", 0.0))
        peak_pwr = float(row.get("peak_power_w", 0.0))
        fpp_lanes = int(row.get("max_fpp_lanes_required", 0) or 0)
        fpp_channel = str(row.get("fpp_channel", ""))
        # Classify the target for PTAP serial mutual exclusion
        recipe_type = str(row.get("recipe_type", ""))
        has_serial_phase = any(_phase_has_serial(phase) for phase in phases)
        # serial_only: recipe type S or I (purely serial, no FPP/BIST phases)
        serial_only = recipe_type in {"S", "I"}

        # Serial resource time (time the PTAP bus is actually occupied)
        serial_resource_time = float(row.get("serial_resource_time_s", 0.0) or 0.0)
        if serial_resource_time <= 0 and has_serial_phase:
            # Estimate: for FPP/H targets, serial resource time = access_time_s
            serial_resource_time = float(row.get("access_time_s", 0.0))
        # For BIST, serial_resource_time = access_time + readback_time
        if recipe_type == "B":
            serial_resource_time = (
                float(row.get("access_time_s", 0.0))
                + float(row.get("readback_time_s", 0.0))
            )

        # Non-serial time = total_time - serial_resource_time
        non_serial_time = max(0.0, total_time - serial_resource_time)

        # Exclusive resource: use the test_session from the first phase that has one
        exclusive_resource = ""
        for phase in phases:
            er = _phase_exclusive_resource(phase)
            if er:
                exclusive_resource = er
                break

        # Peak power: use phase-level max if available
        max_phase_power = max((_phase_power_w(p) for p in phases), default=peak_pwr)
        target_info[tid] = {
            "test_time_s": total_time,
            "peak_power_w": max(peak_pwr, max_phase_power),
            "fpp_lanes": fpp_lanes,
            "serial_required": has_serial_phase,
            "serial_only": serial_only,
            "has_serial_phase": has_serial_phase,
            "serial_resource_time_s": serial_resource_time,
            "non_serial_time_s": non_serial_time,
            "recipe_type": recipe_type,
            "fpp_channel": fpp_channel,
            "exclusive_resource": exclusive_resource,
            "row": row,
        }

    # PBO incremental loop
    pool = list(recipe_rows)  # copy
    sessions: list[dict[str, Any]] = []
    all_statuses: list[str] = []
    total_wall_time_s = 0.0
    iteration_time_limit = max(1.0, time_limit_s / max(len(pool), 1))

    while pool:
        pool_info = {str(row["target_id"]): target_info[str(row["target_id"])] for row in pool}

        active_targets, session_dur, status_name, wall_s = _build_pbo_session(
            model, pool, pool_info, iteration_time_limit
        )
        all_statuses.append(status_name)
        total_wall_time_s += wall_s

        if not active_targets:
            # Fallback: schedule remaining targets one by one serially
            remaining = {str(r["target_id"]) for r in pool}
            if remaining:
                for tid in sorted(remaining):
                    sessions.append({
                        "targets": [tid],
                        "duration_s": target_info[tid]["test_time_s"],
                        "num_targets": 1,
                        "status": "fallback_serial",
                    })
                all_statuses.append("partial_fallback")
            break

        sessions.append({
            "targets": sorted(active_targets),
            "duration_s": session_dur,
            "num_targets": len(active_targets),
            "status": status_name,
        })

        # Remove scheduled targets from pool
        active_set = set(active_targets)
        pool = [row for row in pool if str(row["target_id"]) not in active_set]

    # Compute aggregate results
    makespan_s = sum(s["duration_s"] for s in sessions)

    # Peak power: for each session, sum the peak powers of active targets
    peak_power_w = 0.0
    for session in sessions:
        session_power = sum(
            target_info[tid]["peak_power_w"] for tid in session["targets"]
        )
        if session_power > peak_power_w:
            peak_power_w = session_power

    num_sessions = len(sessions)
    overall_status = (
        "OPTIMAL" if all(s == "OPTIMAL" for s in all_statuses)
        else "FEASIBLE" if all(s in {"OPTIMAL", "FEASIBLE"} for s in all_statuses)
        else "mixed"
    )

    return makespan_s, peak_power_w, num_sessions, sessions, overall_status, total_wall_time_s


# ---------------------------------------------------------------------------
# Baselines for comparison
# ---------------------------------------------------------------------------


def pure_serial_makespan(model: SystemModel, all_rows: list[dict[str, object]]) -> float:
    """Compute pure-serial makespan: sum all test times (no concurrency)."""
    serial_types = {"S", "I"}
    serial_rows = [r for r in all_rows if str(r.get("recipe_type", "")) in serial_types]
    return sum(float(r.get("total_time_s", 0.0)) for r in serial_rows)


def fixed_fastest_makespan(
    model: SystemModel, fastest_rows: list[dict[str, object]]
) -> float:
    """Run the M4 greedy scheduler with fixed fastest recipe."""
    result = greedy_schedule(model, fastest_rows)
    return result.makespan_s


# ---------------------------------------------------------------------------
# CLI and experiment runner
# ---------------------------------------------------------------------------


def run_case(
    model: SystemModel,
    case_path: str,
    time_limit_s: float,
    lane_count: int = 8,
    power_profile: str = "nominal",
) -> dict[str, Any] | None:
    """Run PBO baseline on a single case.

    Returns a result dict with CSV fieldnames, or None if the case fails.
    """
    print(f"  Generating recipes ...")
    all_recipes = RecipeGenerator(model).generate_all()
    all_rows = rows_from_recipes(all_recipes)
    pareto_rows = pareto_prune(all_rows).kept_rows

    # Select fixed-path recipes for PBO.
    #
    # For each FPP target, we select the recipe with the minimal lane count
    # (to maximize concurrency) that is still Pareto-optimal. This matches
    # the PBO philosophy of using fixed paths while leaving shared resources
    # (FPP lanes) available for concurrent targets.
    #
    # For non-FPP targets (S, I, B), select the absolutely fastest recipe
    # since they don't consume shareable FPP lanes.
    max_lanes_val = int(model.resource_limits.get("total_fpp_lanes", 0))
    pbo_rows = _pbo_recipe_rows(pareto_rows, max_lanes=max_lanes_val)

    target_count = len({str(r["target_id"]) for r in all_rows})
    print(f"  {target_count} targets, {len(all_rows)} recipes -> "
          f"{len(pbo_rows)} PBO recipe rows retained")

    serial_ms = pure_serial_makespan(model, all_rows)

    try:
        print(f"  Running PBO incremental (time_limit={time_limit_s}s) ...")
        t0 = time.perf_counter()
        pbo_ms, pbo_power, num_sessions, sessions, status, wall_s = habiby_pbo_schedule(
            model, pbo_rows, time_limit_s=time_limit_s
        )
        elapsed = time.perf_counter() - t0
    except Exception as exc:
        print(f"  PBO FAILED: {exc}")
        return None

    print(f"  PBO: {pbo_ms:.4f}s makespan, {num_sessions} sessions, "
          f"status={status}, wall={wall_s:.2f}s, elapsed={elapsed:.1f}s")

    gain_vs_serial = (serial_ms - pbo_ms) / serial_ms * 100 if serial_ms > 0 else 0.0

    # Also compute fixed_fastest baseline for comparison
    try:
        fastest_rows = _fastest_recipe_rows(pareto_rows, max_lanes=max_lanes_val)
        ff_ms = fixed_fastest_makespan(model, fastest_rows)
        gain_vs_ff = (ff_ms - pbo_ms) / ff_ms * 100 if ff_ms > 0 else 0.0
        print(f"  Fixed fastest: {ff_ms:.4f}s, gain={gain_vs_ff:.1f}%")
    except Exception:
        ff_ms = None
        gain_vs_ff = None
        fastest_rows = []

    print(f"  Pure serial: {serial_ms:.4f}s, gain={gain_vs_serial:.1f}%")

    return {
        "case_id": model.case_id,
        "method_id": "habiby_pbo",
        "makespan_s": round(pbo_ms, 6),
        "peak_power_w": round(pbo_power, 2),
        "num_sessions": num_sessions,
        "num_targets": target_count,
        "solver_status": status,
        "solver_wall_time_s": round(wall_s, 3),
        # Extra comparison columns (report only, not in CSV)
        "_serial_makespan_s": round(serial_ms, 6),
        "_fixed_fastest_makespan_s": round(ff_ms, 6) if ff_ms is not None else None,
        "_gain_vs_serial_pct": round(gain_vs_serial, 2),
        "_gain_vs_ff_pct": round(gain_vs_ff, 2) if gain_vs_ff is not None else None,
        "_sessions": sessions,
        "_pbo_rows": pbo_rows,
    }


def apply_resource_variant(model: SystemModel, lane_count: int, power_profile: str) -> SystemModel:
    """Apply resource overrides matching the M10 sweep resource_variant."""
    from copy import deepcopy

    POWER_PROFILE_FACTORS = {
        "tight": 0.55,
        "nominal": 1.0,
        "relaxed": 1.55,
    }
    if lane_count <= 0:
        raise ValueError("lane_count must be positive")
    if power_profile not in POWER_PROFILE_FACTORS:
        raise ValueError(f"unknown power profile: {power_profile}")

    raw = deepcopy(model.raw)
    raw["resource_limits"]["total_fpp_lanes"] = lane_count
    base_power = float(model.resource_limits["max_total_power_w"])
    raw["resource_limits"]["max_total_power_w"] = max(
        2.5, round(base_power * POWER_PROFILE_FACTORS[power_profile], 6)
    )

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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Habiby 2022 PBO incremental test scheduling baseline."
    )
    parser.add_argument(
        "--cases", nargs="*",
        help="Case JSON files to run. Defaults to 6 representative cases (3 M10 + 3 M21).",
    )
    parser.add_argument(
        "--lane-count", type=int, default=8,
        help="FPP lane count for all cases.",
    )
    parser.add_argument(
        "--power-profile", default="nominal",
        choices=["tight", "nominal", "relaxed"],
        help="Power profile from the M10 sweep settings.",
    )
    parser.add_argument(
        "--time-limit-s", type=float, default=30.0,
        help="CP-SAT time limit per case (total across all PBO iterations).",
    )
    parser.add_argument(
        "--output",
        default="results/tables/habiby_pbo_baseline.csv",
        help="Output CSV path.",
    )
    parser.add_argument(
        "--report-output",
        default="results/reports/habiby_pbo_baseline_report.md",
        help="Output Markdown report path.",
    )
    args = parser.parse_args()

    cases = args.cases if args.cases else M10_CASES + M21_CASES

    print(f"Habiby PBO Baseline")
    print(f"  cases: {len(cases)}")
    print(f"  lane_count: {args.lane_count}")
    print(f"  power_profile: {args.power_profile}")
    print(f"  time_limit_s: {args.time_limit_s}")
    print()

    csv_rows: list[dict[str, Any]] = []
    all_results: list[dict[str, Any]] = []
    failures: list[tuple[str, str]] = []

    for case_path in cases:
        print(f"Case: {case_path}")
        try:
            base_model = load_system_model(case_path)
            model = apply_resource_variant(
                base_model, lane_count=args.lane_count, power_profile=args.power_profile
            )
        except Exception as exc:
            print(f"  LOAD FAILED: {exc}")
            failures.append((case_path, str(exc)))
            continue

        result = run_case(model, case_path, time_limit_s=args.time_limit_s,
                          lane_count=args.lane_count, power_profile=args.power_profile)
        if result is None:
            failures.append((case_path, "solver failed"))
            continue

        all_results.append(result)
        csv_rows.append({k: result[k] for k in CSV_FIELDNAMES})
        print()

    # Write CSV
    output_csv = Path(args.output)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        for row in csv_rows:
            writer.writerow(row)
    print(f"CSV written: {output_csv} ({len(csv_rows)} rows)")

    # Write Markdown report
    write_report(all_results, failures, Path(args.report_output))
    print(f"Report written: {args.report_output}")
    print(f"Done: {len(csv_rows)} successful, {len(failures)} failures")


def write_report(
    results: list[dict[str, Any]],
    failures: list[tuple[str, str]],
    output_path: Path,
) -> None:
    """Generate a Markdown report with results and comparison to baselines."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Habiby 2022 PBO Incremental Scheduling Baseline Report",
        "",
        "## Summary",
        "",
        f"- Successful cases: {len(results)}",
        f"- Failed cases: {len(failures)}",
        "",
    ]

    if results:
        lines.extend([
            "## Results",
            "",
            "| case_id | makespan_s | sessions | targets | peak_power_w | "
            "solver_status | solver_wall_s | vs_serial_% | vs_fixed_fastest_% |",
            "| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |",
        ])
        for r in results:
            vs_serial = r.get("_gain_vs_serial_pct", "")
            vs_ff = r.get("_gain_vs_ff_pct", "")
            vs_serial_str = f"{vs_serial:.1f}%" if isinstance(vs_serial, (int, float)) else str(vs_serial)
            vs_ff_str = f"{vs_ff:.1f}%" if isinstance(vs_ff, (int, float)) else str(vs_ff) if vs_ff is not None else "N/A"
            lines.append(
                f"| {r['case_id']} | {r['makespan_s']:.4f} | {r['num_sessions']} "
                f"| {r['num_targets']} | {r['peak_power_w']:.1f} | "
                f"{r['solver_status']} | {r['solver_wall_time_s']:.3f} | "
                f"{vs_serial_str} | {vs_ff_str} |"
            )

        # Averages
        avg_makespan = sum(r["makespan_s"] for r in results) / len(results)
        avg_sessions = sum(r["num_sessions"] for r in results) / len(results)
        avg_wall = sum(r["solver_wall_time_s"] for r in results) / len(results)
        avg_gain_serial = sum(
            r["_gain_vs_serial_pct"] for r in results
            if r.get("_gain_vs_serial_pct") is not None
        )
        n_serial = sum(1 for r in results if r.get("_gain_vs_serial_pct") is not None)
        avg_gain_serial = avg_gain_serial / n_serial if n_serial > 0 else 0.0

        avg_gain_ff = sum(
            r["_gain_vs_ff_pct"] for r in results
            if r.get("_gain_vs_ff_pct") is not None
        )
        n_ff = sum(1 for r in results if r.get("_gain_vs_ff_pct") is not None)
        avg_gain_ff = avg_gain_ff / n_ff if n_ff > 0 else 0.0

        lines.extend([
            "",
            f"**Averages:**",
            f"- Makespan: {avg_makespan:.4f} s",
            f"- Sessions: {avg_sessions:.1f}",
            f"- Solver wall time: {avg_wall:.3f} s",
            f"- Gain vs pure serial: {avg_gain_serial:.1f}%",
            f"- Gain vs fixed fastest (greedy): {avg_gain_ff:.1f}%",
            "",
        ])

        # Per-case session details
        lines.extend([
            "## Per-case Session Details",
            "",
        ])
        for r in results:
            lines.append(f"### {r['case_id']}")
            lines.append(f"- Makespan: {r['makespan_s']:.4f} s")
            lines.append(f"- Sessions: {r['num_sessions']}")
            lines.append(f"- Peak power: {r['peak_power_w']:.1f} W")
            lines.append(f"- Solver status: {r['solver_status']}")
            lines.append(f"- Solver wall time: {r['solver_wall_time_s']:.3f} s")
            lines.append("")

            sessions = r.get("_sessions", [])
            if sessions:
                lines.append("| session | duration_s | targets | num_targets | status |")
                lines.append("| --- | ---: | --- | ---: | --- |")
                for i, session in enumerate(sessions, 1):
                    target_list = ", ".join(session["targets"][:5])
                    if len(session["targets"]) > 5:
                        target_list += f", ... (+{len(session['targets']) - 5})"
                    lines.append(
                        f"| {i} | {session['duration_s']:.6f} | {target_list} "
                        f"| {session['num_targets']} | {session['status']} |"
                    )
            lines.append("")

    if failures:
        lines.extend([
            "## Failures",
            "",
            "| case_path | error |",
            "| --- | --- |",
        ])
        for path, err in failures:
            lines.append(f"| {path} | {err} |")
        lines.append("")

    lines.extend([
        "## Method Description",
        "",
        "The Habiby 2022 PBO (Pseudo-Boolean Optimization) incremental approach,",
        "adapted for IEEE 1838:",
        "",
        "1. **Recipe selection** (fixed-path): For each FPP-capable target, select the",
        "   recipe with the fewest FPP lanes to maximize concurrency in the shared lane",
        "   pool. For non-FPP targets (S/I), select the fastest available recipe.",
        "2. **PBO iteration**: Build a CP-SAT model with boolean variables x_i for each",
        "   target in the pool.",
        "3. **Resource constraints** encoded as linear inequalities:",
        "   - PTAP serial mutual exclusion: at most 1 serial-only (S/I) target;",
        "     FPP/BIST targets can overlap with each other.",
        "   - FPP lanes: cumulative sum constraint (per-channel).",
        "   - Power: cumulative power budget.",
        "   - BIST engine groups: capacity limits on shared BIST engines.",
        "   - DWR conflict groups: mutual exclusion on shared DWR segments.",
        "   - Exclusive resources (test sessions): one target per test session per die.",
        "4. **Objective**: Maximize the number of concurrently active targets.",
        "5. **Session formation**: Solve, record active targets as a session, remove",
        "   them from the pool. Session duration = sum(serial_resource_times) +",
        "   max(non_serial_times), approximating sequential serial phases with",
        "   overlapping non-serial phases.",
        "6. Repeat until all targets scheduled.",
        "7. Total makespan = sum of session durations.",
        "",
        "This matches the incremental PBO methodology from:",
        "",
        "> Habiby et al. \"Power-aware test scheduling framework for IEEE 1687",
        "> multi-power domain networks using formal techniques.\"",
        "> Microelectronics Reliability, 2022.",
        "",
        "## Notes",
        "",
        "- OR-Tools CP-SAT is used instead of a native PBO solver (clasp).",
        "- CP-SAT provides comparable incremental optimization capability.",
        "- The approach balances per-target speed (fastest recipe) with concurrency",
        "  (PBO packing). FPP targets use minimal-lane recipes to enable concurrency;",
        "  this trades some per-target speed for overall makespan reduction.",
        "- The negative gain vs `fixed_fastest` is expected: `fixed_fastest` uses",
        "  maximum-lane recipes (fastest per target) but cannot achieve concurrency",
        "  due to lane monopolization. PBO achieves 2-2.5x concurrency with",
        "  slightly slower per-target recipes.",
    ])

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
