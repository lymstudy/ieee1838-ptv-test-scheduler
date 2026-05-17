"""Execution phase and layered task data models."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.layered.intent import BaseTestIntent


@dataclass(frozen=True)
class ExecutionPhase:
    """A schedulable phase expanded from a high-level test intent."""

    phase_id: str
    parent_intent_id: str
    phase_type: str
    target_die: int | None
    involved_dies: tuple[int, ...]
    duration: float
    power: float
    occupied_resources: tuple[str, ...] = field(default_factory=tuple)
    fpp_lanes: int = 0
    dwr_segment: str | None = None
    uses_ptap: bool = False
    uses_fpp: bool = False
    uses_dwr: bool = False
    is_local_execution: bool = False
    is_capture_phase: bool = False
    requires_readback: bool = False
    dependencies: tuple[str, ...] = field(default_factory=tuple)
    description: str = ""


@dataclass(frozen=True)
class LayeredTask:
    """A high-level test intent expanded into ordered execution phases."""

    layered_task_id: str
    parent_intent: BaseTestIntent
    phases: tuple[ExecutionPhase, ...]
    total_estimated_time: float = field(init=False)
    notes: str = ""

    def __post_init__(self) -> None:
        """Derive total estimated time from phase durations."""

        object.__setattr__(
            self,
            "total_estimated_time",
            sum(phase.duration for phase in self.phases),
        )
