"""Generate revised Figure 6 -- Resource Utilization Timeline Comparison.

This script produces a 2-panel stacked area chart that explains WHY joint scheduling
achieves gain -- by comparing resource utilization between fixed-fastest and joint
CP-SAT scheduling for a representative 3D stack pressure case.

Top panel: Fixed-fastest -- shows FPP lanes idle while BIST serialises.
Bottom panel: Joint CP-SAT -- shows FPP lanes utilised in parallel with BIST.

Output: results/figures/revised/fig6_resource_occupancy.png
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np

from src.model import load_system_model
from src.recipes import RecipeGenerator, pareto_prune, rows_from_recipes
from src.schedulers import (
    ScheduleResult,
    ScheduledPhase,
    greedy_schedule,
    solve_cpsat_schedule,
    write_schedule_csv,
)


# ---------------------------------------------------------------------------
# Default configuration
# ---------------------------------------------------------------------------

DEFAULT_CASE = "configs/cases/m21/m21_pressure_small_d695_3d_stack.json"
DEFAULT_TIME_LIMIT_S = 120.0

# Colour palette
COLOR_FPP = "#5b9bd5"       # blue for FPP lanes
COLOR_BIST = "#ed7d31"      # orange for shared BIST engine
COLOR_SERIAL = "#70ad47"    # green for PTAP/STAP serial
COLOR_CAPACITY_LINE = "#333333"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate revised Figure 6 occupancy chart.")
    parser.add_argument("--case", default=DEFAULT_CASE, help="Pressure case JSON to use.")
    parser.add_argument(
        "--time-limit-s", type=float, default=DEFAULT_TIME_LIMIT_S,
        help="CP-SAT solver time limit in seconds.",
    )
    parser.add_argument("--figure-dir", default="results/figures/revised")
    parser.add_argument("--schedule-dir", default="results/schedules/revised")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Schedule building (reuse existing CSVs when present)
# ---------------------------------------------------------------------------


def _fastest_recipe_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Select the individually fastest recipe per target (tie-break by power and id)."""
    selected: dict[str, tuple[tuple, dict[str, object]]] = {}
    for row in rows:
        target_id = str(row["target_id"])
        key = (
            float(row.get("total_time_s", 0.0)),
            float(row.get("peak_power_w", 0.0)),
            str(row["recipe_id"]),
        )
        if target_id not in selected or key < selected[target_id][0]:
            selected[target_id] = (key, row)
    return [item[1] for item in selected.values()]


def build_schedules(case_path: str, time_limit_s: float) -> dict[str, ScheduleResult]:
    """Build fixed-fastest and joint CP-SAT schedules for the given pressure case."""
    model = load_system_model(case_path)
    all_rows = rows_from_recipes(RecipeGenerator(model).generate_all())
    pareto_rows = pareto_prune(all_rows).kept_rows

    print(f"case={model.case_id}  recipes={len(all_rows)}  pareto={len(pareto_rows)}")

    print("Building fixed-fastest schedule ...")
    fixed = greedy_schedule(model, _fastest_recipe_rows(pareto_rows))
    print(f"  fixed makespan = {fixed.makespan_s * 1e6:.2f} us")

    print("Building joint CP-SAT schedule ...")
    joint, info = solve_cpsat_schedule(model, pareto_rows, time_limit_s=time_limit_s)
    b_count = sum(1 for r in joint.selected_rows if r.get("recipe_type") == "B")
    f_count = sum(1 for r in joint.selected_rows if r.get("recipe_type") == "F")
    gain = (fixed.makespan_s - joint.makespan_s) / fixed.makespan_s * 100.0
    print(f"  joint makespan = {joint.makespan_s * 1e6:.2f} us  "
          f"b_count={b_count}  f_count={f_count}  "
          f"gain={gain:.1f}%  solver={info.status_name}")

    return {"fixed_fastest": fixed, "m5_cpsat": joint}


# ---------------------------------------------------------------------------
# Occupancy computation
# ---------------------------------------------------------------------------

EPSILON = 1e-12


def compute_occupancy_curves(
    phases: list[ScheduledPhase],
    total_fpp_lanes: int,
) -> dict[str, Any]:
    """Compute resource occupancy timeseries from a schedule's phase list.

    Returns a dict with keys:
      time_us: list[float]       -- boundary timestamps in microseconds
      fpp_lanes: list[int]       -- concurrent FPP lanes at each interval
      bist_busy: list[float]     -- 0.0 or 1.0 for shared BIST engine occupancy
      serial_busy: list[float]   -- 0.0 or 1.0 for PTAP/STAP serial path occupancy
        (Note: serial busy is stretched slightly wider visually so it does not
         disappear into the zero line -- it is drawn as a thin ribbon offset
         above a dummy zero base.)
    """
    # Collect all unique time boundaries
    boundaries_set: set[float] = {0.0}
    for phase in phases:
        boundaries_set.add(phase.start_s)
        boundaries_set.add(phase.end_s)
    boundaries = sorted(boundaries_set)

    time_us: list[float] = []
    fpp_lanes: list[float] = []
    bist_busy: list[float] = []
    serial_busy: list[float] = []

    for i in range(len(boundaries) - 1):
        t0 = boundaries[i]
        t1 = boundaries[i + 1]
        if t1 - t0 <= EPSILON:
            continue

        mid = (t0 + t1) / 2.0
        # Active phases at midpoint of this interval
        active = [
            p for p in phases
            if p.start_s <= mid < p.end_s - EPSILON
        ]

        lanes = sum(p.fpp_lanes_required for p in active)
        bist = 1.0 if any(p.phase_name == "LOCAL_BIST_RUN" for p in active) else 0.0
        # serial_required means the phase needs exclusive PTAP/STAP access
        serial = 1.0 if any(p.serial_required for p in active) else 0.0

        time_us.append(t0 * 1e6)
        fpp_lanes.append(float(lanes))
        bist_busy.append(bist)
        serial_busy.append(serial)

    # Append the final boundary so the last interval has a closing edge
    final_t = boundaries[-1] * 1e6
    time_us.append(final_t)
    fpp_lanes.append(0.0)
    bist_busy.append(0.0)
    serial_busy.append(0.0)

    return {
        "time_us": time_us,
        "fpp_lanes": np.array(fpp_lanes, dtype=float),
        "bist_busy": np.array(bist_busy, dtype=float),
        "serial_busy": np.array(serial_busy, dtype=float),
        "makespan_us": max(time_us),
    }


# ---------------------------------------------------------------------------
# Panel drawing
# ---------------------------------------------------------------------------


def draw_occupancy_panel(
    ax: Any,
    curves: dict[str, Any],
    total_fpp_lanes: int,
    title: str,
    gain_pct: float | None = None,
) -> None:
    """Draw a single stacked-area panel of resource occupancy over time.

    The stack shows:
      - FPP lanes used (blue filled area)
      - BIST engine busy (orange filled area, narrow strip)
      - Serial path busy (green filled area, narrow strip above BIST)

    A dashed horizontal line marks the total FPP lane capacity.
    """
    t = curves["time_us"]
    fpp = curves["fpp_lanes"]
    bist = curves["bist_busy"]
    serial = curves["serial_busy"]

    # We draw serial and bist as thin "ribbons" that sit on top of the FPP area.
    # To make them visible, we give each a fixed visual height (in FPP lane units
    # on the y-axis) and then layer them.

    # FPP lanes: fill from y=0 up to fpp_lanes
    ax.fill_between(
        t, 0, fpp,
        step="post",
        facecolor=COLOR_FPP,
        alpha=0.55,
        edgecolor=COLOR_FPP,
        linewidth=0.3,
        label="FPP lanes used",
    )

    # BIST busy: fill a narrow ribbon above the FPP area during BIST-active intervals
    # Position the BIST ribbon just above the FPP curve
    bist_height = total_fpp_lanes * 0.12  # thin ribbon proportional to total capacity
    bist_base = fpp
    bist_top = bist_base + bist * bist_height
    ax.fill_between(
        t, bist_base, bist_top,
        step="post",
        facecolor=COLOR_BIST,
        alpha=0.72,
        edgecolor=COLOR_BIST,
        linewidth=0.3,
        label="BIST engine busy",
    )

    # Serial busy: fill another thin ribbon above BIST
    serial_height = total_fpp_lanes * 0.10
    serial_base = bist_top
    serial_top = serial_base + serial * serial_height
    ax.fill_between(
        t, serial_base, serial_top,
        step="post",
        facecolor=COLOR_SERIAL,
        alpha=0.65,
        edgecolor=COLOR_SERIAL,
        linewidth=0.3,
        label="Serial path busy",
    )

    # Capacity line
    ax.axhline(
        y=total_fpp_lanes, color=COLOR_CAPACITY_LINE,
        linestyle="--", linewidth=1.2, alpha=0.7,
        label=f"FPP capacity ({total_fpp_lanes} lanes)",
    )

    # Axis decoration
    ax.set_title(title, loc="left", fontsize=11, fontweight="bold")
    ax.set_ylabel("Lanes / Busy", fontsize=9)
    ax.set_ylim(bottom=-0.5, top=total_fpp_lanes * 1.35)
    ax.set_xlim(left=0, right=curves["makespan_us"] * 1.03)
    ax.grid(axis="y", alpha=0.20)
    ax.tick_params(axis="both", labelsize=8)

    # Legend at top-left inside the axes
    ax.legend(
        loc="upper left", fontsize=7.5,
        frameon=True, framealpha=0.85, edgecolor="#cccccc",
        ncol=2,
    )

    if gain_pct is not None:
        ax.text(
            0.985, 0.94, f"Gain: {gain_pct:.1f}%",
            transform=ax.transAxes,
            ha="right", va="top", fontsize=13, fontweight="bold",
            color="#222222",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                      edgecolor="#aaaaaa", alpha=0.85),
        )


# ---------------------------------------------------------------------------
# Main figure assembly
# ---------------------------------------------------------------------------


def plot_figure6_occupancy(
    fixed_curves: dict[str, Any],
    joint_curves: dict[str, Any],
    total_fpp_lanes: int,
    gain_pct: float,
    figure_dir: Path,
) -> Path:
    """Create the 2-panel Fig. 6 occupancy chart and save to disk."""
    fig, axes = plt.subplots(
        2, 1, figsize=(16, 9),
        sharex=True, dpi=200,
    )

    # ---- Top panel: Fixed-fastest ----
    draw_occupancy_panel(
        axes[0], fixed_curves, total_fpp_lanes,
        "Fixed-fastest: Resources Underutilised",
    )

    # annotation: BIST bottleneck
    ann_t = fixed_curves["makespan_us"] * 0.50
    # find y position near BIST ribbon top at that time
    idx = np.searchsorted(fixed_curves["time_us"], ann_t)
    if idx >= len(fixed_curves["fpp_lanes"]):
        idx = len(fixed_curves["fpp_lanes"]) - 1
    fpp_at = float(fixed_curves["fpp_lanes"][idx])
    bist_at = float(fixed_curves["bist_busy"][idx])
    ann_y = fpp_at + bist_at * total_fpp_lanes * 0.12 + 0.5
    axes[0].annotate(
        "Shared BIST serialises\nall local execution",
        xy=(ann_t, ann_y), xytext=(ann_t + fixed_curves["makespan_us"] * 0.18, ann_y + 1.8),
        fontsize=9, color="#b22222",
        arrowprops=dict(arrowstyle="->", color="#b22222", lw=1.2, connectionstyle="arc3,rad=0.2"),
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#fff5f5", edgecolor="#cc8888", alpha=0.9),
    )

    # annotation: FPP idle
    ann_t2 = fixed_curves["makespan_us"] * 0.30
    axes[0].annotate(
        "FPP lanes idle\nthroughout",
        xy=(ann_t2, total_fpp_lanes * 0.15),
        xytext=(ann_t2 + fixed_curves["makespan_us"] * 0.08, total_fpp_lanes * 0.55),
        fontsize=9, color="#1a5276",
        arrowprops=dict(arrowstyle="->", color="#1a5276", lw=1.2, connectionstyle="arc3,rad=-0.3"),
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#f0f8ff", edgecolor="#88aacc", alpha=0.9),
    )

    # ---- Bottom panel: Joint CP-SAT ----
    draw_occupancy_panel(
        axes[1], joint_curves, total_fpp_lanes,
        "Joint CP-SAT: Resources Balanced",
        gain_pct=gain_pct,
    )

    # annotation: FPP active alongside BIST
    ann_joint_t = joint_curves["makespan_us"] * 0.25
    idx_j = np.searchsorted(joint_curves["time_us"], ann_joint_t)
    if idx_j >= len(joint_curves["fpp_lanes"]):
        idx_j = len(joint_curves["fpp_lanes"]) - 1
    fpp_j = float(joint_curves["fpp_lanes"][idx_j])
    axes[1].annotate(
        "FPP lanes utilised\nconcurrently with BIST",
        xy=(ann_joint_t, fpp_j + 2.0),
        xytext=(ann_joint_t + joint_curves["makespan_us"] * 0.12, fpp_j + 4.5),
        fontsize=9, color="#1b6e1b",
        arrowprops=dict(arrowstyle="->", color="#1b6e1b", lw=1.2, connectionstyle="arc3,rad=-0.2"),
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#f5fff5", edgecolor="#88cc88", alpha=0.9),
    )

    # annotation: shorter makespan
    ann_joint_t2 = joint_curves["makespan_us"] * 0.82
    axes[1].annotate(
        f"Shorter makespan\n({joint_curves['makespan_us']:.0f} us)",
        xy=(joint_curves["makespan_us"], 0.3),
        xytext=(ann_joint_t2, 3.5),
        fontsize=9, color="#222222",
        arrowprops=dict(arrowstyle="->", color="#666666", lw=1.2, connectionstyle="arc3,rad=0.3"),
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="#aaaaaa", alpha=0.85),
    )

    # ---- shared x-axis ----
    axes[1].set_xlabel("Time (us)", fontsize=10)

    fig.suptitle(
        "Fig. 6  Resource Utilisation Timeline: Why Joint Scheduling Achieves Gain",
        y=0.99, fontsize=13, fontweight="bold",
    )
    fig.tight_layout(rect=[0.0, 0.0, 1.0, 0.97])

    out_path = figure_dir / "fig6_resource_occupancy.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)

    return out_path


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    args = parse_args()
    configure_matplotlib()

    figure_dir = Path(args.figure_dir)
    schedule_dir = Path(args.schedule_dir)
    figure_dir.mkdir(parents=True, exist_ok=True)
    schedule_dir.mkdir(parents=True, exist_ok=True)

    # Build schedules
    schedules = build_schedules(args.case, time_limit_s=args.time_limit_s)

    fixed = schedules["fixed_fastest"]
    joint = schedules["m5_cpsat"]

    # Write schedule CSVs for reference
    model = load_system_model(args.case)
    fixed_path = schedule_dir / f"{model.case_id}__fixed_fastest_schedule.csv"
    joint_path = schedule_dir / f"{model.case_id}__m5_cpsat_schedule.csv"
    write_schedule_csv(fixed, fixed_path)
    write_schedule_csv(joint, joint_path)
    print(f"Schedule CSVs written to {schedule_dir}")

    total_fpp_lanes = int(model.resource_limits.get("total_fpp_lanes", 8))
    print(f"total_fpp_lanes={total_fpp_lanes}")

    # Compute occupancy curves
    fixed_curves = compute_occupancy_curves(fixed.phases, total_fpp_lanes)
    joint_curves = compute_occupancy_curves(joint.phases, total_fpp_lanes)

    gain_pct = (fixed.makespan_s - joint.makespan_s) / fixed.makespan_s * 100.0

    print(f"Fixed makespan: {fixed_curves['makespan_us']:.1f} us")
    print(f"Joint makespan: {joint_curves['makespan_us']:.1f} us")
    print(f"Gain: {gain_pct:.1f}%")

    # Diagnostic: peak FPP lane usage
    fpp_peak_fixed = float(np.max(fixed_curves["fpp_lanes"]))
    fpp_peak_joint = float(np.max(joint_curves["fpp_lanes"]))
    fpp_avg_fixed = float(np.mean(fixed_curves["fpp_lanes"]))
    fpp_avg_joint = float(np.mean(joint_curves["fpp_lanes"]))
    bist_frac_fixed = float(np.mean(fixed_curves["bist_busy"]))
    bist_frac_joint = float(np.mean(joint_curves["bist_busy"]))
    ser_frac_fixed = float(np.mean(fixed_curves["serial_busy"]))
    ser_frac_joint = float(np.mean(joint_curves["serial_busy"]))

    print(f"FPP peak (fixed/joint): {fpp_peak_fixed:.0f} / {fpp_peak_joint:.0f} lanes")
    print(f"FPP avg  (fixed/joint): {fpp_avg_fixed:.2f} / {fpp_avg_joint:.2f} lanes")
    print(f"BIST busy frac (fixed/joint): {bist_frac_fixed:.3f} / {bist_frac_joint:.3f}")
    print(f"Serial busy frac (fixed/joint): {ser_frac_fixed:.3f} / {ser_frac_joint:.3f}")

    out_path = plot_figure6_occupancy(
        fixed_curves, joint_curves,
        total_fpp_lanes, gain_pct,
        figure_dir,
    )
    print(f"Figure saved to {out_path}")


def configure_matplotlib() -> None:
    available = {font.name for font in fm.fontManager.ttflist}
    candidates = [
        "Microsoft YaHei", "SimHei", "Noto Sans CJK SC",
        "Arial Unicode MS", "DejaVu Sans",
    ]
    chosen = next((font for font in candidates if font in available), "DejaVu Sans")
    plt.rcParams.update({
        "font.family": chosen,
        "axes.unicode_minus": False,
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
    })


if __name__ == "__main__":
    main()
