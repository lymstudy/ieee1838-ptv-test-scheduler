"""Tests for the 4-die stress workload mechanism validation."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.run_case_4die_stress import run


@pytest.fixture(scope="module")
def stress_outputs() -> dict[str, Path]:
    """Run the stress experiment once for this test module."""

    return run()


@pytest.fixture(scope="module")
def stress_config() -> dict:
    """Load the stress workload config."""

    with (ROOT / "configs" / "case_4die_stress.yaml").open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


@pytest.fixture(scope="module")
def stress_summary(stress_outputs: dict[str, Path]) -> dict[str, dict[str, str]]:
    """Read the scheduler metrics summary keyed by scheduler name."""

    with stress_outputs["scheduler_metrics_summary"].open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {row["scheduler_name"]: row for row in rows}


def read_schedule(path: Path) -> list[dict[str, object]]:
    """Read a schedule CSV and normalize numeric fields."""

    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["die_id"] = int(row["die_id"])
        row["start_time"] = float(row["start_time"])
        row["end_time"] = float(row["end_time"])
        row["duration"] = float(row["duration"])
        row["fpp_lanes_used"] = int(row["fpp_lanes_used"])
        row["is_capture_phase"] = row["is_capture_phase"] == "True"
    return rows


def active_entries(entries: list[dict[str, object]], time_s: float) -> list[dict[str, object]]:
    """Return entries active at a given event time."""

    return [entry for entry in entries if entry["start_time"] <= time_s + 1e-15 and entry["end_time"] > time_s + 1e-15]


def event_times(entries: list[dict[str, object]]) -> list[float]:
    """Return sorted event times for a schedule."""

    return sorted({float(entry["start_time"]) for entry in entries} | {float(entry["end_time"]) for entry in entries})


def test_stress_experiment_generates_required_outputs(stress_outputs: dict[str, Path]) -> None:
    """The stress runner should generate all required schedule, metric, and plot files."""

    for key in (
        "serial_schedule",
        "serial_metrics",
        "serial_gantt",
        "serial_temperature_curve",
        "serial_ir_drop_curve",
        "greedy_schedule",
        "greedy_metrics",
        "greedy_gantt",
        "greedy_temperature_curve",
        "greedy_ir_drop_curve",
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
        path = stress_outputs[key]
        assert path.exists()
        assert path.stat().st_size > 0


def test_stress_summary_contains_all_three_schedulers(stress_summary: dict[str, dict[str, str]]) -> None:
    """The stress metrics summary should include serial, greedy, and PTV-aware rows."""

    assert set(stress_summary) == {"serial_ieee1838_style", "bandwidth_greedy", "ptv_aware"}


def test_stress_task_count_is_rich_enough(stress_config: dict) -> None:
    """The stress workload should contain at least sixteen tasks."""

    assert len(stress_config["tasks"]) >= 16


def test_ptv_stress_schedule_respects_fpp_lane_capacity(
    stress_outputs: dict[str, Path],
    stress_config: dict,
) -> None:
    """PTV-aware stress schedule must not exceed FPP lane capacity."""

    entries = read_schedule(stress_outputs["ptv_schedule"])
    capacity = int(stress_config["access"]["fpp_lanes"])
    for start_time, end_time in zip(event_times(entries), event_times(entries)[1:]):
        if end_time <= start_time:
            continue
        assert sum(int(entry["fpp_lanes_used"]) for entry in active_entries(entries, start_time)) <= capacity


def test_ptv_stress_schedule_prevents_same_dwr_overlap(stress_outputs: dict[str, Path]) -> None:
    """PTV-aware stress schedule must not overlap users of the same DWR segment."""

    entries = read_schedule(stress_outputs["ptv_schedule"])
    for start_time, end_time in zip(event_times(entries), event_times(entries)[1:]):
        if end_time <= start_time:
            continue
        used_segments = [entry["dwr_segment"] for entry in active_entries(entries, start_time) if entry["dwr_segment"] != "DWR_NONE"]
        assert len(used_segments) == len(set(used_segments))


def test_ptv_stress_schedule_respects_capture_limit(
    stress_outputs: dict[str, Path],
    stress_config: dict,
) -> None:
    """PTV-aware stress schedule should satisfy max_concurrent_capture."""

    entries = read_schedule(stress_outputs["ptv_schedule"])
    limit = int(stress_config["scheduler"]["max_concurrent_capture"])
    for start_time, end_time in zip(event_times(entries), event_times(entries)[1:]):
        if end_time <= start_time:
            continue
        capture_count = sum(1 for entry in active_entries(entries, start_time) if entry["is_capture_phase"])
        assert capture_count <= limit


def test_ptv_stress_violations_are_no_worse_than_greedy(stress_summary: dict[str, dict[str, str]]) -> None:
    """PTV-aware stress schedule should reduce or preserve violation counts versus greedy."""

    greedy = stress_summary["bandwidth_greedy"]
    ptv = stress_summary["ptv_aware"]
    assert int(ptv["temperature_violation_count"]) <= int(greedy["temperature_violation_count"])
    assert int(ptv["voltage_violation_count"]) <= int(greedy["voltage_violation_count"])
    assert float(ptv["tat"]) >= float(greedy["tat"]) - 1e-12


def test_stress_case_activates_ptv_constraints(stress_summary: dict[str, dict[str, str]]) -> None:
    """The stress case should make at least one PTV constraint binding."""

    greedy = stress_summary["bandwidth_greedy"]
    ptv = stress_summary["ptv_aware"]
    greedy_violations = int(greedy["temperature_violation_count"]) + int(greedy["voltage_violation_count"])
    assert greedy_violations > 0
    assert ptv["constraints_were_binding"] == "True"
    assert ptv["capture_staggering_applied"] == "True"
