from __future__ import annotations

from experiments.generate_m14_experiment_chapter import summarize_m10, summarize_m12b


def test_m14_summarize_m10_counts_nominal_lane8_rows() -> None:
    rows = [
        {
            "case_id": "case_a",
            "source_soc": "d695",
            "scale": "small",
            "topology_type": "3d_stack",
            "status": "ok",
            "method_id": "m4_greedy",
            "power_profile": "nominal",
            "lane_count": "8",
            "normalized_makespan": "0.5",
            "speedup_vs_serial": "2.0",
        },
        {
            "case_id": "case_a",
            "source_soc": "d695",
            "scale": "small",
            "topology_type": "3d_stack",
            "status": "ok",
            "method_id": "pure_serial",
            "power_profile": "nominal",
            "lane_count": "8",
            "normalized_makespan": "1.0",
            "speedup_vs_serial": "1.0",
        },
    ]

    summary = summarize_m10(rows)

    assert summary["case_count"] == 1
    assert summary["nominal_lane8_rows"] == 1
    assert summary["nominal_lane8_avg_speedup"] == 2.0


def test_m14_summarize_m12b_ranking_match() -> None:
    rows = [
        {
            "case_id": "case_a",
            "schedule_id": "m4_greedy",
            "status": "ok",
            "proxy_peak_temperature_c": "25.0",
            "hotspot_peak_temperature_c": "60.0",
        },
        {
            "case_id": "case_a",
            "schedule_id": "thermal_min_risk",
            "status": "ok",
            "proxy_peak_temperature_c": "26.0",
            "hotspot_peak_temperature_c": "62.0",
        },
    ]

    summary = summarize_m12b(rows)

    assert summary["ok_rows"] == 2
    assert summary["ranking_match_count"] == 1
    assert summary["ranking_matches"][0]["proxy_best"] == "m4_greedy"
