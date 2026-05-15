"""Tests for scaffold config loading and model behavior."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.model.access import AccessConfig
from src.model.stack import DieStack
from src.model.task import TaskType, build_tasks
from src.model.thermal import RCThermalModel, TemperatureState, ThermalConfig
from src.model.voltage import EquivalentPdnModel, VoltageConfig


def load_config(name: str) -> dict:
    """Load a config file from the repository configs directory."""

    with (ROOT / "configs" / name).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def test_case_4die_config_builds_models() -> None:
    """The 4-die case should build stack, access, and task models."""

    case = load_config("case_4die.yaml")

    stack = DieStack.from_config(case["stack"])
    access = AccessConfig.from_config(case["access"])
    tasks = build_tasks(case["tasks"])

    assert len(stack.dies) == 4
    assert stack.die_ids() == (0, 1, 2, 3)
    assert access.fpp.enabled is True
    assert access.fpp.total_width_bits == 2
    assert access.dwr_for_die(0).length_bits == 256
    assert len(tasks) == 4
    assert {task.task_type for task in tasks} == {
        TaskType.SCAN,
        TaskType.BIST,
        TaskType.DWR_EXTEST,
        TaskType.INSTRUMENT_ACCESS,
    }


def test_task_duration_uses_configured_clock() -> None:
    """Task duration should be computed from cycles and clock frequency."""

    defaults = load_config("default_params.yaml")
    case = load_config("case_4die.yaml")
    task = build_tasks(case["tasks"])[0]

    assert task.duration_s(defaults["simulation"]["clock_hz"]) == pytest.approx(0.004)


def test_rc_thermal_step_changes_temperature_reasonably() -> None:
    """The RC model should heat under power and cool without power."""

    config = ThermalConfig(
        ambient_temp_c=25.0,
        thermal_resistance_c_per_w=2.0,
        thermal_capacitance_j_per_c=0.5,
        max_temp_c=85.0,
    )
    model = RCThermalModel(config)

    heated = model.step(TemperatureState({0: 25.0}), {0: 1.0}, 0.1)
    cooled = model.step(TemperatureState({0: 35.0}), {0: 0.0}, 0.1)

    assert heated.by_die_id[0] > 25.0
    assert cooled.by_die_id[0] < 35.0


def test_voltage_model_estimates_shared_ir_drop_by_default() -> None:
    """The default shared PDN mode should accumulate current across active dies."""

    config = VoltageConfig(
        nominal_voltage_v=0.8,
        pdn_resistance_ohm=0.04,
        max_ir_drop_v=0.08,
    )
    state = EquivalentPdnModel(config).estimate({0: 0.4, 1: 0.8})

    assert state.total_power_w == pytest.approx(1.2)
    assert state.total_current_a == pytest.approx(1.5)
    assert state.ir_drop_by_die_v[0] == pytest.approx(0.06)
    assert state.ir_drop_by_die_v[1] == pytest.approx(0.06)
    assert not EquivalentPdnModel(config).violates_limit(state)


def test_voltage_model_can_estimate_per_die_ir_drop() -> None:
    """The optional per-die mode preserves independent die-current estimation."""

    config = VoltageConfig(
        nominal_voltage_v=0.8,
        pdn_resistance_ohm=0.04,
        max_ir_drop_v=0.08,
        mode="per_die",
    )
    state = EquivalentPdnModel(config).estimate({0: 0.4, 1: 0.8})

    assert state.ir_drop_by_die_v[0] == pytest.approx(0.02)
    assert state.ir_drop_by_die_v[1] == pytest.approx(0.04)

