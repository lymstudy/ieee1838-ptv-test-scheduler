"""Tests for the voltage-limit sweep experiment."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.sweep_voltage_limits import VOLTAGE_LIMITS, run


SCHEDULERS = {"serial_ieee1838_style", "bandwidth_greedy", "ptv_aware"}
PLOT_KEYS = {
    "tat_vs_voltage_limit",
    "peak_ir_drop_vs_voltage_limit",
    "voltage_violations_vs_voltage_limit",
}


@pytest.fixture(scope="module")
def sweep_outputs() -> dict[str, Path]:
    """Run the voltage-limit sweep once for this module."""

    return run()


@pytest.fixture(scope="module")
def sweep_rows(sweep_outputs: dict[str, Path]) -> list[dict[str, str]]:
    """Read the voltage-limit sweep summary CSV."""

    with sweep_outputs["voltage_limit_sweep_summary"].open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def rows_by_limit(sweep_rows: list[dict[str, str]]) -> dict[float, dict[str, dict[str, str]]]:
    """Group summary rows by voltage limit and scheduler."""

    grouped: dict[float, dict[str, dict[str, str]]] = {}
    for row in sweep_rows:
        grouped.setdefault(float(row["voltage_limit"]), {})[row["scheduler_name"]] = row
    return grouped


def test_voltage_limit_sweep_generates_summary_csv(sweep_outputs: dict[str, Path]) -> None:
    """The voltage-limit sweep should write a non-empty summary CSV."""

    summary_path = sweep_outputs["voltage_limit_sweep_summary"]
    assert summary_path.exists()
    assert summary_path.stat().st_size > 0


def test_voltage_limit_sweep_contains_all_limits_and_schedulers(sweep_rows: list[dict[str, str]]) -> None:
    """Each voltage limit should include all three scheduler rows."""

    grouped = rows_by_limit(sweep_rows)
    assert set(grouped) == set(VOLTAGE_LIMITS)
    for voltage_limit in VOLTAGE_LIMITS:
        assert set(grouped[voltage_limit]) == SCHEDULERS


def test_voltage_limit_sweep_tat_values_are_positive(sweep_rows: list[dict[str, str]]) -> None:
    """All sweep rows should report positive TAT."""

    assert all(float(row["tat"]) > 0.0 for row in sweep_rows)


def test_ptv_voltage_violations_are_no_worse_than_greedy(sweep_rows: list[dict[str, str]]) -> None:
    """PTV-aware should not exceed greedy voltage violations for each voltage limit."""

    grouped = rows_by_limit(sweep_rows)
    for voltage_limit in VOLTAGE_LIMITS:
        greedy = grouped[voltage_limit]["bandwidth_greedy"]
        ptv = grouped[voltage_limit]["ptv_aware"]
        assert int(ptv["voltage_violation_count"]) <= int(greedy["voltage_violation_count"])


def test_voltage_limit_sweep_plots_are_generated(sweep_outputs: dict[str, Path]) -> None:
    """The sweep should generate all requested SVG plots."""

    for key in PLOT_KEYS:
        path = sweep_outputs[key]
        assert path.exists()
        assert path.stat().st_size > 0
