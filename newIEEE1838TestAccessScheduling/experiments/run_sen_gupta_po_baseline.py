from __future__ import annotations

"""
Sen Gupta 2011 "Partial Overlapping" (PO) test scheduling baseline.

Reference:
  Sen Gupta et al. "Scheduling Tests for 3D Stacked Chips under Power Constraints"
  IEEE DELTA 2011.

Strategy:
  1. Each target receives its individually fastest recipe (min total_time_s).
  2. Targets are grouped into sessions greedily:
     - Sort targets by peak power (descending).
     - Try to add each target to the current session. It fits if all its phases
       can coexist with phases already in that session under:
         * System power budget
         * PTAP serial port capacity
         * FPP lane and channel capacity
         * DWR conflict groups
         * Exclusive resource (test session) mutual exclusion
         * BIST engine groups
         * Concurrent capture limit
     - When no more targets fit, start a new session.
  3. Sessions execute sequentially. Each session's duration = longest target
     duration in the session.
  4. Total makespan = sum of session durations.
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.run_m10_benchmark_sweep import POWER_PROFILE_FACTORS, resource_variant
from src.evaluators.comparison import build_comparison_rows
from src.model import SystemModel, load_system_model
from src.recipes import RecipeGenerator, pareto_prune, rows_from_recipes
from src.schedulers import (
    ScheduleResult,
    ScheduledPhase,
    SchedulingError,
    greedy_schedule,
)
from src.schedulers.greedy import (
    _parse_phase_resources,
    _to_bool,
    _is_capture,
    _fpp_channel_capacities,
    _bist_engine_groups_fit,
    _exclusive_resources_fit,
    _dwr_groups_fit,
)

EPSILON = 1e-12

# ---- Case selection ---------------------------------------------------------

M10_COVERAGE_CASES = [
    "configs/cases/m10/m10_small_d695_3d_stack.json",
    "configs/cases/m10/m10_medium_p22810_3d_stack.json",
    "configs/cases/m10/m10_large_p34392_3d_stack.json",
]

M21_PRESSURE_CASES = [
    "configs/cases/m21/m21_pressure_medium_p22810_3d_stack.json",
    "configs/cases/m21/m21_pressure_large_p34392_3d_stack.json",
    "configs/cases/m21/m21_pressure_xlarge_p93791_3d_stack.json",
]

DEFAULT_CASES = M10_COVERAGE_CASES + M21_PRESSURE_CASES

FIELDNAMES = [
    "case_id",
    "method_id",
    "makespan_s",
    "peak_power_w",
    "fpp_utilization",
    "num_sessions",
    "status",
    "error",
]

# ---- PO scheduler -----------------------------------------------------------

def _fastest_recipe_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Return the single fastest recipe (min total_time_s) per target."""
    selected: dict[str, tuple[tuple[float, float, str], dict[str, object]]] = {}
    for row in rows:
        target_id = str(row["target_id"])
        key = (
            float(row.get("total_time_s", 0.0)),
            float(row.get("peak_power_w", 0.0)),
            str(row["recipe_id"]),
        )
        if target_id not in selected or key < selected[target_id][0]:
            selected[target_id] = (key, row)
    return [item[1] for item in selected.values()]


def _target_duration_s(row: dict[str, object]) -> float:
    return float(row.get("total_time_s", 0.0))


def _target_peak_power_w(row: dict[str, object]) -> float:
    return float(row.get("peak_power_w", 0.0))


def _phase_list_from_row(row: dict[str, object], model: SystemModel) -> list[dict[str, object]]:
    """Return the list of phase dicts for a recipe row."""
    phases = _parse_phase_resources(row)
    for phase in phases:
        phase.setdefault("target_id", row.get("target_id", ""))
        phase.setdefault("recipe_id", str(row["recipe_id"]))
    return phases


def _phase_resources_fit(
    model: SystemModel,
    phases: list[dict[str, object]],
    active_phases: list[dict[str, object]],
) -> bool:
    """Check if *all* phases of a candidate target can coexist with *active_phases*.

    This is a relaxed check: we check the maximum resource demand across all the
    candidate phases vs the active phases.  Since sessions execute as blocks,
    the worst-case resource usage across phases determines feasibility.
    """
    candidate_lanes = max(
        (int(phase.get("fpp_lanes_required", 0) or 0) for phase in phases),
        default=0,
    )
    candidate_power = max(
        (float(phase.get("power_w", 0.0) or 0.0) for phase in phases),
        default=0.0,
    )
    candidate_serial = any(_to_bool(phase.get("serial_required", False)) for phase in phases)

    # Serial
    serial_capacity = int(model.resource_limits.get("ptap_ports", 1))
    serial_used = (1 if candidate_serial else 0) + sum(
        1 for phase in active_phases if _to_bool(phase.get("serial_required", False))
    )
    if serial_used > serial_capacity:
        return False

    # FPP lanes
    total_active_lanes = sum(
        int(phase.get("fpp_lanes_required", 0) or 0) for phase in active_phases
    )
    if candidate_lanes + total_active_lanes > int(
        model.resource_limits.get("total_fpp_lanes", candidate_lanes + total_active_lanes)
    ):
        return False

    # FPP channel capacities
    candidate_channel = str(phases[0].get("fpp_channel", "")) if candidate_lanes > 0 else ""
    channel_caps = _fpp_channel_capacities(model)
    for channel_id, capacity in channel_caps.items():
        used = sum(
            int(phase.get("fpp_lanes_required", 0) or 0)
            for phase in active_phases
            if str(phase.get("fpp_channel", "")) == channel_id
        )
        if channel_id == candidate_channel:
            used += candidate_lanes
        if used > capacity:
            return False

    # Power
    total_active_power = sum(
        float(phase.get("power_w", 0.0) or 0.0) for phase in active_phases
    )
    if candidate_power + total_active_power > float(
        model.resource_limits.get("max_total_power_w", candidate_power + total_active_power)
    ) + EPSILON:
        return False

    # Concurrent capture limit
    capture_limit = int(model.resource_limits.get("max_concurrent_capture", len(active_phases) + 1))
    candidate_capture = any(
        _is_capture(str(phase.get("phase_name", ""))) for phase in phases
    )
    active_capture = sum(
        1 for phase in active_phases if _is_capture(str(phase.get("phase_name", "")))
    )
    if (1 if candidate_capture else 0) + active_capture > capture_limit:
        return False

    # DWR conflict groups
    candidate_dwr = set()
    for phase in phases:
        dwr_segs = phase.get("dwr_segments", [])
        if isinstance(dwr_segs, (str,)):
            dwr_segs = [s for s in dwr_segs.split(";") if s]
        candidate_dwr.update(str(s) for s in dwr_segs)

    for group in model.raw.get("resource_groups", {}).get("dwr_conflict_groups", []):
        members = set(str(m) for m in group.get("members", []))
        used = 1 if (candidate_dwr & members) else 0
        for active_phase in active_phases:
            active_segs = set(str(active_phase.get("dwr_segments", "")).split(";"))
            if active_segs & members:
                used += 1
        if used > int(group.get("capacity", 1)):
            return False

    # Exclusive resources
    candidate_exclusive = set()
    for phase in phases:
        res = str(phase.get("exclusive_resource", ""))
        if res:
            candidate_exclusive.add(res)
    for active_phase in active_phases:
        active_res = str(active_phase.get("exclusive_resource", ""))
        if active_res and active_res in candidate_exclusive:
            return False
    active_exclusive = set()
    for active_phase in active_phases:
        res = str(active_phase.get("exclusive_resource", ""))
        if res:
            active_exclusive.add(res)
    if candidate_exclusive & active_exclusive:
        # Actually, this is OK if they're different targets sharing the same
        # test session group — in that case they would conflict.  The check above
        # is correct: if the candidate wants an exclusive resource already held
        # by someone else, conflict.
        return False

    # BIST engine groups: check if any BIST_RUN phases conflict
    candidate_bist_phases = [
        phase for phase in phases
        if str(phase.get("phase_name", "")) == "LOCAL_BIST_RUN"
    ]
    active_bist_phases = [
        phase for phase in active_phases
        if str(phase.get("phase_name", "")) == "LOCAL_BIST_RUN"
    ]
    if candidate_bist_phases or active_bist_phases:
        candidate_targets = {str(phase.get("target_id", "")) for phase in candidate_bist_phases}
        for group in model.raw.get("resource_groups", {}).get("bist_engine_groups", []):
            members = set(str(m) for m in group.get("members", []))
            used = 1 if (candidate_targets & members) else 0
            used += sum(
                1 for phase in active_bist_phases
                if str(phase.get("target_id", "")) in members
            )
            if used > int(group.get("capacity", 1)):
                return False

    return True


def sen_gupta_po_schedule(
    model: SystemModel,
    recipe_rows: list[dict[str, object]],
) -> ScheduleResult:
    """Run the Sen Gupta 2011 Partial Overlapping scheduling strategy.

    1. Each target gets its fastest recipe.
    2. Targets are grouped greedily into sessions based on power and resource
       compatibility.
    3. Sessions execute sequentially.
    """
    if not recipe_rows:
        raise SchedulingError("no recipe rows supplied")

    # Step 1: each target's fastest recipe
    fastest_rows = _fastest_recipe_rows(recipe_rows)

    # Sort by peak power descending (Sen Gupta's heuristic)
    sorted_rows = sorted(fastest_rows, key=_target_peak_power_w, reverse=True)

    # Build sessions greedily
    sessions: list[list[dict[str, object]]] = []
    for row in sorted_rows:
        target_phases = _phase_list_from_row(row, model)
        placed = False
        for session in sessions:
            # Collect all phases from targets already in this session
            session_phases: list[dict[str, object]] = []
            for session_row in session:
                session_phases.extend(_phase_list_from_row(session_row, model))
            if _phase_resources_fit(model, target_phases, session_phases):
                session.append(row)
                placed = True
                break
        if not placed:
            sessions.append([row])

    # Build ScheduledPhase list: sessions are sequential
    current_time = 0.0
    scheduled: list[ScheduledPhase] = []
    for session in sessions:
        # Session duration = max target duration in this session
        session_duration = max(_target_duration_s(row) for row in session)
        # Each target's phases are scheduled in the session block
        for row in session:
            phases = _parse_phase_resources(row)
            for index, phase in enumerate(phases):
                duration = float(phase.get("duration_s", 0.0))
                scheduled.append(
                    ScheduledPhase(
                        case_id=model.case_id,
                        target_id=str(row["target_id"]),
                        target_kind=str(row.get("target_kind", "")),
                        die_id=str(row.get("die_id", "")),
                        recipe_id=str(row["recipe_id"]),
                        recipe_type=str(row.get("recipe_type", "")),
                        phase_index=index,
                        phase_name=str(phase.get("phase_name", "")),
                        start_s=current_time,
                        end_s=current_time + duration,
                        duration_s=duration,
                        serial_required=_to_bool(phase.get("serial_required", False)),
                        fpp_lanes_required=int(phase.get("fpp_lanes_required", 0) or 0),
                        fpp_channel=str(phase.get("fpp_channel", "")),
                        dwr_segments=";".join(
                            str(s) for s in phase.get("dwr_segments", [])
                        ),
                        route_resource=str(phase.get("route_resource", "")),
                        exclusive_resource=str(phase.get("exclusive_resource", "")),
                        power_w=float(phase.get("power_w", 0.0) or 0.0),
                        thermal_region=str(phase.get("thermal_region", "")),
                        resource_notes=str(phase.get("notes", "")),
                    )
                )
        current_time += session_duration

    # Compute aggregate metrics
    makespan = max((phase.end_s for phase in scheduled), default=0.0)
    peak_power = _max_concurrent_power(scheduled)
    peak_lanes = max(
        sum(
            phase.fpp_lanes_required
            for phase in scheduled
            if phase.start_s <= b < phase.end_s - EPSILON
        )
        for b in sorted({p.start_s for p in scheduled} | {p.end_s for p in scheduled})
    )

    return ScheduleResult(
        case_id=model.case_id,
        selected_rows=sorted(fastest_rows, key=lambda r: str(r["target_id"])),
        phases=sorted(scheduled, key=lambda p: (p.start_s, p.end_s, p.target_id, p.phase_index)),
        makespan_s=makespan,
        peak_power_w=peak_power,
        max_fpp_lanes_used=peak_lanes,
        serial_busy_time_s=sum(phase.duration_s for phase in scheduled if phase.serial_required),
        fpp_lane_time_s=sum(
            phase.duration_s * phase.fpp_lanes_required for phase in scheduled
        ),
    )


def _max_concurrent_power(phases: list[ScheduledPhase]) -> float:
    peak = 0.0
    for boundary in sorted({p.start_s for p in phases} | {p.end_s for p in phases}):
        active = sum(
            p.power_w for p in phases if p.start_s <= boundary < p.end_s - EPSILON
        )
        peak = max(peak, active)
    return peak


def _fpp_utilization(model: SystemModel, schedule: ScheduleResult) -> float:
    total_lanes = int(model.resource_limits.get("total_fpp_lanes", 0))
    if schedule.makespan_s <= 0 or total_lanes <= 0:
        return 0.0
    return schedule.fpp_lane_time_s / (schedule.makespan_s * total_lanes)


def _filter_recipe_types(
    rows: list[dict[str, object]], recipe_types: set[str]
) -> list[dict[str, object]]:
    filtered = [row for row in rows if str(row.get("recipe_type", "")) in recipe_types]
    target_ids = {str(row["target_id"]) for row in rows}
    covered = {str(row["target_id"]) for row in filtered}
    missing = sorted(target_ids - covered)
    if missing:
        raise ValueError(
            f"baseline cannot cover targets with recipe types {recipe_types}: {missing}"
        )
    return filtered


# ---- Main -------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Sen Gupta 2011 Partial Overlapping baseline."
    )
    parser.add_argument(
        "--cases",
        nargs="*",
        default=DEFAULT_CASES,
        help="Case JSONs to schedule.",
    )
    parser.add_argument(
        "--lane-count",
        type=int,
        default=8,
        help="FPP lane count.",
    )
    parser.add_argument(
        "--power-profile",
        default="nominal",
        choices=["tight", "nominal", "relaxed"],
        help="Power budget profile.",
    )
    parser.add_argument(
        "--output-table",
        default="results/tables/sen_gupta_po_baseline.csv",
        help="Output CSV path for results table.",
    )
    parser.add_argument(
        "--output-report",
        default="results/reports/sen_gupta_po_baseline_report.md",
        help="Output Markdown report path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows: list[dict[str, Any]] = []

    for case_path_str in args.cases:
        case_path = Path(case_path_str)
        if not case_path.exists():
            print(f"SKIP: case not found: {case_path}")
            continue

        base_model = load_system_model(case_path)
        model = resource_variant(
            base_model,
            lane_count=args.lane_count,
            power_profile=args.power_profile,
        )

        all_recipes = rows_from_recipes(RecipeGenerator(model).generate_all())
        pareto_rows = pareto_prune(all_recipes).kept_rows

        # ---- Run PO schedule ----
        try:
            po_schedule = sen_gupta_po_schedule(model, pareto_rows)
            rows.append(
                _success_row(
                    model,
                    "po_sen_gupta_2011",
                    po_schedule,
                )
            )
        except (SchedulingError, ValueError, RuntimeError) as exc:
            rows.append(
                _error_row(model, "po_sen_gupta_2011", str(exc))
            )

        # ---- Reference: pure serial baseline ----
        try:
            serial_rows = _filter_recipe_types(all_recipes, {"S", "I"})
            serial_schedule = greedy_schedule(model, serial_rows)
            rows.append(
                _success_row(model, "pure_serial", serial_schedule)
            )
        except (SchedulingError, ValueError, RuntimeError) as exc:
            rows.append(
                _error_row(model, "pure_serial", str(exc))
            )

        # ---- Reference: fixed fastest recipe baseline ----
        try:
            fastest_rows = _fastest_recipe_rows(pareto_rows)
            ff_schedule = greedy_schedule(model, fastest_rows)
            rows.append(
                _success_row(model, "fixed_fastest", ff_schedule)
            )
        except (SchedulingError, ValueError, RuntimeError) as exc:
            rows.append(
                _error_row(model, "fixed_fastest", str(exc))
            )

    _write_rows(rows, args.output_table)
    _write_report(rows, args.output_report)

    print(f"cases={len(args.cases)}")
    print(f"rows={len(rows)}")
    print(f"output_table={args.output_table}")
    print(f"output_report={args.output_report}")


def _success_row(
    model: SystemModel,
    method_id: str,
    schedule: ScheduleResult,
) -> dict[str, Any]:
    # Count sessions from the phasing: a new "session" starts each time the
    # makespan advances by the longest-target-duration block.  We count unique
    # start times among phases that share a common start meaning they're in the
    # same session.  Our scheduler schedules all targets in a session at the
    # same start time, so we count unique start times.
    start_times = sorted(set(phase.start_s for phase in schedule.phases))
    num_sessions = len(start_times)

    return {
        "case_id": model.case_id,
        "method_id": method_id,
        "makespan_s": schedule.makespan_s,
        "peak_power_w": schedule.peak_power_w,
        "fpp_utilization": _fpp_utilization(model, schedule),
        "num_sessions": num_sessions,
        "status": "ok",
        "error": "",
    }


def _error_row(model: SystemModel, method_id: str, error: str) -> dict[str, Any]:
    return {
        "case_id": model.case_id,
        "method_id": method_id,
        "makespan_s": "",
        "peak_power_w": "",
        "fpp_utilization": "",
        "num_sessions": "",
        "status": "failed",
        "error": error,
    }


def _write_rows(rows: list[dict[str, Any]], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDNAMES})


def _write_report(rows: list[dict[str, Any]], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    ok_rows = [r for r in rows if r["status"] == "ok"]
    failed = [r for r in rows if r["status"] != "ok"]

    lines = [
        "# Sen Gupta 2011 Partial Overlapping Baseline Report",
        "",
        f"- Cases processed: {len({r['case_id'] for r in rows})}",
        f"- Total rows: {len(rows)}",
        f"- Successful rows: {len(ok_rows)}",
        f"- Failed rows: {len(failed)}",
        f"- Lane count: {8}",
        f"- Power profile: nominal",
        "",
        "## Results Table",
        "",
        "| case_id | method_id | makespan_s | peak_power_w | fpp_utilization | num_sessions | status |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]

    for row in rows:
        ms = f"{row['makespan_s']:.9f}" if row['makespan_s'] != "" else ""
        pw = f"{row['peak_power_w']:.6f}" if row['peak_power_w'] != "" else ""
        fu = f"{row['fpp_utilization']:.4f}" if row['fpp_utilization'] != "" else ""
        ns = row['num_sessions'] if row['num_sessions'] != "" else ""
        lines.append(
            f"| {row['case_id']} | {row['method_id']} | {ms} | {pw} | {fu} | {ns} | {row['status']} |"
        )

    # Compute gains
    lines.extend(["", "## Gain Analysis", ""])

    for case_id in sorted({r["case_id"] for r in ok_rows}):
        case_ok = [r for r in ok_rows if r["case_id"] == case_id]
        po_row = next((r for r in case_ok if r["method_id"] == "po_sen_gupta_2011"), None)
        ps_row = next((r for r in case_ok if r["method_id"] == "pure_serial"), None)
        ff_row = next((r for r in case_ok if r["method_id"] == "fixed_fastest"), None)

        lines.append(f"### {case_id}")
        if po_row and ps_row:
            po_ms = float(po_row["makespan_s"])
            ps_ms = float(ps_row["makespan_s"])
            gain_vs_serial = (ps_ms - po_ms) / ps_ms * 100 if ps_ms > 0 else 0.0
            lines.append(
                f"- PO makespan: {po_ms:.9f} s (sessions: {po_row['num_sessions']})"
            )
            lines.append(f"- Pure serial makespan: {ps_ms:.9f} s")
            lines.append(
                f"- Gain vs pure_serial: {gain_vs_serial:+.2f}% ({ps_ms - po_ms:+.9f} s)"
            )
        if po_row and ff_row:
            po_ms = float(po_row["makespan_s"])
            ff_ms = float(ff_row["makespan_s"])
            gain_vs_ff = (ff_ms - po_ms) / ff_ms * 100 if ff_ms > 0 else 0.0
            lines.append(f"- Fixed fastest makespan: {ff_ms:.9f} s")
            lines.append(
                f"- Gain vs fixed_fastest: {gain_vs_ff:+.2f}% ({ff_ms - po_ms:+.9f} s)"
            )
        lines.append("")

    if failed:
        lines.extend(["## Failures", ""])
        for row in failed:
            lines.append(f"- **{row['case_id']}** / `{row['method_id']}`: {row['error']}")
        lines.append("")

    lines.extend(
        [
            "## Notes",
            "",
            "- PO strategy packs targets into concurrent sessions; sessions run sequentially.",
            "- Session count reflects the degree of achievable parallelism under the resource model.",
            "- Compare against pure_serial and fixed_fastest to isolate the PO contribution.",
            "- Resource constraints honored: PTAP serial, FPP lanes/channels, DWR groups,",
            "  BIST engine groups, exclusive test sessions, concurrent capture limit, and power budget.",
        ]
    )

    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
