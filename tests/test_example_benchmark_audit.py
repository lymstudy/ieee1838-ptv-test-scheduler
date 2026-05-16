"""Tests for the example benchmark schedule audit."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.audit_example_benchmark_schedule import run as run_audit
from experiments.run_example_benchmark_workload import run as run_example


REQUIRED_OUTPUTS = {
    "greedy_schedule_audit",
    "ptv_schedule_audit",
    "schedule_comparison_audit",
}


@pytest.fixture(scope="module")
def audit_outputs() -> dict[str, Path]:
    """Run the example benchmark workload and its audit once."""

    run_example()
    return run_audit()


def read_rows(path: Path) -> list[dict[str, str]]:
    """Read a CSV file into dictionaries."""

    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def interval_rows(path: Path) -> list[dict[str, str]]:
    """Return interval-level rows from one audit CSV."""

    return [row for row in read_rows(path) if row["record_type"] == "interval"]


def test_audit_script_generates_outputs(audit_outputs: dict[str, Path]) -> None:
    """The audit script should produce the requested files."""

    assert REQUIRED_OUTPUTS.issubset(audit_outputs)
    for key in REQUIRED_OUTPUTS:
        path = audit_outputs[key]
        assert path.exists()
        assert path.stat().st_size > 0


def test_greedy_and_ptv_have_no_fpp_lane_capacity_violation(audit_outputs: dict[str, Path]) -> None:
    """Audit interval rows should not report FPP capacity violations."""

    for key in ("greedy_schedule_audit", "ptv_schedule_audit"):
        rows = interval_rows(audit_outputs[key])
        assert rows
        assert all(row["fpp_capacity_violation"] == "False" for row in rows)
        assert all(int(row["fpp_lane_usage"]) <= int(row["fpp_lane_capacity"]) for row in rows)


def test_greedy_and_ptv_have_no_dwr_segment_overlap(audit_outputs: dict[str, Path]) -> None:
    """Audit interval rows should not report DWR segment overlap."""

    for key in ("greedy_schedule_audit", "ptv_schedule_audit"):
        rows = interval_rows(audit_outputs[key])
        assert rows
        assert all(row["dwr_overlap_violation"] == "False" for row in rows)


def test_ptv_voltage_violations_are_no_worse_than_greedy() -> None:
    """PTV-aware should not exceed greedy voltage violations for the example workload."""

    metrics_path = ROOT / "results" / "benchmarks" / "example" / "scheduler_metrics_summary.csv"
    with metrics_path.open(newline="", encoding="utf-8") as handle:
        metrics = {row["scheduler_name"]: row for row in csv.DictReader(handle)}

    assert int(metrics["ptv_aware"]["voltage_violation_count"]) <= int(
        metrics["bandwidth_greedy"]["voltage_violation_count"]
    )


def test_audit_markdown_records_no_scheduler_bug(audit_outputs: dict[str, Path]) -> None:
    """The audit summary should record the interpretation of the TAT difference."""

    text = audit_outputs["schedule_comparison_audit"].read_text(encoding="utf-8")

    assert "No scheduler bug was found" in text
    assert "heuristic ordering difference" in text
    assert "should not be generalized" in text
