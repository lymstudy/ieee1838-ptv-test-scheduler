"""Tests for deterministic synthetic workload generation."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.model.access import AccessConfig
from src.model.stack import DieStack
from src.model.task import TaskType, build_tasks
from src.workload.synthetic import DENSITY_ORDER, expected_task_count, generate_synthetic_case


@pytest.mark.parametrize("die_count", [4, 8, 12])
def test_synthetic_generator_builds_supported_die_counts(die_count: int) -> None:
    """Generated cases should build stack, access, and task models for supported die counts."""

    case = generate_synthetic_case(die_count, "small")
    stack = DieStack.from_config(case["stack"])
    access = AccessConfig.from_config(case["access"])
    tasks = build_tasks(case["tasks"])

    assert len(stack.dies) == die_count
    assert access.fpp.enabled is True
    assert len(tasks) == expected_task_count(die_count, "small")


def test_synthetic_task_count_increases_with_density() -> None:
    """Task count should increase from small to medium to large for a fixed die count."""

    counts = [len(generate_synthetic_case(8, density)["tasks"]) for density in DENSITY_ORDER]

    assert counts == sorted(counts)
    assert len(set(counts)) == len(counts)


def test_synthetic_task_count_increases_with_die_count() -> None:
    """Task count should increase as die count increases for a fixed density."""

    counts = [len(generate_synthetic_case(die_count, "medium")["tasks"]) for die_count in (4, 8, 12)]

    assert counts == sorted(counts)
    assert len(set(counts)) == len(counts)


def test_synthetic_workload_contains_required_task_types_and_capture_flags() -> None:
    """Synthetic workload should include all MVP task classes and capture flags."""

    tasks = build_tasks(generate_synthetic_case(4, "large")["tasks"])
    task_types = {task.task_type for task in tasks}
    capture_tasks = [task for task in tasks if task.is_capture_phase]

    assert TaskType.SCAN in task_types
    assert TaskType.BIST in task_types
    assert TaskType.DWR_EXTEST in task_types
    assert TaskType.INSTRUMENT_ACCESS in task_types
    assert capture_tasks
    assert all(task.is_capture_phase for task in capture_tasks)
    assert all(task.dependencies for task in capture_tasks)


def test_synthetic_generator_is_deterministic() -> None:
    """The same generator inputs should produce identical config dictionaries."""

    assert generate_synthetic_case(8, "medium") == generate_synthetic_case(8, "medium")
