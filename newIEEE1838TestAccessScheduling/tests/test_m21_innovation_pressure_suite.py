from __future__ import annotations

from pathlib import Path

from experiments.generate_m21_innovation_pressure_suite import build_pressure_case
from experiments.run_m21_innovation_pressure_suite import claim_support, selected_type_counts, topology_summary
from src.model import load_system_model


def test_m21_pressure_case_adds_shared_bist_and_keeps_itc02_source() -> None:
    source = load_system_model(Path("configs/cases/m10/m10_small_d695_3d_stack.json"))

    payload = build_pressure_case(source)

    assert payload["case_id"] == "m21_pressure_small_d695_3d_stack"
    assert payload["benchmark_source"]["source_case_id"] == "m10_small_d695_3d_stack"
    assert payload["benchmark_source"]["source"] == "ITC02_SOC_PRESSURE_TRANSFORM"
    assert payload["experimental_controls"]["shared_bist_group_count"] == 1
    assert all(
        "B" in obj["supported_recipes"]
        for obj in payload["test_objects"]
        if obj.get("object_type") != "instrument"
    )


def test_m21_selected_type_counts_parses_recipe_mix() -> None:
    counts = selected_type_counts("B:5;F:4;I:3;S:1")

    assert counts == {"B": 5, "F": 4, "H": 0, "S": 1}


def test_m21_claim_support_marks_path_schedule_supported_with_pressure_gains() -> None:
    rows = [
        _detail("case_a", "3d_stack", "fixed_fastest", "fixed_path", 0.0, 8, 0, 1, 31.0),
        _detail("case_a", "3d_stack", "m4_greedy", "joint", 20.0, 4, 4, 1, 37.0),
        _detail("case_b", "5_5d_multi_tower", "fixed_fastest", "fixed_path", 0.0, 8, 0, 3, 30.0),
        _detail("case_b", "5_5d_multi_tower", "m4_greedy", "joint", 12.0, 6, 2, 3, 36.0),
    ]

    topology_rows = topology_summary(rows)
    claims = claim_support(rows, topology_rows)
    path_claim = next(row for row in claims if row["claim_id"] == "path_schedule_joint_optimization")

    assert path_claim["support_status"] == "supported"
    assert "min_gain=12.00%" in path_claim["evidence"]


def _detail(
    case_id: str,
    topology: str,
    method_id: str,
    family: str,
    gain: float,
    b_count: int,
    f_count: int,
    group_count: int,
    temp: float,
) -> dict[str, object]:
    return {
        "case_id": case_id,
        "source_case_id": case_id.replace("m21", "m10"),
        "source_soc": "d695",
        "scale": "small",
        "topology_type": topology,
        "die_count": 4,
        "tower_count": group_count,
        "target_count": 8,
        "recipe_count": 32,
        "pareto_recipe_count": 20,
        "shared_bist_group_count": group_count,
        "method_id": method_id,
        "method_family": family,
        "status": "ok",
        "error": "",
        "makespan_s": 1.0,
        "normalized_makespan": 1.0,
        "speedup_vs_serial": 1.0,
        "gain_vs_fixed_fastest_percent": gain,
        "peak_power_w": 1.0,
        "peak_temperature_c": temp,
        "temperature_rise_c": temp - 25.0,
        "peak_thermal_region": "thermal_die0",
        "fpp_utilization": 0.5,
        "serial_busy_ratio": 0.1,
        "selected_recipe_types": f"B:{b_count};F:{f_count}",
        "selected_b_count": b_count,
        "selected_f_count": f_count,
        "selected_h_count": 0,
        "selected_s_count": 0,
        "solver_status": "greedy",
    }
