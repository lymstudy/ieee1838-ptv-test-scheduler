"""Tests for the workload-scale sweep experiment."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.sweep_workload_scale import DIE_COUNTS, TASK_DENSITIES, run


SCHEDULERS = {"serial_ieee1838_style", "bandwidth_greedy", "ptv_aware"}
PLOT_KEYS = {
    "tat_vs_workload_scale",
    "peak_ir_drop_vs_workload_scale",
    "peak_temperature_vs_workload_scale",
    "voltage_violations_vs_workload_scale",
    "temperature_violations_vs_workload_scale",
    "task_count_vs_workload_scale",
}


@pytest.fixture(scope="module")
def sweep_outputs() -> dict[str, Path]:
    """Run the workload-scale sweep once for this module."""

    return run()


@pytest.fixture(scope="module")
def sweep_rows(sweep_outputs: dict[str, Path]) -> list[dict[str, str]]:
    """Read the workload-scale sweep summary CSV."""

    with sweep_outputs["workload_scale_summary"].open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def rows_by_case(sweep_rows: list[dict[str, str]]) -> dict[tuple[int, str], dict[str, dict[str, str]]]:
    """Group summary rows by workload case and scheduler."""

    grouped: dict[tuple[int, str], dict[str, dict[str, str]]] = {}
    for row in sweep_rows:
        key = (int(row["die_count"]), row["task_density"])
        grouped.setdefault(key, {})[row["scheduler_name"]] = row
    return grouped


def test_workload_scale_sweep_generates_summary_csv(sweep_outputs: dict[str, Path]) -> None:
    """The workload-scale sweep should write a non-empty summary CSV."""

    summary_path = sweep_outputs["workload_scale_summary"]
    assert summary_path.exists()
    assert summary_path.stat().st_size > 0


def test_workload_scale_summary_contains_all_cases_and_schedulers(sweep_rows: list[dict[str, str]]) -> None:
    """Each die-count/density combination should include all scheduler rows."""

    grouped = rows_by_case(sweep_rows)
    expected_cases = {(die_count, density) for die_count in DIE_COUNTS for density in TASK_DENSITIES}
    assert set(grouped) == expected_cases
    for case_key in expected_cases:
        assert set(grouped[case_key]) == SCHEDULERS


def test_workload_scale_tat_values_are_positive(sweep_rows: list[dict[str, str]]) -> None:
    """All workload-scale rows should report positive TAT."""

    assert all(float(row["tat"]) > 0.0 for row in sweep_rows)


def test_workload_scale_task_counts_increase(sweep_rows: list[dict[str, str]]) -> None:
    """Task counts should increase with density and die count."""

    grouped = rows_by_case(sweep_rows)
    for die_count in DIE_COUNTS:
        counts = [int(grouped[(die_count, density)]["serial_ieee1838_style"]["num_tasks"]) for density in TASK_DENSITIES]
        assert counts == sorted(counts)
        assert len(set(counts)) == len(counts)
    for density in TASK_DENSITIES:
        counts = [int(grouped[(die_count, density)]["serial_ieee1838_style"]["num_tasks"]) for die_count in DIE_COUNTS]
        assert counts == sorted(counts)
        assert len(set(counts)) == len(counts)


def test_ptv_violations_are_no_worse_than_greedy(sweep_rows: list[dict[str, str]]) -> None:
    """PTV-aware should not exceed greedy violations unless marked over-constrained."""

    grouped = rows_by_case(sweep_rows)
    for case_key, scheduler_rows in grouped.items():
        greedy = scheduler_rows["bandwidth_greedy"]
        ptv = scheduler_rows["ptv_aware"]
        assert int(ptv["voltage_violation_count"]) <= int(greedy["voltage_violation_count"])
        if ptv["over_constrained"] != "True":
            assert int(ptv["temperature_violation_count"]) <= int(greedy["temperature_violation_count"])


def test_ptv_tat_is_below_serial_for_generated_cases(sweep_rows: list[dict[str, str]]) -> None:
    """PTV-aware TAT should remain below serial TAT on generated mechanism workloads."""

    grouped = rows_by_case(sweep_rows)
    for scheduler_rows in grouped.values():
        assert float(scheduler_rows["ptv_aware"]["tat"]) <= float(scheduler_rows["serial_ieee1838_style"]["tat"])


def test_workload_scale_plots_are_generated(sweep_outputs: dict[str, Path]) -> None:
    """The sweep should generate all requested SVG plots."""

    for key in PLOT_KEYS:
        path = sweep_outputs[key]
        assert path.exists()
        assert path.stat().st_size > 0
