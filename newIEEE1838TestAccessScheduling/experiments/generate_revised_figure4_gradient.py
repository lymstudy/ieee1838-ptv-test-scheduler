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
TOPOLOGY_ORDER = ["2_5d_interposer", "3d_stack", "5_5d_multi_tower"]
TOPOLOGY_LABELS = {"2_5d_interposer": "2.5D", "3d_stack": "3D", "5_5d_multi_tower": "5.5D"}
TOPOLOGY_COLORS = {"2_5d_interposer": "#1f77b4", "3d_stack": "#d62728", "5_5d_multi_tower": "#9467bd"}
TOPOLOGY_MARKERS = {"2_5d_interposer": "o", "3d_stack": "s", "5_5d_multi_tower": "D"}

BIST_COUNT_ORDER = ["1", "2", "4", "8", "inf"]
BIST_LABELS = {"1": "1", "2": "2", "4": "4", "8": "8", "inf": "∞ (private)"}

PATH_TYPE_ORDER = ["BIST_only", "BIST_FPP", "BIST_FPP_Hybrid"]
PATH_LABELS = {"BIST_only": "BIST only", "BIST_FPP": "BIST+FPP", "BIST_FPP_Hybrid": "BIST+FPP+Hybrid"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate revised Figure 4: resource pressure and path diversity gradient curves.",
    )
    parser.add_argument(
        "--sweep-table",
        default="results/tables/resource_pressure_sweep.csv",
        help="Path to the resource_pressure_sweep.csv data file.",
    )
    parser.add_argument(
        "--figure-dir",
        default="results/figures/revised",
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
    plt.rcParams.update(
        {
            "font.family": chosen,
            "axes.unicode_minus": False,
            "axes.titlesize": 13,
            "axes.labelsize": 12,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
        }
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"missing input table: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


# ---------------------------------------------------------------------------
# Data extraction
# ---------------------------------------------------------------------------
def extract_part_a(rows: list[dict[str, str]]) -> dict[str, dict[str, float]]:
    """Extract Part A: BIST count sweep (bist_count=1,2,4,8,inf with all recipe types).

    Returns: {topology: {bist_count: gain_pct}} using M5 CP-SAT only.
    """
    result: dict[str, dict[str, float]] = {t: {} for t in TOPOLOGY_ORDER}
    for row in rows:
        if row.get("status") != "ok":
            continue
        topology = row["topology"]
        if topology not in TOPOLOGY_ORDER:
            continue
        if row.get("allowed_recipe_types") != "all":
            continue
        if row.get("method_id") != "m5_cpsat":
            continue
        bist_count = row["bist_count"]
        if bist_count not in BIST_COUNT_ORDER:
            continue
        try:
            gain = float(row["gain_vs_fixed_fastest_pct"])
        except (ValueError, KeyError):
            gain = 0.0
        result[topology][bist_count] = gain
    return result


def extract_part_b(rows: list[dict[str, str]]) -> dict[str, dict[str, float]]:
    """Extract Part B: Path diversity sweep (bist_count=1, recipe_types varying).

    Returns: {topology: {recipe_type: gain_pct}} using M5 CP-SAT only.
    """
    result: dict[str, dict[str, float]] = {t: {} for t in TOPOLOGY_ORDER}
    for row in rows:
        if row.get("status") != "ok":
            continue
        topology = row["topology"]
        if topology not in TOPOLOGY_ORDER:
            continue
        if row.get("bist_count") != "1":
            continue
        if row.get("method_id") != "m5_cpsat":
            continue
        recipe_types = row.get("allowed_recipe_types", "")
        if recipe_types not in PATH_TYPE_ORDER:
            continue
        try:
            gain = float(row["gain_vs_fixed_fastest_pct"])
        except (ValueError, KeyError):
            gain = 0.0
        result[topology][recipe_types] = gain
    return result


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------
def draw_curve_with_markers(
    ax: object,
    x_values: list[float],
    y_values: list[float],
    color: str,
    marker: str,
    label: str,
    linewidth: float = 2.0,
    markersize: float = 9.0,
) -> None:
    """Draw a connected line with markers at each data point."""
    ax.plot(
        x_values,
        y_values,
        color=color,
        marker=marker,
        markersize=markersize,
        linewidth=linewidth,
        markerfacecolor="white",
        markeredgewidth=1.5,
        markeredgecolor=color,
        label=label,
        zorder=5,
    )


def add_annotation_arrow(
    ax: object,
    text: str,
    xy: tuple[float, float],
    xytext: tuple[float, float],
    fontsize: float = 9.0,
) -> None:
    """Add an arrow annotation."""
    ax.annotate(
        text,
        xy=xy,
        xytext=xytext,
        fontsize=fontsize,
        fontstyle="italic",
        color="#555555",
        arrowprops=dict(
            arrowstyle="->",
            color="#888888",
            lw=1.2,
            connectionstyle="arc3,rad=0.15",
        ),
        ha="center",
        va="center",
    )


# ---------------------------------------------------------------------------
# Panel plotting
# ---------------------------------------------------------------------------
def plot_panel_a(ax: object, part_a: dict[str, dict[str, float]]) -> None:
    """Left panel: Resource Pressure Gradient (BIST count sweep)."""
    x_positions = np.arange(len(BIST_COUNT_ORDER))

    for topology in TOPOLOGY_ORDER:
        y_values = []
        for bist_count in BIST_COUNT_ORDER:
            gain = part_a[topology].get(bist_count, 0.0)
            y_values.append(gain)

        draw_curve_with_markers(
            ax,
            x_positions,
            y_values,
            color=TOPOLOGY_COLORS[topology],
            marker=TOPOLOGY_MARKERS[topology],
            label=TOPOLOGY_LABELS[topology],
        )

    # Horizontal dashed line at y=0
    ax.axhline(y=0, linestyle="--", color="#888888", linewidth=1.0, alpha=0.7, zorder=2)

    # X-axis labels
    ax.set_xticks(x_positions)
    ax.set_xticklabels([BIST_LABELS[bc] for bc in BIST_COUNT_ORDER])

    # Labels and title
    ax.set_title("(a) Resource Pressure Gradient", pad=10)
    ax.set_xlabel("Number of Shared BIST Engines")
    ax.set_ylabel("Joint Gain vs Fixed-Fastest (%)")

    # Annotation: arrow pointing right
    add_annotation_arrow(
        ax,
        "Less pressure → 0% gain",
        xy=(3.2, 2.0),
        xytext=(2.2, 8.0),
    )

    # Grid and legend
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    ax.set_axisbelow(True)
    ax.legend(frameon=True, fontsize=9, loc="upper right")

    # Y-axis range with headroom
    all_gains = [v for t in TOPOLOGY_ORDER for v in part_a[t].values() if part_a[t]]
    y_min = min(all_gains) - 3 if all_gains else -5
    y_max = max(all_gains) + 6 if all_gains else 55
    ax.set_ylim(y_min, y_max)


def plot_panel_b(ax: object, part_b: dict[str, dict[str, float]]) -> None:
    """Right panel: Path Diversity Gradient (recipe type sweep)."""
    x_positions = np.arange(len(PATH_TYPE_ORDER))

    for topology in TOPOLOGY_ORDER:
        y_values = []
        for recipe_type in PATH_TYPE_ORDER:
            gain = part_b[topology].get(recipe_type, 0.0)
            y_values.append(gain)

        draw_curve_with_markers(
            ax,
            x_positions,
            y_values,
            color=TOPOLOGY_COLORS[topology],
            marker=TOPOLOGY_MARKERS[topology],
            label=TOPOLOGY_LABELS[topology],
        )

    # Horizontal dashed line at y=0
    ax.axhline(y=0, linestyle="--", color="#888888", linewidth=1.0, alpha=0.7, zorder=2)

    # X-axis labels
    ax.set_xticks(x_positions)
    ax.set_xticklabels([PATH_LABELS[pt] for pt in PATH_TYPE_ORDER])

    # Labels and title
    ax.set_title("(b) Path Diversity Gradient", pad=10)
    ax.set_xlabel("Available Alternative Paths")
    ax.set_ylabel("Joint Gain vs Fixed-Fastest (%)")

    # Annotation: arrow pointing right and up
    add_annotation_arrow(
        ax,
        "More alternatives → higher gain",
        xy=(1.5, 46.0),
        xytext=(0.6, 36.0),
    )

    # Grid and legend
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    ax.set_axisbelow(True)
    ax.legend(frameon=True, fontsize=9, loc="upper left")

    # Y-axis range with headroom
    all_gains = [v for t in TOPOLOGY_ORDER for v in part_b[t].values() if part_b[t]]
    y_min = min(all_gains) - 3 if all_gains else -5
    y_max = max(all_gains) + 6 if all_gains else 55
    ax.set_ylim(y_min, y_max)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    args = parse_args()
    configure_matplotlib()

    figure_dir = Path(args.figure_dir)
    figure_dir.mkdir(parents=True, exist_ok=True)

    # ---- load data ---------------------------------------------------------
    table_path = Path(args.sweep_table)
    rows = read_csv(table_path)
    print(f"Loaded {len(rows)} rows from {table_path}")

    # ---- extract data ------------------------------------------------------
    part_a = extract_part_a(rows)
    part_b = extract_part_b(rows)

    # ---- validate data -----------------------------------------------------
    print("\nPart A (BIST count sweep) -- M5 CP-SAT gains:")
    for topology in TOPOLOGY_ORDER:
        gains = {bc: part_a[topology].get(bc, None) for bc in BIST_COUNT_ORDER}
        print(f"  {TOPOLOGY_LABELS[topology]}: {gains}")

    print("\nPart B (Path diversity sweep) -- M5 CP-SAT gains:")
    for topology in TOPOLOGY_ORDER:
        gains = {pt: part_b[topology].get(pt, None) for pt in PATH_TYPE_ORDER}
        print(f"  {TOPOLOGY_LABELS[topology]}: {gains}")

    # ---- build the figure --------------------------------------------------
    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(16, 6.5))

    plot_panel_a(ax_a, part_a)
    plot_panel_b(ax_b, part_b)

    # ---- figure-level title and annotation ---------------------------------
    fig.suptitle(
        "Fig. 4  Continuous Response: When and Why Joint Scheduling Matters",
        fontsize=14,
        fontweight="bold",
        y=0.98,
    )

    # Bottom annotation
    fig.text(
        0.5,
        0.01,
        "3 ITC'02-derived pressure cases x 5 BIST levels x 3 path diversity levels = 72 schedule rows (all OPTIMAL)",
        ha="center",
        va="top",
        fontsize=8.5,
        style="italic",
        color="#555555",
    )

    fig.tight_layout(rect=[0, 0.04, 1, 0.92])

    # ---- save -------------------------------------------------------------
    output_path = figure_dir / "fig4_pressure_gradient.png"
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)

    print(f"\nFigure saved to: {output_path}")


if __name__ == "__main__":
    main()
