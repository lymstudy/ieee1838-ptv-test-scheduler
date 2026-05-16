"""Tests for the manually specified realistic UART statistics workload."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.audit_realistic_uart_schedule import run as run_audit
from experiments.run_realistic_uart_workload import run as run_uart
from src.model.task import TaskType, build_tasks
from src.workload.benchmark_adapter import generate_tasks_from_benchmark, load_benchmark_stats


STATS_PATH = ROOT / "benchmarks" / "realistic_uart_stats.yaml"
SCHEDULERS = {"serial_ieee1838_style", "bandwidth_greedy", "ptv_aware"}
REQUIRED_WORKLOAD_OUTPUTS = {
    "benchmark_task_summary",
    "serial_schedule",
    "greedy_schedule",
    "ptv_schedule",
    "scheduler_metrics_summary",
    "serial_gantt",
    "greedy_gantt",
    "ptv_gantt",
    "tat_comparison",
    "peak_ir_drop_comparison",
    "peak_temperature_comparison",
}
REQUIRED_AUDIT_OUTPUTS = {
    "greedy_schedule_audit",
    "ptv_schedule_audit",
    "schedule_comparison_audit",
}


@pytest.fixture(scope="module")
def stats():
    """Load realistic UART statistics once."""

    return load_benchmark_stats(STATS_PATH)


@pytest.fixture(scope="module")
def generated_tasks(stats):
    """Build scheduler task objects from realistic UART stats."""

    return build_tasks(generate_tasks_from_benchmark(stats))


@pytest.fixture(scope="module")
def workload_outputs() -> dict[str, Path]:
    """Run the realistic UART workload experiment once."""

    return run_uart()


@pytest.fixture(scope="module")
def audit_outputs(workload_outputs: dict[str, Path]) -> dict[str, Path]:
    """Run the realistic UART schedule audit once."""

    return run_audit()


def test_realistic_uart_stats_can_be_loaded(stats) -> None:
    """The realistic UART statistics YAML should load successfully."""

    assert stats.benchmark_name == "realistic_uart_controller"
    assert stats.die_count == 4
    assert stats.fpp_lanes == 2
    assert len(stats.dies) == 4
    assert len(stats.interconnects) == 3


def test_realistic_uart_adapter_generates_non_empty_task_set(generated_tasks) -> None:
    """The adapter should generate tasks from realistic UART stats."""

    assert len(generated_tasks) > 0


def test_realistic_uart_workload_contains_required_task_types(generated_tasks) -> None:
    """Generated UART workload should include all scheduler task categories."""

    task_types = {task.task_type for task in generated_tasks}
    capture_tasks = [task for task in generated_tasks if task.is_capture_phase]

    assert TaskType.SCAN in task_types
    assert TaskType.BIST in task_types
    assert TaskType.INSTRUMENT_ACCESS in task_types
    assert TaskType.DWR_EXTEST in task_types
    assert capture_tasks
    assert all(task.is_capture_phase for task in capture_tasks)


def test_run_realistic_uart_workload_generates_outputs(workload_outputs: dict[str, Path]) -> None:
    """The realistic UART experiment should generate required outputs."""

    assert REQUIRED_WORKLOAD_OUTPUTS.issubset(workload_outputs)
    for key in REQUIRED_WORKLOAD_OUTPUTS:
        path = workload_outputs[key]
        assert path.exists()
        assert path.stat().st_size > 0


def test_realistic_uart_summary_contains_three_schedulers(workload_outputs: dict[str, Path]) -> None:
    """The realistic UART summary should include all three schedulers."""

    with workload_outputs["scheduler_metrics_summary"].open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert {row["scheduler_name"] for row in rows} == SCHEDULERS
    assert all(float(row["tat"]) > 0.0 for row in rows)


def test_realistic_uart_ptv_voltage_violations_no_worse_than_greedy(workload_outputs: dict[str, Path]) -> None:
    """PTV-aware should not exceed greedy voltage violations for this workload."""

    with workload_outputs["scheduler_metrics_summary"].open(newline="", encoding="utf-8") as handle:
        metrics = {row["scheduler_name"]: row for row in csv.DictReader(handle)}

    assert int(metrics["ptv_aware"]["voltage_violation_count"]) <= int(
        metrics["bandwidth_greedy"]["voltage_violation_count"]
    )


def test_audit_realistic_uart_schedule_generates_outputs(audit_outputs: dict[str, Path]) -> None:
    """The realistic UART audit should generate required outputs."""

    assert REQUIRED_AUDIT_OUTPUTS.issubset(audit_outputs)
    for key in REQUIRED_AUDIT_OUTPUTS:
        path = audit_outputs[key]
        assert path.exists()
        assert path.stat().st_size > 0


def test_realistic_uart_audit_reports_no_resource_conflicts(audit_outputs: dict[str, Path]) -> None:
    """Audit interval rows should report no FPP or DWR conflicts."""

    for key in ("greedy_schedule_audit", "ptv_schedule_audit"):
        with audit_outputs[key].open(newline="", encoding="utf-8") as handle:
            rows = [row for row in csv.DictReader(handle) if row["record_type"] == "interval"]
        assert rows
        assert all(row["fpp_capacity_violation"] == "False" for row in rows)
        assert all(row["dwr_overlap_violation"] == "False" for row in rows)
