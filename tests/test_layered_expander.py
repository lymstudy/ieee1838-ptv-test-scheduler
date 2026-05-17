"""Tests for B2 layered TestIntent expansion."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.demo_layered_task_expansion import run as run_layered_demo
from src.access_path import AccessPathGenerator, StackAccessConfig
from src.layered import (
    BISTIntent,
    DWRExTestIntent,
    InstrumentAccessIntent,
    InternalScanIntent,
    LayeredTask,
    LayeredTaskExpander,
)


@pytest.fixture()
def expander() -> LayeredTaskExpander:
    """Create a deterministic layered expander."""

    config = StackAccessConfig(
        die_count=4,
        first_die_id=0,
        tck_frequency_hz=50_000_000.0,
        ptap_instruction_bits=8,
        stap_select_bits_per_die=4,
        three_dcr_bits_per_die=8,
        dwr_config_bits_per_die=16,
        bypass_bits_per_die=1,
        fpp_config_bits=16,
        fpp_lane_count=2,
        fpp_bandwidth_bits_per_s=1_000_000_000.0,
        default_readback_bits=32,
    )
    return LayeredTaskExpander(config, AccessPathGenerator(config))


def phase_types(task: LayeredTask) -> list[str]:
    """Return phase types for one layered task."""

    return [phase.phase_type for phase in task.phases]


def test_bist_expands_to_local_run_and_readback(expander: LayeredTaskExpander) -> None:
    """BIST should include a PTAP-free local execution phase and result readback."""

    task = expander.expand(
        BISTIntent(
            intent_id="bist_die2",
            target_die=2,
            bist_id="bist0",
            local_run_time=0.001,
            trigger_bits=16,
            result_bits=64,
            trigger_power=0.2,
            local_power=0.8,
            readback_power=0.2,
        )
    )

    phases = {phase.phase_type: phase for phase in task.phases}
    assert "LOCAL_BIST_RUN" in phases
    assert phases["LOCAL_BIST_RUN"].uses_ptap is False
    assert phases["LOCAL_BIST_RUN"].is_local_execution is True
    assert "READ_BIST_RESULT" in phases


def test_internal_scan_expands_to_fpp_capture_sequence(
    expander: LayeredTaskExpander,
) -> None:
    """Internal scan should expand into FPP shift and capture phases."""

    task = expander.expand(
        InternalScanIntent(
            intent_id="scan_die3",
            target_die=3,
            scan_chain_length=1024,
            pattern_count=2,
            requires_fpp=True,
            fpp_lanes=2,
            shift_power=0.5,
            capture_power=0.9,
            readback_bits=32,
        )
    )

    types = phase_types(task)
    assert "FPP_SHIFT_IN" in types
    assert "SCAN_CAPTURE" in types
    assert "FPP_SHIFT_OUT" in types
    capture = next(phase for phase in task.phases if phase.phase_type == "SCAN_CAPTURE")
    assert capture.is_capture_phase is True


def test_dwr_extest_expands_to_dwr_capture_sequence(
    expander: LayeredTaskExpander,
) -> None:
    """DWR EXTEST should include DWR config, capture, and shift-out."""

    task = expander.expand(
        DWRExTestIntent(
            intent_id="dwr_die1_die2",
            src_die=1,
            dst_die=2,
            dwr_bits=512,
            pattern_count=1,
            shift_power=0.5,
            capture_power=0.9,
            readback_bits=512,
        )
    )

    phases = {phase.phase_type: phase for phase in task.phases}
    assert "CONFIG_DWR_MODE" in phases
    assert "DWR_CAPTURE" in phases
    assert "DWR_SHIFT_OUT" in phases
    assert phases["DWR_CAPTURE"].is_capture_phase is True


def test_instrument_access_contains_access_phase(expander: LayeredTaskExpander) -> None:
    """Instrument access should include ACCESS_INSTRUMENT."""

    task = expander.expand(
        InstrumentAccessIntent(
            intent_id="instrument_die0",
            target_die=0,
            instrument_id="status",
            access_type="read",
            network_depth=2,
            register_bits=32,
            access_power=0.1,
            readback_bits=32,
        )
    )

    assert "ACCESS_INSTRUMENT" in phase_types(task)


def test_all_layered_tasks_have_positive_total_time(
    expander: LayeredTaskExpander,
) -> None:
    """Every representative layered task should have positive total time."""

    intents = [
        BISTIntent(
            intent_id="bist_die2",
            target_die=2,
            bist_id="bist0",
            local_run_time=0.001,
            trigger_bits=16,
            result_bits=64,
        ),
        InternalScanIntent(
            intent_id="scan_die3",
            target_die=3,
            scan_chain_length=1024,
            pattern_count=2,
            requires_fpp=True,
            fpp_lanes=2,
        ),
        DWRExTestIntent(
            intent_id="dwr_die1_die2",
            src_die=1,
            dst_die=2,
            dwr_bits=512,
        ),
        InstrumentAccessIntent(
            intent_id="instrument_die0",
            target_die=0,
            instrument_id="status",
            access_type="read",
            network_depth=2,
            register_bits=32,
        ),
    ]

    tasks = [expander.expand(intent) for intent in intents]
    assert all(task.total_estimated_time > 0.0 for task in tasks)


def test_demo_layered_task_expansion_writes_phase_summary(tmp_path: Path) -> None:
    """The layered expansion demo should generate phase summary CSV output."""

    outputs = run_layered_demo(tmp_path)
    phase_summary = outputs["execution_phase_summary"]
    task_summary = outputs["layered_task_summary"]
    markdown_summary = outputs["layered_task_summary_md"]

    assert phase_summary.exists()
    assert task_summary.exists()
    assert markdown_summary.exists()
    with phase_summary.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert {row["phase_type"] for row in rows} >= {
        "LOCAL_BIST_RUN",
        "FPP_SHIFT_IN",
        "SCAN_CAPTURE",
        "DWR_CAPTURE",
        "ACCESS_INSTRUMENT",
    }
