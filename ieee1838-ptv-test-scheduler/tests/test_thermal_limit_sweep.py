"""Tests for the thermal-limit sweep experiment."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.sweep_thermal_limits import THERMAL_LIMITS, run


SCHEDULERS = {"serial_ieee1838_style", "bandwidth_greedy", "ptv_aware"}
PLOT_KEYS = {
    "tat_vs_thermal_limit",
    "peak_temperature_vs_thermal_limit",
    "temperature_violations_vs_thermal_limit",
    "dummy_cycles_vs_thermal_limit",
}


@pytest.fixture(scope="module")
def sweep_outputs() -> dict[str, Path]:
    """Run the thermal-limit sweep once for this module."""

    return run()


@pytest.fixture(scope="module")
def sweep_rows(sweep_outputs: dict[str, Path]) -> list[dict[str, str]]:
    """Read the thermal-limit sweep summary CSV."""

    with sweep_outputs["thermal_limit_sweep_summary"].open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def rows_by_limit(sweep_rows: list[dict[str, str]]) -> dict[float, dict[str, dict[str, str]]]:
    """Group summary rows by thermal limit and scheduler."""

    grouped: dict[float, dict[str, dict[str, str]]] = {}
    for row in sweep_rows:
        grouped.setdefault(float(row["thermal_limit"]), {})[row["scheduler_name"]] = row
    return grouped


def test_thermal_limit_sweep_generates_summary_csv(sweep_outputs: dict[str, Path]) -> None:
    """The thermal-limit sweep should write a non-empty summary CSV."""

    summary_path = sweep_outputs["thermal_limit_sweep_summary"]
    assert summary_path.exists()
    assert summary_path.stat().st_size > 0


def test_thermal_limit_sweep_contains_all_limits_and_schedulers(sweep_rows: list[dict[str, str]]) -> None:
    """Each thermal limit should include all three scheduler rows."""

    grouped = rows_by_limit(sweep_rows)
    assert set(grouped) == set(THERMAL_LIMITS)
    for thermal_limit in THERMAL_LIMITS:
        assert set(grouped[thermal_limit]) == SCHEDULERS


def test_thermal_limit_sweep_tat_values_are_positive(sweep_rows: list[dict[str, str]]) -> None:
    """All sweep rows should report positive TAT."""

    assert all(float(row["tat"]) > 0.0 for row in sweep_rows)


def test_ptv_temperature_violations_are_no_worse_than_greedy_unless_over_constrained(
    sweep_rows: list[dict[str, str]],
) -> None:
    """PTV-aware should not exceed greedy thermal violations except marked tight-limit cases."""

    grouped = rows_by_limit(sweep_rows)
    for thermal_limit in THERMAL_LIMITS:
        greedy = grouped[thermal_limit]["bandwidth_greedy"]
        ptv = grouped[thermal_limit]["ptv_aware"]
        over_constrained = ptv["over_constrained"] == "True"
        if not over_constrained:
            assert int(ptv["temperature_violation_count"]) <= int(greedy["temperature_violation_count"])


def test_thermal_limit_sweep_plots_are_generated(sweep_outputs: dict[str, Path]) -> None:
    """The sweep should generate all requested SVG plots."""

    for key in PLOT_KEYS:
        path = sweep_outputs[key]
        assert path.exists()
        assert path.stat().st_size > 0
