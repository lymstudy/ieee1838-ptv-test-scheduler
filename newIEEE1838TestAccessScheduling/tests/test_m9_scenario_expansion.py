from __future__ import annotations

from pathlib import Path

from experiments.generate_m9_cases import build_2_5d_case, build_5_5d_case, write_json
from experiments.run_m9_scenario_suite import run_case
from src.model import load_system_model, parse_soc_file
from src.recipes import RecipeGenerator, pareto_prune, rows_from_recipes


ITC02_DIR = Path("docs/data/itc02_benchmarks")


def test_itc02_parser_reads_scan_chains_and_patterns() -> None:
    soc = parse_soc_file(ITC02_DIR / "d695.soc")
    module5 = next(module for module in soc.modules if module.module_id == 5)

    assert soc.soc_name == "d695"
    assert soc.total_modules == 11
    assert len(soc.modules) == 11
    assert module5.chain_count == 32
    assert module5.max_chain_length_bits == 45
    assert module5.total_chain_length_bits == 1426
    assert module5.pattern_count == 110


def test_m9_generated_cases_are_valid_recipe_inputs(tmp_path) -> None:
    d695 = parse_soc_file(ITC02_DIR / "d695.soc")
    p22810 = parse_soc_file(ITC02_DIR / "p22810.soc")
    cases = [
        build_2_5d_case(d695.leaf_modules[:10]),
        build_5_5d_case(p22810.leaf_modules[:8]),
    ]

    for index, payload in enumerate(cases):
        output = tmp_path / f"case{index}.json"
        write_json(payload, output)

        model = load_system_model(output)
        rows = rows_from_recipes(RecipeGenerator(model).generate_all())
        pruned = pareto_prune(rows).kept_rows

        assert model.raw["package"]["topology_type"] in {"2_5d_interposer", "5_5d_multi_tower"}
        assert len(rows) > len(model.test_objects)
        assert len(pruned) <= len(rows)
        assert {row["target_id"] for row in pruned}


def test_m9_scenario_suite_emits_cross_scenario_rows(tmp_path) -> None:
    d695 = parse_soc_file(ITC02_DIR / "d695.soc")
    case_path = tmp_path / "m9_2_5d.json"
    write_json(build_2_5d_case(d695.leaf_modules[:6]), case_path)

    rows = run_case(case_path, time_limit_s=1.0, include_cpsat=False)

    assert {row["method_id"] for row in rows} == {"pure_serial", "m4_greedy"}
    assert {row["topology_type"] for row in rows} == {"2_5d_interposer"}
    assert all(int(row["recipe_count"]) >= int(row["pareto_recipe_count"]) for row in rows)
    assert all(float(row["makespan_s"]) > 0.0 for row in rows)
