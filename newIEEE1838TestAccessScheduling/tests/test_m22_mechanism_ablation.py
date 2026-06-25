from __future__ import annotations

from pathlib import Path

from experiments.run_m22_mechanism_ablation import (
    build_ablation_payloads,
    remove_parallel_escape_paths,
    summarize_ablation_rows,
)
from src.model import load_system_model


def test_m22_builds_four_ablation_payloads_without_writing_cases() -> None:
    source = load_system_model(Path("configs/cases/m10/m10_small_d695_3d_stack.json"))

    payloads = build_ablation_payloads(source)
    ablation_ids = [payload["experimental_controls"]["m22_ablation_id"] for payload in payloads]

    assert ablation_ids == [
        "m10_original_control",
        "bist_private_control",
        "shared_bist_no_parallel_escape",
        "shared_bist_with_parallel_escape",
    ]
    assert all(payload["benchmark_source"]["source_case_id"] == source.case_id for payload in payloads)


def test_m22_no_parallel_escape_removes_fpp_and_hybrid_from_test_objects() -> None:
    source = load_system_model(Path("configs/cases/m10/m10_small_d695_3d_stack.json"))
    payload = remove_parallel_escape_paths(build_ablation_payloads(source)[-1])

    for obj in payload["test_objects"]:
        if obj.get("object_type") == "instrument":
            continue
        assert "F" not in obj["supported_recipes"]
        assert "H" not in obj["supported_recipes"]


def test_m22_summary_exposes_mechanism_gain_only_in_full_pressure_case() -> None:
    rows = []
    for ablation_id, gain, f_count in [
        ("m10_original_control", 0.0, 0),
        ("bist_private_control", 0.0, 0),
        ("shared_bist_no_parallel_escape", 0.0, 0),
        ("shared_bist_with_parallel_escape", 25.0, 4),
    ]:
        rows.extend(
            [
                _row(ablation_id, "fixed_fastest", "fixed_path", 0.0, 8, 0),
                _row(ablation_id, "m4_greedy", "joint", gain, 4, f_count),
            ]
        )

    summary = summarize_ablation_rows(rows)
    by_id = {row["ablation_id"]: row for row in summary}

    assert by_id["m10_original_control"]["avg_best_joint_gain_percent"] == 0.0
    assert by_id["shared_bist_no_parallel_escape"]["avg_best_joint_gain_percent"] == 0.0
    assert by_id["shared_bist_with_parallel_escape"]["avg_best_joint_gain_percent"] == 25.0
    assert by_id["shared_bist_with_parallel_escape"]["avg_joint_f_count"] == 4.0


def _row(
    ablation_id: str,
    method_id: str,
    family: str,
    gain: float,
    b_count: int,
    f_count: int,
) -> dict[str, object]:
    return {
        "ablation_id": ablation_id,
        "ablation_label": ablation_id,
        "case_id": f"{ablation_id}_case_a",
        "source_case_id": "m10_case_a",
        "source_soc": "d695",
        "scale": "small",
        "topology_type": "3d_stack",
        "die_count": 4,
        "tower_count": 1,
        "target_count": 8,
        "recipe_count": 32,
        "pareto_recipe_count": 20,
        "shared_bist_group_count": 1,
        "method_id": method_id,
        "method_family": family,
        "status": "ok",
        "error": "",
        "makespan_s": 10.0 if method_id == "fixed_fastest" else 10.0 - gain / 10.0,
        "normalized_makespan": 1.0,
        "speedup_vs_serial": 1.0,
        "gain_vs_fixed_fastest_percent": gain,
        "peak_power_w": 1.0,
        "peak_temperature_c": 30.0 + gain / 10.0,
        "temperature_rise_c": 5.0,
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
