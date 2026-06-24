from __future__ import annotations

from pathlib import Path

from experiments.generate_m10_benchmark_suite import BenchmarkSpec, build_m10_case, generate_suite, select_modules
from experiments.run_m10_benchmark_sweep import resource_variant, run_variant
from src.model import load_system_model, parse_soc_file
from src.recipes import RecipeGenerator, rows_from_recipes


ITC02_DIR = Path("docs/data/itc02_benchmarks")


def test_m10_select_modules_prefers_nonzero_workload() -> None:
    soc = parse_soc_file(ITC02_DIR / "p22810.soc")
    modules = select_modules(soc, 5)

    assert len(modules) == 5
    assert all(module.pattern_count > 0 for module in modules)
    assert modules[0].total_chain_length_bits * modules[0].pattern_count >= modules[-1].total_chain_length_bits


def test_m10_case_builder_generates_valid_topologies(tmp_path) -> None:
    soc = parse_soc_file(ITC02_DIR / "d695.soc")
    modules = select_modules(soc, 6)
    spec = BenchmarkSpec("d695", "small", 6, 4)

    for topology in ("3d_stack", "2_5d_interposer", "5_5d_multi_tower"):
        payload = build_m10_case(soc, spec, modules, topology, max_fpp_lanes=8)
        output = tmp_path / f"{topology}.json"
        output.write_text(__import__("json").dumps(payload), encoding="utf-8")
        model = load_system_model(output)
        rows = rows_from_recipes(RecipeGenerator(model).generate_all())

        assert model.raw["benchmark_source"]["soc_name"] == "d695"
        assert model.raw["package"]["topology_type"] == topology
        assert len(rows) > len(model.test_objects)


def test_m10_suite_and_sweep_smoke(tmp_path) -> None:
    rows = generate_suite(
        itc02_dir=ITC02_DIR,
        case_dir=tmp_path / "cases",
        manifest_output=tmp_path / "manifest.csv",
        max_fpp_lanes=8,
        specs=(BenchmarkSpec("d695", "small", 4, 4),),
        topologies=("2_5d_interposer",),
    )
    model = load_system_model(rows[0]["case_path"])
    variant = resource_variant(model, lane_count=2, power_profile="nominal")
    sweep_rows = run_variant(variant, lane_count=2, power_profile="nominal")

    assert len(rows) == 1
    assert (tmp_path / "manifest.csv").exists()
    assert {row["method_id"] for row in sweep_rows if row["status"] == "ok"} == {"pure_serial", "m4_greedy"}
