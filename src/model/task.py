"""Test task model objects."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class TaskType(str, Enum):
    """Supported abstract test task types."""

    SCAN = "scan"
    BIST = "bist"
    DWR_EXTEST = "dwr_extest"
    INSTRUMENT_ACCESS = "instrument_access"


@dataclass(frozen=True)
class TestTask:
    """An abstract test task assigned to one die."""

    id: str
    die_id: int
    task_type: TaskType
    duration_cycles: int
    access_width_bits: int
    power_w: float
    fpp_lanes_required: int | None = None
    is_capture_phase: bool = False
    dwr_segment: str | None = None
    dependencies: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("task id must be non-empty")
        if self.die_id < 0:
            raise ValueError("die_id must be non-negative")
        if isinstance(self.task_type, str):
            object.__setattr__(self, "task_type", TaskType(self.task_type))
        if self.duration_cycles <= 0:
            raise ValueError("duration_cycles must be positive")
        if self.access_width_bits <= 0:
            raise ValueError("access_width_bits must be positive")
        if self.power_w < 0:
            raise ValueError("power_w must be non-negative")
        if self.fpp_lanes_required is not None and self.fpp_lanes_required < 0:
            raise ValueError("fpp_lanes_required must be non-negative")
        if self.dwr_segment is not None and not self.dwr_segment:
            raise ValueError("dwr_segment must be non-empty when provided")

        dependencies = self.dependencies
        if dependencies is None:
            normalized_dependencies = ()
        elif isinstance(dependencies, str):
            normalized_dependencies = (dependencies,)
        elif isinstance(dependencies, Iterable):
            normalized_dependencies = tuple(str(value) for value in dependencies)
        else:
            raise TypeError("dependencies must be iterable")
        object.__setattr__(self, "dependencies", normalized_dependencies)

    def duration_s(self, clock_hz: float) -> float:
        """Return task duration in seconds for a test clock frequency."""

        if clock_hz <= 0:
            raise ValueError("clock_hz must be positive")
        return self.duration_cycles / clock_hz


def build_tasks(task_entries: Iterable[dict]) -> tuple[TestTask, ...]:
    """Build tasks from iterable config entries."""

    tasks = tuple(TestTask(**entry) for entry in task_entries)
    ids = [task.id for task in tasks]
    if len(ids) != len(set(ids)):
        raise ValueError("task ids must be unique")
    return tasks
