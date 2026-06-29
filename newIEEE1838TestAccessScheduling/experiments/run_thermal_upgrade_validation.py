"""Validate the upgraded thermal proxy model.

Runs 3 representative cases (one per topology: 2.5D, 3D, 5.5D) with
M4 greedy and fixed-fastest scheduling, then computes thermal proxy with
the upgraded model. Reports peak temperatures and cross-method deltas.

Expected results:
  - Peak temperatures in the 30-60 C range (not ~25 C)
  - Cross-method temperature deltas of at least 5 C
  - Clear thermal gradient from bottom die to top die
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluators import evaluate_schedule_thermal, HotspotRow
from src.model import SystemModel, load_system_model
from src.recipes import RecipeGenerator, pareto_prune, rows_from_recipes
from src.schedulers import ScheduleResult, greedy_schedule

TOPOLOGY_CASES = {
    "2.5D": "configs/cases/m10/m10_small_d695_2_5d_interposer.json",
    "3D": "configs/cases/m10/m10_small_d695_3d_stack.json",
    "5.5D": "configs/cases/m10/m10_small_d695_5_5d_multi_tower.json",
}


@dataclass
class ValidationRow:
    topology: str
    case_id: str
    method_id: str
    makespan_s: float
    peak_temperature_c: float
    peak_region: str
    peak_die: str
    per_die_peaks: dict[str, float]
    cross_method_delta_c: float


def main() -> None:
    print("=" * 72)
    print("Thermal Proxy Upgrade Validation")
    print("=" * 72)

    all_rows: list[ValidationRow] = []

    for topology, case_path in TOPOLOGY_CASES.items():
        print(f"\n--- {topology} ({case_path}) ---")
        model = load_system_model(case_path)
        all_rows.extend(run_case(model, topology))

    # Summary
    print("\n" + "=" * 72)
    print("VALIDATION SUMMARY")
    print("=" * 72)

    for topology in ["2.5D", "3D", "5.5D"]:
        case_rows = [r for r in all_rows if r.topology == topology]
        print(f"\n## {topology}")
        for row in case_rows:
            print(f"  {row.method_id:20s} | makespan={row.makespan_s:.6f}s | "
                  f"peak_temp={row.peak_temperature_c:.2f}C | peak_die={row.peak_die}")
            die_str = "  Die temps: " + " | ".join(
                f"{die}: {temp:.2f}C" for die, temp in sorted(row.per_die_peaks.items())
            )
            print(die_str)

        methods = set(r.method_id for r in case_rows)
        if len(methods) >= 2:
            peaks = [r.peak_temperature_c for r in case_rows]
            delta = max(peaks) - min(peaks)
            for r in case_rows:
                r.cross_method_delta_c = delta
            if delta >= 5.0:
                print(f"  [PASS] Cross-method delta = {delta:.2f}C >= 5.0C (methods: {len(methods)})")
            else:
                print(f"  [WARN] Cross-method delta = {delta:.2f}C < 5.0C (methods may produce identical schedules)")

    # Overall checks
    all_peaks = [r.peak_temperature_c for r in all_rows]
    min_peak = min(all_peaks)
    max_peak = max(all_peaks)
    print(f"\nOverall temperature range: {min_peak:.2f}C - {max_peak:.2f}C")

    if max_peak >= 30.0:
        print("[PASS] Max peak temperature >= 30 C (meaningful thermal range)")
    else:
        print("[WARN] Max peak temperature < 30 C (thermal proxy may still be too mild)")

    deltas = [r.cross_method_delta_c for r in all_rows if r.cross_method_delta_c > 0]
    if deltas:
        avg_delta = sum(deltas) / len(deltas)
        min_delta = min(deltas)
        print(f"Cross-method deltas: avg={avg_delta:.2f}C, min={min_delta:.2f}C")
        if min_delta >= 5.0:
            print("[PASS] All cases achieve >= 5C cross-method delta")
        else:
            print("[WARN] Some cases have cross-method delta < 5C")

    # Print thermal gradient check
    print("\n## Thermal Gradient Check (distance from heat sink)")
    for row in all_rows:
        peaks = row.per_die_peaks
        die_temps = [(die, temp) for die, temp in peaks.items()]
        if len(die_temps) >= 2:
            gradient = max(p[1] for p in die_temps) - min(p[1] for p in die_temps)
            hottest = max(die_temps, key=lambda x: x[1])
            coolest = min(die_temps, key=lambda x: x[1])
            if gradient >= 2.5:
                print(f"  [PASS] {row.topology}/{row.method_id}: gradient={gradient:.2f}C ({coolest[0]}={coolest[1]:.2f}C -> {hottest[0]}={hottest[1]:.2f}C)")
            else:
                print(f"  [WARN] {row.topology}/{row.method_id}: gradient={gradient:.2f}C (weak gradient between dies)")

    print("\nDone.")


def run_case(model: SystemModel, topology: str) -> list[ValidationRow]:
    all_rows = rows_from_recipes(RecipeGenerator(model).generate_all())
    pareto_rows = pareto_prune(all_rows).kept_rows

    # Select fastest recipe per target (fixed-fastest)
    fastest_rows = _select_fastest_per_target(pareto_rows)

    # Force pure serial: select only serial (S) recipe per target
    serial_rows = _select_serial_per_target(all_rows)

    # BIST-preferred: select BIST recipe where available, otherwise fastest
    bist_rows = _select_bist_preferred_per_target(all_rows, pareto_rows)

    schedules: list[tuple[str, ScheduleResult]] = [
        ("fixed_fastest", greedy_schedule(model, fastest_rows)),
        ("m4_greedy", greedy_schedule(model, pareto_rows)),
        ("pure_serial", greedy_schedule(model, serial_rows)),
        ("bist_preferred", greedy_schedule(model, bist_rows)),
    ]

    rows: list[ValidationRow] = []
    for method_id, schedule in schedules:
        schedule_id = f"{model.case_id}::{method_id}"
        result = evaluate_schedule_thermal(model, schedule.phases, schedule_id)

        per_die_peaks: dict[str, float] = {}
        for hotspot in result.hotspots:
            per_die_peaks[hotspot.die_id] = hotspot.peak_temperature_c

        rows.append(ValidationRow(
            topology=topology,
            case_id=model.case_id,
            method_id=method_id,
            makespan_s=result.makespan_s,
            peak_temperature_c=result.peak_temperature_c,
            peak_region=result.peak_region,
            peak_die=_peak_die(result.hotspots),
            per_die_peaks=per_die_peaks,
            cross_method_delta_c=0.0,
        ))

        peaks = list(per_die_peaks.values())
        if peaks:
            print(f"  {method_id}: peak={max(peaks):.2f}C, range={min(peaks):.2f}-{max(peaks):.2f}C, "
                  f"makespan={result.makespan_s:.6f}s")

    # Compute cross-method deltas (max - min within this case)
    if rows:
        peaks_in_case = [r.peak_temperature_c for r in rows]
        max_peak = max(peaks_in_case)
        min_peak = min(peaks_in_case)
        delta = max_peak - min_peak
        for r in rows:
            r.cross_method_delta_c = delta

    return rows


def _select_fastest_per_target(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    selected: dict[str, tuple[float, dict[str, object]]] = {}
    for row in rows:
        target_id = str(row["target_id"])
        time_s = float(row.get("total_time_s", 0.0))
        if target_id not in selected or time_s < selected[target_id][0]:
            selected[target_id] = (time_s, row)
    return [item[1] for item in selected.values()]


def _select_serial_per_target(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Select only serial (S) recipe per target. Falls back to fastest if no S recipe."""
    selected: dict[str, dict[str, object]] = {}
    for row in rows:
        target_id = str(row["target_id"])
        recipe_type = str(row.get("recipe_type", ""))
        time_s = float(row.get("total_time_s", 0.0))
        if recipe_type == "S":
            if target_id not in selected or time_s < float(selected[target_id].get("total_time_s", float("inf"))):
                selected[target_id] = row
    # Fall back to fastest for targets without S recipe
    if len(selected) < len({str(r["target_id"]) for r in rows}):
        fastest = _select_fastest_per_target(rows)
        for row in fastest:
            target_id = str(row["target_id"])
            if target_id not in selected:
                selected[target_id] = row
    return list(selected.values())


def _select_bist_preferred_per_target(
    all_rows: list[dict[str, object]],
    pareto_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Select BIST recipe where available, otherwise fastest non-serial from pareto."""
    selected: dict[str, dict[str, object]] = {}
    target_ids = {str(r["target_id"]) for r in all_rows}

    for row in all_rows:
        target_id = str(row["target_id"])
        recipe_type = str(row.get("recipe_type", ""))
        time_s = float(row.get("total_time_s", 0.0))
        if recipe_type == "B":
            if target_id not in selected or time_s < float(selected[target_id].get("total_time_s", float("inf"))):
                selected[target_id] = row

    # Fall back to fastest non-serial from pareto
    for target_id in target_ids:
        if target_id in selected:
            continue
        candidates = [r for r in pareto_rows if str(r["target_id"]) == target_id and str(r.get("recipe_type", "")) != "S"]
        if not candidates:
            candidates = [r for r in pareto_rows if str(r["target_id"]) == target_id]
        if candidates:
            selected[target_id] = min(candidates, key=lambda r: float(r.get("total_time_s", float("inf"))))

    return list(selected.values())


def _peak_die(hotspots: list[HotspotRow]) -> str:
    if not hotspots:
        return "N/A"
    peak = max(hotspots, key=lambda h: h.peak_temperature_c)
    return peak.die_id


if __name__ == "__main__":
    main()
