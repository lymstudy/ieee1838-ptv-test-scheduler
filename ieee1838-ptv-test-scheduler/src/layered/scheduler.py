"""ExecutionPhase-level access-time-aware scheduler."""

from __future__ import annotations

from dataclasses import dataclass

from src.layered.phase import ExecutionPhase


@dataclass(frozen=True)
class ScheduledPhase:
    """One scheduled execution phase with a concrete time interval."""

    phase: ExecutionPhase
    start_time: float
    end_time: float


@dataclass(frozen=True)
class LayeredScheduleResult:
    """Result of scheduling a list of execution phases."""

    scheduled_phases: list[ScheduledPhase]
    total_time: float
    resource_conflicts: int
    dependency_violations: int


class AccessTimeAwareScheduler:
    """Deterministic earliest-start scheduler for expanded execution phases."""

    def __init__(self, total_fpp_lanes: int = 1, capture_exclusive: bool = True):
        if total_fpp_lanes < 0:
            raise ValueError("total_fpp_lanes must be non-negative")
        self.total_fpp_lanes = total_fpp_lanes
        self.capture_exclusive = capture_exclusive

    def schedule(self, phases: list[ExecutionPhase]) -> LayeredScheduleResult:
        """Schedule phases while respecting phase dependencies and access resources."""

        self._validate_phases(phases)
        scheduled: list[ScheduledPhase] = []
        scheduled_ids: set[str] = set()
        unscheduled = list(phases)
        input_order = {phase.phase_id: index for index, phase in enumerate(phases)}

        while unscheduled:
            progress = False
            for phase in list(unscheduled):
                if not all(dependency in scheduled_ids for dependency in phase.dependencies):
                    continue
                start_time = self._earliest_start_time(phase, scheduled)
                end_time = start_time + phase.duration
                scheduled.append(ScheduledPhase(phase=phase, start_time=start_time, end_time=end_time))
                scheduled_ids.add(phase.phase_id)
                unscheduled.remove(phase)
                progress = True
            if not progress:
                blocked = ", ".join(phase.phase_id for phase in unscheduled)
                raise ValueError(f"cyclic or unsatisfied phase dependencies block scheduling: {blocked}")

        ordered_schedule = sorted(
            scheduled,
            key=lambda item: (item.start_time, input_order[item.phase.phase_id]),
        )
        total_time = max((item.end_time for item in ordered_schedule), default=0.0)
        return LayeredScheduleResult(
            scheduled_phases=ordered_schedule,
            total_time=total_time,
            resource_conflicts=0,
            dependency_violations=0,
        )

    def _validate_phases(self, phases: list[ExecutionPhase]) -> None:
        phase_ids: set[str] = set()
        for phase in phases:
            if phase.phase_id in phase_ids:
                raise ValueError(f"duplicate phase_id in schedule input: {phase.phase_id}")
            if phase.duration < 0.0:
                raise ValueError(f"phase {phase.phase_id} has negative duration: {phase.duration}")
            phase_ids.add(phase.phase_id)

        for phase in phases:
            for dependency in phase.dependencies:
                if dependency not in phase_ids:
                    raise ValueError(
                        f"phase {phase.phase_id} depends on missing phase id: {dependency}"
                    )

        for phase in phases:
            fpp_lanes = self._fpp_lanes_required(phase)
            if fpp_lanes > self.total_fpp_lanes:
                raise ValueError(
                    f"phase {phase.phase_id} requires {fpp_lanes} FPP lanes, "
                    f"but scheduler only has {self.total_fpp_lanes}"
                )

    def _earliest_start_time(
        self,
        phase: ExecutionPhase,
        scheduled: list[ScheduledPhase],
    ) -> float:
        dependency_end_time = max(
            (
                item.end_time
                for item in scheduled
                if item.phase.phase_id in phase.dependencies
            ),
            default=0.0,
        )
        if phase.duration == 0.0:
            return dependency_end_time

        start_time = dependency_end_time
        while True:
            conflict_until = self._conflict_until(phase, start_time, scheduled)
            if conflict_until is None:
                return start_time
            if conflict_until <= start_time:
                raise RuntimeError(f"resource conflict search did not advance for {phase.phase_id}")
            start_time = conflict_until

    def _conflict_until(
        self,
        phase: ExecutionPhase,
        start_time: float,
        scheduled: list[ScheduledPhase],
    ) -> float | None:
        end_time = start_time + phase.duration
        demands = self._resource_demands(phase)
        if not demands:
            return None

        conflict_ends: list[float] = []
        for resource_id, demand in demands.items():
            capacity = self._resource_capacity(resource_id)
            resource_intervals = [
                (item.start_time, item.end_time, self._resource_demands(item.phase)[resource_id])
                for item in scheduled
                if resource_id in self._resource_demands(item.phase)
                and self._intervals_overlap(start_time, end_time, item.start_time, item.end_time)
            ]
            if not resource_intervals:
                continue

            points = {start_time, end_time}
            for interval_start, interval_end, _ in resource_intervals:
                points.add(max(start_time, interval_start))
                points.add(min(end_time, interval_end))
            ordered_points = sorted(points)

            for left, right in zip(ordered_points, ordered_points[1:]):
                if left == right:
                    continue
                used = sum(
                    interval_demand
                    for interval_start, interval_end, interval_demand in resource_intervals
                    if interval_start < right and interval_end > left
                )
                if used + demand > capacity:
                    conflict_ends.append(right)

        return min(conflict_ends) if conflict_ends else None

    def _resource_demands(self, phase: ExecutionPhase) -> dict[str, int]:
        demands: dict[str, int] = {}
        if phase.uses_ptap:
            demands["PTAP"] = 1
        if phase.uses_fpp:
            demands["FPP"] = self._fpp_lanes_required(phase)
        if phase.uses_dwr:
            demands[f"DWR:{phase.dwr_segment or 'GLOBAL'}"] = 1
        if self.capture_exclusive and phase.is_capture_phase:
            demands["CAPTURE"] = 1
        return demands

    def _resource_capacity(self, resource_id: str) -> int:
        if resource_id == "FPP":
            return self.total_fpp_lanes
        return 1

    @staticmethod
    def _fpp_lanes_required(phase: ExecutionPhase) -> int:
        if not phase.uses_fpp:
            return 0
        if phase.fpp_lanes is None or phase.fpp_lanes <= 0:
            return 1
        return phase.fpp_lanes

    @staticmethod
    def _intervals_overlap(
        start_a: float,
        end_a: float,
        start_b: float,
        end_b: float,
    ) -> bool:
        return start_a < end_b and end_a > start_b
