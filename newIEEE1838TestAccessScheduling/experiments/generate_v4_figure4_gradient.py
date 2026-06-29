"""Generate v4 Figure 4 -- Mechanism Gradient: contribution of each mechanism.

Reads v4_final_experiment.csv, filters for m5_cpsat, and produces a grouped bar chart
showing the incremental contribution of TAP time-multiplexing (BIST), FPP, combined
BIST+FPP, and thermal-aware scheduling relative to the serial baseline.

Output: results/figures/v4_final/fig4_gradient.png
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

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
TOPOLOGY_ORDER = ["v4_small_3d_stack", "v4_4die_3d_stack", "v4_4die_2_5d_interposer"]
TOPOLOGY_LABELS = {
    "v4_small_3d_stack": "Small 3D Stack\n(3 die)",
    "v4_4die_3d_stack": "4-Die 3D Stack",
    "v4_4die_2_5d_interposer": "4-Die 2.5D\nInterposer",
}

CONDITION_ORDER = ["serial_baseline", "bist_only", "fpp_only", "bist_fpp", "bist_fpp_thermal"]
CONDITION_LABELS = {
    "serial_baseline": "Serial\nBaseline",
    "bist_only": "BIST\nOnly",
    "fpp_only": "FPP\nOnly",
    "bist_fpp": "BIST\n+ FPP",
    "bist_fpp_thermal": "BIST+FPP\n+Thermal",
}

# Color for each condition bar
CONDITION_COLORS = {
    "serial_baseline": "#7f7f7f",
    "bist_only": "#59a14f",
    "fpp_only": "#f28e2b",
    "bist_fpp": "#4e79a7",
    "bist_fpp_thermal": "#e15759",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate v4 Figure 4: mechanism gradient grouped bar chart.",
    )
    parser.add_argument(
        "--experiment-table",
        default="results/tables/v4_final_experiment.csv",
        help="Path to v4_final_experiment.csv.",
    )
    parser.add_argument(
        "--figure-dir",
        default="results/figures/v4_final",
        help="Output directory for the generated figure.",
    )
    return parser.parse_args()


def configure_matplotlib() -> None:
    available = {font.name for font in fm.fontManager.ttflist}
    candidates = [
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    chosen = next((font for font in candidates if font in available), "DejaVu Sans")
    plt.rcParams.update({
        "font.family": chosen,
        "axes.unicode_minus": False,
        "axes.titlesize": 13,
        "axes.labelsize": 12,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
    })


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"missing input table: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def extract_makespans(rows: list[dict[str, str]]) -> dict[str, dict[str, float]]:
    """Extract {case_id: {condition_id: makespan_s}} for m5_cpsat only, ok status."""
    result: dict[str, dict[str, float]] = {t: {} for t in TOPOLOGY_ORDER}
    for row in rows:
        if row.get("status") != "ok":
            continue
        if row.get("method_id") != "m5_cpsat":
            continue
        case_id = row["case_id"]
        if case_id not in TOPOLOGY_ORDER:
            continue
        condition_id = row["condition_id"]
        if condition_id not in CONDITION_ORDER:
            continue
        try:
            mksp = float(row["makespan_s"])
        except (ValueError, KeyError):
            continue
        result[case_id][condition_id] = mksp
    return result


def main() -> None:
    args = parse_args()
    configure_matplotlib()

    figure_dir = Path(args.figure_dir)
    figure_dir.mkdir(parents=True, exist_ok=True)

    table_path = Path(args.experiment_table)
    rows = read_csv(table_path)
    print(f"Loaded {len(rows)} rows from {table_path}")

    data = extract_makespans(rows)

    # Normalize each case so serial_baseline = 1.0
    normalized: dict[str, dict[str, float]] = {}
    for case_id in TOPOLOGY_ORDER:
        baseline = data[case_id].get("serial_baseline", 1.0)
        if baseline == 0:
            baseline = 1.0
        normalized[case_id] = {
            cond: data[case_id].get(cond, 0.0) / baseline
            for cond in CONDITION_ORDER
        }
        # serial_baseline should be exactly 1.0
        normalized[case_id]["serial_baseline"] = 1.0

    # Print summary
    print("\nNormalized makespan (serial_baseline = 1.0):")
    for case_id in TOPOLOGY_ORDER:
        vals = {c: f"{normalized[case_id][c]:.4f}" for c in CONDITION_ORDER}
        print(f"  {case_id}: {vals}")

    # Compute speedup for annotations
    speedups: dict[str, dict[str, float]] = {}
    for case_id in TOPOLOGY_ORDER:
        base = data[case_id]["serial_baseline"]
        speedups[case_id] = {
            cond: base / data[case_id][cond] if data[case_id].get(cond, 0) > 0 else 1.0
            for cond in CONDITION_ORDER
        }
    print("\nSpeedups vs serial_baseline:")
    for case_id in TOPOLOGY_ORDER:
        vals = {c: f"{speedups[case_id][c]:.2f}x" for c in CONDITION_ORDER}
        print(f"  {case_id}: {vals}")

    # ---- Build the grouped bar chart ---------------------------------------
    n_cases = len(TOPOLOGY_ORDER)
    n_conds = len(CONDITION_ORDER)
    x = np.arange(n_cases)
    bar_width = 0.15
    group_width = n_conds * bar_width

    fig, ax = plt.subplots(figsize=(14, 7))

    for i, cond in enumerate(CONDITION_ORDER):
        offset = (i - (n_conds - 1) / 2) * bar_width
        y_values = [normalized[cid][cond] for cid in TOPOLOGY_ORDER]
        bars = ax.bar(
            x + offset,
            y_values,
            bar_width * 0.9,
            color=CONDITION_COLORS[cond],
            edgecolor="#333333",
            linewidth=0.5,
            label=CONDITION_LABELS[cond],
            zorder=3,
        )

    # Add value labels above each bar
    for i, cond in enumerate(CONDITION_ORDER):
        offset = (i - (n_conds - 1) / 2) * bar_width
        for j, cid in enumerate(TOPOLOGY_ORDER):
            val = normalized[cid][cond]
            ax.text(
                x[j] + offset,
                val + 0.015,
                f"{val:.3f}",
                ha="center",
                va="bottom",
                fontsize=7,
                rotation=90,
                color="#333333",
            )

    # X-axis
    ax.set_xticks(x)
    ax.set_xticklabels([TOPOLOGY_LABELS[cid] for cid in TOPOLOGY_ORDER])

    # Y-axis: normalized makespan
    ax.set_ylabel("Normalized Makespan (Serial Baseline = 1.0)", fontsize=12)
    ax.set_title(
        "Fig. 4  Mechanism Contribution Gradient: Incremental Effect of Each Optimisation",
        fontsize=13,
        fontweight="bold",
        pad=12,
    )

    # Reference line at y=1.0
    ax.axhline(y=1.0, linestyle="--", color="#333333", linewidth=1.0, alpha=0.6, zorder=2)

    # Annotations showing incremental gains
    # For the most representative case (4die_3d_stack, index 1):
    rep_idx = 1  # v4_4die_3d_stack
    rep_case = TOPOLOGY_ORDER[rep_idx]

    # Annotate bist_fpp_thermal speedup for the rep case
    best_speedup = speedups[rep_case]["bist_fpp_thermal"]
    ax.annotate(
        f"{best_speedup:.1f}x speedup\nvs serial",
        xy=(rep_idx, normalized[rep_case]["bist_fpp_thermal"]),
        xytext=(rep_idx + 0.55, 1.08),
        fontsize=9,
        fontweight="bold",
        color="#e15759",
        arrowprops=dict(arrowstyle="->", color="#e15759", lw=1.5, connectionstyle="arc3,rad=0.3"),
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="#e15759", alpha=0.9),
        ha="center",
        va="center",
    )

    # Legend
    ax.legend(
        loc="upper right",
        fontsize=9,
        frameon=True,
        framealpha=0.9,
        edgecolor="#cccccc",
        ncol=5,
    )

    ax.grid(axis="y", alpha=0.25, linestyle="--")
    ax.set_axisbelow(True)
    ax.set_ylim(0, 1.25)

    # Bottom annotation
    fig.text(
        0.5,
        0.01,
        "Data: v4_final_experiment.csv  |  Method: m5_cpsat (CP-SAT optimal)  |  "
        "Each topology normalised to its own serial_baseline",
        ha="center",
        va="top",
        fontsize=8,
        style="italic",
        color="#555555",
    )

    fig.tight_layout(rect=[0, 0.04, 1, 0.95])

    output_path = figure_dir / "fig4_gradient.png"
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)

    print(f"\nFigure saved to: {output_path}")


if __name__ == "__main__":
    main()
