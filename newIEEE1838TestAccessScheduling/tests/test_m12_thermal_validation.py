from __future__ import annotations

from experiments.run_m10_benchmark_sweep import resource_variant
from experiments.run_m12_thermal_validation import build_schedules, export_hotspot_inputs, thermal_profile_variant
from src.evaluators import evaluate_schedule_thermal
from src.model import load_system_model


def test_m12_thermal_profile_increases_proxy_peak() -> None:
    base = load_system_model("configs/cases/m10/m10_small_d695_5_5d_multi_tower.json")
    model = resource_variant(base, lane_count=4, power_profile="nominal")
    schedules, _status = build_schedules(model, time_limit_s=1.0, include_cpsat=False)
    nominal = evaluate_schedule_thermal(model, schedules[0][2].phases, "nominal")
    stress = evaluate_schedule_thermal(thermal_profile_variant(model, "stress_proxy"), schedules[0][2].phases, "stress")

    assert stress.peak_temperature_c >= nominal.peak_temperature_c


def test_m12_hotspot_export_writes_floorplan_and_power_trace(tmp_path) -> None:
    base = load_system_model("configs/cases/m10/m10_small_d695_5_5d_multi_tower.json")
    model = resource_variant(base, lane_count=4, power_profile="nominal")
    schedules, _status = build_schedules(model, time_limit_s=1.0, include_cpsat=False)

    rows = export_hotspot_inputs(model, schedules, tmp_path, sample_period_s=0.0001, method_filter={"m4_greedy"})

    assert len(rows) == 1
    assert (tmp_path / f"{model.case_id}.flp").exists()
    assert (tmp_path / f"{model.case_id}__m4_greedy.ptrace").exists()
    assert rows[0].sample_count > 0
