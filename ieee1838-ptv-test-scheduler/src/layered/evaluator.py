"""Lightweight metrics for ExecutionPhase-level schedules."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.layered.scheduler import LayeredScheduleResult, ScheduledPhase


@dataclass(frozen=True)
class LayeredScheduleMetrics:
    """Aggregate access/resource metrics for a layered phase schedule."""

    total_time: float
    phase_count: int
    ptap_busy_time: float
    ptap_utilization: float
    fpp_busy_time: float
    fpp_utilization: float
    dwr_busy_time: float
    capture_busy_time: float
    local_execution_time: float
    access_overhead_time: float
    access_overhead_ratio: float
    max_parallel_phases: int
    average_parallelism: float
    resource_busy_time: dict[str, float] = field(default_factory=dict)
    phase_type_time: dict[str, float] = field(default_factory=dict)


class LayeredScheduleEvaluator:
    """Evaluate phase-level access and resource behavior."""

    @staticmethod
    def evaluate(
        result: LayeredScheduleResult,
        total_fpp_lanes: int = 1,
    ) -> LayeredScheduleMetrics:
        """Compute lightweight metrics for a layered schedule result."""

        scheduled = result.scheduled_phases
        total_time = result.total_time
        phase_count = len(scheduled)
        ptap_busy_time = sum(_duration(item) for item in scheduled if item.phase.uses_ptap)
        fpp_busy_time = sum(
            _duration(item) * _fpp_lanes_required(item)
            for item in scheduled
            if item.phase.uses_fpp
        )
        dwr_busy_time = sum(_duration(item) for item in scheduled if item.phase.uses_dwr)
        capture_busy_time = sum(
            _duration(item) for item in scheduled if item.phase.is_capture_phase
        )
        local_execution_time = sum(
            _duration(item) for item in scheduled if item.phase.is_local_execution
        )
        access_overhead_time = sum(
            _duration(item) for item in scheduled if _is_access_overhead(item)
        )
        max_parallel, average_parallelism = _parallelism_metrics(scheduled, total_time)
        resource_busy_time = _resource_busy_times(scheduled)
        phase_type_time = _phase_type_times(scheduled)

        return LayeredScheduleMetrics(
            total_time=total_time,
            phase_count=phase_count,
            ptap_busy_time=ptap_busy_time,
            ptap_utilization=_safe_ratio(ptap_busy_time, total_time),
            fpp_busy_time=fpp_busy_time,
            fpp_utilization=_safe_ratio(fpp_busy_time, total_time * max(total_fpp_lanes, 0)),
            dwr_busy_time=dwr_busy_time,
            capture_busy_time=capture_busy_time,
            local_execution_time=local_execution_time,
            access_overhead_time=access_overhead_time,
            access_overhead_ratio=_safe_ratio(access_overhead_time, total_time),
            max_parallel_phases=max_parallel,
            average_parallelism=average_parallelism,
            resource_busy_time=resource_busy_time,
            phase_type_time=phase_type_time,
        )


def _duration(item: ScheduledPhase) -> float:
    return max(0.0, item.end_time - item.start_time)


def _fpp_lanes_required(item: ScheduledPhase) -> int:
    lanes = item.phase.fpp_lanes
    if lanes is None or lanes <= 0:
        return 1
    return lanes


def _is_access_overhead(item: ScheduledPhase) -> bool:
    phase = item.phase
    if phase.phase_type == "LOCAL_BIST_RUN":
        return False
    if phase.is_local_execution:
        return False
    text = f"{phase.phase_type} {phase.description}".upper()
    keywords = (
        "CONFIG",
        "ACCESS",
        "SHIFT_IN",
        "SHIFT_OUT",
        "READBACK",
        "READ_",
        "TRANSFER",
    )
    return any(keyword in text for keyword in keywords)


def _parallelism_metrics(scheduled: list[ScheduledPhase], total_time: float) -> tuple[int, float]:
    if total_time <= 0.0 or not scheduled:
        return 0, 0.0

    points = sorted(
        {
            point
            for item in scheduled
            for point in (item.start_time, item.end_time)
        }
    )
    max_parallel = 0
    active_time = 0.0
    for left, right in zip(points, points[1:]):
        if right <= left:
            continue
        active_count = sum(
            1 for item in scheduled if item.start_time < right and item.end_time > left
        )
        max_parallel = max(max_parallel, active_count)
        active_time += active_count * (right - left)
    return max_parallel, active_time / total_time


def _resource_busy_times(scheduled: list[ScheduledPhase]) -> dict[str, float]:
    busy: dict[str, float] = {}
    for item in scheduled:
        duration = _duration(item)
        phase = item.phase
        if phase.uses_ptap:
            _add_busy_time(busy, "PTAP", duration)
        if phase.uses_fpp:
            _add_busy_time(busy, "FPP", duration * _fpp_lanes_required(item))
        if phase.uses_dwr:
            _add_busy_time(busy, "DWR", duration)
            _add_busy_time(busy, f"DWR:{phase.dwr_segment or 'GLOBAL'}", duration)
        if phase.is_capture_phase:
            _add_busy_time(busy, "CAPTURE", duration)
        if phase.is_local_execution:
            _add_busy_time(busy, "LOCAL_EXECUTION", duration)
    return busy


def _phase_type_times(scheduled: list[ScheduledPhase]) -> dict[str, float]:
    phase_type_time: dict[str, float] = {}
    for item in scheduled:
        _add_busy_time(phase_type_time, item.phase.phase_type, _duration(item))
    return phase_type_time


def _add_busy_time(values: dict[str, float], key: str, duration: float) -> None:
    values[key] = values.get(key, 0.0) + duration


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0.0:
        return 0.0
    return numerator / denominator
