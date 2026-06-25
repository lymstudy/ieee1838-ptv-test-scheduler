from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any

from src.model import SystemModel

from .greedy import ScheduleResult, ScheduledPhase, _peak_fpp_lanes, _peak_power


TIME_SCALE = 1_000_000_000
POWER_SCALE = 1_000


class CpSatUnavailableError(RuntimeError):
    """Raised when the OR-Tools CP-SAT backend is requested but unavailable."""


@dataclass(frozen=True)
class CpSatSolveInfo:
    status_name: str
    objective_s: float
    wall_time_s: float


def solve_cpsat_schedule(
    model: SystemModel,
    recipe_rows: list[dict[str, object]],
    time_limit_s: float = 10.0,
    workers: int = 8,
) -> tuple[ScheduleResult, CpSatSolveInfo]:
    try:
        from ortools.sat.python import cp_model
    except ImportError as exc:
        raise CpSatUnavailableError(
            "OR-Tools is not installed. Install project dependencies with: python -m pip install -r requirements.txt"
        ) from exc

    if not recipe_rows:
        raise ValueError("no recipe rows supplied")

    recipe_specs = [_recipe_spec(row) for row in recipe_rows]
    horizon = sum(sum(phase["duration_ticks"] for phase in spec["phases"]) for spec in recipe_specs)
    horizon = max(horizon, 1)

    cp = cp_model.CpModel()
    intervals: list[dict[str, Any]] = []
    selected_by_recipe: dict[str, Any] = {}

    for spec in recipe_specs:
        selected = cp.NewBoolVar(f"select_{spec['recipe_id']}")
        selected_by_recipe[spec["recipe_id"]] = selected
        previous_end = None
        for index, phase in enumerate(spec["phases"]):
            start = cp.NewIntVar(0, horizon, f"start_{spec['recipe_id']}_{index}")
            end = cp.NewIntVar(0, horizon, f"end_{spec['recipe_id']}_{index}")
            interval = cp.NewOptionalIntervalVar(
                start,
                phase["duration_ticks"],
                end,
                selected,
                f"interval_{spec['recipe_id']}_{index}",
            )
            if previous_end is not None:
                cp.Add(start >= previous_end).OnlyEnforceIf(selected)
            previous_end = end
            intervals.append(
                {
                    "spec": spec,
                    "phase": phase,
                    "index": index,
                    "selected": selected,
                    "start": start,
                    "end": end,
                    "interval": interval,
                }
            )

    for target_id in sorted({spec["target_id"] for spec in recipe_specs}):
        cp.AddExactlyOne(
            selected_by_recipe[spec["recipe_id"]]
            for spec in recipe_specs
            if spec["target_id"] == target_id
        )

    serial_intervals = [item["interval"] for item in intervals if item["phase"]["serial_required"]]
    if int(model.resource_limits.get("ptap_ports", 1)) == 1:
        cp.AddNoOverlap(serial_intervals)
    elif serial_intervals:
        cp.AddCumulative(serial_intervals, [1] * len(serial_intervals), int(model.resource_limits["ptap_ports"]))

    _add_cumulative(
        cp,
        intervals,
        lambda item: int(item["phase"]["fpp_lanes_required"]),
        int(model.resource_limits.get("total_fpp_lanes", 0)),
    )

    for channel in model.access.get("fpp_channels", []):
        channel_id = str(channel["channel_id"])
        _add_cumulative(
            cp,
            [item for item in intervals if item["phase"]["fpp_channel"] == channel_id],
            lambda item: int(item["phase"]["fpp_lanes_required"]),
            int(channel.get("max_lanes", model.resource_limits.get("total_fpp_lanes", 0))),
        )

    _add_cumulative(
        cp,
        intervals,
        lambda item: _ceil_scaled(float(item["phase"]["power_w"]), POWER_SCALE),
        _ceil_scaled(float(model.resource_limits.get("max_total_power_w", 0.0)), POWER_SCALE),
    )

    capture_limit = int(model.resource_limits.get("max_concurrent_capture", 0))
    capture_items = [item for item in intervals if _is_capture(item["phase"]["phase_name"])]
    _add_cumulative(cp, capture_items, lambda _item: 1, capture_limit)

    for group in model.raw.get("resource_groups", {}).get("dwr_conflict_groups", []):
        members = set(str(member) for member in group.get("members", []))
        group_items = [
            item
            for item in intervals
            if set(item["phase"]["dwr_segments"]) & members
        ]
        _add_cumulative(cp, group_items, lambda _item: 1, int(group.get("capacity", 1)))

    for group in model.raw.get("resource_groups", {}).get("bist_engine_groups", []):
        members = set(str(member) for member in group.get("members", []))
        group_items = [
            item
            for item in intervals
            if item["phase"]["phase_name"] == "LOCAL_BIST_RUN" and item["spec"]["target_id"] in members
        ]
        _add_cumulative(cp, group_items, lambda _item: 1, int(group.get("capacity", 1)))

    for resource in sorted({item["phase"]["exclusive_resource"] for item in intervals if item["phase"]["exclusive_resource"]}):
        resource_items = [item for item in intervals if item["phase"]["exclusive_resource"] == resource]
        cp.AddNoOverlap([item["interval"] for item in resource_items])

    makespan = cp.NewIntVar(0, horizon, "makespan")
    for spec in recipe_specs:
        spec_items = [item for item in intervals if item["spec"]["recipe_id"] == spec["recipe_id"]]
        if spec_items:
            cp.Add(makespan >= spec_items[-1]["end"]).OnlyEnforceIf(selected_by_recipe[spec["recipe_id"]])
    cp.Minimize(makespan)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(time_limit_s)
    solver.parameters.num_search_workers = int(workers)
    status = solver.Solve(cp)
    if status not in {cp_model.OPTIMAL, cp_model.FEASIBLE}:
        raise RuntimeError(f"CP-SAT could not find a feasible schedule, status={solver.StatusName(status)}")

    selected_rows = []
    scheduled: list[ScheduledPhase] = []
    for spec in recipe_specs:
        if not solver.BooleanValue(selected_by_recipe[spec["recipe_id"]]):
            continue
        selected_rows.append(spec["row"])
        for item in [entry for entry in intervals if entry["spec"]["recipe_id"] == spec["recipe_id"]]:
            phase = item["phase"]
            start_s = solver.Value(item["start"]) / TIME_SCALE
            end_s = solver.Value(item["end"]) / TIME_SCALE
            scheduled.append(
                ScheduledPhase(
                    case_id=model.case_id,
                    target_id=spec["target_id"],
                    target_kind=spec["target_kind"],
                    die_id=spec["die_id"],
                    recipe_id=spec["recipe_id"],
                    recipe_type=spec["recipe_type"],
                    phase_index=item["index"],
                    phase_name=phase["phase_name"],
                    start_s=start_s,
                    end_s=end_s,
                    duration_s=phase["duration_ticks"] / TIME_SCALE,
                    serial_required=phase["serial_required"],
                    fpp_lanes_required=phase["fpp_lanes_required"],
                    fpp_channel=phase["fpp_channel"],
                    dwr_segments=";".join(phase["dwr_segments"]),
                    route_resource=phase["route_resource"],
                    exclusive_resource=phase["exclusive_resource"],
                    power_w=phase["power_w"],
                    thermal_region=phase["thermal_region"],
                    resource_notes=phase["notes"],
                )
            )

    phases = sorted(scheduled, key=lambda phase: (phase.start_s, phase.end_s, phase.target_id, phase.phase_index))
    result = ScheduleResult(
        case_id=model.case_id,
        selected_rows=sorted(selected_rows, key=lambda row: str(row["target_id"])),
        phases=phases,
        makespan_s=solver.Value(makespan) / TIME_SCALE,
        peak_power_w=_peak_power(phases),
        max_fpp_lanes_used=_peak_fpp_lanes(phases),
        serial_busy_time_s=sum(phase.duration_s for phase in phases if phase.serial_required),
        fpp_lane_time_s=sum(phase.duration_s * phase.fpp_lanes_required for phase in phases),
    )
    info = CpSatSolveInfo(
        status_name=solver.StatusName(status),
        objective_s=solver.ObjectiveValue() / TIME_SCALE,
        wall_time_s=solver.WallTime(),
    )
    return result, info


def _recipe_spec(row: dict[str, object]) -> dict[str, Any]:
    phases = json.loads(str(row.get("phase_resources", "[]")))
    return {
        "row": row,
        "recipe_id": str(row["recipe_id"]),
        "target_id": str(row["target_id"]),
        "target_kind": str(row.get("target_kind", "")),
        "die_id": str(row.get("die_id", "")),
        "recipe_type": str(row.get("recipe_type", "")),
        "phases": [_phase_spec(phase) for phase in phases],
    }


def _phase_spec(phase: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase_name": str(phase.get("phase_name", "")),
        "duration_ticks": _ceil_scaled(float(phase.get("duration_s", 0.0)), TIME_SCALE),
        "serial_required": _to_bool(phase.get("serial_required", False)),
        "fpp_lanes_required": int(phase.get("fpp_lanes_required", 0) or 0),
        "fpp_channel": str(phase.get("fpp_channel", "")),
        "dwr_segments": [str(segment) for segment in phase.get("dwr_segments", [])],
        "route_resource": str(phase.get("route_resource", "")),
        "exclusive_resource": str(phase.get("exclusive_resource", "")),
        "power_w": float(phase.get("power_w", 0.0) or 0.0),
        "thermal_region": str(phase.get("thermal_region", "")),
        "notes": str(phase.get("notes", "")),
    }


def _add_cumulative(cp: Any, items: list[dict[str, Any]], demand_fn: Any, capacity: int) -> None:
    active = [(item, int(demand_fn(item))) for item in items]
    active = [(item, demand) for item, demand in active if demand > 0]
    if not active:
        return
    if capacity <= 0:
        raise ValueError("cumulative resource capacity must be positive when demand exists")
    cp.AddCumulative(
        [item["interval"] for item, _demand in active],
        [demand for _item, demand in active],
        capacity,
    )


def _ceil_scaled(value: float, scale: int) -> int:
    if value <= 0:
        return 0
    return int(math.ceil(value * scale - 1e-9))


def _is_capture(phase_name: str) -> bool:
    return phase_name == "CAPTURE" or phase_name.endswith("_CAPTURE") or "DWR_CAPTURE" in phase_name


def _to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}
