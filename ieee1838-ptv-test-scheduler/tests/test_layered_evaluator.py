"""Tests for B3.1.5 layered schedule metrics evaluation."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.layered import (
    ExecutionPhase,
    LayeredScheduleEvaluator,
    LayeredScheduleResult,
    ScheduledPhase,
)


def phase(
    phase_id: str,
    duration: float,
    *,
    phase_type: str = "TEST_PHASE",
    uses_ptap: bool = False,
    uses_fpp: bool = False,
    fpp_lanes: int = 0,
    uses_dwr: bool = False,
    dwr_segment: str | None = None,
    is_capture_phase: bool = False,
    is_local_execution: bool = False,
    description: str = "",
) -> ExecutionPhase:
    """Build a compact ExecutionPhase for evaluator tests."""

    return ExecutionPhase(
        phase_id=phase_id,
        parent_intent_id="intent",
        phase_type=phase_type,
        target_die=0,
        involved_dies=(0,),
        duration=duration,
        power=0.0,
        fpp_lanes=fpp_lanes,
        dwr_segment=dwr_segment,
        uses_ptap=uses_ptap,
        uses_fpp=uses_fpp,
        uses_dwr=uses_dwr,
        is_capture_phase=is_capture_phase,
        is_local_execution=is_local_execution,
        description=description,
    )


def scheduled(item: ExecutionPhase, start_time: float) -> ScheduledPhase:
    """Place one phase at the requested start time."""

    return ScheduledPhase(
        phase=item,
        start_time=start_time,
        end_time=start_time + item.duration,
    )


def schedule_result(items: list[ScheduledPhase]) -> LayeredScheduleResult:
    """Build a LayeredScheduleResult from scheduled test phases."""

    return LayeredScheduleResult(
        scheduled_phases=items,
        total_time=max((item.end_time for item in items), default=0.0),
        resource_conflicts=0,
        dependency_violations=0,
    )


def test_empty_schedule_evaluates_to_zero_metrics() -> None:
    """An empty schedule should produce zero-valued metrics."""

    metrics = LayeredScheduleEvaluator.evaluate(schedule_result([]))

    assert metrics.total_time == 0.0
    assert metrics.phase_count == 0
    assert metrics.ptap_utilization == 0.0
    assert metrics.fpp_utilization == 0.0
    assert metrics.max_parallel_phases == 0
    assert metrics.average_parallelism == 0.0
    assert metrics.resource_busy_time == {}
    assert metrics.phase_type_time == {}


def test_ptap_utilization_is_computed_correctly() -> None:
    """PTAP utilization should be busy time divided by total schedule time."""

    result = schedule_result(
        [
            scheduled(phase("config", 2.0, phase_type="CONFIG_ACCESS_PATH", uses_ptap=True), 0.0),
            scheduled(phase("local", 4.0, phase_type="LOCAL_BIST_RUN", is_local_execution=True), 0.0),
        ]
    )
    metrics = LayeredScheduleEvaluator.evaluate(result)

    assert metrics.ptap_busy_time == 2.0
    assert metrics.ptap_utilization == 0.5


def test_fpp_utilization_accounts_for_lane_count() -> None:
    """FPP utilization should use lane-seconds over available lane-seconds."""

    result = schedule_result(
        [
            scheduled(
                phase("fpp_shift", 3.0, phase_type="FPP_SHIFT_IN", uses_fpp=True, fpp_lanes=2),
                0.0,
            ),
            scheduled(phase("tail", 6.0), 0.0),
        ]
    )
    metrics = LayeredScheduleEvaluator.evaluate(result, total_fpp_lanes=4)

    assert metrics.fpp_busy_time == 6.0
    assert metrics.fpp_utilization == 0.25


def test_local_execution_time_is_separated_from_ptap_busy_time() -> None:
    """Local execution should not count as PTAP busy time unless uses_ptap is set."""

    result = schedule_result(
        [
            scheduled(
                phase("local", 5.0, phase_type="LOCAL_BIST_RUN", is_local_execution=True),
                0.0,
            ),
            scheduled(phase("read", 2.0, phase_type="READBACK", uses_ptap=True), 0.0),
        ]
    )
    metrics = LayeredScheduleEvaluator.evaluate(result)

    assert metrics.local_execution_time == 5.0
    assert metrics.ptap_busy_time == 2.0


def test_access_overhead_excludes_local_bist_run() -> None:
    """LOCAL_BIST_RUN should not be counted as access overhead."""

    result = schedule_result(
        [
            scheduled(
                phase("local", 10.0, phase_type="LOCAL_BIST_RUN", is_local_execution=True),
                0.0,
            ),
            scheduled(phase("config", 2.0, phase_type="CONFIG_ACCESS_PATH"), 0.0),
        ]
    )
    metrics = LayeredScheduleEvaluator.evaluate(result)

    assert metrics.access_overhead_time == 2.0
    assert metrics.access_overhead_ratio == pytest.approx(0.2)


def test_max_parallel_phases_detects_overlapping_phases() -> None:
    """The maximum active phase count should reflect interval overlap."""

    result = schedule_result(
        [
            scheduled(phase("a", 4.0), 0.0),
            scheduled(phase("b", 2.0), 1.0),
            scheduled(phase("c", 3.0), 2.0),
        ]
    )
    metrics = LayeredScheduleEvaluator.evaluate(result)

    assert metrics.max_parallel_phases == 3


def test_average_parallelism_is_greater_than_one_for_overlapping_phases() -> None:
    """Average parallelism should exceed one when phases overlap."""

    result = schedule_result(
        [
            scheduled(phase("a", 4.0), 0.0),
            scheduled(phase("b", 4.0), 0.0),
        ]
    )
    metrics = LayeredScheduleEvaluator.evaluate(result)

    assert metrics.average_parallelism == 2.0
    assert metrics.average_parallelism > 1.0


def test_phase_type_time_aggregates_durations_by_phase_type() -> None:
    """Phase-type totals should aggregate all phases with the same type."""

    result = schedule_result(
        [
            scheduled(phase("config_a", 1.0, phase_type="CONFIG_ACCESS_PATH"), 0.0),
            scheduled(phase("config_b", 2.0, phase_type="CONFIG_ACCESS_PATH"), 1.0),
            scheduled(phase("local", 3.0, phase_type="LOCAL_BIST_RUN"), 0.0),
        ]
    )
    metrics = LayeredScheduleEvaluator.evaluate(result)

    assert metrics.phase_type_time["CONFIG_ACCESS_PATH"] == 3.0
    assert metrics.phase_type_time["LOCAL_BIST_RUN"] == 3.0
