"""Tests for B3.1 ExecutionPhase-level access-time-aware scheduling."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.layered import AccessTimeAwareScheduler, ExecutionPhase


def phase(
    phase_id: str,
    duration: float,
    *,
    dependencies: tuple[str, ...] = (),
    phase_type: str = "TEST_PHASE",
    uses_ptap: bool = False,
    uses_fpp: bool = False,
    fpp_lanes: int = 0,
    uses_dwr: bool = False,
    dwr_segment: str | None = None,
    is_capture_phase: bool = False,
    is_local_execution: bool = False,
) -> ExecutionPhase:
    """Build a compact ExecutionPhase for scheduler tests."""

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
        dependencies=dependencies,
    )


def by_id(result, phase_id: str):
    """Return a scheduled phase by ID."""

    return next(item for item in result.scheduled_phases if item.phase.phase_id == phase_id)


def test_pure_dependency_chain_schedules_serially() -> None:
    """A dependency chain should run in dependency order."""

    scheduler = AccessTimeAwareScheduler()
    result = scheduler.schedule(
        [
            phase("p1", 1.0),
            phase("p2", 2.0, dependencies=("p1",)),
            phase("p3", 3.0, dependencies=("p2",)),
        ]
    )

    assert by_id(result, "p1").start_time == 0.0
    assert by_id(result, "p2").start_time == 1.0
    assert by_id(result, "p3").start_time == 3.0
    assert result.total_time == 6.0
    assert result.dependency_violations == 0


def test_two_independent_local_execution_phases_can_overlap() -> None:
    """Independent local execution phases should not occupy PTAP implicitly."""

    scheduler = AccessTimeAwareScheduler()
    result = scheduler.schedule(
        [
            phase("local_a", 3.0, phase_type="LOCAL_BIST_RUN", is_local_execution=True),
            phase("local_b", 5.0, phase_type="LOCAL_BIST_RUN", is_local_execution=True),
        ]
    )

    assert by_id(result, "local_a").start_time == 0.0
    assert by_id(result, "local_b").start_time == 0.0
    assert result.total_time == 5.0
    assert result.resource_conflicts == 0


def test_two_ptap_phases_cannot_overlap() -> None:
    """Global PTAP phases should be serialized."""

    scheduler = AccessTimeAwareScheduler()
    result = scheduler.schedule(
        [
            phase("ptap_a", 3.0, uses_ptap=True),
            phase("ptap_b", 2.0, uses_ptap=True),
        ]
    )

    assert by_id(result, "ptap_a").start_time == 0.0
    assert by_id(result, "ptap_b").start_time == 3.0
    assert result.total_time == 5.0


def test_bist_local_run_can_overlap_with_ptap_config_when_ptap_is_false() -> None:
    """A PTAP-free BIST local run can overlap another PTAP config phase."""

    scheduler = AccessTimeAwareScheduler()
    result = scheduler.schedule(
        [
            phase("bist_local", 10.0, phase_type="LOCAL_BIST_RUN", is_local_execution=True),
            phase("config_other", 2.0, phase_type="CONFIG_ACCESS_PATH", uses_ptap=True),
        ]
    )

    assert by_id(result, "bist_local").start_time == 0.0
    assert by_id(result, "config_other").start_time == 0.0
    assert result.total_time == 10.0


def test_fpp_lane_capacity_is_respected() -> None:
    """FPP phases should not exceed the configured lane capacity."""

    scheduler = AccessTimeAwareScheduler(total_fpp_lanes=2)
    result = scheduler.schedule(
        [
            phase("wide_fpp", 4.0, uses_fpp=True, fpp_lanes=2),
            phase("narrow_fpp", 1.0, uses_fpp=True, fpp_lanes=1),
        ]
    )

    assert by_id(result, "wide_fpp").start_time == 0.0
    assert by_id(result, "narrow_fpp").start_time == 4.0
    assert result.total_time == 5.0


def test_dwr_segments_conflict_only_when_same_segment_is_used() -> None:
    """Different DWR segments can overlap, but the same segment is exclusive."""

    scheduler = AccessTimeAwareScheduler()
    result = scheduler.schedule(
        [
            phase("dwr_a1", 4.0, uses_dwr=True, dwr_segment="dwr_a"),
            phase("dwr_b", 3.0, uses_dwr=True, dwr_segment="dwr_b"),
            phase("dwr_a2", 2.0, uses_dwr=True, dwr_segment="dwr_a"),
        ]
    )

    assert by_id(result, "dwr_a1").start_time == 0.0
    assert by_id(result, "dwr_b").start_time == 0.0
    assert by_id(result, "dwr_a2").start_time == 4.0
    assert result.total_time == 6.0


def test_missing_dependency_raises_value_error() -> None:
    """A dependency on an absent phase ID should be rejected."""

    scheduler = AccessTimeAwareScheduler()
    with pytest.raises(ValueError, match="missing phase id"):
        scheduler.schedule([phase("p1", 1.0, dependencies=("missing",))])


def test_output_total_time_equals_max_end_time() -> None:
    """The reported total time should match the maximum scheduled end time."""

    scheduler = AccessTimeAwareScheduler()
    result = scheduler.schedule(
        [
            phase("local", 2.0, is_local_execution=True),
            phase("ptap", 5.0, uses_ptap=True),
        ]
    )

    assert result.total_time == max(item.end_time for item in result.scheduled_phases)
