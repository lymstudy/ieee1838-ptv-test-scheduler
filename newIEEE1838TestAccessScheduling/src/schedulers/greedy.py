from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence, Union

from src.model import SystemModel


EPSILON = 1e-12


class SchedulingError(RuntimeError):
    """Raised when no legal schedule can be built for the supplied recipes."""


@dataclass(frozen=True)
class ScheduledPhase:
    case_id: str
    target_id: str
    target_kind: str
    die_id: str
    recipe_id: str
    recipe_type: str
    phase_index: int
    phase_name: str
    start_s: float
    end_s: float
    duration_s: float
    serial_required: bool
    fpp_lanes_required: int
    fpp_channel: str
    dwr_segments: str
    route_resource: str
    exclusive_resource: str
    power_w: float
    thermal_region: str
    resource_notes: str


@dataclass(frozen=True)
class ScheduleResult:
    case_id: str
    selected_rows: list[dict[str, object]]
    phases: list[ScheduledPhase]
    makespan_s: float
    peak_power_w: float
    max_fpp_lanes_used: int
    serial_busy_time_s: float
    fpp_lane_time_s: float


def _normalize_rows(
    rows: list[dict[str, object]] | list[Any],
) -> tuple[list[dict[str, object]], str]:
    """Normalize input to a list of phase-capable dicts + detect scheduling mode.

    Returns (normalized_rows, mode) where mode is one of:
      - "recipe": old model — recipes are mutually exclusive per target_id
      - "task":   new model — each task is mandatory; one variant per task_id
    """
    if not rows:
        raise SchedulingError("no recipe rows supplied")

    first = rows[0]
    # If the items are dicts already, check if they carry a task_id key
    if isinstance(first, dict):
        has_task_id = any("task_id" in r for r in rows if isinstance(r, dict))  # type: ignore[attr-defined]
        if has_task_id:
            # New model: CompilationVariant already converted to dicts
            return list(rows), "task"  # type: ignore[arg-type]
        # Old model: plain dict rows
        return list(rows), "recipe"  # type: ignore[arg-type]

    # Otherwise, try to call .to_recipe_row() on each item (CompilationVariant)
    normalized: list[dict[str, object]] = []
    for item in rows:
        converter = getattr(item, "to_recipe_row", None)
        if converter is None:
            raise SchedulingError(
                f"unsupported row type: {type(item).__name__} — "
                f"expected dict or object with to_recipe_row() method"
            )
        normalized.append(converter())
    return normalized, "task"


def greedy_schedule(
    model: SystemModel,
    rows_or_variants: list[dict[str, object]] | list[Any],
) -> ScheduleResult:
    """Build a greedy schedule.

    Supports two input modes:

    OLD (recipe mode) — list of RecipeRow-style dicts:
        One recipe per target.  Groups by ``target_id`` and picks
        exactly one recipe for each target.

    NEW (task mode) — list of CompilationVariant objects (or their
    dict equivalents):
        Groups by ``task_id``.  Every task is mandatory — the
        scheduler picks exactly one variant per task and schedules
        all tasks.
    """
    rows, mode = _normalize_rows(rows_or_variants)  # type: ignore[arg-type]

    # --- group rows according to current mode --------------------------------
    groups: dict[str, list[dict[str, object]]] = {}
    group_key = "task_id" if mode == "task" else "target_id"
    for row in rows:
        groups.setdefault(str(row[group_key]), []).append(row)

    # --- greedy selection ----------------------------------------------------
    scheduled: list[ScheduledPhase] = []
    selected: list[dict[str, object]] = []
    for group_id in _group_order(groups, mode):
        best_phases: list[ScheduledPhase] | None = None
        best_row: dict[str, object] | None = None
        best_key: tuple[float, float, float, int, str] | None = None

        for row in sorted(groups[group_id], key=_recipe_order_key):
            try:
                trial = _schedule_recipe(model, row, scheduled)
            except SchedulingError:
                continue
            finish = max((phase.end_s for phase in trial), default=0.0)
            key = (
                finish,
                float(row.get("peak_power_w", 0.0)),
                float(row.get("lane_occupancy", 0.0)),
                _recipe_type_priority(str(row.get("recipe_type", ""))),
                str(row.get("recipe_id", "")),
            )
            if best_key is None or key < best_key:
                best_key = key
                best_row = row
                best_phases = trial

        if best_row is None or best_phases is None:
            label = "task" if mode == "task" else "target"
            raise SchedulingError(f"no legal variant found for {label} {group_id}")

        selected.append(best_row)
        scheduled.extend(best_phases)

    # --- assemble result -----------------------------------------------------
    phases = sorted(scheduled, key=lambda phase: (phase.start_s, phase.end_s, phase.target_id, phase.phase_index))
    return ScheduleResult(
        case_id=model.case_id,
        selected_rows=sorted(selected, key=lambda row: str(row["target_id"])),
        phases=phases,
        makespan_s=max((phase.end_s for phase in phases), default=0.0),
        peak_power_w=_peak_power(phases),
        max_fpp_lanes_used=_peak_fpp_lanes(phases),
        serial_busy_time_s=sum(phase.duration_s for phase in phases if phase.serial_required),
        fpp_lane_time_s=sum(phase.duration_s * phase.fpp_lanes_required for phase in phases),
    )


def write_schedule_csv(result: ScheduleResult, output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(asdict(result.phases[0]).keys()) if result.phases else list(ScheduledPhase.__dataclass_fields__)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for phase in result.phases:
            writer.writerow(asdict(phase))


def write_schedule_report_markdown(result: ScheduleResult, output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# M4 Greedy Schedule Report",
        "",
        f"- Case: {result.case_id}",
        f"- Selected recipes: {len(result.selected_rows)}",
        f"- Scheduled phases: {len(result.phases)}",
        f"- Makespan: {result.makespan_s:.9f} s",
        f"- Peak scheduled power: {result.peak_power_w:.6f} W",
        f"- Peak FPP lanes used: {result.max_fpp_lanes_used}",
        f"- Serial busy time: {result.serial_busy_time_s:.9f} s",
        f"- FPP lane-time: {result.fpp_lane_time_s:.9f} lane*s",
        "",
        "## Selected Recipes",
        "",
        "| target_id | recipe_id | type | total_time_s | peak_power_w |",
        "| --- | --- | --- | ---: | ---: |",
    ]
    for row in result.selected_rows:
        lines.append(
            "| {target_id} | {recipe_id} | {recipe_type} | {total_time_s} | {peak_power_w} |".format(
                target_id=row.get("target_id", ""),
                recipe_id=row.get("recipe_id", ""),
                recipe_type=row.get("recipe_type", ""),
                total_time_s=row.get("total_time_s", ""),
                peak_power_w=row.get("peak_power_w", ""),
            )
        )

    lines.extend(["", "## Gantt Preview", "", "```text"])
    lines.extend(_gantt_lines(result.phases, result.makespan_s))
    lines.extend(["```", ""])
    output.write_text("\n".join(lines), encoding="utf-8")


def _schedule_recipe(
    model: SystemModel,
    row: dict[str, object],
    committed: list[ScheduledPhase],
) -> list[ScheduledPhase]:
    phases = _parse_phase_resources(row)
    trial: list[ScheduledPhase] = []
    earliest = 0.0
    for index, phase in enumerate(phases):
        duration = float(phase.get("duration_s", 0.0))
        start = _find_earliest_start(model, phase, duration, earliest, committed + trial)
        end = start + duration
        trial.append(
            ScheduledPhase(
                case_id=model.case_id,
                target_id=str(row["target_id"]),
                target_kind=str(row.get("target_kind", "")),
                die_id=str(row.get("die_id", "")),
                recipe_id=str(row["recipe_id"]),
                recipe_type=str(row.get("recipe_type", "")),
                phase_index=index,
                phase_name=str(phase.get("phase_name", "")),
                start_s=start,
                end_s=end,
                duration_s=duration,
                serial_required=_to_bool(phase.get("serial_required", False)),
                fpp_lanes_required=int(phase.get("fpp_lanes_required", 0) or 0),
                fpp_channel=str(phase.get("fpp_channel", "")),
                dwr_segments=";".join(str(segment) for segment in phase.get("dwr_segments", [])),
                route_resource=str(phase.get("route_resource", "")),
                exclusive_resource=str(phase.get("exclusive_resource", "")),
                power_w=float(phase.get("power_w", 0.0) or 0.0),
                thermal_region=str(phase.get("thermal_region", "")),
                resource_notes=str(phase.get("notes", "")),
            )
        )
        earliest = end

    # Annotate with task_id when present (new task model)
    if "task_id" in row:
        task_id = str(row["task_id"])
        for tp in trial:
            object.__setattr__(tp, "recipe_id", f"{tp.recipe_id}|task={task_id}")

    return trial


def _find_earliest_start(
    model: SystemModel,
    phase: dict[str, object],
    duration: float,
    earliest: float,
    scheduled: list[ScheduledPhase],
) -> float:
    if duration < -EPSILON:
        raise SchedulingError(f"negative phase duration: {duration}")
    if duration <= EPSILON:
        return earliest

    start = earliest
    while True:
        end = start + duration
        if _interval_is_feasible(model, phase, start, end, scheduled):
            return start

        overlapping_ends = [
            existing.end_s
            for existing in scheduled
            if existing.start_s < end - EPSILON and start < existing.end_s - EPSILON
        ]
        if not overlapping_ends:
            raise SchedulingError(f"phase cannot satisfy resource constraints: {phase.get('phase_name', '')}")
        start = max(start + EPSILON, min(overlapping_ends))


def _interval_is_feasible(
    model: SystemModel,
    candidate: dict[str, object],
    start: float,
    end: float,
    scheduled: list[ScheduledPhase],
) -> bool:
    boundaries = {start, end}
    for phase in scheduled:
        if phase.start_s < end - EPSILON and start < phase.end_s - EPSILON:
            boundaries.add(max(start, phase.start_s))
            boundaries.add(min(end, phase.end_s))

    ordered = sorted(boundaries)
    for left, right in zip(ordered, ordered[1:]):
        if right - left <= EPSILON:
            continue
        active = [
            phase
            for phase in scheduled
            if phase.start_s < right - EPSILON and left < phase.end_s - EPSILON
        ]
        if not _resources_fit(model, candidate, active):
            return False
    return True


def _resources_fit(model: SystemModel, candidate: dict[str, object], active: list[ScheduledPhase]) -> bool:
    serial_capacity = int(model.resource_limits.get("ptap_ports", 1))
    serial_used = int(_to_bool(candidate.get("serial_required", False))) + sum(int(phase.serial_required) for phase in active)
    if serial_used > serial_capacity:
        return False

    candidate_lanes = int(candidate.get("fpp_lanes_required", 0) or 0)
    total_lanes = candidate_lanes + sum(phase.fpp_lanes_required for phase in active)
    if total_lanes > int(model.resource_limits.get("total_fpp_lanes", total_lanes)):
        return False

    channel = str(candidate.get("fpp_channel", ""))
    for channel_id, capacity in _fpp_channel_capacities(model).items():
        used = sum(phase.fpp_lanes_required for phase in active if phase.fpp_channel == channel_id)
        if channel == channel_id:
            used += candidate_lanes
        if used > capacity:
            return False

    power = float(candidate.get("power_w", 0.0) or 0.0) + sum(phase.power_w for phase in active)
    if power > float(model.resource_limits.get("max_total_power_w", power)) + EPSILON:
        return False

    capture_limit = int(model.resource_limits.get("max_concurrent_capture", len(active) + 1))
    capture_count = int(_is_capture(str(candidate.get("phase_name", "")))) + sum(int(_is_capture(phase.phase_name)) for phase in active)
    if capture_count > capture_limit:
        return False

    if not _dwr_groups_fit(model, candidate, active):
        return False
    if not _exclusive_resources_fit(candidate, active):
        return False
    if not _bist_engine_groups_fit(model, candidate, active):
        return False
    return True


def _dwr_groups_fit(model: SystemModel, candidate: dict[str, object], active: list[ScheduledPhase]) -> bool:
    candidate_segments = set(str(segment) for segment in candidate.get("dwr_segments", []))
    for group in model.raw.get("resource_groups", {}).get("dwr_conflict_groups", []):
        members = set(str(member) for member in group.get("members", []))
        used = int(bool(candidate_segments & members))
        for phase in active:
            if set(phase.dwr_segments.split(";")) & members:
                used += 1
        if used > int(group.get("capacity", 1)):
            return False
    return True


def _exclusive_resources_fit(candidate: dict[str, object], active: list[ScheduledPhase]) -> bool:
    resource = str(candidate.get("exclusive_resource", ""))
    if not resource:
        return True
    return all(phase.exclusive_resource != resource for phase in active)


def _bist_engine_groups_fit(model: SystemModel, candidate: dict[str, object], active: list[ScheduledPhase]) -> bool:
    if str(candidate.get("phase_name", "")) != "LOCAL_BIST_RUN":
        candidate_targets: set[str] = set()
    else:
        candidate_targets = {str(candidate.get("target_id", ""))}

    for group in model.raw.get("resource_groups", {}).get("bist_engine_groups", []):
        members = set(str(member) for member in group.get("members", []))
        used = int(bool(candidate_targets & members))
        used += sum(int(phase.phase_name == "LOCAL_BIST_RUN" and phase.target_id in members) for phase in active)
        if used > int(group.get("capacity", 1)):
            return False
    return True


def _parse_phase_resources(row: dict[str, object]) -> list[dict[str, object]]:
    payload = row.get("phase_resources", "[]")
    if isinstance(payload, list):
        phases = payload
    else:
        phases = json.loads(str(payload))
    rows = [dict(phase) for phase in phases]
    for phase in rows:
        phase.setdefault("target_id", row.get("target_id", ""))
    return rows


def _group_order(groups: dict[str, list[dict[str, object]]], mode: str) -> list[str]:
    """Sort groups (targets or tasks) by thermal risk (descending), then id."""
    return sorted(
        groups,
        key=lambda gid: (
            -max(float(row.get("thermal_risk", 0.0)) for row in groups[gid]),
            gid,
        ),
    )


def _recipe_order_key(row: dict[str, object]) -> tuple[float, float, float, int, str]:
    blocking_time = float(row.get("serial_time_s", 0.0)) + float(row.get("fpp_time_s", 0.0))
    return (
        blocking_time,
        float(row.get("total_time_s", 0.0)),
        float(row.get("thermal_risk", 0.0)),
        _recipe_type_priority(str(row.get("recipe_type", ""))),
        str(row.get("recipe_id", "")),
    )


def _recipe_type_priority(recipe_type: str) -> int:
    return {"B": 0, "F": 1, "H": 2, "S": 3, "I": 4}.get(recipe_type, 99)


def _fpp_channel_capacities(model: SystemModel) -> dict[str, int]:
    return {
        str(channel["channel_id"]): int(channel.get("max_lanes", model.resource_limits.get("total_fpp_lanes", 0)))
        for channel in model.access.get("fpp_channels", [])
    }


def _peak_power(phases: list[ScheduledPhase]) -> float:
    peak = 0.0
    for boundary in sorted({time for phase in phases for time in (phase.start_s, phase.end_s)}):
        active_power = sum(phase.power_w for phase in phases if phase.start_s <= boundary < phase.end_s - EPSILON)
        peak = max(peak, active_power)
    return peak


def _peak_fpp_lanes(phases: list[ScheduledPhase]) -> int:
    peak = 0
    for boundary in sorted({time for phase in phases for time in (phase.start_s, phase.end_s)}):
        active_lanes = sum(phase.fpp_lanes_required for phase in phases if phase.start_s <= boundary < phase.end_s - EPSILON)
        peak = max(peak, active_lanes)
    return peak


def _gantt_lines(phases: list[ScheduledPhase], makespan: float) -> list[str]:
    if makespan <= EPSILON:
        return []
    width = 60
    lines = []
    for phase in sorted(phases, key=lambda item: (item.start_s, item.target_id, item.phase_index)):
        left = int((phase.start_s / makespan) * width)
        span = max(1, int((phase.duration_s / makespan) * width))
        bar = " " * left + "#" * min(span, width - left)
        label = f"{phase.target_id}:{phase.phase_name}"
        lines.append(f"{phase.start_s:>11.9f}-{phase.end_s:>11.9f} | {bar:<60} | {label}")
    return lines


def _is_capture(phase_name: str) -> bool:
    return phase_name == "CAPTURE" or phase_name.endswith("_CAPTURE") or "DWR_CAPTURE" in phase_name


def _to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}
