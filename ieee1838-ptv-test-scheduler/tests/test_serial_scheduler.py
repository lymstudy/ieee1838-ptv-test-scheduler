"""Tests for the serial IEEE 1838-style baseline scheduler."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.run_case_4die import run
from src.model.access import AccessConfig
from src.model.stack import DieStack
from src.model.task import build_tasks
from src.model.thermal import RCThermalModel, ThermalConfig
from src.model.voltage import EquivalentPdnModel, VoltageConfig
from src.scheduler.serial import SerialScheduler


def load_config(name: str) -> dict:
    """Load a config file from the repository configs directory."""

    with (ROOT / "configs" / name).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def build_serial_result():
    """Build the serial schedule result for the 4-die case."""

    defaults = load_config("default_params.yaml")
    case = load_config("case_4die.yaml")
    stack = DieStack.from_config(case["stack"])
    access = AccessConfig.from_config(case["access"])
    tasks = build_tasks(case["tasks"])
    scheduler = SerialScheduler(
        stack=stack,
        access=access,
        thermal_model=RCThermalModel(ThermalConfig.from_config(defaults["thermal"])),
        voltage_model=EquivalentPdnModel(VoltageConfig.from_config(defaults["voltage"])),
        clock_hz=float(defaults["simulation"]["clock_hz"]),
        time_step_s=float(defaults["simulation"]["time_step_s"]),
    )
    return scheduler.schedule(tasks), tasks


def test_serial_scheduler_schedules_every_task_once() -> None:
    """Every configured task should appear exactly once in the serial schedule."""

    result, tasks = build_serial_result()

    assert sorted(entry.task_id for entry in result.entries) == sorted(task.id for task in tasks)
    assert len({entry.task_id for entry in result.entries}) == len(tasks)


def test_serial_scheduler_has_no_overlaps() -> None:
    """Serial schedule entries must not overlap."""

    result, _ = build_serial_result()
    entries = sorted(result.entries, key=lambda entry: entry.start_time)

    for previous, current in zip(entries, entries[1:]):
        assert previous.end_time <= current.start_time


def test_serial_scheduler_tat_equals_last_end_time() -> None:
    """TAT should equal the end time of the last scheduled task."""

    result, _ = build_serial_result()

    assert result.tat == pytest.approx(result.entries[-1].end_time)


def test_run_case_4die_generates_serial_schedule_csv() -> None:
    """The experiment runner should generate the serial schedule CSV."""

    outputs = run()
    schedule_path = outputs["serial_schedule"]

    assert schedule_path.exists()
    assert schedule_path.stat().st_size > 0
