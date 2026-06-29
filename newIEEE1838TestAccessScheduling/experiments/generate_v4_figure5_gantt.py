"""Generate v4 Figure 5 -- Gantt Comparison: serial_baseline vs bist_fpp.

Reads pre-built v4 schedule CSVs for the 4die_3d_stack (most representative) case and
produces a 2-panel Gantt chart showing serial_baseline (top) vs bist_fpp (bottom).

Resource rows:
  - Serial TAP (purple): phases where serial_required=True
  - FPP Lanes (orange): phases where fpp_lanes_required > 0
  - Die0 BIST, Die1 BIST (green): LOCAL_BIST_RUN phases

Output: results/figures/v4_final/fig5_gantt.png  (200 DPI, ~16"x9")
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

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCHEDULE_DIR = PROJECT_ROOT / "results" / "schedules" / "v4_final"
DEFAULT_CASE = "v4_4die_3d_stack"

# Resource row labels (top to bottom, inverted y-axis so "top" is row 0)
ROW_SERIAL_TAP = "Serial TAP"
ROW_FPP_LANES = "FPP Lanes"
DIE_LIST = ["die0", "die1", "die2", "die3"]
BIST_ROWS = {die: f"{die} BIST" for die in DIE_LIST}

# Colors
COLOR_SERIAL = "#8d62c8"   # purple
COLOR_FPP = "#f28e2b"      # orange
COLOR_BIST = "#59a14f"     # green
COLOR_TARGET_BG = "#d0d0d0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate v4 Figure 5 Gantt chart.")
    parser.add_argument("--case", default=DEFAULT_CASE, help="Case ID to plot.")
    parser.add_argument("--figure-dir", default="results/figures/v4_final")
    parser.add_argument("--schedule-dir", default=str(SCHEDULE_DIR))
    return parser.parse_args()


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


def load_schedule_csv(case_id: str, condition_id: str, schedule_dir: Path) -> list[dict[str, str]]:
    """Load a v4 schedule CSV and return rows as list of dicts."""
    filename = f"{case_id}__{condition_id}__cpsat.csv"
    path = schedule_dir / filename
    if not path.exists():
        raise FileNotFoundError(f"Schedule CSV not found: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def get_dies_from_rows(rows: list[dict[str, str]]) -> list[str]:
    """Get sorted unique die IDs from the rows."""
    dies = sorted({row["die_id"] for row in rows})
    return dies


def compact_target(target_id: str) -> str:
    """Shorten a target id to a human-readable label."""
    # Keep just the die part for display
    parts = target_id.split("_")
    for i, part in enumerate(parts):
        if part.startswith("die") and len(part) >= 4:
            return "_".join(parts[i:])
    # fallback: return last meaningful part
    short = target_id.replace("v4_4die_3d_stack_", "").replace("v4_small_3d_stack_", "").replace("v4_4die_2_5d_interposer_", "")
    return short if short else target_id


def target_intervals(rows: list[dict[str, str]]) -> dict[str, tuple[float, float]]:
    """Return {target_id: (min_start_s, max_end_s)} per target."""
    intervals: dict[str, tuple[float, float]] = {}
    for row in rows:
        tid = row["target_id"]
        t0 = float(row["start_s"])
        t1 = float(row["end_s"])
        if tid not in intervals:
            intervals[tid] = (t0, t1)
        else:
            intervals[tid] = (min(intervals[tid][0], t0), max(intervals[tid][1], t1))
    return intervals


def draw_bar(ax: Any, y: float, start_us: float, width_us: float, color: str,
             label: str = "", alpha: float = 0.86, height: float = 0.58) -> None:
    """Draw a single horizontal bar with optional centred text label."""
    ax.barh(y, width_us, left=start_us, height=height, color=color,
            edgecolor="#333333", linewidth=0.35, alpha=alpha)
    if label and width_us > 0:
        fontsize = 5.5 if len(label) > 12 else 7
        ax.text(start_us + width_us / 2.0, y, label,
                ha="center", va="center", fontsize=fontsize, clip_on=True)


def get_makespan_s(rows: list[dict[str, str]]) -> float:
    """Get maximum end_s from schedule rows."""
    return max(float(row["end_s"]) for row in rows)


def draw_gantt_panel(
    ax: Any,
    rows: list[dict[str, str]],
    dies: list[str],
    title: str,
    xmax_us: float,
    gain_annotation: str | None = None,
) -> None:
    """Draw a multi-row Gantt panel from schedule CSV rows.

    Rows (top to bottom):
      - Serial TAP
      - FPP Lanes
      - die0 BIST, die1 BIST, die2 BIST, ... (one per die)

    The y-axis is inverted so Serial TAP appears at the top.
    """
    # Only show BIST rows for dies that actually have BIST phases
    bist_dies = set()
    for row in rows:
        if row.get("phase_name") == "LOCAL_BIST_RUN":
            bist_dies.add(row["die_id"])
    bist_dies = sorted(bist_dies)

    resource_rows = [ROW_SERIAL_TAP, ROW_FPP_LANES] + [BIST_ROWS[d] for d in bist_dies]
    n_rows = len(resource_rows)
    y_map = {name: idx for idx, name in enumerate(resource_rows)}

    min_bar_width = xmax_us * 0.0008

    # ---- per-target background bars ----
    for target_id, (t0, t1) in target_intervals(rows).items():
        draw_bar(ax, -0.6, t0 * 1e6, (t1 - t0) * 1e6, COLOR_TARGET_BG,
                 compact_target(target_id), alpha=0.18, height=0.7)

    # ---- phase bars ----
    for row in sorted(rows, key=lambda r: (float(r["start_s"]), float(r["end_s"]), r["target_id"])):
        start_us = float(row["start_s"]) * 1e6
        end_us = float(row["end_s"]) * 1e6
        width_us = max(end_us - start_us, min_bar_width)
        phase_name = row["phase_name"]
        serial_req = row.get("serial_required", "False").lower() == "true"
        fpp_lanes = int(row.get("fpp_lanes_required", 0))
        die_id = row["die_id"]
        target_id = row["target_id"]

        # Serial TAP
        if serial_req:
            draw_bar(ax, y_map[ROW_SERIAL_TAP], start_us, width_us, COLOR_SERIAL,
                     "")

        # FPP Lanes
        if fpp_lanes > 0:
            label = f"{compact_target(target_id)}"
            draw_bar(ax, y_map[ROW_FPP_LANES], start_us, width_us, COLOR_FPP,
                     label)

        # BIST (LOCAL_BIST_RUN only)
        if phase_name == "LOCAL_BIST_RUN" and die_id in bist_dies:
            draw_bar(ax, y_map[BIST_ROWS[die_id]], start_us, width_us, COLOR_BIST,
                     compact_target(target_id))

    # ---- axis decoration ----
    ax.set_title(title, loc="left", fontsize=11, fontweight="bold")
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels(resource_rows, fontsize=9)
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.18)
    ax.set_xlim(0, xmax_us * 1.03)
    ax.tick_params(axis="x", labelsize=8)

    if gain_annotation:
        ax.text(0.985, 0.96, gain_annotation, transform=ax.transAxes,
                ha="right", va="top", fontsize=14, fontweight="bold",
                color="#222222",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                          edgecolor="#aaaaaa", alpha=0.85))


def main() -> None:
    args = parse_args()
    configure_matplotlib()

    figure_dir = Path(args.figure_dir)
    figure_dir.mkdir(parents=True, exist_ok=True)

    schedule_dir = Path(args.schedule_dir)
    case_id = args.case

    # Load both schedules
    print(f"Loading schedules for case: {case_id}")
    serial_rows = load_schedule_csv(case_id, "serial_baseline", schedule_dir)
    bist_fpp_rows = load_schedule_csv(case_id, "bist_fpp", schedule_dir)

    print(f"  serial_baseline: {len(serial_rows)} phases")
    print(f"  bist_fpp: {len(bist_fpp_rows)} phases")

    dies = get_dies_from_rows(serial_rows)
    print(f"  dies: {dies}")

    serial_mksp = get_makespan_s(serial_rows)
    bist_fpp_mksp = get_makespan_s(bist_fpp_rows)
    speedup = serial_mksp / bist_fpp_mksp
    print(f"  serial makespan: {serial_mksp * 1e6:.1f} us")
    print(f"  bist_fpp makespan: {bist_fpp_mksp * 1e6:.1f} us")
    print(f"  speedup: {speedup:.2f}x")

    xmax_us = max(serial_mksp, bist_fpp_mksp) * 1e6

    # Build the figure
    fig, axes = plt.subplots(2, 1, figsize=(16, 9), sharex=True)

    # ---- Top panel: serial_baseline ----
    draw_gantt_panel(
        axes[0],
        serial_rows,
        dies,
        f"serial_baseline: all tasks use serial TAP, no parallelism",
        xmax_us,
    )

    # Annotate: TAP always busy
    ann_x = xmax_us * 0.45
    axes[0].annotate(
        "Serial TAP nearly\nalways busy",
        xy=(ann_x, 0.2),
        xytext=(ann_x + xmax_us * 0.12, -0.7),
        fontsize=9,
        color="#b22222",
        arrowprops=dict(arrowstyle="->", color="#b22222", lw=1.2, connectionstyle="arc3,rad=0.2"),
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#fff5f5", edgecolor="#cc8888", alpha=0.9),
    )

    # Annotate: no FPP
    ann_x2 = xmax_us * 0.3
    axes[0].annotate(
        "FPP Lanes idle\n(no FPP used)",
        xy=(ann_x2, 1.2),
        xytext=(ann_x2 + xmax_us * 0.1, 1.6),
        fontsize=9,
        color="#b22222",
        arrowprops=dict(arrowstyle="->", color="#b22222", lw=1.2, connectionstyle="arc3,rad=-0.3"),
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#fff5f5", edgecolor="#cc8888", alpha=0.9),
    )

    # ---- Bottom panel: bist_fpp ----
    gain_text = f"{speedup:.1f}x speedup vs serial"
    draw_gantt_panel(
        axes[1],
        bist_fpp_rows,
        dies,
        f"bist_fpp: BIST overlaps across dies, FPP parallel paths utilised",
        xmax_us,
        gain_annotation=gain_text,
    )

    # Annotate: TAP has gaps
    ann_x3 = xmax_us * 0.15
    axes[1].annotate(
        "Serial TAP has gaps\n(BIST executes locally)",
        xy=(ann_x3, 0.3),
        xytext=(ann_x3 + xmax_us * 0.1, -0.6),
        fontsize=9,
        color="#1b6e1b",
        arrowprops=dict(arrowstyle="->", color="#1b6e1b", lw=1.2, connectionstyle="arc3,rad=0.2"),
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#f5fff5", edgecolor="#88cc88", alpha=0.9),
    )

    # Annotate: BIST overlaps
    ann_x4 = xmax_us * 0.22
    axes[1].annotate(
        "BIST overlaps\nacross dies",
        xy=(ann_x4, 3.0),
        xytext=(ann_x4 + xmax_us * 0.06, 4.2),
        fontsize=9,
        color="#1b6e1b",
        arrowprops=dict(arrowstyle="->", color="#1b6e1b", lw=1.2, connectionstyle="arc3,rad=-0.2"),
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#f5fff5", edgecolor="#88cc88", alpha=0.9),
    )

    # Annotate: FPP active
    ann_x5 = xmax_us * 0.35
    axes[1].annotate(
        "FPP carries data\nin parallel",
        xy=(ann_x5, 1.3),
        xytext=(ann_x5 + xmax_us * 0.08, 1.8),
        fontsize=9,
        color="#1b6e1b",
        arrowprops=dict(arrowstyle="->", color="#1b6e1b", lw=1.2, connectionstyle="arc3,rad=-0.3"),
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#f5fff5", edgecolor="#88cc88", alpha=0.9),
    )

    # ---- shared x-axis ----
    axes[1].set_xlabel("Time (us)", fontsize=10)

    fig.suptitle(
        "Fig. 5  Scheduling Gantt Comparison: Serial Baseline vs BIST+FPP (v4_4die_3d_stack, CP-SAT)",
        y=0.99, fontsize=13, fontweight="bold",
    )
    fig.tight_layout(rect=[0.0, 0.0, 1.0, 0.97])

    out_path = figure_dir / "fig5_gantt.png"
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)

    print(f"\nFigure saved to: {out_path}")


if __name__ == "__main__":
    main()
