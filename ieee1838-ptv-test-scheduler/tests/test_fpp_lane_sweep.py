"""Tests for the FPP lane sweep experiment."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.sweep_fpp_lanes import FPP_LANES, run


SCHEDULERS = {"serial_ieee1838_style", "bandwidth_greedy", "ptv_aware"}
PLOT_KEYS = {
    "tat_vs_fpp_lanes",
    "peak_ir_drop_vs_fpp_lanes",
    "peak_temperature_vs_fpp_lanes",
    "voltage_violations_vs_fpp_lanes",
    "temperature_violations_vs_fpp_lanes",
}


@pytest.fixture(scope="module")
def sweep_outputs() -> dict[str, Path]:
    """Run the FPP lane sweep once for this module."""

    return run()


@pytest.fixture(scope="module")
def sweep_rows(sweep_outputs: dict[str, Path]) -> list[dict[str, str]]:
    """Read the FPP lane sweep summary CSV."""

    with sweep_outputs["fpp_lane_sweep_summary"].open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def rows_by_lane(sweep_rows: list[dict[str, str]]) -> dict[int, dict[str, dict[str, str]]]:
    """Group summary rows by FPP lane count and scheduler."""

    grouped: dict[int, dict[str, dict[str, str]]] = {}
    for row in sweep_rows:
        grouped.setdefault(int(row["fpp_lanes"]), {})[row["scheduler_name"]] = row
    return grouped


def test_fpp_lane_sweep_generates_summary_csv(sweep_outputs: dict[str, Path]) -> None:
    """The FPP lane sweep should write a non-empty summary CSV."""

    summary_path = sweep_outputs["fpp_lane_sweep_summary"]
    assert summary_path.exists()
    assert summary_path.stat().st_size > 0


def test_fpp_lane_sweep_contains_all_lanes_and_schedulers(sweep_rows: list[dict[str, str]]) -> None:
    """Each lane value should include all three scheduler rows."""

    grouped = rows_by_lane(sweep_rows)
    assert set(grouped) == set(FPP_LANES)
    for lane in FPP_LANES:
        assert set(grouped[lane]) == SCHEDULERS


def test_fpp_lane_sweep_tat_values_are_positive(sweep_rows: list[dict[str, str]]) -> None:
    """All sweep rows should report positive TAT."""

    assert all(float(row["tat"]) > 0.0 for row in sweep_rows)


def test_ptv_violations_are_no_worse_than_greedy(sweep_rows: list[dict[str, str]]) -> None:
    """PTV-aware should not exceed greedy violation counts for each FPP lane count."""

    grouped = rows_by_lane(sweep_rows)
    for lane in FPP_LANES:
        greedy = grouped[lane]["bandwidth_greedy"]
        ptv = grouped[lane]["ptv_aware"]
        assert int(ptv["voltage_violation_count"]) <= int(greedy["voltage_violation_count"])
        assert int(ptv["temperature_violation_count"]) <= int(greedy["temperature_violation_count"])


def test_fpp_lane_sweep_plots_are_generated(sweep_outputs: dict[str, Path]) -> None:
    """The sweep should generate all requested SVG plots."""

    for key in PLOT_KEYS:
        path = sweep_outputs[key]
        assert path.exists()
        assert path.stat().st_size > 0
