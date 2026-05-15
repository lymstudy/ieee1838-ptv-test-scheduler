"""Tests for benchmark-derived workload schema adapter."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.run_example_benchmark_workload import run
from src.model.task import TaskType, build_tasks
from src.workload.benchmark_adapter import (
    benchmark_stats_from_dict,
    generate_case_from_benchmark,
    generate_tasks_from_benchmark,
    load_benchmark_stats,
)


EXAMPLE_STATS = ROOT / "benchmarks" / "example_benchmark_stats.yaml"
SCHEDULERS = {"serial_ieee1838_style", "bandwidth_greedy", "ptv_aware"}


@pytest.fixture(scope="module")
def stats():
    """Load the example benchmark statistics once."""

    return load_benchmark_stats(EXAMPLE_STATS)


@pytest.fixture(scope="module")
def generated_tasks(stats):
    """Build scheduler task objects from the example benchmark stats."""

    return build_tasks(generate_tasks_from_benchmark(stats))


@pytest.fixture(scope="module")
def benchmark_outputs() -> dict[str, Path]:
    """Run the example benchmark workload experiment once."""

    return run()


def test_example_benchmark_stats_can_be_loaded(stats) -> None:
    """The example benchmark statistics YAML should load into a dataclass."""

    assert stats.benchmark_name == "example_schema_validation_4die"
    assert stats.die_count == 4
    assert len(stats.dies) == 4
    assert stats.interconnects


def test_adapter_generates_non_empty_task_set(generated_tasks) -> None:
    """The adapter should generate scheduler-compatible tasks."""

    assert len(generated_tasks) > 0


def test_generated_workload_contains_required_task_types(generated_tasks) -> None:
    """Generated tasks should include the MVP task categories and capture phase."""

    task_types = {task.task_type for task in generated_tasks}
    capture_tasks = [task for task in generated_tasks if task.is_capture_phase]

    assert TaskType.SCAN in task_types
    assert TaskType.BIST in task_types
    assert TaskType.INSTRUMENT_ACCESS in task_types
    assert TaskType.DWR_EXTEST in task_types
    assert capture_tasks
    assert all(task.is_capture_phase for task in capture_tasks)


def test_scan_duration_depends_on_scan_chain_length() -> None:
    """Increasing scan_chain_length should increase the generated scan shift duration."""

    with EXAMPLE_STATS.open("r", encoding="utf-8") as handle:
        baseline_data = yaml.safe_load(handle)
    modified_data = yaml.safe_load(yaml.safe_dump(baseline_data))
    modified_data["dies"][0]["scan_chain_length"] = baseline_data["dies"][0]["scan_chain_length"] + 500

    baseline_stats = benchmark_stats_from_dict(baseline_data)
    modified_stats = benchmark_stats_from_dict(modified_data)
    baseline_tasks = {task["id"]: task for task in generate_tasks_from_benchmark(baseline_stats)}
    modified_tasks = {task["id"]: task for task in generate_tasks_from_benchmark(modified_stats)}

    assert modified_tasks["scan_shift_die0"]["duration_cycles"] > baseline_tasks["scan_shift_die0"]["duration_cycles"]


def test_dwr_extest_tasks_are_generated_from_interconnects(stats) -> None:
    """Each interconnect entry should generate one DWR EXTEST task."""

    tasks = generate_tasks_from_benchmark(stats)
    extest_tasks = [task for task in tasks if task["task_type"] == "dwr_extest"]

    assert len(extest_tasks) == len(stats.interconnects)
    assert {task["id"] for task in extest_tasks} == {
        f"dwr_extest_die{item.src_die}_die{item.dst_die}" for item in stats.interconnects
    }


def test_generated_case_builds_existing_models(stats) -> None:
    """The adapter output should have the same shape as scheduler config dictionaries."""

    case = generate_case_from_benchmark(stats)
    tasks = build_tasks(case["tasks"])

    assert len(tasks) == len(generate_tasks_from_benchmark(stats))
    assert case["access"]["fpp_lanes"] == stats.fpp_lanes
    assert case["voltage"]["max_ir_drop_v"] == stats.voltage_limit
    assert case["thermal"]["max_temp_c"] == stats.thermal_limit


def test_example_benchmark_experiment_generates_outputs(benchmark_outputs: dict[str, Path]) -> None:
    """The example benchmark workload experiment should generate required files."""

    required = {
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
    assert required.issubset(benchmark_outputs)
    for key in required:
        path = benchmark_outputs[key]
        assert path.exists()
        assert path.stat().st_size > 0


def test_example_scheduler_summary_contains_three_schedulers(benchmark_outputs: dict[str, Path]) -> None:
    """The example summary CSV should contain serial, greedy, and PTV-aware rows."""

    with benchmark_outputs["scheduler_metrics_summary"].open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert {row["scheduler_name"] for row in rows} == SCHEDULERS
    assert all(float(row["tat"]) > 0.0 for row in rows)
