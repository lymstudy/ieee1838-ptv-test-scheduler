from __future__ import annotations

from experiments.run_m10_benchmark_sweep import resource_variant
from experiments.run_m11_algorithm_study import run_case
from src.model import load_system_model


def test_m11_run_case_emits_algorithm_rows() -> None:
    base = load_system_model("configs/cases/m10/m10_small_d695_2_5d_interposer.json")
    model = resource_variant(base, lane_count=4, power_profile="nominal")

    rows = run_case(model, lane_count=4, power_profile="nominal", time_limit_s=1.0, alns_iterations=1, max_alns_targets=0)
    ok_methods = {row["method_id"] for row in rows if row["status"] == "ok"}
    skipped_methods = {row["method_id"] for row in rows if row["status"] == "skipped"}

    assert {"pure_serial", "fixed_fastest", "tam_like", "low_power", "m4_all_recipes", "m4_greedy"}.issubset(ok_methods)
    assert "m5_cpsat" in ok_methods
    assert skipped_methods == {"m6_alns"}
    assert all(float(row["makespan_s"]) > 0.0 for row in rows if row["status"] == "ok")
