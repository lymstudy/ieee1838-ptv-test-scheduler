"""Generate revised Figure 2 -- Coverage Matrix from v4 final experiment data.

v4 experiment data columns:
  case_id, topology, condition_id, method_id, status, error, makespan_s,
  makespan_us, serial_busy_ratio, fpp_utilization, bist_overlap_ratio,
  max_concurrent_bist, peak_temperature_c, thermal_violations,
  selected_recipe_types, task_count, variant_count, scheduled_task_count,
  peak_power_w, solver_status, solver_wall_time_s, die_count,
  fpp_lane_count, bist_engine_count

Filter: method_id == "m5_cpsat" (CP-SAT optimal/suboptimal results).

Matrix: cases (rows) x conditions (columns) showing speedup vs serial_baseline.
Also show: die_count, task_count, fpp_lane_count per case.

Output: results/figures/v4_final/fig2_coverage.png
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
TABLE_PATH = PROJECT_ROOT / "results" / "tables" / "v4_final_experiment.csv"
FIGURE_DIR = PROJECT_ROOT / "results" / "figures" / "v4_final"
FIGURE_PATH = FIGURE_DIR / "fig2_coverage.png"

# ---------------------------------------------------------------------------
# Display constants
# ---------------------------------------------------------------------------
# Order of conditions (columns) for display
CONDITION_ORDER = [
    "serial_baseline",
    "bist_only",
    "fpp_only",
    "bist_fpp",
    "bist_fpp_thermal",
]
CONDITION_LABELS = [
    "Serial\nBaseline",
    "BIST\nOnly",
    "FPP\nOnly",
    "BIST+FPP",
    "BIST+FPP\n+Thermal",
]
CONDITION_COLORS = [
    "#999999",   # grey -- baseline
    "#59a14f",   # green -- BIST only
    "#f28e2b",   # orange -- FPP only
    "#4c78a8",   # blue -- BIST+FPP
    "#8d62c8",   # purple -- full (thermal)
]

# Case metadata display names (short)
CASE_DISPLAY = {
    "v4_small_3d_stack": "Small\n3D Stack",
    "v4_4die_3d_stack": "4-Die\n3D Stack",
    "v4_4die_2_5d_interposer": "4-Die\n2.5D Interposer",
}


def load_data(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    # Filter to m5_cpsat only
    df = df[df["method_id"] == "m5_cpsat"].copy()
    return df


def build_speedup_matrix(df: pd.DataFrame) -> dict:
    """Build a dict: case_id -> serial_baseline_makespan and condition_id -> makespan."""
    cases = sorted(df["case_id"].unique())
    conditions = [c for c in CONDITION_ORDER if c in df["condition_id"].unique()]

    # Get serial baseline makespan for each case
    serial_baselines = {}
    for case in cases:
        baseline_row = df[(df["case_id"] == case) & (df["condition_id"] == "serial_baseline")]
        if not baseline_row.empty:
            serial_baselines[case] = baseline_row.iloc[0]["makespan_s"]

    # Build matrix: case -> condition -> speedup
    matrix = {}
    case_info = {}
    for case in cases:
        case_df = df[df["case_id"] == case]
        # Get die_count (same across all conditions)
        die_count = int(case_df.iloc[0]["die_count"])
        # Get max FPP lane count (from fpp conditions)
        max_fpp = int(case_df["fpp_lane_count"].max())
        # Get task count from serial_baseline
        base_row = case_df[case_df["condition_id"] == "serial_baseline"]
        task_count = int(base_row.iloc[0]["task_count"]) if not base_row.empty else int(case_df.iloc[0]["task_count"])
        # Task count with BIST (from bist_only condition)
        bist_row = case_df[case_df["condition_id"] == "bist_only"]
        task_count_bist = int(bist_row.iloc[0]["task_count"]) if not bist_row.empty else task_count
        case_info[case] = {
            "die_count": die_count,
            "task_count": task_count,
            "task_count_bist": task_count_bist,
            "fpp_lane_count": max_fpp,
            "topology": case_df.iloc[0]["topology"],
        }
        baseline = serial_baselines.get(case, None)
        row = {}
        for cond in conditions:
            cond_df = case_df[case_df["condition_id"] == cond]
            if not cond_df.empty:
                makespan = cond_df.iloc[0]["makespan_s"]
                if baseline and baseline > 0:
                    speedup = baseline / makespan
                else:
                    speedup = 1.0
                row[cond] = speedup
            else:
                row[cond] = None
        matrix[case] = row

    return matrix, case_info, cases, conditions


def draw_matrix(ax, matrix, case_info, cases, conditions):
    """Draw a cells x conditions heatmap-style matrix with speedup values."""
    n_rows = len(cases)
    n_cols = len(conditions)

    # Collect all speedups for color mapping
    all_sp = []
    for case in cases:
        for cond in conditions:
            sp = matrix[case].get(cond)
            if sp is not None:
                all_sp.append(sp)
    sp_min = min(all_sp) if all_sp else 1.0
    sp_max = max(all_sp) if all_sp else 10.0

    # Color map: green = faster (higher speedup), red = slower (lower speedup)
    cmap = plt.cm.RdYlGn
    norm = Normalize(vmin=1.0, vmax=sp_max)

    cell_w = 1.0
    cell_h = 1.0

    for i, case in enumerate(cases):
        for j, cond in enumerate(conditions):
            sp = matrix[case].get(cond)
            if sp is None:
                color = "#eeeeee"
                text = "N/A"
                tc = "#aaaaaa"
            else:
                color = cmap(norm(sp))
                text = f"{sp:.2f}x"
                # Determine text color based on luminance
                lum = 0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]
                tc = "white" if lum < 0.5 else "black"

            x = j + 0.5
            y = i + 0.5
            rect = plt.Rectangle(
                (x, y), cell_w, cell_h,
                facecolor=color, edgecolor="#333333",
                linewidth=1.0, zorder=2,
            )
            ax.add_patch(rect)
            ax.text(x + cell_w / 2, y + cell_h / 2, text,
                    ha="center", va="center", fontsize=11, fontweight="bold",
                    color=tc, zorder=3)

    # ---- Case labels (left side) ----
    for i, case in enumerate(cases):
        info = case_info[case]
        display = CASE_DISPLAY.get(case, case)
        label = (f"{display}\n"
                 f"dies={info['die_count']}, tasks={info['task_count']}-{info['task_count_bist']}, "
                 f"FPP={info['fpp_lane_count']} lanes")
        ax.text(0.35, i + 1.0, label, ha="right", va="center",
                fontsize=9.5, fontweight="bold", color="#333333")

    # ---- Column headers ----
    for j, (cond, label) in enumerate(zip(conditions, CONDITION_LABELS)):
        ax.text(j + 1.0, n_rows + 0.75, label,
                ha="center", va="bottom", fontsize=9.5, fontweight="bold",
                color=CONDITION_COLORS[j] if j < len(CONDITION_COLORS) else "#333333")

    # Axes
    ax.set_xlim(0, n_cols + 1.0)
    ax.set_ylim(n_rows + 0.2, 0.3)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_aspect("equal")


def draw_colorbar(fig, sp_min, sp_max):
    """Horizontal colorbar below the matrix."""
    cax = fig.add_axes([0.18, 0.08, 0.64, 0.025])
    cmap = plt.cm.RdYlGn
    norm = Normalize(vmin=1.0, vmax=sp_max)
    sm = ScalarMappable(norm=norm, cmap=cmap)
    cb = plt.colorbar(sm, cax=cax, orientation="horizontal")
    cb.set_label("Speedup vs. Serial Baseline (higher = better)",
                 fontsize=8, fontweight="bold")
    cb.ax.tick_params(labelsize=7)


def main():
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    df = load_data(str(TABLE_PATH))
    print(f"Loaded {len(df)} rows (m5_cpsat only)")
    print(f"Cases: {sorted(df['case_id'].unique())}")
    print(f"Conditions: {sorted(df['condition_id'].unique())}")
    print()

    matrix, case_info, cases, conditions = build_speedup_matrix(df)

    # Print summary
    for case in cases:
        print(f"\n--- {case} (dies={case_info[case]['die_count']}, "
              f"tasks={case_info[case]['task_count']}, "
              f"FPP={case_info[case]['fpp_lane_count']}) ---")
        for cond in conditions:
            sp = matrix[case].get(cond)
            if sp is not None:
                print(f"  {cond:25s}: speedup = {sp:.3f}x")
            else:
                print(f"  {cond:25s}: N/A")

    # Collect all speedups
    all_sp = []
    for case in cases:
        for cond in conditions:
            sp = matrix[case].get(cond)
            if sp is not None:
                all_sp.append(sp)
    sp_min = min(all_sp) if all_sp else 1.0
    sp_max = max(all_sp) if all_sp else 10.0

    # Create figure
    fig = plt.figure(figsize=(12, 6.5), dpi=200)
    fig.patch.set_facecolor("white")

    ax_mat = fig.add_axes([0.28, 0.18, 0.68, 0.72])
    draw_matrix(ax_mat, matrix, case_info, cases, conditions)

    draw_colorbar(fig, sp_min, sp_max)

    # Title
    fig.text(0.5, 0.965,
             "Fig. 2  Coverage Matrix: Speedup by Case and Mechanism Configuration (CP-SAT)",
             ha="center", va="center", fontsize=13, fontweight="bold")

    # Footer
    fig.text(0.5, 0.025,
             f"3 benchmark cases x {len(conditions)} mechanism conditions. "
             f"Speedup = T_serial / T_condition.  Higher values (green) are better.",
             ha="center", va="center", fontsize=8.5, fontstyle="italic", color="#666666")

    fig.savefig(str(FIGURE_PATH), dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"\nSaved: {FIGURE_PATH}")


if __name__ == "__main__":
    main()
