from __future__ import annotations

from experiments.run_m17_innovation_support import (
    _lowest_thermal_risk_rows,
    merge_m18_pressure_support,
    path_joint_gain_summary,
    thermal_validation_summary,
)


def test_m17_path_joint_gain_marks_supported_when_joint_beats_fixed() -> None:
    rows = [
        _ablation_row("case_a", "fixed_fastest", 10.0),
        _ablation_row("case_a", "joint_m4_greedy", 8.5),
        _ablation_row("case_b", "fixed_fastest", 20.0),
        _ablation_row("case_b", "m5_cpsat", 18.0),
    ]

    summary = path_joint_gain_summary(rows)

    assert summary["status"] == "supported"
    assert "cases=2" in summary["evidence"]
    assert "cases_gain_gt_1pct=2" in summary["evidence"]


def test_m17_path_joint_gain_marks_weak_when_joint_does_not_help() -> None:
    rows = [
        _ablation_row("case_a", "fixed_fastest", 10.0),
        _ablation_row("case_a", "joint_m4_greedy", 10.2),
        _ablation_row("case_b", "fixed_fastest", 20.0),
        _ablation_row("case_b", "m5_cpsat", 20.1),
    ]

    summary = path_joint_gain_summary(rows)

    assert summary["status"] == "weak"
    assert "avg_joint_gain_vs_best_fixed" in summary["evidence"]


def test_m17_thermal_validation_marks_partial_when_hotspot_ranking_matches_proxy() -> None:
    rows = []
    for case_id in ["case_a", "case_b", "case_c"]:
        rows.append(_hotspot_row(case_id, "m4_greedy", 70.0, 72.0))
        rows.append(_hotspot_row(case_id, "thermal_min_risk", 65.0, 66.0))

    summary = thermal_validation_summary(rows)

    assert summary["status"] == "partial"
    assert summary["evidence"] == "hotspot_ok_rows=6, cases=3, ranking_matches=3/3"


def test_m17_merges_m18_pressure_support_into_path_claim() -> None:
    path_gain = {"status": "weak", "evidence": "cases=12", "wording": "old", "gap": "old"}
    m18_rows = [
        _m18_row("case_a", "m4_greedy", "joint", 45.0),
        _m18_row("case_a", "fixed_fastest", "fixed_path", 0.0),
        _m18_row("case_b", "m5_cpsat", "joint", 46.0),
        _m18_row("case_b", "fixed_fastest", "fixed_path", 0.0),
    ]

    summary = merge_m18_pressure_support(path_gain, m18_rows)

    assert summary["status"] == "supported"
    assert "M18 pressure cases=2" in summary["evidence"]
    assert "best_joint_gain=46.00%" in summary["evidence"]


def test_m17_lowest_thermal_risk_rows_selects_one_recipe_per_target() -> None:
    rows = [
        {"target_id": "core_a", "recipe_id": "hot", "thermal_risk": 2.0, "peak_power_w": 5.0, "total_time_s": 1.0},
        {"target_id": "core_a", "recipe_id": "cool", "thermal_risk": 1.0, "peak_power_w": 7.0, "total_time_s": 3.0},
        {"target_id": "core_b", "recipe_id": "slow", "thermal_risk": 1.0, "peak_power_w": 4.0, "total_time_s": 9.0},
        {"target_id": "core_b", "recipe_id": "fast", "thermal_risk": 1.0, "peak_power_w": 4.0, "total_time_s": 2.0},
    ]

    selected = _lowest_thermal_risk_rows(rows)

    assert {row["recipe_id"] for row in selected} == {"cool", "fast"}


def _ablation_row(case_id: str, method_id: str, makespan_s: float) -> dict[str, object]:
    return {"case_id": case_id, "method_id": method_id, "makespan_s": makespan_s}


def _hotspot_row(case_id: str, schedule_id: str, proxy_peak: float, hotspot_peak: float) -> dict[str, str]:
    return {
        "case_id": case_id,
        "schedule_id": schedule_id,
        "status": "ok",
        "proxy_peak_temperature_c": str(proxy_peak),
        "hotspot_peak_temperature_c": str(hotspot_peak),
    }


def _m18_row(case_id: str, method_id: str, family: str, gain: float) -> dict[str, str]:
    return {
        "case_id": case_id,
        "method_id": method_id,
        "method_family": family,
        "status": "ok",
        "gain_vs_fixed_fastest_percent": str(gain),
    }
