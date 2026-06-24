from __future__ import annotations

import json

import pytest

from src.model import load_system_model
from src.recipes import RecipeGenerator, pareto_prune, rows_from_recipes
from src.schedulers import greedy_schedule, write_schedule_csv, write_schedule_report_markdown


CASE_PATH = "configs/cases/3d_stack_m1_example.json"


def _m3_rows():
    model = load_system_model(CASE_PATH)
    rows = rows_from_recipes(RecipeGenerator(model).generate_all())
    return model, pareto_prune(rows).kept_rows


def test_greedy_schedule_selects_one_recipe_per_target() -> None:
    model, rows = _m3_rows()
    result = greedy_schedule(model, rows)

    target_ids = {str(row["target_id"]) for row in rows}
    assert {str(row["target_id"]) for row in result.selected_rows} == target_ids
    assert len(result.selected_rows) == len(target_ids)
    assert result.makespan_s > 0
    assert result.peak_power_w <= float(model.resource_limits["max_total_power_w"])
    assert result.max_fpp_lanes_used <= int(model.resource_limits["total_fpp_lanes"])


def test_greedy_schedule_preserves_phase_order() -> None:
    model, rows = _m3_rows()
    result = greedy_schedule(model, rows)

    by_recipe: dict[str, list] = {}
    for phase in result.phases:
        by_recipe.setdefault(phase.recipe_id, []).append(phase)

    for phases in by_recipe.values():
        ordered = sorted(phases, key=lambda phase: phase.phase_index)
        for left, right in zip(ordered, ordered[1:]):
            assert left.end_s <= right.start_s + 1e-12


def test_greedy_schedule_respects_serial_fpp_and_power_limits() -> None:
    model, rows = _m3_rows()
    result = greedy_schedule(model, rows)
    boundaries = sorted({time for phase in result.phases for time in (phase.start_s, phase.end_s)})

    for left, right in zip(boundaries, boundaries[1:]):
        if right - left <= 1e-12:
            continue
        active = [phase for phase in result.phases if phase.start_s < right - 1e-12 and left < phase.end_s - 1e-12]
        assert sum(int(phase.serial_required) for phase in active) <= int(model.resource_limits["ptap_ports"])
        assert sum(phase.fpp_lanes_required for phase in active) <= int(model.resource_limits["total_fpp_lanes"])
        assert sum(phase.power_w for phase in active) <= float(model.resource_limits["max_total_power_w"]) + 1e-12


def test_bist_local_execution_can_overlap() -> None:
    model = load_system_model(CASE_PATH)
    rows = [
        _bist_row("mem_die2_sram", "die2", "B_mem_overlap", 1.0),
        _bist_row("core_die3_accel", "die3", "B_core_overlap", 1.1),
    ]
    result = greedy_schedule(model, rows)
    local_runs = [phase for phase in result.phases if phase.phase_name == "LOCAL_BIST_RUN"]

    assert len(local_runs) == 2
    assert local_runs[0].start_s < local_runs[1].end_s
    assert local_runs[1].start_s < local_runs[0].end_s


def test_schedule_writers_create_outputs(tmp_path) -> None:
    model, rows = _m3_rows()
    result = greedy_schedule(model, rows)
    schedule_output = tmp_path / "schedule.csv"
    report_output = tmp_path / "report.md"

    write_schedule_csv(result, schedule_output)
    write_schedule_report_markdown(result, report_output)

    assert schedule_output.read_text(encoding="utf-8").startswith("case_id,target_id")
    assert "M4 Greedy Schedule Report" in report_output.read_text(encoding="utf-8")


def _bist_row(target_id: str, die_id: str, recipe_id: str, power_w: float) -> dict[str, object]:
    phases = [
        {
            "phase_name": "CONFIG_BIST",
            "duration_s": 1.0,
            "serial_required": True,
            "fpp_lanes_required": 0,
            "fpp_channel": "",
            "dwr_segments": [],
            "route_resource": "",
            "power_w": 0.1,
            "thermal_region": f"thermal_{die_id}",
            "notes": "",
        },
        {
            "phase_name": "LOCAL_BIST_RUN",
            "duration_s": 10.0,
            "serial_required": False,
            "fpp_lanes_required": 0,
            "fpp_channel": "",
            "dwr_segments": [],
            "route_resource": "",
            "power_w": power_w,
            "thermal_region": f"thermal_{die_id}",
            "notes": "",
        },
        {
            "phase_name": "READ_BIST_RESULT",
            "duration_s": 1.0,
            "serial_required": True,
            "fpp_lanes_required": 0,
            "fpp_channel": "",
            "dwr_segments": [],
            "route_resource": "",
            "power_w": 0.1,
            "thermal_region": f"thermal_{die_id}",
            "notes": "",
        },
    ]
    return {
        "recipe_id": recipe_id,
        "target_id": target_id,
        "target_kind": "core",
        "die_id": die_id,
        "recipe_type": "B",
        "variant": "local_bist",
        "total_time_s": 12.0,
        "serial_time_s": 2.0,
        "fpp_time_s": 0.0,
        "lane_occupancy": 0.0,
        "peak_power_w": power_w,
        "thermal_risk": power_w,
        "phase_resources": json.dumps(phases),
    }
