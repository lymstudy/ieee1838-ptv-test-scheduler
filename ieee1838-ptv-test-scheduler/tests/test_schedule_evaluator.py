"""Tests for the unified schedule evaluator."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.model.access import AccessConfig, DwrSegment, FppConfig
from src.model.stack import Die, DieStack
from src.model.thermal import RCThermalModel, ThermalConfig
from src.model.voltage import EquivalentPdnModel, VoltageConfig
from src.scheduler.base import ScheduleEntry
from src.scheduler.evaluator import evaluate_schedule


def two_die_stack() -> DieStack:
    """Return a compact two-die stack for evaluator tests."""

    return DieStack(
        (
            Die(0, "die0", 0, 10.0, 25.0, 0.1),
            Die(1, "die1", 1, 10.0, 25.0, 0.1),
        )
    )


def two_die_access() -> AccessConfig:
    """Return simple FPP and DWR access resources."""

    return AccessConfig(
        ptap_width_bits=1,
        stap_count=2,
        dwr_segments=(
            DwrSegment(0, "dwr_die0", 32),
            DwrSegment(1, "dwr_die1", 32),
        ),
        fpp=FppConfig(enabled=True, lanes=2, lane_width_bits=1),
    )


def entry(task_id: str, die_id: int, start: float, end: float) -> ScheduleEntry:
    """Build a schedule entry with fixed power for evaluator comparisons."""

    return ScheduleEntry(
        task_id=task_id,
        task_type="scan",
        die_id=die_id,
        start_time=start,
        end_time=end,
        duration=end - start,
        power=1.0,
        fpp_lanes_used=1,
        access_resource="FPP_SCAN",
        dwr_segment=f"dwr_die{die_id}",
        is_capture_phase=False,
    )


def evaluate(entries: tuple[ScheduleEntry, ...]):
    """Evaluate entries with a shared-PDN voltage model."""

    return evaluate_schedule(
        scheduler_name="toy",
        entries=entries,
        stack=two_die_stack(),
        access=two_die_access(),
        thermal_model=RCThermalModel(
            ThermalConfig(
                ambient_temp_c=25.0,
                thermal_resistance_c_per_w=2.0,
                thermal_capacitance_j_per_c=0.5,
                max_temp_c=100.0,
            )
        ),
        voltage_model=EquivalentPdnModel(
            VoltageConfig(
                nominal_voltage_v=1.0,
                pdn_resistance_ohm=0.1,
                max_ir_drop_v=1.0,
                mode="shared",
            )
        ),
        time_step_s=0.1,
    )


def test_parallel_schedule_has_higher_peak_ir_drop_than_serial_schedule() -> None:
    """Shared-PDN evaluation should accumulate concurrent task current."""

    serial = evaluate((entry("a", 0, 0.0, 1.0), entry("b", 1, 1.0, 2.0)))
    parallel = evaluate((entry("a", 0, 0.0, 1.0), entry("b", 1, 0.0, 1.0)))

    assert parallel.peak_ir_drop > serial.peak_ir_drop
    assert parallel.peak_ir_drop == pytest.approx(0.2)
    assert serial.peak_ir_drop == pytest.approx(0.1)
    assert parallel.peak_temperature >= serial.peak_temperature
    assert serial.metrics["max_parallelism"] == 1
    assert parallel.metrics["max_parallelism"] == 2
