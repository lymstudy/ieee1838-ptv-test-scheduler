"""Tests for the bandwidth-greedy baseline scheduler."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.run_case_4die import run
from src.model.access import AccessConfig, DwrSegment, FppConfig
from src.model.stack import Die, DieStack
from src.model.task import TaskType, TestTask as ModelTask, build_tasks
from src.model.thermal import RCThermalModel, ThermalConfig
from src.model.voltage import EquivalentPdnModel, VoltageConfig
from src.scheduler.greedy import BandwidthGreedyScheduler
from src.scheduler.serial import SerialScheduler


def load_config(name: str) -> dict:
    """Load a config file from the repository configs directory."""

    with (ROOT / "configs" / name).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def build_schedulers():
    """Build serial and greedy schedulers for the 4-die case."""

    defaults = load_config("default_params.yaml")
    case = load_config("case_4die.yaml")
    stack = DieStack.from_config(case["stack"])
    access = AccessConfig.from_config(case["access"])
    tasks = build_tasks(case["tasks"])
    thermal_config = ThermalConfig.from_config(defaults["thermal"])
    voltage_config = VoltageConfig.from_config(defaults["voltage"])
    kwargs = {
        "stack": stack,
        "access": access,
        "clock_hz": float(defaults["simulation"]["clock_hz"]),
        "time_step_s": float(defaults["simulation"]["time_step_s"]),
    }
    serial = SerialScheduler(
        thermal_model=RCThermalModel(thermal_config),
        voltage_model=EquivalentPdnModel(voltage_config),
        **kwargs,
    )
    greedy = BandwidthGreedyScheduler(
        thermal_model=RCThermalModel(thermal_config),
        voltage_model=EquivalentPdnModel(voltage_config),
        **kwargs,
    )
    return serial, greedy, tasks, access


def overlaps(first, second) -> bool:
    """Return true if two schedule entries overlap in time."""

    return first.start_time < second.end_time and second.start_time < first.end_time


def test_greedy_scheduler_schedules_every_task_once() -> None:
    """Every configured task should appear exactly once in the greedy schedule."""

    _, greedy, tasks, _ = build_schedulers()
    result = greedy.schedule(tasks)

    assert sorted(entry.task_id for entry in result.entries) == sorted(task.id for task in tasks)
    assert len({entry.task_id for entry in result.entries}) == len(tasks)


def test_greedy_scheduler_respects_fpp_lane_capacity() -> None:
    """Overlapping greedy tasks must not exceed FPP lane capacity."""

    _, greedy, tasks, access = build_schedulers()
    result = greedy.schedule(tasks)
    event_times = sorted({time for entry in result.entries for time in (entry.start_time, entry.end_time)})

    for start_time, end_time in zip(event_times, event_times[1:]):
        if end_time <= start_time:
            continue
        active = [entry for entry in result.entries if entry.start_time <= start_time and entry.end_time > start_time]
        assert sum(entry.fpp_lanes_used for entry in active) <= access.fpp.lanes

    assert any(overlaps(a, b) for index, a in enumerate(result.entries) for b in result.entries[index + 1 :])


def test_greedy_scheduler_prevents_same_dwr_segment_overlap() -> None:
    """Tasks using the same Die Wrapper Register segment must not overlap."""

    stack = DieStack(
        (
            Die(
                id=0,
                name="die0",
                layer_index=0,
                area_mm2=10.0,
                initial_temp_c=25.0,
                nominal_power_w=0.1,
            ),
        )
    )
    access = AccessConfig(
        ptap_width_bits=1,
        stap_count=1,
        dwr_segments=(DwrSegment(die_id=0, name="dwr_die0", length_bits=32),),
        fpp=FppConfig(enabled=True, lanes=2, lane_width_bits=1),
    )
    scheduler = BandwidthGreedyScheduler(
        stack=stack,
        access=access,
        thermal_model=RCThermalModel(
            ThermalConfig(
                ambient_temp_c=25.0,
                thermal_resistance_c_per_w=2.0,
                thermal_capacitance_j_per_c=0.5,
                max_temp_c=85.0,
            )
        ),
        voltage_model=EquivalentPdnModel(
            VoltageConfig(nominal_voltage_v=0.8, pdn_resistance_ohm=0.04, max_ir_drop_v=0.08)
        ),
        clock_hz=100.0,
        time_step_s=0.01,
    )
    tasks = (
        ModelTask("dwr_a", 0, TaskType.DWR_EXTEST, 10, 1, 0.2),
        ModelTask("dwr_b", 0, TaskType.DWR_EXTEST, 10, 1, 0.2),
    )

    result = scheduler.schedule(tasks)

    assert not overlaps(result.entries[0], result.entries[1])
    assert {entry.dwr_segment for entry in result.entries} == {"dwr_die0"}


def test_greedy_tat_is_no_greater_than_serial_tat() -> None:
    """Bandwidth-greedy TAT should be no greater than serial TAT for the same tasks."""

    serial, greedy, tasks, _ = build_schedulers()

    assert greedy.schedule(tasks).tat <= serial.schedule(tasks).tat + 1e-12


def test_run_case_4die_generates_greedy_schedule_csv() -> None:
    """The experiment runner should generate the greedy schedule CSV."""

    outputs = run()
    schedule_path = outputs["greedy_schedule"]

    assert schedule_path.exists()
    assert schedule_path.stat().st_size > 0


