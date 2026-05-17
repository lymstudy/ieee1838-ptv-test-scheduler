"""Tests for B1 AccessPath generation and timing estimates."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.demo_access_path_generation import run as run_access_path_demo
from src.access_path import AccessPathGenerator, StackAccessConfig


@pytest.fixture()
def generator() -> AccessPathGenerator:
    """Create a deterministic 4-die access path generator."""

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
    return AccessPathGenerator(config)


def test_generate_path_to_first_die(generator: AccessPathGenerator) -> None:
    """The first-die path should contain only the first die."""

    path = generator.generate_path_to_die(0)

    assert path.target_die == 0
    assert path.path_dies == (0,)
    assert path.selected_staps == ()
    assert path.estimated_access_time > 0.0
    assert any(
        resource.resource_type == "PTAP_CONTROL_PATH" for resource in path.occupied_resources
    )


def test_generate_path_to_deeper_die_includes_stack_prefix(
    generator: AccessPathGenerator,
) -> None:
    """The die3 path should include all dies from die0 to die3."""

    path = generator.generate_path_to_die(3)

    assert path.path_dies == (0, 1, 2, 3)
    assert path.selected_staps == (1, 2, 3)


def test_deeper_die_access_time_increases(generator: AccessPathGenerator) -> None:
    """Deeper die access should carry at least as much overhead as shallow access."""

    die0 = generator.generate_path_to_die(0)
    die3 = generator.generate_path_to_die(3)

    assert die3.estimated_access_time > die0.estimated_access_time
    assert len(die3.selected_staps) > len(die0.selected_staps)


def test_dwr_access_path_is_longer_than_basic(generator: AccessPathGenerator) -> None:
    """DWR access should add wrapper config, shift, and readback time."""

    basic = generator.generate_path_to_die(3)
    dwr = generator.generate_dwr_access_path(3, dwr_bits=512)

    assert dwr.estimated_access_time > basic.estimated_access_time
    assert dwr.access_bit_length > basic.access_bit_length
    assert "dwr_die3" in dwr.required_dwr_segments


def test_fpp_data_path_contains_fpp_transfer(generator: AccessPathGenerator) -> None:
    """FPP data paths should include FPP_TRANSFER and FPP_LANE resources."""

    path = generator.generate_fpp_data_path(3, data_bits=8192, lanes=2)

    assert any(operation.op_type == "FPP_TRANSFER" for operation in path.operations)
    assert any(resource.resource_type == "FPP_LANE" for resource in path.occupied_resources)
    assert path.required_fpp_lanes == 2
    assert "not a universal control path" in path.notes


def test_invalid_target_die_raises(generator: AccessPathGenerator) -> None:
    """Out-of-range die IDs should be rejected."""

    with pytest.raises(ValueError):
        generator.generate_path_to_die(4)


def test_demo_access_path_generation_writes_summary_csv() -> None:
    """The access-path demo should write the requested CSV and Markdown files."""

    outputs = run_access_path_demo()
    csv_path = outputs["access_path_summary_csv"]
    markdown_path = outputs["access_path_summary_md"]

    assert csv_path.exists()
    assert markdown_path.exists()
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert {row["path_id"] for row in rows} >= {
        "basic_die0",
        "basic_die3",
        "dwr_die3_512b",
        "fpp_die3_8192b_2lanes",
    }
