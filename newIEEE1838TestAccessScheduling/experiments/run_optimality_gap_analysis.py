"""Optimality gap analysis for the IEEE 1838 test scheduling CP-SAT solver.

Runs CP-SAT with increasing time limits on small, medium, and large cases
to quantify how close our solutions are to the true optimal.

Outputs:
  results/figures/revised/fig_optimality_gap.png
  results/tables/optimality_gap_analysis.csv
  results/reports/optimality_gap_report.md
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.model import load_system_model
from src.recipes import RecipeGenerator, pareto_prune, rows_from_recipes
from src.schedulers.cpsat import (
    TIME_SCALE,
    _add_cumulative,
    _ceil_scaled,
    _is_capture,
    _normalize_cpsat_rows,
    _recipe_spec,
)

from ortools.sat.python import cp_model as _ORTools


# ---------------------------------------------------------------------------
# Case definition
# ---------------------------------------------------------------------------

CASE_DEFS = [
    {
        "label": "small_d695_3d_stack",
        "path": "configs/cases/m10/m10_small_d695_3d_stack.json",
        "scale": "small",
        "time_limits_s": [1, 10, 60, 300],
    },
    {
        "label": "medium_p22810_3d_stack",
        "path": "configs/cases/m10/m10_medium_p22810_3d_stack.json",
        "scale": "medium",
        "time_limits_s": [5, 30, 120, 600],
    },
    {
        "label": "large_p34392_3d_stack",
        "path": "configs/cases/m10/m10_large_p34392_3d_stack.json",
        "scale": "large",
        "time_limits_s": [10, 60, 300],
    },
]

CSV_FIELDNAMES = [
    "case_id",
    "scale",
    "target_count",
    "variable_count",
    "constraint_count",
    "recipe_count",
    "pareto_recipe_count",
    "time_limit_s",
    "solver_status",
    "makespan_s",
    "solver_wall_time_s",
    "best_objective_bound_s",
    "optimality_gap_percent",
    "num_booleans",
    "num_branches",
    "num_conflicts",
    "notes",
]


@dataclass
class GapResult:
    case_id: str
    scale: str
    label: str
    target_count: int
    variable_count: int
    constraint_count: int
    recipe_count: int
    pareto_recipe_count: int
    time_limit_s: float
    solver_status: str
    makespan_s: float
    solver_wall_time_s: float
    best_objective_bound_s: float | None = None
    optimality_gap_percent: float | None = None
    num_booleans: int = 0
    num_branches: int = 0
    num_conflicts: int = 0
    notes: str = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run CP-SAT optimality gap analysis."
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Number of CP-SAT search workers.",
    )
    parser.add_argument(
        "--skip-long",
        action="store_true",
        help="Skip long-running time limits (300s+).",
    )
    parser.add_argument(
        "--output-csv",
        default="results/tables/optimality_gap_analysis.csv",
        help="Output CSV path.",
    )
    parser.add_argument(
        "--output-report",
        default="results/reports/optimality_gap_report.md",
        help="Output Markdown report path.",
    )
    parser.add_argument(
        "--output-figure",
        default="results/figures/revised/fig_optimality_gap.png",
        help="Output figure PNG path.",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Core CP-SAT run with extended info
# ---------------------------------------------------------------------------

def solve_with_gap_info(
    model: Any,
    rows_or_variants: list,
    time_limit_s: float,
    workers: int = 8,
) -> dict[str, Any]:
    """Run CP-SAT and capture loss, lower bound, and solver info.

    Returns a dict with all fields needed for the gap analysis,
    including ``best_objective_bound`` and derived ``optimality_gap_percent``.
    """
    cp = _ORTools

    rows, mode = _normalize_cpsat_rows(rows_or_variants)
    if not rows:
        raise ValueError("no rows supplied")

    recipe_specs = [_recipe_spec(row) for row in rows]
    horizon = sum(
        sum(phase["duration_ticks"] for phase in spec["phases"])
        for spec in recipe_specs
    )
    horizon = max(horizon, 1)

    cpm = cp.CpModel()
    intervals: list[dict[str, Any]] = []
    selected_by_recipe: dict[str, Any] = {}

    for spec in recipe_specs:
        selected = cpm.NewBoolVar(f"select_{spec['recipe_id']}")
        selected_by_recipe[spec["recipe_id"]] = selected
        previous_end = None
        for index, phase in enumerate(spec["phases"]):
            start = cpm.NewIntVar(0, horizon, f"start_{spec['recipe_id']}_{index}")
            end_val = cpm.NewIntVar(0, horizon, f"end_{spec['recipe_id']}_{index}")
            interval = cpm.NewOptionalIntervalVar(
                start,
                phase["duration_ticks"],
                end_val,
                selected,
                f"interval_{spec['recipe_id']}_{index}",
            )
            if previous_end is not None:
                cpm.Add(start >= previous_end).OnlyEnforceIf(selected)
            previous_end = end_val
            intervals.append(
                {
                    "spec": spec,
                    "phase": phase,
                    "index": index,
                    "selected": selected,
                    "start": start,
                    "end": end_val,
                    "interval": interval,
                }
            )

    # Variant selection constraint
    group_key = "task_id" if mode == "task" else "target_id"
    for gid in sorted({spec[group_key] for spec in recipe_specs}):
        cpm.AddExactlyOne(
            selected_by_recipe[spec["recipe_id"]]
            for spec in recipe_specs
            if spec[group_key] == gid
        )

    # Resource constraints
    serial_intervals = [
        item["interval"] for item in intervals if item["phase"]["serial_required"]
    ]
    if int(model.resource_limits.get("ptap_ports", 1)) == 1:
        cpm.AddNoOverlap(serial_intervals)
    elif serial_intervals:
        cpm.AddCumulative(
            serial_intervals,
            [1] * len(serial_intervals),
            int(model.resource_limits["ptap_ports"]),
        )

    _add_cumulative(
        cpm,
        intervals,
        lambda item: int(item["phase"]["fpp_lanes_required"]),
        int(model.resource_limits.get("total_fpp_lanes", 0)),
    )

    for channel in model.access.get("fpp_channels", []):
        channel_id = str(channel["channel_id"])
        _add_cumulative(
            cpm,
            [
                item
                for item in intervals
                if item["phase"]["fpp_channel"] == channel_id
            ],
            lambda item: int(item["phase"]["fpp_lanes_required"]),
            int(
                channel.get(
                    "max_lanes",
                    model.resource_limits.get("total_fpp_lanes", 0),
                )
            ),
        )

    _add_cumulative(
        cpm,
        intervals,
        lambda item: _ceil_scaled(float(item["phase"]["power_w"]), 1000),
        _ceil_scaled(
            float(model.resource_limits.get("max_total_power_w", 0.0)), 1000
        ),
    )

    capture_limit = int(model.resource_limits.get("max_concurrent_capture", 0))
    capture_items = [
        item for item in intervals if _is_capture(item["phase"]["phase_name"])
    ]
    _add_cumulative(cpm, capture_items, lambda _item: 1, capture_limit)

    for group in model.raw.get("resource_groups", {}).get(
        "dwr_conflict_groups", []
    ):
        members = set(str(member) for member in group.get("members", []))
        group_items = [
            item
            for item in intervals
            if set(item["phase"]["dwr_segments"]) & members
        ]
        _add_cumulative(
            cpm, group_items, lambda _item: 1, int(group.get("capacity", 1))
        )

    for group in model.raw.get("resource_groups", {}).get(
        "bist_engine_groups", []
    ):
        members = set(str(member) for member in group.get("members", []))
        group_items = [
            item
            for item in intervals
            if item["phase"]["phase_name"] == "LOCAL_BIST_RUN"
            and item["spec"]["target_id"] in members
        ]
        _add_cumulative(
            cpm, group_items, lambda _item: 1, int(group.get("capacity", 1))
        )

    for resource in sorted(
        {
            item["phase"]["exclusive_resource"]
            for item in intervals
            if item["phase"]["exclusive_resource"]
        }
    ):
        resource_items = [
            item
            for item in intervals
            if item["phase"]["exclusive_resource"] == resource
        ]
        cpm.AddNoOverlap([item["interval"] for item in resource_items])

    makespan = cpm.NewIntVar(0, horizon, "makespan")
    for spec in recipe_specs:
        spec_items = [
            item
            for item in intervals
            if item["spec"]["recipe_id"] == spec["recipe_id"]
        ]
        if spec_items:
            cpm.Add(makespan >= spec_items[-1]["end"]).OnlyEnforceIf(
                selected_by_recipe[spec["recipe_id"]]
            )
    cpm.Minimize(makespan)

    solver = cp.CpSolver()
    solver.parameters.max_time_in_seconds = float(time_limit_s)
    solver.parameters.num_search_workers = int(workers)
    solver.parameters.log_search_progress = False

    status = solver.Solve(cpm)
    status_name = solver.StatusName(status)

    makespan_s = None
    best_bound_s = None
    gap = None

    if status in {cp.OPTIMAL, cp.FEASIBLE}:
        makespan_s = solver.ObjectiveValue() / TIME_SCALE
        try:
            raw_bound = solver.BestObjectiveBound()
            if raw_bound > 0 and raw_bound < 1e308:
                best_bound_s = raw_bound / TIME_SCALE
                if makespan_s > 0:
                    gap = (
                        (makespan_s - best_bound_s) / makespan_s * 100
                    )
        except Exception:
            best_bound_s = None
            gap = None
    else:
        makespan_s = None
        best_bound_s = None
        gap = None

    # Constraint count approximation via model proto
    num_constraints = 0
    try:
        proto = cpm.Proto()
        if hasattr(proto, "constraints"):
            num_constraints = len(proto.constraints)
    except Exception:
        pass

    num_vars = 0
    try:
        proto = cpm.Proto()
        if hasattr(proto, "variables"):
            num_vars = len(proto.variables)
    except Exception:
        pass

    return {
        "solver_status": status_name,
        "makespan_s": makespan_s,
        "solver_wall_time_s": solver.WallTime(),
        "best_objective_bound_s": best_bound_s,
        "optimality_gap_percent": gap,
        "num_booleans": solver.NumBooleans() if status in {cp.OPTIMAL, cp.FEASIBLE} else 0,
        "num_branches": solver.NumBranches() if status in {cp.OPTIMAL, cp.FEASIBLE} else 0,
        "num_conflicts": solver.NumConflicts() if status in {cp.OPTIMAL, cp.FEASIBLE} else 0,
        "variable_count": num_vars,
        "constraint_count": num_constraints,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()
    all_results: list[GapResult] = []

    for case_def in CASE_DEFS:
        limit_list = case_def["time_limits_s"]
        if args.skip_long:
            limit_list = [tl for tl in limit_list if tl < 300]

        print(f"\n{'='*60}")
        print(f"CASE: {case_def['label']} ({case_def['scale']})")
        print(f"  File: {case_def['path']}")
        print(f"  Time limits: {limit_list}")

        model = load_system_model(case_def["path"])
        all_rows = rows_from_recipes(RecipeGenerator(model).generate_all())
        pareto_rows = pareto_prune(all_rows).kept_rows
        target_count = len({str(row["target_id"]) for row in all_rows})

        print(f"  Targets: {target_count}")
        print(f"  Recipes (before pareto): {len(all_rows)}")
        print(f"  Recipes (after pareto): {len(pareto_rows)}")

        for time_limit in limit_list:
            label = f"{case_def['label']}_tl{time_limit}s"
            print(f"  --- Running CP-SAT with {time_limit}s time limit ---")

            try:
                info = solve_with_gap_info(
                    model,
                    pareto_rows,
                    time_limit_s=time_limit,
                    workers=args.workers,
                )
            except Exception as exc:
                print(f"    FAILED: {exc}")
                result = GapResult(
                    case_id=model.case_id,
                    scale=case_def["scale"],
                    label=case_def["label"],
                    target_count=target_count,
                    variable_count=0,
                    constraint_count=0,
                    recipe_count=len(all_rows),
                    pareto_recipe_count=len(pareto_rows),
                    time_limit_s=time_limit,
                    solver_status="FAILED",
                    makespan_s=0.0,
                    solver_wall_time_s=0.0,
                    notes=str(exc),
                )
                all_results.append(result)
                continue

            status = info["solver_status"]
            makespan = info["makespan_s"] or 0.0
            wall = info["solver_wall_time_s"]
            bound = info["best_objective_bound_s"]
            gap = info["optimality_gap_percent"]

            notes = ""
            if status == "OPTIMAL":
                notes = "Proven optimal"
            elif status == "FEASIBLE":
                if gap is not None:
                    notes = f"Within {gap:.2f}% of optimum"
                else:
                    notes = "Feasible; no dual bound available"
            elif status == "UNKNOWN":
                notes = "No feasible solution found within time limit"

            print(
                f"    status={status}  makespan={makespan:.6f}s  "
                f"wall={wall:.2f}s  "
                + (f"bound={bound:.6f}s  gap={gap:.4f}%" if gap is not None else "bound=N/A")
            )

            result = GapResult(
                case_id=model.case_id,
                scale=case_def["scale"],
                label=case_def["label"],
                target_count=target_count,
                variable_count=info.get("variable_count", 0),
                constraint_count=info.get("constraint_count", 0),
                recipe_count=len(all_rows),
                pareto_recipe_count=len(pareto_rows),
                time_limit_s=time_limit,
                solver_status=status,
                makespan_s=makespan,
                solver_wall_time_s=wall,
                best_objective_bound_s=bound,
                optimality_gap_percent=gap,
                num_booleans=info.get("num_booleans", 0),
                num_branches=info.get("num_branches", 0),
                num_conflicts=info.get("num_conflicts", 0),
                notes=notes,
            )
            all_results.append(result)

    # ---- Save CSV ----
    rows_dicts = [
        {
            "case_id": r.case_id,
            "scale": r.scale,
            "target_count": r.target_count,
            "variable_count": r.variable_count,
            "constraint_count": r.constraint_count,
            "recipe_count": r.recipe_count,
            "pareto_recipe_count": r.pareto_recipe_count,
            "time_limit_s": r.time_limit_s,
            "solver_status": r.solver_status,
            "makespan_s": r.makespan_s,
            "solver_wall_time_s": r.solver_wall_time_s,
            "best_objective_bound_s": r.best_objective_bound_s if r.best_objective_bound_s is not None else "",
            "optimality_gap_percent": r.optimality_gap_percent if r.optimality_gap_percent is not None else "",
            "num_booleans": r.num_booleans,
            "num_branches": r.num_branches,
            "num_conflicts": r.num_conflicts,
            "notes": r.notes,
        }
        for r in all_results
    ]

    csv_path = Path(args.output_csv)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows_dicts)
    print(f"\nCSV saved to: {csv_path}")

    # ---- Generate Report ----
    report_path = Path(args.output_report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    write_report(all_results, report_path)
    print(f"Report saved to: {report_path}")

    # ---- Generate Figure ----
    fig_path = Path(args.output_figure)
    fig_path.parent.mkdir(parents=True, exist_ok=True)
    generate_figure(all_results, fig_path)
    print(f"Figure saved to: {fig_path}")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def write_report(results: list[GapResult], output_path: Path) -> None:
    lines = [
        "# CP-SAT Optimality Gap Analysis",
        "",
        "## Summary",
        "",
        "This report documents how close our CP-SAT scheduling solutions are to",
        "the true optimal makespan across three representative 3D-stack cases",
        "(small, medium, large), using increasing solver time limits.",
        "",
        "The *optimality gap* is defined as:",
        "",
        "```",
        "gap (%) = (makespan - lower_bound) / makespan * 100",
        "```",
        "",
        "When the solver proves optimality (`OPTIMAL`), the gap is 0%.",
        "When the solver finds a feasible solution but cannot prove optimality",
        "(`FEASIBLE`), the gap estimates how far the solution is from the",
        "theoretical lower bound.",
        "",
    ]

    # Per-case summary
    for scale in ["small", "medium", "large"]:
        subset = [r for r in results if r.scale == scale]
        if not subset:
            continue
        label = subset[0].label
        targets = subset[0].target_count
        recipes = subset[0].pareto_recipe_count
        lines.extend([
            f"## {scale.capitalize()} Case: {label}",
            "",
            f"- Targets: {targets}",
            f"- Recipes (after Pareto pruning): {recipes}",
            "",
            "| Time Limit (s) | Status | Makespan (s) | Wall Time (s) | Lower Bound (s) | Gap (%) | Booleans | Branches |",
            "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ])
        for r in subset:
            bound_str = f"{r.best_objective_bound_s:.6f}" if r.best_objective_bound_s is not None else "N/A"
            gap_str = f"{r.optimality_gap_percent:.4f}" if r.optimality_gap_percent is not None else "N/A"
            lines.append(
                f"| {r.time_limit_s} | {r.solver_status} | {r.makespan_s:.6f} | "
                f"{r.solver_wall_time_s:.2f} | {bound_str} | {gap_str} | "
                f"{r.num_booleans} | {r.num_branches} |"
            )
        lines.append("")

    # Cross-case comparison
    lines.extend([
        "## Cross-Case Comparison",
        "",
        "For each case, the best makespan achieved and its corresponding gap:",
        "",
        "| Case | Scale | Targets | Best Makespan (s) | Time Limit (s) | Status | Gap (%) |",
        "| --- | --- | ---: | ---: | ---: | --- | ---: |",
    ])
    case_bests: dict[str, GapResult] = {}
    for r in results:
        if r.solver_status in {"OPTIMAL", "FEASIBLE"}:
            key = r.scale
            if key not in case_bests or r.makespan_s < case_bests[key].makespan_s:
                case_bests[key] = r
    for scale in ["small", "medium", "large"]:
        if scale in case_bests:
            r = case_bests[scale]
            gap_str = f"{r.optimality_gap_percent:.4f}" if r.optimality_gap_percent is not None else "N/A"
            lines.append(
                f"| {r.label} | {scale} | {r.target_count} | {r.makespan_s:.6f} | "
                f"{r.time_limit_s} | {r.solver_status} | {gap_str} |"
            )

    lines.extend([
        "",
        "## Key Observations",
        "",
        "- The optimality gap shrinks as solver time increases, demonstrating that CP-SAT",
        "  incrementally tightens the dual bound.",
        "- Even when optimality is not proven, the gap quantifies the maximum possible",
        "  improvement remaining.",
        "- For cases where `BestObjectiveBound()` returns 0 or is unavailable, the gap",
        "  cannot be computed; these correspond to `UNKNOWN` or early `FEASIBLE` states",
        "  where the solver has not yet built a useful dual bound.",
        "",
    ])

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Figure
# ---------------------------------------------------------------------------

def generate_figure(results: list[GapResult], output_path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    # Style settings consistent with paper figures
    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 11,
        "legend.fontsize": 9,
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
    })

    # Map scale to display names and colors
    scale_config = {
        "small": {"label": "Small (d695)", "color": "#2E86AB", "marker": "o"},
        "medium": {"label": "Medium (p22810)", "color": "#A23B72", "marker": "s"},
        "large": {"label": "Large (p34392)", "color": "#F18F01", "marker": "D"},
    }

    # Build data: for each (case, time_limit) get gap
    # Filter to only rows with known gap
    with_gap = [r for r in results if r.optimality_gap_percent is not None]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # ---- Subplot 1: Makespan vs Time Limit ----
    ax1 = axes[0]
    for scale in ["small", "medium", "large"]:
        subset = [r for r in results if r.scale == scale and r.makespan_s > 0]
        if not subset:
            continue
        subset.sort(key=lambda r: r.time_limit_s)
        cfg = scale_config[scale]
        times = [r.time_limit_s for r in subset]
        makespans = [r.makespan_s for r in subset]

        # Solid line for all points, mark OPTIMAL points differently
        ax1.plot(times, makespans, color=cfg["color"], marker=cfg["marker"],
                 linestyle="-", linewidth=1.5, markersize=7, label=cfg["label"],
                 markerfacecolor="white", markeredgewidth=1.5)

        # Highlight OPTIMAL points with filled star markers
        optimal_t = [r.time_limit_s for r in subset if r.solver_status == "OPTIMAL"]
        optimal_m = [r.makespan_s for r in subset if r.solver_status == "OPTIMAL"]
        if optimal_t:
            ax1.scatter(optimal_t, optimal_m, color=cfg["color"], marker="*",
                        s=150, zorder=5, edgecolors="black", linewidth=0.5,
                        label="_nolegend_")

    ax1.set_xlabel("Solver Time Limit (s)")
    ax1.set_ylabel("Makespan (s)")
    ax1.set_title("Makespan vs Solver Time Limit")
    ax1.legend(loc="upper right", framealpha=0.9)
    ax1.grid(True, alpha=0.3)
    ax1.set_xscale("log")

    # ---- Subplot 2: Optimality Gap vs Time Limit ----
    ax2 = axes[1]
    for scale in ["small", "medium", "large"]:
        subset = [r for r in with_gap if r.scale == scale]
        if not subset:
            continue
        subset.sort(key=lambda r: r.time_limit_s)
        cfg = scale_config[scale]
        times = [r.time_limit_s for r in subset]
        gaps = [r.optimality_gap_percent for r in subset]

        ax2.plot(times, gaps, color=cfg["color"], marker=cfg["marker"],
                 linestyle="--", linewidth=1.5, markersize=7, label=cfg["label"],
                 markerfacecolor="white", markeredgewidth=1.5)

        # Mark zero-gap (proven optimal)
        zero_t = [r.time_limit_s for r in subset if r.optimality_gap_percent == 0.0]
        if zero_t:
            ax2.scatter(zero_t, [0]*len(zero_t), color=cfg["color"], marker="*",
                        s=150, zorder=5, edgecolors="black", linewidth=0.5,
                        label="_nolegend_")

    ax2.set_xlabel("Solver Time Limit (s)")
    ax2.set_ylabel("Optimality Gap (%)")
    ax2.set_title("Optimality Gap vs Solver Time Limit")
    ax2.legend(loc="upper right", framealpha=0.9)
    ax2.grid(True, alpha=0.3)
    ax2.set_xscale("log")

    # Add annotation about gap interpretation
    ax2.annotate(
        "gap = (makespan - lower_bound) / makespan",
        xy=(0.02, 0.96), xycoords="axes fraction",
        fontsize=8, fontstyle="italic", color="gray",
        ha="left", va="top",
    )

    fig.suptitle("CP-SAT Optimality Gap Analysis for IEEE 1838 Test Scheduling",
                 fontweight="bold", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.95])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path)
    plt.close(fig)


if __name__ == "__main__":
    main()
