from __future__ import annotations

from src.schedulers import ScheduledPhase
from experiments.generate_m16_paper_value_figures import block_peak_matrix, target_total_intervals


def test_m16_block_peak_matrix_orders_thermal_die_ids() -> None:
    matrix = block_peak_matrix({"thermal_die1": 61.0, "thermal_die0": 60.0, "thermal_die2": 62.0})

    assert matrix.shape == (2, 2)
    assert matrix[0, 0] == 60.0
    assert matrix[0, 1] == 61.0
    assert matrix[1, 0] == 62.0


def test_m16_target_total_intervals_span_all_target_phases() -> None:
    phases = [
        _phase("target_a", 0.0, 1.0),
        _phase("target_a", 2.0, 3.0),
        _phase("target_b", 4.0, 5.0),
    ]

    intervals = target_total_intervals(phases, ["target_a"])

    assert intervals == {"target_a": (0.0, 3.0)}


def _phase(target_id: str, start_s: float, end_s: float) -> ScheduledPhase:
    return ScheduledPhase(
        case_id="case",
        target_id=target_id,
        target_kind="core",
        die_id="die0",
        recipe_id="recipe",
        recipe_type="F",
        phase_index=0,
        phase_name="CAPTURE",
        start_s=start_s,
        end_s=end_s,
        duration_s=end_s - start_s,
        serial_required=False,
        fpp_lanes_required=0,
        fpp_channel="",
        dwr_segments="",
        route_resource="",
        exclusive_resource="",
        power_w=0.0,
        thermal_region="thermal_die0",
        resource_notes="",
    )
