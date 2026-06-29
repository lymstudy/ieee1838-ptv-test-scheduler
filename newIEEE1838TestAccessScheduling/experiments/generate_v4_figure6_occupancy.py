"""Generate v4 Figure 6 -- Resource Utilization Timeline Comparison.

Reads pre-built v4 schedule CSVs for the 4die_3d_stack case and produces a 2-panel
stacked area chart comparing resource utilization between serial_baseline and bist_fpp.

Key insight: In serial_baseline, TAP is always busy. In bist_fpp, TAP has idle periods
(BIST execution windows) and FPP carries data in parallel.

Output: results/figures/v4_final/fig6_occupancy.png  (200 DPI)
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
TOTAL_FPP_LANES = 8  # For 4die_3d_stack

# Color palette (matching the task spec)
COLOR_TAP = "#8d62c8"     # purple for Serial TAP
COLOR_FPP = "#f28e2b"     # orange for FPP lanes
COLOR_BIST = "#59a14f"    # green for BIST
COLOR_CAPACITY = "#333333"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate v4 Figure 6 occupancy chart.")
    parser.add_argument("--case", default=DEFAULT_CASE, help="Case ID to plot.")
    parser.add_argument("--figure-dir", default="results/figures/v4_final")
    parser.add_argument("--schedule-dir", default=str(SCHEDULE_DIR))
    parser.add_argument("--total-fpp-lanes", type=int, default=TOTAL_FPP_LANES,
                        help="Total FPP lanes available.")
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
    filename = f"{case_id}__{condition_id}__cpsat.csv"
    path = schedule_dir / filename
    if not path.exists():
        raise FileNotFoundError(f"Schedule CSV not found: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


EPSILON = 1e-12


def compute_occupancy_curves(rows: list[dict[str, str]], total_fpp_lanes: int) -> dict[str, Any]:
    """Compute resource occupancy timeseries from schedule CSV rows.

    Returns:
        time_us: list of boundary timestamps in microseconds
        tap_busy: fraction of time TAP is busy (0 or 1 per interval)
        fpp_lanes: number of FPP lanes used per interval
        bist_busy: whether BIST is running (0 or 1 per interval)
        makespan_us: total makespan in microseconds
    """
    # Collect all unique time boundaries
    boundaries_set: set[float] = {0.0}
    for row in rows:
        boundaries_set.add(float(row["start_s"]))
        boundaries_set.add(float(row["end_s"]))
    boundaries = sorted(boundaries_set)

    time_us: list[float] = []
    tap_busy: list[float] = []
    fpp_lanes: list[float] = []
    bist_busy: list[float] = []

    for i in range(len(boundaries) - 1):
        t0 = boundaries[i]
        t1 = boundaries[i + 1]
        if t1 - t0 <= EPSILON:
            continue

        mid = (t0 + t1) / 2.0

        # Active phases at midpoint
        active = [
            r for r in rows
            if float(r["start_s"]) <= mid < float(r["end_s"]) - EPSILON
        ]

        # TAP busy: any phase requires serial_required
        tap = 1.0 if any(r.get("serial_required", "False").lower() == "true" for r in active) else 0.0

        # FPP lanes: sum of fpp_lanes_required
        lanes = sum(int(r.get("fpp_lanes_required", 0)) for r in active)

        # BIST busy: any LOCAL_BIST_RUN phase
        bist = 1.0 if any(r.get("phase_name") == "LOCAL_BIST_RUN" for r in active) else 0.0

        time_us.append(t0 * 1e6)
        tap_busy.append(tap)
        fpp_lanes.append(float(lanes))
        bist_busy.append(bist)

    # Append final boundary
    final_t = boundaries[-1] * 1e6
    time_us.append(final_t)
    tap_busy.append(0.0)
    fpp_lanes.append(0.0)
    bist_busy.append(0.0)

    return {
        "time_us": np.array(time_us),
        "tap_busy": np.array(tap_busy),
        "fpp_lanes": np.array(fpp_lanes),
        "bist_busy": np.array(bist_busy),
        "makespan_us": max(time_us),
    }


def draw_occupancy_panel(
    ax: Any,
    curves: dict[str, Any],
    total_fpp_lanes: int,
    title: str,
    gain_annotation: str | None = None,
) -> None:
    """Draw a single stacked-area panel of resource occupancy over time.

    Shows:
      - FPP lanes used (orange fill)
      - BIST busy (green ribbon above FPP)
      - TAP busy (purple ribbon above BIST)

    Uses step="post" filled areas for a clean resource timeline appearance.
    """
    t = curves["time_us"]
    fpp = curves["fpp_lanes"]
    tap = curves["tap_busy"]
    bist = curves["bist_busy"]

    # FPP lanes: fill from y=0 up to fpp_lanes
    ax.fill_between(
        t, 0, fpp,
        step="post",
        facecolor=COLOR_FPP,
        alpha=0.55,
        edgecolor=COLOR_FPP,
        linewidth=0.3,
        label="FPP Lanes Used",
    )

    # BIST busy ribbon
    bist_height = total_fpp_lanes * 0.15
    bist_base = fpp
    bist_top = bist_base + bist * bist_height
    ax.fill_between(
        t, bist_base, bist_top,
        step="post",
        facecolor=COLOR_BIST,
        alpha=0.72,
        edgecolor=COLOR_BIST,
        linewidth=0.3,
        label="BIST Engine Busy",
    )

    # TAP busy ribbon (on top of BIST)
    tap_height = total_fpp_lanes * 0.12
    tap_base = bist_top
    tap_top = tap_base + tap * tap_height
    ax.fill_between(
        t, tap_base, tap_top,
        step="post",
        facecolor=COLOR_TAP,
        alpha=0.65,
        edgecolor=COLOR_TAP,
        linewidth=0.3,
        label="Serial TAP Busy",
    )

    # FPP capacity line
    ax.axhline(
        y=total_fpp_lanes, color=COLOR_CAPACITY,
        linestyle="--", linewidth=1.2, alpha=0.7,
        label=f"FPP Capacity ({total_fpp_lanes} lanes)",
    )

    # Axis decoration
    ax.set_title(title, loc="left", fontsize=11, fontweight="bold")
    ax.set_ylabel("Lanes / Busy Status", fontsize=9)
    ax.set_ylim(bottom=-0.5, top=total_fpp_lanes * 1.4)
    ax.set_xlim(left=0, right=curves["makespan_us"] * 1.03)
    ax.grid(axis="y", alpha=0.18)
    ax.tick_params(axis="both", labelsize=8)

    # Legend
    ax.legend(
        loc="upper left", fontsize=7.5,
        frameon=True, framealpha=0.85, edgecolor="#cccccc",
        ncol=2,
    )

    if gain_annotation:
        ax.text(
            0.985, 0.94, gain_annotation,
            transform=ax.transAxes,
            ha="right", va="top", fontsize=13, fontweight="bold",
            color="#222222",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                      edgecolor="#aaaaaa", alpha=0.85),
        )


def main() -> None:
    args = parse_args()
    configure_matplotlib()

    figure_dir = Path(args.figure_dir)
    figure_dir.mkdir(parents=True, exist_ok=True)

    schedule_dir = Path(args.schedule_dir)
    case_id = args.case
    total_fpp_lanes = args.total_fpp_lanes

    # Load schedules
    print(f"Loading schedules for case: {case_id}")
    serial_rows = load_schedule_csv(case_id, "serial_baseline", schedule_dir)
    bist_fpp_rows = load_schedule_csv(case_id, "bist_fpp", schedule_dir)

    print(f"  serial_baseline: {len(serial_rows)} phases")
    print(f"  bist_fpp: {len(bist_fpp_rows)} phases")
    print(f"  total_fpp_lanes: {total_fpp_lanes}")

    # Compute occupancy curves
    serial_curves = compute_occupancy_curves(serial_rows, total_fpp_lanes)
    bist_fpp_curves = compute_occupancy_curves(bist_fpp_rows, total_fpp_lanes)

    # Compute speedup
    serial_mksp = serial_curves["makespan_us"]
    bist_fpp_mksp = bist_fpp_curves["makespan_us"]
    speedup = serial_mksp / bist_fpp_mksp

    print(f"  serial makespan: {serial_mksp:.1f} us")
    print(f"  bist_fpp makespan: {bist_fpp_mksp:.1f} us")
    print(f"  speedup: {speedup:.2f}x")

    # Diagnostics
    tap_frac_serial = float(np.mean(serial_curves["tap_busy"]))
    tap_frac_bist_fpp = float(np.mean(bist_fpp_curves["tap_busy"]))
    fpp_avg_serial = float(np.mean(serial_curves["fpp_lanes"]))
    fpp_avg_bist_fpp = float(np.mean(bist_fpp_curves["fpp_lanes"]))
    fpp_peak_bist_fpp = float(np.max(bist_fpp_curves["fpp_lanes"]))
    bist_frac_serial = float(np.mean(serial_curves["bist_busy"]))
    bist_frac_bist_fpp = float(np.mean(bist_fpp_curves["bist_busy"]))

    print(f"\n  TAP busy fraction:  serial={tap_frac_serial:.3f}  bist_fpp={tap_frac_bist_fpp:.3f}")
    print(f"  FPP avg lanes:      serial={fpp_avg_serial:.2f}  bist_fpp={fpp_avg_bist_fpp:.2f}")
    print(f"  FPP peak lanes:     bist_fpp={fpp_peak_bist_fpp:.0f}")
    print(f"  BIST busy fraction: serial={bist_frac_serial:.3f}  bist_fpp={bist_frac_bist_fpp:.3f}")

    # Build the figure
    fig, axes = plt.subplots(2, 1, figsize=(16, 9), sharex=True)

    xmax = max(serial_mksp, bist_fpp_mksp)

    # ---- Top panel: serial_baseline ----
    draw_occupancy_panel(
        axes[0],
        serial_curves,
        total_fpp_lanes,
        "serial_baseline: TAP Nearly Always Busy, FPP Idle",
    )

    # Annotation: TAP solidly busy
    ann_t = serial_mksp * 0.40
    axes[0].annotate(
        "Serial TAP nearly\nalways busy (no gaps)",
        xy=(ann_t, total_fpp_lanes * 0.08),
        xytext=(ann_t + serial_mksp * 0.12, total_fpp_lanes * 0.50),
        fontsize=9, color="#b22222",
        arrowprops=dict(arrowstyle="->", color="#b22222", lw=1.2, connectionstyle="arc3,rad=-0.3"),
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#fff5f5", edgecolor="#cc8888", alpha=0.9),
    )

    # Annotation: FPP idle
    axes[0].annotate(
        "FPP lanes entirely idle\n(no parallel data path used)",
        xy=(serial_mksp * 0.65, 0.3),
        xytext=(serial_mksp * 0.78, total_fpp_lanes * 0.6),
        fontsize=9, color="#b22222",
        arrowprops=dict(arrowstyle="->", color="#b22222", lw=1.2, connectionstyle="arc3,rad=0.2"),
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#fff5f5", edgecolor="#cc8888", alpha=0.9),
    )

    # ---- Bottom panel: bist_fpp ----
    gain_text = f"Gain: {speedup:.1f}x speedup"
    draw_occupancy_panel(
        axes[1],
        bist_fpp_curves,
        total_fpp_lanes,
        "bist_fpp: TAP Has Idle Gaps, FPP Carries Data in Parallel",
        gain_annotation=gain_text,
    )

    # Annotation: TAP gaps
    ann_t2 = bist_fpp_mksp * 0.55
    axes[1].annotate(
        "TAP idle gaps\n(BIST runs locally)",
        xy=(ann_t2, total_fpp_lanes * 0.06),
        xytext=(ann_t2 + bist_fpp_mksp * 0.08, total_fpp_lanes * 0.55),
        fontsize=9, color="#1b6e1b",
        arrowprops=dict(arrowstyle="->", color="#1b6e1b", lw=1.2, connectionstyle="arc3,rad=-0.3"),
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#f5fff5", edgecolor="#88cc88", alpha=0.9),
    )

    # Annotation: FPP active
    ann_t3 = bist_fpp_mksp * 0.25
    idx_j = np.searchsorted(bist_fpp_curves["time_us"], ann_t3)
    if idx_j >= len(bist_fpp_curves["fpp_lanes"]):
        idx_j = len(bist_fpp_curves["fpp_lanes"]) - 1
    fpp_at = float(bist_fpp_curves["fpp_lanes"][idx_j])
    axes[1].annotate(
        "FPP lanes active\nconcurrently with BIST",
        xy=(ann_t3, fpp_at + 1.5),
        xytext=(ann_t3 + bist_fpp_mksp * 0.10, fpp_at + 4.5),
        fontsize=9, color="#1b6e1b",
        arrowprops=dict(arrowstyle="->", color="#1b6e1b", lw=1.2, connectionstyle="arc3,rad=-0.2"),
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#f5fff5", edgecolor="#88cc88", alpha=0.9),
    )

    # Annotation: BIST appears
    ann_t4 = bist_fpp_mksp * 0.22
    axes[1].annotate(
        "BIST Engine\nshown as ribbon",
        xy=(ann_t4, total_fpp_lanes * 0.3),
        xytext=(ann_t4 + bist_fpp_mksp * 0.06, total_fpp_lanes * 0.95),
        fontsize=9, color="#1b6e1b",
        arrowprops=dict(arrowstyle="->", color="#1b6e1b", lw=1.2, connectionstyle="arc3,rad=-0.3"),
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#f5fff5", edgecolor="#88cc88", alpha=0.9),
    )

    # ---- shared x-axis ----
    axes[1].set_xlabel("Time (us)", fontsize=10)

    fig.suptitle(
        "Fig. 6  Resource Utilization: Why BIST+FPP Achieves Speedup over Serial Baseline",
        y=0.99, fontsize=13, fontweight="bold",
    )
    fig.tight_layout(rect=[0.0, 0.0, 1.0, 0.97])

    out_path = figure_dir / "fig6_occupancy.png"
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)

    print(f"\nFigure saved to: {out_path}")


if __name__ == "__main__":
    main()
