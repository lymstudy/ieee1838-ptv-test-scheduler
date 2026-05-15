"""Common scheduler interfaces and schedule result types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Sequence

from src.model.access import AccessConfig
from src.model.stack import DieStack
from src.model.task import TestTask
from src.model.thermal import RCThermalModel
from src.model.voltage import EquivalentPdnModel


@dataclass(frozen=True)
class ScheduleEntry:
    """One scheduled test task interval."""

    task_id: str
    task_type: str
    die_id: int
    start_time: float
    end_time: float
    duration: float
    power: float
    fpp_lanes_used: int
    access_resource: str
    dwr_segment: str | None = None
    is_capture_phase: bool | None = None

    def to_row(self) -> dict[str, Any]:
        """Return a CSV-friendly row representation."""

        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "die_id": self.die_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "power": self.power,
            "fpp_lanes_used": self.fpp_lanes_used,
            "access_resource": self.access_resource,
            "dwr_segment": self.dwr_segment or "",
            "is_capture_phase": "" if self.is_capture_phase is None else self.is_capture_phase,
        }


@dataclass(frozen=True)
class ScheduleResult:
    """Completed schedule and PTV metrics."""

    scheduler_name: str
    entries: tuple[ScheduleEntry, ...]
    tat: float
    peak_temperature: float
    peak_ir_drop: float
    temperature_trace: tuple[dict[str, float], ...]
    ir_drop_trace: tuple[dict[str, float], ...]
    metrics: dict[str, Any] = field(default_factory=dict)


class BaseScheduler(ABC):
    """Abstract base class for test access schedulers."""

    scheduler_name: str

    def __init__(
        self,
        stack: DieStack,
        access: AccessConfig,
        thermal_model: RCThermalModel,
        voltage_model: EquivalentPdnModel,
        clock_hz: float,
        time_step_s: float,
    ) -> None:
        if clock_hz <= 0:
            raise ValueError("clock_hz must be positive")
        if time_step_s <= 0:
            raise ValueError("time_step_s must be positive")
        self.stack = stack
        self.access = access
        self.thermal_model = thermal_model
        self.voltage_model = voltage_model
        self.clock_hz = clock_hz
        self.time_step_s = time_step_s

    @abstractmethod
    def schedule(self, tasks: Sequence[TestTask]) -> ScheduleResult:
        """Build a schedule for the supplied tasks."""

