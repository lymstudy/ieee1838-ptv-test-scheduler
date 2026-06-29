"""Resource Pressure Sweep Experiment.

Produces Figure 4 data — the "Pressure Gradient Continuous Response Curves" —
by characterising how joint scheduling gain changes as a function of:

  Part A — Shared BIST engine count (resource pressure gradient)
  Part B — Available alternative path types   (path diversity gradient)

For three representative topologies (2.5D interposer, 3D stack, 5.5D multi-tower)
using the *small* M21 pressure cases.
"""

from __future__ import annotations

import argparse
import copy
import csv
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.run_m11_algorithm_study import _fastest_recipe_rows, _filter_recipe_types
from src.evaluators.comparison import build_comparison_rows
from src.evaluators.thermal import evaluate_schedule_thermal
from src.model import SystemModel, load_system_model
from src.recipes import RecipeGenerator, pareto_prune, rows_from_recipes
from src.schedulers import (
    CpSatUnavailableError,
    SchedulingError,
    greedy_schedule,
    solve_cpsat_schedule,
)

# ---------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------

M21_CASE_DIR = Path("configs/cases/m21")

# pick one small/medium-pressure case per topology
REPRESENTATIVE_CASES: dict[str, str] = {
    "2_5d_interposer": "m21_pressure_small_d695_2_5d_interposer.json",
    "3d_stack": "m21_pressure_small_d695_3d_stack.json",
    "5_5d_multi_tower": "m21_pressure_small_d695_5_5d_multi_tower.json",
}

# Part A: shared BIST counts to sweep
BIST_COUNTS = [1, 2, 4, 8, None]  # None = private (infinite)

# Part B: recipe type restrictions (ordered from most restricted to full set)
# Serial (S) is always included as the baseline fallback — the restriction
# is about which *additional* path types are available beyond serial.
PATH_DIVERSITY_LEVELS: list[tuple[str, set[str]]] = [
    ("BIST_only", {"S", "B", "I"}),
    ("BIST_FPP", {"S", "B", "F", "I"}),
    ("BIST_FPP_Hybrid", {"S", "B", "F", "H", "I"}),
]

CP_SAT_TIME_LIMIT_S = 10.0
MAX_CPSAT_TARGETS = 22  # small cases have ~14 targets, well within this

# ---------------------------------------------------------------------------
# output schema
# ---------------------------------------------------------------------------

OUTPUT_FIELDNAMES = [
    "case_id",
    "topology",
    "bist_count",
    "allowed_recipe_types",
    "method_id",
    "makespan_s",
    "gain_vs_fixed_fastest_pct",
    "peak_power_w",
    "peak_temperature_c",
    "fpp_utilization",
    "selected_recipe_types",
    "status",
]

# ---------------------------------------------------------------------------
# shared-BIST model manipulation
# ---------------------------------------------------------------------------


def _set_shared_bist_count(raw: dict[str, Any], count: int | None) -> dict[str, Any]:
    """Return a deep copy of *raw* with bist_engine_groups rewritten.

    - ``count`` = 1..N  -> create that many groups, evenly distributing members
    - ``count`` = None  -> each BIST-enabled target gets its own private engine
                           (i.e. capacity=1 per group, one member per group)
    """
    model = copy.deepcopy(raw)

    bist_target_ids: list[str] = []
    for obj in model["test_objects"]:
        if obj.get("bist", {}).get("enabled"):
            bist_target_ids.append(obj["object_id"])

    if not bist_target_ids:
        # No BIST targets → empty groups
        model["resource_groups"]["bist_engine_groups"] = []
        return model

    groups: list[dict[str, Any]] = []

    if count is None:
        # ---- private: one engine per BIST target ----
        for tid in bist_target_ids:
            groups.append({
                "group_id": f"bist_private_{tid}",
                "capacity": 1,
                "members": [tid],
            })
        model["experimental_controls"]["shared_bist_group_count"] = len(bist_target_ids)
        # update per-object engine_id & required_resources.bist_engine
        for obj in model["test_objects"]:
            if obj.get("bist", {}).get("enabled"):
                engine_name = f"bist_private_{obj['object_id']}"
                obj["bist"]["engine_id"] = engine_name
                obj["required_resources"]["bist_engine"] = engine_name
    else:
        # ---- shared: split members evenly across *count* groups ----
        n = int(count)
        assert n >= 1
        k = len(bist_target_ids)
        per_group = (k + n - 1) // n  # ceil division
        for g in range(n):
            start = g * per_group
            end = min(start + per_group, k)
            members = bist_target_ids[start:end]
            groups.append({
                "group_id": f"bist_shared_g{g:02d}",
                "capacity": 1,
                "members": members,
            })

        model["experimental_controls"]["shared_bist_group_count"] = min(n, k)
        # update per-object engine_id & required_resources.bist_engine
        group_index: dict[str, int] = {}
        for g_idx, group in enumerate(groups):
            for member in group["members"]:
                group_index[member] = g_idx
        for obj in model["test_objects"]:
            if obj.get("bist", {}).get("enabled"):
                g_idx = group_index.get(obj["object_id"], 0)
                engine_name = f"bist_shared_g{g_idx:02d}"
                obj["bist"]["engine_id"] = engine_name
                obj["required_resources"]["bist_engine"] = engine_name

    model["resource_groups"]["bist_engine_groups"] = groups
    return model


def _bist_count_label(count: int | None) -> str:
    if count is None:
        return "inf"
    return str(count)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _selected_type_counts(selected_types_str: str) -> dict[str, int]:
    counts: dict[str, int] = {"B": 0, "F": 0, "H": 0, "S": 0, "I": 0}
    if not selected_types_str:
        return counts
    for token in selected_types_str.split(";"):
        token = token.strip()
        if not token or ":" not in token:
            continue
        typ, val = token.split(":", 1)
        try:
            counts[typ.strip()] = int(val.strip())
        except (ValueError, KeyError):
            pass
    return counts


def _schedule_phase_stats(phases: list[Any]) -> dict[str, Any]:
    tap_phases = 0
    tap_time = 0.0
    fpp_time = 0.0
    excl_time = 0.0
    for ph in phases:
        if getattr(ph, "serial_required", False):
            tap_phases += 1
            tap_time += float(getattr(ph, "duration_s", 0.0))
        pn = str(getattr(ph, "phase_name", ""))
        if pn.startswith("FPP_"):
            fpp_time += float(getattr(ph, "duration_s", 0.0))
        if getattr(ph, "exclusive_resource", ""):
            excl_time += float(getattr(ph, "duration_s", 0.0))
    return {
        "tap_access_phase_count": tap_phases,
        "tap_access_time_s": tap_time,
        "fpp_data_time_s": fpp_time,
        "exclusive_test_time_s": excl_time,
    }


# ---------------------------------------------------------------------------
# core run
# ---------------------------------------------------------------------------


def run_part_a_bist_sweep(
    case_path: Path,
    time_limit_s: float,
) -> list[dict[str, Any]]:
    """Sweep shared BIST counts for a single topology case."""
    base_model = load_system_model(case_path)
    topology = base_model.raw["package"]["topology_type"]
    rows: list[dict[str, Any]] = []

    for bist_count in BIST_COUNTS:
        bist_label = _bist_count_label(bist_count)
        variant_raw = _set_shared_bist_count(base_model.raw, bist_count)
        variant_model = SystemModel(variant_raw, source_path=case_path)

        # Generate recipes — use ALL recipe types for Part A
        all_rows = rows_from_recipes(RecipeGenerator(variant_model).generate_all())
        pareto_rows = pareto_prune(all_rows).kept_rows

        try:
            part_rows = _run_methods_for_variant(
                variant_model,
                pareto_rows,
                all_rows,
                bist_count=bist_label,
                allowed_recipe_types="all",
                time_limit_s=time_limit_s,
            )
        except Exception:
            # fallback: mark all methods as failed for this variant
            part_rows = _failed_variant_rows(variant_model, bist_label, "all")

        rows.extend(part_rows)

    return rows


def run_part_b_path_sweep(
    case_path: Path,
    time_limit_s: float,
) -> list[dict[str, Any]]:
    """Sweep recipe type restrictions for a single topology case (shared BIST=1)."""
    base_model = load_system_model(case_path)
    topology = base_model.raw["package"]["topology_type"]
    rows: list[dict[str, Any]] = []

    # Use shared BIST = 1 (default: keep original groups as-is if they have 1 group,
    # otherwise force to 1 shared group)
    variant_raw = _set_shared_bist_count(base_model.raw, 1)
    variant_model = SystemModel(variant_raw, source_path=case_path)

    all_recipes = RecipeGenerator(variant_model).generate_all()
    all_recipe_rows = rows_from_recipes(all_recipes)

    for label, allowed_types in PATH_DIVERSITY_LEVELS:
        try:
            filtered_rows = _filter_recipe_types(all_recipe_rows, allowed_types)
        except ValueError as exc:
            # Some targets cannot be covered → mark as failed for this restriction
            rows.extend(_failed_variant_rows(variant_model, "1", label, str(exc)))
            continue

        pareto_rows = pareto_prune(filtered_rows).kept_rows

        try:
            part_rows = _run_methods_for_variant(
                variant_model,
                pareto_rows,
                filtered_rows,
                bist_count="1",
                allowed_recipe_types=label,
                time_limit_s=time_limit_s,
            )
        except Exception:
            part_rows = _failed_variant_rows(variant_model, "1", label)

        rows.extend(part_rows)

    return rows


def _run_methods_for_variant(
    model: SystemModel,
    pareto_rows: list[dict[str, object]],
    all_rows: list[dict[str, object]] | None,
    bist_count: str,
    allowed_recipe_types: str,
    time_limit_s: float,
) -> list[dict[str, Any]]:
    """Run all scheduling methods for one (model, recipe) variant."""

    rows_out: list[dict[str, Any]] = []
    fixed_makespan: float | None = None

    # --- fixed_fastest (baseline) ---
    fastest_rows = _fastest_recipe_rows(pareto_rows)
    try:
        f_schedule = greedy_schedule(model, fastest_rows)
    except (SchedulingError, ValueError, RuntimeError) as exc:
        rows_out.append(
            _base_row(model, bist_count, allowed_recipe_types, "fixed_fastest",
                       status="failed", error=str(exc))
        )
        # Without a valid fixed_fastest baseline we cannot compute gain
        # Still try to run the other methods for relative comparison
    else:
        fixed_makespan = f_schedule.makespan_s
        thermal = evaluate_schedule_thermal(model, f_schedule.phases, "fixed_fastest")
        rows_out.append(_success_row(
            model, f_schedule, "fixed_fastest", thermal,
            bist_count, allowed_recipe_types,
            fixed_makespan=fixed_makespan, solver_status="greedy",
        ))

    # --- m4_greedy (joint) ---
    try:
        m4_schedule = greedy_schedule(model, pareto_rows)
    except (SchedulingError, ValueError, RuntimeError) as exc:
        rows_out.append(
            _base_row(model, bist_count, allowed_recipe_types, "m4_greedy",
                       status="failed", error=str(exc))
        )
    else:
        thermal = evaluate_schedule_thermal(model, m4_schedule.phases, "m4_greedy")
        rows_out.append(_success_row(
            model, m4_schedule, "m4_greedy", thermal,
            bist_count, allowed_recipe_types,
            fixed_makespan=fixed_makespan, solver_status="greedy",
        ))

    # --- m5_cpsat (joint, optional) ---
    target_count = len(model.test_objects) + len(model.interconnects)
    if target_count <= MAX_CPSAT_TARGETS:
        try:
            m5_schedule, m5_info = solve_cpsat_schedule(
                model, pareto_rows, time_limit_s=time_limit_s
            )
        except (CpSatUnavailableError, RuntimeError, ValueError) as exc:
            rows_out.append(
                _base_row(model, bist_count, allowed_recipe_types, "m5_cpsat",
                           status="failed", error=str(exc))
            )
        else:
            thermal = evaluate_schedule_thermal(model, m5_schedule.phases, "m5_cpsat")
            rows_out.append(_success_row(
                model, m5_schedule, "m5_cpsat", thermal,
                bist_count, allowed_recipe_types,
                fixed_makespan=fixed_makespan,
                solver_status=m5_info.status_name,
            ))

    return rows_out


def _failed_variant_rows(
    model: SystemModel,
    bist_count: str,
    allowed_recipe_types: str,
    error: str = "variant construction failed",
) -> list[dict[str, Any]]:
    """Produce failure rows for all three methods."""
    rows: list[dict[str, Any]] = []
    for method_id in ("fixed_fastest", "m4_greedy", "m5_cpsat"):
        rows.append(_base_row(
            model, bist_count, allowed_recipe_types, method_id,
            status="failed", error=error,
        ))
    return rows


def _base_row(
    model: SystemModel,
    bist_count: str,
    allowed_recipe_types: str,
    method_id: str,
    status: str = "ok",
    error: str = "",
) -> dict[str, Any]:
    return {
        "case_id": model.case_id,
        "topology": model.raw["package"]["topology_type"],
        "bist_count": bist_count,
        "allowed_recipe_types": allowed_recipe_types,
        "method_id": method_id,
        "makespan_s": "",
        "gain_vs_fixed_fastest_pct": "",
        "peak_power_w": "",
        "peak_temperature_c": "",
        "fpp_utilization": "",
        "selected_recipe_types": "",
        "status": status,
        "error": error,
    }


def _success_row(
    model: SystemModel,
    schedule: Any,
    method_id: str,
    thermal: Any,
    bist_count: str,
    allowed_recipe_types: str,
    fixed_makespan: float | None,
    solver_status: str = "",
) -> dict[str, Any]:
    gain = ""
    if fixed_makespan is not None and fixed_makespan > 0:
        gain = (fixed_makespan - schedule.makespan_s) / fixed_makespan * 100.0
    else:
        gain = ""

    row = _base_row(model, bist_count, allowed_recipe_types, method_id, status="ok")
    row.update({
        "makespan_s": schedule.makespan_s,
        "gain_vs_fixed_fastest_pct": gain,
        "peak_power_w": schedule.peak_power_w,
        "peak_temperature_c": thermal.peak_temperature_c,
        "fpp_utilization": _fpp_utilization_from_schedule(model, schedule),
        "selected_recipe_types": _recipe_type_counts(schedule),
    })
    if solver_status:
        row["solver_status"] = solver_status
    return row


def _fpp_utilization_from_schedule(model: SystemModel, schedule: Any) -> float:
    total_lanes = int(model.resource_limits.get("total_fpp_lanes", 0))
    if schedule.makespan_s <= 0 or total_lanes <= 0:
        return 0.0
    return schedule.fpp_lane_time_s / (schedule.makespan_s * total_lanes)


def _recipe_type_counts(schedule: Any) -> str:
    counts: dict[str, int] = {}
    for row in schedule.selected_rows:
        rt = str(row.get("recipe_type", ""))
        counts[rt] = counts.get(rt, 0) + 1
    return ";".join(f"{k}:{counts[k]}" for k in sorted(counts))


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------


def write_report(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# Resource Pressure Sweep Report")
    lines.append("")
    lines.append("## Experiment Summary")
    lines.append("")
    lines.append(f"- Total rows: {len(rows)}")
    ok_rows = [r for r in rows if r["status"] == "ok"]
    failed_rows = [r for r in rows if r["status"] == "failed"]
    lines.append(f"- Successful schedules: {len(ok_rows)}")
    lines.append(f"- Failed schedules: {len(failed_rows)}")
    lines.append("")

    # --- Part A summary: gain vs BIST count per topology ---
    lines.append("## Part A: Shared BIST Count Sweep")
    lines.append("")
    for topo in ["2_5d_interposer", "3d_stack", "5_5d_multi_tower"]:
        lines.append(f"### Topology: {topo}")
        lines.append("")
        lines.append("| BIST Count | fixed_fastest (s) | M4 Greedy (s) | M4 Gain (%) | M5 CP-SAT (s) | M5 Gain (%) | M5 Status |")
        lines.append("|-----------|-------------------|---------------|-------------|---------------|-------------|-----------|")
        topo_rows = [r for r in ok_rows if r["topology"] == topo]
        bist_order = ["1", "2", "4", "8", "inf"]
        for bist in bist_order:
            ff = _find_row(topo_rows, bist, "all", "fixed_fastest")
            m4 = _find_row(topo_rows, bist, "all", "m4_greedy")
            m5 = _find_row(topo_rows, bist, "all", "m5_cpsat")
            ff_ms = f'{ff["makespan_s"]:.3f}' if ff else "-"
            m4_ms = f'{m4["makespan_s"]:.3f}' if m4 else "-"
            m4_g = f'{m4["gain_vs_fixed_fastest_pct"]:.2f}' if m4 and m4["gain_vs_fixed_fastest_pct"] != "" else "-"
            m5_ms = f'{m5["makespan_s"]:.3f}' if m5 else "-"
            m5_g = f'{m5["gain_vs_fixed_fastest_pct"]:.2f}' if m5 and m5["gain_vs_fixed_fastest_pct"] != "" else "-"
            m5_st = m5.get("solver_status", "-") if m5 else "-"
            lines.append(f"| {bist} | {ff_ms} | {m4_ms} | {m4_g} | {m5_ms} | {m5_g} | {m5_st} |")
        lines.append("")

    # --- Part B summary: gain vs path diversity per topology ---
    lines.append("## Part B: Path Diversity Sweep (shared BIST=1)")
    lines.append("")
    for topo in ["2_5d_interposer", "3d_stack", "5_5d_multi_tower"]:
        lines.append(f"### Topology: {topo}")
        lines.append("")
        lines.append("| Allowed Types | fixed_fastest (s) | M4 Greedy (s) | M4 Gain (%) | M5 CP-SAT (s) | M5 Gain (%) | M5 Status |")
        lines.append("|--------------|-------------------|---------------|-------------|---------------|-------------|-----------|")
        topo_rows = [r for r in ok_rows if r["topology"] == topo and r["bist_count"] == "1"]
        for label, _ in PATH_DIVERSITY_LEVELS:
            ff = _find_row(topo_rows, "1", label, "fixed_fastest")
            m4 = _find_row(topo_rows, "1", label, "m4_greedy")
            m5 = _find_row(topo_rows, "1", label, "m5_cpsat")
            ff_ms = f'{ff["makespan_s"]:.3f}' if ff else "-"
            m4_ms = f'{m4["makespan_s"]:.3f}' if m4 else "-"
            m4_g = f'{m4["gain_vs_fixed_fastest_pct"]:.2f}' if m4 and m4["gain_vs_fixed_fastest_pct"] != "" else "-"
            m5_ms = f'{m5["makespan_s"]:.3f}' if m5 else "-"
            m5_g = f'{m5["gain_vs_fixed_fastest_pct"]:.2f}' if m5 and m5["gain_vs_fixed_fastest_pct"] != "" else "-"
            m5_st = m5.get("solver_status", "-") if m5 else "-"
            lines.append(f"| {label} | {ff_ms} | {m4_ms} | {m4_g} | {m5_ms} | {m5_g} | {m5_st} |")
        lines.append("")

    lines.append("## Interpretation Notes")
    lines.append("")
    lines.append("1. **BIST pressure gradient (Part A):** As shared BIST count decreases (fewer engines "
                "shared by more targets), pressure increases. Joint scheduling gain should be largest "
                "at shared BIST=1 and approach 0% when BIST is private (inf). "
                "The gain curve by topology reveals which topologies benefit most from joint scheduling "
                "under resource pressure.")
    lines.append("2. **Path diversity gradient (Part B):** When only BIST is available, all test must "
                "serialise on shared engines. Adding FPP creates an alternative path for concurrent "
                "scheduling. Adding Hybrid further increases flexibility. "
                "Gain should monotonically increase as path diversity increases.")
    lines.append("3. **CP-SAT feasibility:** When CP-SAT status is FEASIBLE (not OPTIMAL), the "
                "reported makespan is an upper bound. The true optimal gain may be higher.")

    with output_path.open("w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def _find_row(
    rows: list[dict[str, Any]], bist_count: str, allowed_types: str, method_id: str
) -> dict[str, Any] | None:
    for r in rows:
        if (r["bist_count"] == bist_count and
            r["allowed_recipe_types"] == allowed_types and
            r["method_id"] == method_id and
            r["status"] == "ok"):
            return r
    return None


def write_rows(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({f: row.get(f, "") for f in OUTPUT_FIELDNAMES})


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resource Pressure Sweep (Fig 4)")
    parser.add_argument(
        "--case-dir",
        type=Path,
        default=M21_CASE_DIR,
        help="Directory containing M21 pressure case JSON files",
    )
    parser.add_argument(
        "--time-limit-s",
        type=float,
        default=CP_SAT_TIME_LIMIT_S,
        help="CP-SAT time limit per solve",
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        default=Path("results/tables/resource_pressure_sweep.csv"),
        help="Output CSV path",
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=Path("results/reports/resource_pressure_sweep_report.md"),
        help="Output report path",
    )
    parser.add_argument(
        "--part",
        choices=["A", "B", "both"],
        default="both",
        help="Which part to run",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # verify case directory exists
    if not args.case_dir.exists():
        print(f"ERROR: case directory not found: {args.case_dir}", file=sys.stderr)
        sys.exit(1)

    all_rows: list[dict[str, Any]] = []

    for topo_name, case_fname in REPRESENTATIVE_CASES.items():
        case_path = args.case_dir / case_fname
        if not case_path.exists():
            print(f"WARNING: case file not found, skipping: {case_path}", file=sys.stderr)
            continue

        case_id = case_path.stem
        print(f"\n{'='*60}")
        print(f"Processing {case_id} (topology: {topo_name})")
        print(f"{'='*60}")

        if args.part in ("A", "both"):
            print("--- Part A: BIST Count Sweep ---")
            part_a_rows = run_part_a_bist_sweep(case_path, args.time_limit_s)
            # Keep only columns matching OUTPUT_FIELDNAMES (dropping "error" column)
            all_rows.extend(part_a_rows)
            ok_a = sum(1 for r in part_a_rows if r["status"] == "ok")
            print(f"  Part A: {len(part_a_rows)} rows ({ok_a} ok)")

        if args.part in ("B", "both"):
            print("--- Part B: Path Diversity Sweep ---")
            part_b_rows = run_part_b_path_sweep(case_path, args.time_limit_s)
            all_rows.extend(part_b_rows)
            ok_b = sum(1 for r in part_b_rows if r["status"] == "ok")
            print(f"  Part B: {len(part_b_rows)} rows ({ok_b} ok)")

    # ---- write outputs ----
    print(f"\nWriting {len(all_rows)} rows to {args.csv_output}")
    write_rows(all_rows, args.csv_output)

    print(f"Writing report to {args.report_output}")
    write_report(all_rows, args.report_output)

    ok_total = sum(1 for r in all_rows if r["status"] == "ok")
    print(f"\nDone. {ok_total}/{len(all_rows)} schedules succeeded.")


if __name__ == "__main__":
    main()
