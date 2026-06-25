from __future__ import annotations

from experiments.generate_m19_pressure_figures import case_label, occupancy_intervals, target_intervals
from src.schedulers import ScheduledPhase


def test_m19_occupancy_intervals_counts_fpp_and_bist() -> None:
    phases = [
        _phase("target_a", "LOCAL_BIST_RUN", 0.0, 2.0, recipe_type="B"),
        _phase("target_b", "FPP_SHIFT_IN", 1.0, 3.0, recipe_type="F", fpp_lanes_required=4),
        _phase("target_c", "FPP_SHIFT_OUT", 2.0, 4.0, recipe_type="F", fpp_lanes_required=2),
    ]

    fpp = occupancy_intervals(phases, "fpp_lanes")
    bist = occupancy_intervals(phases, "bist_engine")

    assert fpp == [(0.0, 1000000.0, 0.0), (1000000.0, 2000000.0, 4.0), (2000000.0, 3000000.0, 6.0), (3000000.0, 4000000.0, 2.0)]
    assert bist == [(0.0, 1000000.0, 1.0), (1000000.0, 2000000.0, 1.0), (2000000.0, 3000000.0, 0.0), (3000000.0, 4000000.0, 0.0)]


def test_m19_target_intervals_span_all_phases() -> None:
    phases = [
        _phase("target_a", "CONFIG_BIST", 0.0, 1.0),
        _phase("target_a", "LOCAL_BIST_RUN", 4.0, 5.0),
        _phase("target_b", "FPP_SHIFT_IN", 2.0, 3.0),
    ]

    intervals = target_intervals(phases)

    assert intervals["target_a"] == (0.0, 5.0)
    assert intervals["target_b"] == (2.0, 3.0)


def test_m19_case_label_uses_paper_friendly_names() -> None:
    assert case_label("m18_shared_bist_12die_5_5d_multi_tower") == "12-die\n5.5D multi-tower"
    assert case_label("m18_shared_bist_8die_3d_stack") == "8-die\n3D stack"


def _phase(
    target_id: str,
    phase_name: str,
    start_s: float,
    end_s: float,
    recipe_type: str = "S",
    fpp_lanes_required: int = 0,
) -> ScheduledPhase:
    return ScheduledPhase(
        case_id="case",
        target_id=target_id,
        target_kind="memory",
        die_id="die0",
        recipe_id="recipe",
        recipe_type=recipe_type,
        phase_index=0,
        phase_name=phase_name,
        start_s=start_s,
        end_s=end_s,
        duration_s=end_s - start_s,
        serial_required=False,
        fpp_lanes_required=fpp_lanes_required,
        fpp_channel="fpp",
        dwr_segments="",
        route_resource="",
        exclusive_resource="",
        power_w=0.0,
        thermal_region="thermal_die0",
        resource_notes="",
    )
