"""Tests for the PTV-aware scheduler."""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.run_case_4die import run
from src.model.access import AccessConfig, FppConfig
from src.model.stack import Die, DieStack
from src.model.task import TaskType, build_tasks
from src.model.thermal import RCThermalModel, ThermalConfig
from src.model.voltage import EquivalentPdnModel, VoltageConfig
from src.scheduler.greedy import BandwidthGreedyScheduler
from src.scheduler.ptv_aware import PTVAwareScheduler


@dataclass(frozen=True)
class SyntheticTask:
    """Small task double used to exercise PTV mechanisms in tests."""

    id: str
    die_id: int
    task_type: TaskType
    duration_cycles: int
    access_width_bits: int
    power_w: float
    is_capture_phase: bool = False
    fpp_lanes_required: int | None = None

    def duration_s(self, clock_hz: float) -> float:
        """Return duration in seconds."""

        return self.duration_cycles / clock_hz


def load_config(name: str) -> dict:
    """Load a config file from the repository configs directory."""

    with (ROOT / "configs" / name).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def build_case_schedulers():
    """Build greedy and PTV-aware schedulers for the 4-die case."""

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
    greedy = BandwidthGreedyScheduler(
        thermal_model=RCThermalModel(thermal_config),
        voltage_model=EquivalentPdnModel(voltage_config),
        **kwargs,
    )
    ptv = PTVAwareScheduler(
        thermal_model=RCThermalModel(thermal_config),
        voltage_model=EquivalentPdnModel(voltage_config),
        **kwargs,
    )
    return greedy, ptv, tasks, access


def one_die_access(lanes: int = 2) -> AccessConfig:
    """Return access resources without DWR segments for synthetic stress tests."""

    return AccessConfig(
        ptap_width_bits=1,
        stap_count=1,
        dwr_segments=(),
        fpp=FppConfig(enabled=True, lanes=lanes, lane_width_bits=1),
    )


def one_die_stack() -> DieStack:
    """Return a one-die synthetic stack."""

    return DieStack(
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


def build_ptv_for_stress(
    thermal_config: ThermalConfig,
    voltage_config: VoltageConfig,
    max_concurrent_capture: int = 1,
) -> PTVAwareScheduler:
    """Build a PTV scheduler for synthetic mechanism tests."""

    return PTVAwareScheduler(
        stack=one_die_stack(),
        access=one_die_access(lanes=2),
        thermal_model=RCThermalModel(thermal_config),
        voltage_model=EquivalentPdnModel(voltage_config),
        clock_hz=10.0,
        time_step_s=0.1,
        max_concurrent_capture=max_concurrent_capture,
        dummy_cycle_duration_s=0.1,
    )


def overlaps(first, second) -> bool:
    """Return true if two schedule entries overlap in time."""

    return first.start_time < second.end_time and second.start_time < first.end_time


def test_ptv_scheduler_schedules_every_task_once() -> None:
    """Every configured task should appear exactly once in the PTV schedule."""

    _, ptv, tasks, _ = build_case_schedulers()
    result = ptv.schedule(tasks)

    assert sorted(entry.task_id for entry in result.entries) == sorted(task.id for task in tasks)
    assert len({entry.task_id for entry in result.entries}) == len(tasks)


def test_ptv_scheduler_respects_fpp_lane_capacity() -> None:
    """Overlapping PTV tasks must not exceed FPP lane capacity."""

    _, ptv, tasks, access = build_case_schedulers()
    result = ptv.schedule(tasks)
    event_times = sorted({time for entry in result.entries for time in (entry.start_time, entry.end_time)})

    for start_time, end_time in zip(event_times, event_times[1:]):
        if end_time <= start_time:
            continue
        active = [entry for entry in result.entries if entry.start_time <= start_time and entry.end_time > start_time]
        assert sum(entry.fpp_lanes_used for entry in active) <= access.fpp.lanes


def test_ptv_scheduler_prevents_same_dwr_segment_overlap() -> None:
    """Tasks using the same Die Wrapper Register segment must not overlap."""

    _, ptv, tasks, _ = build_case_schedulers()
    result = ptv.schedule(tasks)

    for index, first in enumerate(result.entries):
        for second in result.entries[index + 1 :]:
            assert not (overlaps(first, second) and first.dwr_segment == second.dwr_segment)


def test_ptv_metrics_are_no_worse_than_greedy_for_violations() -> None:
    """PTV-aware should not have more violations than bandwidth-greedy on the MVP case."""

    greedy, ptv, tasks, _ = build_case_schedulers()
    greedy_result = greedy.schedule(tasks)
    ptv_result = ptv.schedule(tasks)

    assert ptv_result.tat >= greedy_result.tat - 1e-12
    assert ptv_result.metrics["temperature_violation_count"] <= greedy_result.metrics["temperature_violation_count"]
    assert ptv_result.metrics["voltage_violation_count"] <= greedy_result.metrics["voltage_violation_count"]


def test_ptv_voltage_constraint_blocks_parallel_ir_drop_stress() -> None:
    """Voltage prediction should prevent a parallel start that would exceed IR-drop limit."""

    scheduler = build_ptv_for_stress(
        ThermalConfig(ambient_temp_c=25.0, thermal_resistance_c_per_w=1.0, thermal_capacitance_j_per_c=1.0, max_temp_c=100.0),
        VoltageConfig(nominal_voltage_v=1.0, pdn_resistance_ohm=0.1, max_ir_drop_v=0.075),
    )
    tasks = (
        SyntheticTask("scan_a", 0, TaskType.SCAN, 1, 1, 0.5),
        SyntheticTask("scan_b", 0, TaskType.SCAN, 1, 1, 0.5),
    )

    result = scheduler.schedule(tasks)

    assert not overlaps(result.entries[0], result.entries[1])
    assert result.metrics["voltage_violation_count"] == 0
    assert result.metrics["constraints_were_binding"] is True


def test_ptv_thermal_constraint_and_dummy_cycle_run() -> None:
    """Thermal prediction should delay a hot task and exercise dummy cycle insertion."""

    scheduler = build_ptv_for_stress(
        ThermalConfig(ambient_temp_c=25.0, thermal_resistance_c_per_w=1.0, thermal_capacitance_j_per_c=1.0, max_temp_c=25.75),
        VoltageConfig(nominal_voltage_v=1.0, pdn_resistance_ohm=0.01, max_ir_drop_v=1.0),
    )
    tasks = (
        SyntheticTask("hot_a", 0, TaskType.SCAN, 1, 1, 5.0),
        SyntheticTask("hot_b", 0, TaskType.SCAN, 1, 1, 5.0),
    )

    result = scheduler.schedule(tasks)

    assert not overlaps(result.entries[0], result.entries[1])
    assert result.metrics["dummy_cycle_count"] > 0
    assert result.metrics["constraints_were_binding"] is True


def test_ptv_capture_staggering_limits_capture_overlap() -> None:
    """Capture staggering should limit concurrent capture-phase tasks."""

    scheduler = build_ptv_for_stress(
        ThermalConfig(ambient_temp_c=25.0, thermal_resistance_c_per_w=1.0, thermal_capacitance_j_per_c=1.0, max_temp_c=100.0),
        VoltageConfig(nominal_voltage_v=1.0, pdn_resistance_ohm=0.01, max_ir_drop_v=1.0),
        max_concurrent_capture=1,
    )
    tasks = (
        SyntheticTask("cap_a", 0, TaskType.BIST, 1, 1, 0.1, is_capture_phase=True, fpp_lanes_required=0),
        SyntheticTask("cap_b", 0, TaskType.BIST, 1, 1, 0.1, is_capture_phase=True, fpp_lanes_required=0),
    )

    result = scheduler.schedule(tasks)

    assert not overlaps(result.entries[0], result.entries[1])
    assert result.metrics["capture_staggering_applied"] is True
    assert result.metrics["constraints_were_binding"] is True


def test_run_case_4die_generates_ptv_outputs_and_comparison_plots() -> None:
    """The experiment runner should generate PTV outputs and comparison plots."""

    outputs = run()

    for key in (
        "ptv_schedule",
        "ptv_metrics",
        "ptv_gantt",
        "ptv_temperature_curve",
        "ptv_ir_drop_curve",
        "scheduler_metrics_summary",
        "tat_comparison",
        "peak_temperature_comparison",
        "peak_ir_drop_comparison",
    ):
        path = outputs[key]
        assert path.exists()
        assert path.stat().st_size > 0

    with outputs["scheduler_metrics_summary"].open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert {row["scheduler_name"] for row in rows} == {
        "serial_ieee1838_style",
        "bandwidth_greedy",
        "ptv_aware",
    }
