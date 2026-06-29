"""Generate revised Figure 5 -- Fixed-fastest vs Joint Scheduling Gantt Comparison.

This script produces a 2-panel Gantt chart comparing fixed-fastest scheduling (every
target chooses its individually fastest BIST path) with joint scheduling (M5 CP-SAT
mixes BIST and FPP paths) for a representative 3D stack pressure case.

Target: m21_pressure_small_d695_3d_stack (best 3D stack gain: 46.67% via M5 CP-SAT).

Output: results/figures/revised/fig5_gantt_fixed_vs_joint.png
"""

from __future__ import annotations

import argparse
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

from src.model import load_system_model
from src.recipes import RecipeGenerator, pareto_prune, rows_from_recipes
from src.schedulers import ScheduleResult, ScheduledPhase, greedy_schedule, solve_cpsat_schedule, write_schedule_csv


# ---------------------------------------------------------------------------
# Default configuration
# ---------------------------------------------------------------------------

DEFAULT_CASE = "configs/cases/m21/m21_pressure_small_d695_3d_stack.json"
DEFAULT_TIME_LIMIT_S = 120.0

# Three resource rows (top to bottom on the y-axis)
ROW_SHARED_BIST = "Shared BIST\nengine"
ROW_FPP_LANES = "FPP Lanes"
ROW_PTAP_STAP = "PTAP/STAP\nserial config"
RESOURCE_ROWS = [ROW_SHARED_BIST, ROW_FPP_LANES, ROW_PTAP_STAP]

# Color palette
COLOR_BIST = "#59a14f"
COLOR_FPP = "#f28e2b"
COLOR_SERIAL = "#8d62c8"
COLOR_TARGET_BG = "#d0d0d0"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate revised Figure 5 Gantt chart.")
    parser.add_argument("--case", default=DEFAULT_CASE, help="Pressure case JSON to use.")
    parser.add_argument("--time-limit-s", type=float, default=DEFAULT_TIME_LIMIT_S,
                        help="CP-SAT solver time limit in seconds.")
    parser.add_argument("--figure-dir", default="results/figures/revised")
    parser.add_argument("--schedule-dir", default="results/schedules/revised")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Schedule generation
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
    print(f"  fixed makespan = {fixed.makespan_s * 1e6:.2f} us  b_count={sum(1 for r in fixed.selected_rows if r.get('recipe_type') == 'B')}")

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
# Drawing helpers
# ---------------------------------------------------------------------------


def compact_target(target_id: str) -> str:
    """Shorten a target id to a human-readable label (e.g. 'm21_mem00_die0' -> 'die0')."""
    parts = target_id.split("_")
    for i, part in enumerate(parts):
        if part.startswith("die") and len(part) >= 4:
            return "_".join(parts[i:])
    return target_id


def target_intervals(phases: list[ScheduledPhase]) -> dict[str, tuple[float, float]]:
    """Return {target_id: (min_start_s, max_end_s)} per target from its phases."""
    intervals: dict[str, tuple[float, float]] = {}
    for target_id in sorted({p.target_id for p in phases}):
        group = [p for p in phases if p.target_id == target_id]
        intervals[target_id] = (min(p.start_s for p in group), max(p.end_s for p in group))
    return intervals


def draw_bar(ax: Any, y: float, start_us: float, width_us: float, color: str,
             label: str = "", alpha: float = 0.86) -> None:
    """Draw a single horizontal bar with optional centred text label."""
    ax.barh(y, width_us, left=start_us, height=0.58, color=color,
            edgecolor="#333333", linewidth=0.45, alpha=alpha)
    if label and width_us > 0:
        ax.text(start_us + width_us / 2.0, y, label,
                ha="center", va="center", fontsize=6.5, clip_on=True)


# ---------------------------------------------------------------------------
# Gantt panel drawing
# ---------------------------------------------------------------------------


def draw_gantt_panel(ax: Any, schedule: ScheduleResult, title: str,
                     xmax_us: float, gain_pct: float | None = None) -> None:
    """Draw a single 3-row Gantt panel for one schedule.

    Parameters
    ----------
    ax : matplotlib Axes
        Axis to draw into.
    schedule : ScheduleResult
        The schedule whose phases should be visualised.
    title : str
        Left-aligned panel title.
    xmax_us : float
        Upper bound for the x-axis (microseconds).
    gain_pct : float or None
        If given, a large gain annotation is placed at the top-right of the panel.
    """
    y_map = {name: idx for idx, name in enumerate(RESOURCE_ROWS)}
    min_bar_width = xmax_us * 0.0008  # ensure very short phases are still visible

    # ---- per-target background bars ----
    for target_id, (t0, t1) in target_intervals(schedule.phases).items():
        draw_bar(ax, -0.5, t0 * 1e6, (t1 - t0) * 1e6, COLOR_TARGET_BG,
                 compact_target(target_id), alpha=0.25)

    # ---- phase bars ----
    for phase in sorted(schedule.phases, key=lambda p: (p.start_s, p.end_s, p.target_id)):
        start_us = phase.start_s * 1e6
        width_us = max((phase.end_s - phase.start_s) * 1e6, min_bar_width)

        if phase.phase_name == "LOCAL_BIST_RUN":
            draw_bar(ax, y_map[ROW_SHARED_BIST], start_us, width_us,
                     COLOR_BIST, compact_target(phase.target_id))

        if phase.fpp_lanes_required > 0:
            label = f"{compact_target(phase.target_id)} L{phase.fpp_lanes_required}"
            draw_bar(ax, y_map[ROW_FPP_LANES], start_us, width_us,
                     COLOR_FPP, label)

        if phase.serial_required:
            phase_label = "cfg" if "CONFIG" in (phase.phase_name or "") else "cfg/read"
            draw_bar(ax, y_map[ROW_PTAP_STAP], start_us, width_us,
                     COLOR_SERIAL, phase_label)

    # ---- axis decoration ----
    ax.set_title(title, loc="left", fontsize=11)
    ax.set_yticks(range(len(RESOURCE_ROWS)))
    ax.set_yticklabels(RESOURCE_ROWS, fontsize=9)
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.22)
    ax.set_xlim(0, xmax_us * 1.03)
    ax.tick_params(axis="x", labelsize=8)

    if gain_pct is not None:
        ax.text(0.985, 0.96, f"Gain: {gain_pct:.1f}%", transform=ax.transAxes,
                ha="right", va="top", fontsize=14, fontweight="bold",
                color="#222222",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                          edgecolor="#aaaaaa", alpha=0.85))


# ---------------------------------------------------------------------------
# Main figure assembly
# ---------------------------------------------------------------------------


def plot_figure5_gantt(
    fixed: ScheduleResult,
    joint: ScheduleResult,
    fixed_schedule_path: Path,
    joint_schedule_path: Path,
    figure_dir: Path,
    time_limit_s: float,
) -> Path:
    """Create the 2-panel Fig.5 Gantt chart and save it to disk.

    Returns the output path so the caller can print it.
    """
    xmax_us = max(fixed.makespan_s, joint.makespan_s) * 1e6
    gain = (fixed.makespan_s - joint.makespan_s) / fixed.makespan_s * 100.0

    fig, axes = plt.subplots(2, 1, figsize=(16, 9), sharex=True, dpi=200)

    # ---- Top panel: Fixed-fastest ----
    draw_gantt_panel(axes[0], fixed,
                     "Fixed-fastest: every target independently chooses the fastest path (BIST)",
                     xmax_us)

    # Annotate bottleneck
    ann_x = xmax_us * 0.55
    ann_y = 0.12  # near the Shared BIST row (row 0, but in data coords ~0.12)
    axes[0].annotate(
        "Shared BIST bottleneck\nserialises all local execution",
        xy=(ann_x, ann_y), xytext=(ann_x + xmax_us * 0.15, ann_y - 0.35),
        fontsize=9, color="#b22222",
        arrowprops=dict(arrowstyle="->", color="#b22222", lw=1.2, connectionstyle="arc3,rad=0.2"),
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#fff5f5", edgecolor="#cc8888", alpha=0.9),
    )

    # ---- Bottom panel: Joint CP-SAT ----
    draw_gantt_panel(axes[1], joint,
                     "Joint scheduling (M5 CP-SAT): optimiser mixes BIST + FPP paths under shared-resource constraints",
                     xmax_us, gain_pct=gain)

    # Annotate parallel escape
    ann_x2 = xmax_us * 0.32
    ann_y2 = 1.08  # near the FPP Lanes row (row 1, inverted so ~1.08)
    axes[1].annotate(
        "FPP parallel escape\npaths are utilised",
        xy=(ann_x2, ann_y2), xytext=(ann_x2 + xmax_us * 0.18, ann_y2 + 0.45),
        fontsize=9, color="#1b6e1b",
        arrowprops=dict(arrowstyle="->", color="#1b6e1b", lw=1.2, connectionstyle="arc3,rad=-0.2"),
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#f5fff5", edgecolor="#88cc88", alpha=0.9),
    )

    # ---- shared x-axis ----
    axes[1].set_xlabel("Time (us)", fontsize=10)

    fig.suptitle("Fig. 5  Fixed-Path vs Joint Scheduling: 3D Stack Pressure Case",
                 y=0.985, fontsize=13, fontweight="bold")
    fig.tight_layout(rect=[0.0, 0.0, 1.0, 0.97])

    out_path = figure_dir / "fig5_gantt_fixed_vs_joint.png"
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

    model = load_system_model(args.case)
    schedules = build_schedules(args.case, time_limit_s=args.time_limit_s)

    fixed_path = schedule_dir / f"{model.case_id}__fixed_fastest_schedule.csv"
    joint_path = schedule_dir / f"{model.case_id}__m5_cpsat_schedule.csv"
    write_schedule_csv(schedules["fixed_fastest"], fixed_path)
    write_schedule_csv(schedules["m5_cpsat"], joint_path)
    print(f"Schedule CSVs written to {schedule_dir}")

    out_path = plot_figure5_gantt(
        schedules["fixed_fastest"],
        schedules["m5_cpsat"],
        fixed_path,
        joint_path,
        figure_dir,
        time_limit_s=args.time_limit_s,
    )
    print(f"Figure saved to {out_path}")


def configure_matplotlib() -> None:
    available = {font.name for font in fm.fontManager.ttflist}
    candidates = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS", "DejaVu Sans"]
    chosen = next((font for font in candidates if font in available), "DejaVu Sans")
    plt.rcParams.update(
        {
            "font.family": chosen,
            "axes.unicode_minus": False,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
        }
    )


if __name__ == "__main__":
    main()
