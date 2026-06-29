"""Generate revised Figure 3 -- Mechanism Ablation Bar Chart from v4 final experiment data.

Shows makespan normalized to serial_baseline=1.0 for each condition, grouped by case.
Different colors for different topologies (3d_stack vs 2_5d_interposer).

Ablation conditions:
  - serial_baseline  (no BIST, no FPP) -> baseline (always 1.0)
  - bist_only        (BIST fire-and-release) -> Mechanism 1
  - fpp_only         (FPP data offload, no BIST) -> Mechanism 2
  - bist_fpp         (both) -> Mechanisms 1+2
  - bist_fpp_thermal (all + thermal) -> Full model

Output: results/figures/v4_final/fig3_mechanism.png
"""

from __future__ import annotations

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
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
TABLE_PATH = PROJECT_ROOT / "results" / "tables" / "v4_final_experiment.csv"
FIGURE_DIR = PROJECT_ROOT / "results" / "figures" / "v4_final"
FIGURE_PATH = FIGURE_DIR / "fig3_mechanism.png"

# ---------------------------------------------------------------------------
# Display constants
# ---------------------------------------------------------------------------
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
CONDITION_SHORT = [
    "Baseline",
    "+BIST\n(Mech.1)",
    "+FPP\n(Mech.2)",
    "BIST+FPP\n(Mech.1+2)",
    "All\n(Full Model)",
]

TOPOLOGY_COLORS = {
    "3d_stack": "#4c78a8",           # blue
    "2_5d_interposer": "#f28e2b",    # orange
}
TOPOLOGY_HATCH = {
    "3d_stack": "",
    "2_5d_interposer": "///",
}
CASE_DISPLAY = {
    "v4_small_3d_stack": "Small\n3D Stack",
    "v4_4die_3d_stack": "4-Die\n3D Stack",
    "v4_4die_2_5d_interposer": "4-Die\n2.5D Int.",
}


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
    plt.rcParams.update(
        {
            "font.family": chosen,
            "axes.unicode_minus": False,
            "figure.facecolor": "white",
        }
    )


def load_data(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    # Filter to CP-SAT results
    df = df[df["method_id"] == "m5_cpsat"].copy()
    return df


def build_normalized_data(df: pd.DataFrame) -> dict:
    """Build dict: condition -> list of (case_display, topology, norm_makespan)."""
    cases = sorted(df["case_id"].unique())
    conditions = [c for c in CONDITION_ORDER if c in df["condition_id"].unique()]

    # Get serial baseline for each case
    serial_baselines = {}
    for case in cases:
        row = df[(df["case_id"] == case) & (df["condition_id"] == "serial_baseline")]
        if not row.empty:
            serial_baselines[case] = row.iloc[0]["makespan_s"]

    # Build data
    data_by_condition = {cond: [] for cond in conditions}
    for case in cases:
        baseline = serial_baselines.get(case, 1.0)
        topology = df[df["case_id"] == case].iloc[0]["topology"]
        for cond in conditions:
            row = df[(df["case_id"] == case) & (df["condition_id"] == cond)]
            if not row.empty:
                makespan = row.iloc[0]["makespan_s"]
                norm = makespan / baseline if baseline > 0 else 1.0
                data_by_condition[cond].append({
                    "case": case,
                    "display": CASE_DISPLAY.get(case, case),
                    "topology": topology,
                    "norm_makespan": norm,
                })
    return data_by_condition, conditions, cases


def draw_mechanism_chart(ax, data_by_condition, conditions, cases):
    """Draw grouped bar chart: each condition has bars for each case, colored by topology."""
    n_conditions = len(conditions)
    n_cases = len(cases)

    x = np.arange(n_conditions)
    bar_width = 0.22
    gap = 0.03

    # Offset each case's bars within each condition group
    offsets = []
    total_group_width = n_cases * bar_width + (n_cases - 1) * gap
    start_offset = -total_group_width / 2 + bar_width / 2
    for i in range(n_cases):
        offsets.append(start_offset + i * (bar_width + gap))

    # Map case index to a fixed topological color
    case_topologies = [data_by_condition[conditions[0]][i]["topology"] for i in range(n_cases)]

    for c_idx, case in enumerate(cases):
        values = []
        for cond in conditions:
            entry = data_by_condition[cond][c_idx]
            values.append(entry["norm_makespan"])
        topo = case_topologies[c_idx]
        color = TOPOLOGY_COLORS.get(topo, "#999999")
        hatch = TOPOLOGY_HATCH.get(topo, "")
        label = data_by_condition[conditions[0]][c_idx]["display"]

        bars = ax.bar(
            x + offsets[c_idx], values, bar_width,
            color=color, edgecolor="#333333", linewidth=0.8,
            hatch=hatch, alpha=0.88, label=label, zorder=3,
        )
        # Annotate bar values
        for bar, val in zip(bars, values):
            y_pos = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                y_pos + 0.015,
                f"{val:.3f}",
                ha="center", va="bottom", fontsize=7.5,
                fontweight="bold", color="#333333",
            )

    # Reference line at 1.0
    ax.axhline(y=1.0, linestyle="--", color="#888888", linewidth=1.2, alpha=0.8, zorder=1)
    ax.text(n_conditions - 0.15, 1.0 + 0.01, "serial baseline = 1.0",
            fontsize=7.5, color="#888888", ha="right", va="bottom", fontstyle="italic")

    # Axis labels
    ax.set_xticks(x)
    ax.set_xticklabels(CONDITION_SHORT, fontsize=9.5, fontweight="bold")
    ax.set_ylabel("Normalized Makespan (Serial Baseline = 1.0)", fontsize=10)
    ax.set_ylim(0, 1.15)

    # Grid
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    ax.set_axisbelow(True)

    # Legend
    ax.legend(
        loc="upper right", fontsize=8.5, framealpha=0.9,
        title="Case", title_fontsize=9,
    )

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)


def main():
    configure_matplotlib()
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    df = load_data(str(TABLE_PATH))
    print(f"Loaded {len(df)} rows (m5_cpsat)")
    print(f"Cases: {sorted(df['case_id'].unique())}")
    print(f"Conditions: {sorted(df['condition_id'].unique())}")
    print()

    data_by_condition, conditions, cases = build_normalized_data(df)

    # Print data
    for cond in conditions:
        print(f"\n--- {cond} ---")
        for entry in data_by_condition[cond]:
            print(f"  {entry['case']:30s} ({entry['topology']:20s}): "
                  f"norm_makespan = {entry['norm_makespan']:.4f}")

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 6), dpi=200)

    draw_mechanism_chart(ax, data_by_condition, conditions, cases)

    # Title
    ax.set_title(
        "Fig. 3  Mechanism Ablation: Normalized Makespan by Condition and Case (CP-SAT)",
        fontsize=13, fontweight="bold", pad=16,
    )

    # Footer annotations
    fig.text(
        0.5, 0.01,
        "Lower is better.  FPP gives most of the speedup; BIST alone (fire-and-release) gives negligible gain "
        "without FPP due to serial TAP bottleneck.  BIST+FPP achieves full gain.  "
        "Thermal constraint not binding at this scale.",
        ha="center", va="bottom", fontsize=8, fontstyle="italic", color="#666666",
    )

    fig.tight_layout(rect=[0, 0.06, 1, 0.96])

    fig.savefig(str(FIGURE_PATH), dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"\nSaved: {FIGURE_PATH}")


if __name__ == "__main__":
    main()
