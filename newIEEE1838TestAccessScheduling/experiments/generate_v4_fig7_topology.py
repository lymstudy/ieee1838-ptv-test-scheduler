from __future__ import annotations

"""Figure 7 - Topology Impact (v4 experiment data).

Filters v4_final_experiment.csv for m5_cpsat + bist_fpp.
Produces a 3-panel figure:
  - Panel A: Makespan comparison across topologies (2.5D, 3D, 5.5D if available)
  - Panel B: FPP utilization by topology (only dies with FPP contribute)
  - Panel C: BIST overlap ratio by topology

Output: results/figures/v4_final/fig7_topology.png
"""

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

CSV_PATH = "results/tables/v4_final_experiment.csv"
OUTPUT_DIR = "results/figures/v4_final"
OUTPUT_PATH = "results/figures/v4_final/fig7_topology.png"

TOPOLOGY_ORDER = ["2_5d_interposer", "3d_stack", "5_5d_multi_tower"]
TOPOLOGY_LABELS = {"2_5d_interposer": "2.5D\nInterposer", "3d_stack": "3D\nStack", "5_5d_multi_tower": "5.5D\nMulti-tower"}
TOPOLOGY_SHORT = {"2_5d_interposer": "2.5D", "3d_stack": "3D", "5_5d_multi_tower": "5.5D"}
TOPOLOGY_COLORS = {"2_5d_interposer": "#4e79a7", "3d_stack": "#e15759", "5_5d_multi_tower": "#f28e2b"}

ANNOTATIONS = {
    "2_5d_interposer": "More FPP lanes\n(interposer metal),\nweaker thermal coupling\n-> lower BIST overlap possible",
    "3d_stack": "TAP bottleneck deeper\n(more STAPs to traverse),\nstronger thermal coupling\n-> limits concurrent execution",
    "5_5d_multi_tower": "Multi-tower grouping,\nmixed characteristics\n-> intermediate behavior",
}


def read_csv(path_str: str) -> list[dict[str, str]]:
    path = PROJECT_ROOT / path_str
    if not path.exists():
        raise FileNotFoundError(f"missing input table: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def filter_data(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Filter for method_id == m5_cpsat and condition_id == bist_fpp and status ok."""
    return [
        row for row in rows
        if row["method_id"] == "m5_cpsat"
        and row["condition_id"] == "bist_fpp"
        and row.get("status", "") == "ok"
    ]


def collect_topology_data(filtered: list[dict[str, str]]) -> dict:
    """Build per-topology data dictionary."""
    grouped: dict[str, list[dict]] = {}
    for row in filtered:
        topo = row["topology"]
        grouped.setdefault(topo, []).append(row)

    result = {}
    for topo in TOPOLOGY_ORDER:
        rows_t = grouped.get(topo, [])
        if not rows_t:
            result[topo] = None
            continue

        makespans_us = [float(r["makespan_us"]) for r in rows_t]
        fpp_utils = [float(r["fpp_utilization"]) for r in rows_t]
        bist_overlaps = [float(r["bist_overlap_ratio"]) for r in rows_t]
        case_ids = [r["case_id"] for r in rows_t]

        result[topo] = {
            "case_ids": case_ids,
            "makespan_us_mean": np.mean(makespans_us),
            "makespan_us": makespans_us,
            "fpp_util_mean": np.mean(fpp_utils),
            "fpp_util": fpp_utils,
            "bist_overlap_mean": np.mean(bist_overlaps),
            "bist_overlap": bist_overlaps,
        }
    return result


def configure_matplotlib() -> None:
    available = {font.name for font in fm.fontManager.ttflist}
    candidates = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS", "DejaVu Sans"]
    chosen = next((font for font in candidates if font in available), "DejaVu Sans")
    plt.rcParams.update({
        "font.family": chosen,
        "axes.unicode_minus": False,
        "axes.titlesize": 13,
        "axes.labelsize": 11,
        "xtick.labelsize": 10,
        "ytick.labelsize": 9,
    })


def panel_a_makespan(ax, data: dict) -> None:
    """Panel A: Makespan comparison across topologies with scatter points."""
    topologies = [t for t in TOPOLOGY_ORDER if data.get(t) is not None]
    if not topologies:
        ax.text(0.5, 0.5, "No topology data available", transform=ax.transAxes, ha="center", va="center")
        return

    x = np.arange(len(topologies))
    width = 0.5

    means = [data[t]["makespan_us_mean"] for t in topologies]
    colors = [TOPOLOGY_COLORS[t] for t in topologies]

    bars = ax.bar(x, means, width, color=colors, edgecolor="#333333", linewidth=0.8, zorder=2)

    # Annotate values on bars
    for i, (bar, mean) in enumerate(zip(bars, means)):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() * 1.02,
                f"{mean/1e6:.2f}s", ha="center", va="bottom", fontsize=9, fontweight="bold")

    # Overlay individual case scatter points
    for i, topo in enumerate(topologies):
        vals = data[topo]["makespan_us"]
        jitter = np.random.default_rng(42).uniform(-0.15, 0.15, len(vals))
        ax.scatter(x[i] + jitter, vals, color="#333333", edgecolor="white", linewidth=0.4, s=60, zorder=4, alpha=0.8)

    ax.set_xticks(x)
    ax.set_xticklabels([TOPOLOGY_LABELS[t] for t in topologies])
    ax.set_ylabel("Makespan (us)")
    ax.set_title("(a) Makespan by Topology\n(m5_cpsat, bist_fpp)", loc="left", fontweight="bold")
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)

    # Set ylim with some headroom
    if means:
        ax.set_ylim(0, max(means) * 1.25)


def panel_b_fpp_util(ax, data: dict) -> None:
    """Panel B: FPP utilization by topology."""
    topologies = [t for t in TOPOLOGY_ORDER if data.get(t) is not None]
    if not topologies:
        ax.text(0.5, 0.5, "No topology data available", transform=ax.transAxes, ha="center", va="center")
        return

    x = np.arange(len(topologies))
    width = 0.5

    means = [data[t]["fpp_util_mean"] for t in topologies]
    colors = [TOPOLOGY_COLORS[t] for t in topologies]

    bars = ax.bar(x, means, width, color=colors, edgecolor="#333333", linewidth=0.8, zorder=2)

    # Annotate values
    for i, (bar, mean) in enumerate(zip(bars, means)):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.0002,
                f"{mean:.4f}", ha="center", va="bottom", fontsize=9, fontweight="bold")

    # Overlay individual case scatter points
    for i, topo in enumerate(topologies):
        vals = data[topo]["fpp_util"]
        jitter = np.random.default_rng(42).uniform(-0.15, 0.15, len(vals))
        ax.scatter(x[i] + jitter, vals, color="#333333", edgecolor="white", linewidth=0.4, s=60, zorder=4, alpha=0.8)

    ax.set_xticks(x)
    ax.set_xticklabels([TOPOLOGY_LABELS[t] for t in topologies])
    ax.set_ylabel("FPP Lane Utilization")
    ax.set_title("(b) FPP Utilization by Topology\n(only dies with FPP contribute)", loc="left", fontweight="bold")
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    if means:
        ax.set_ylim(0, max(means) * 1.5)


def panel_c_bist_overlap(ax, data: dict) -> None:
    """Panel C: BIST overlap ratio by topology."""
    topologies = [t for t in TOPOLOGY_ORDER if data.get(t) is not None]
    if not topologies:
        ax.text(0.5, 0.5, "No topology data available", transform=ax.transAxes, ha="center", va="center")
        return

    x = np.arange(len(topologies))
    width = 0.5

    means = [data[t]["bist_overlap_mean"] for t in topologies]
    colors = [TOPOLOGY_COLORS[t] for t in topologies]

    bars = ax.bar(x, means, width, color=colors, edgecolor="#333333", linewidth=0.8, zorder=2)

    for i, (bar, mean) in enumerate(zip(bars, means)):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                f"{mean:.3f}", ha="center", va="bottom", fontsize=9, fontweight="bold")

    for i, topo in enumerate(topologies):
        vals = data[topo]["bist_overlap"]
        jitter = np.random.default_rng(42).uniform(-0.15, 0.15, len(vals))
        ax.scatter(x[i] + jitter, vals, color="#333333", edgecolor="white", linewidth=0.4, s=60, zorder=4, alpha=0.8)

    ax.set_xticks(x)
    ax.set_xticklabels([TOPOLOGY_LABELS[t] for t in topologies])
    ax.set_ylabel("BIST Overlap Ratio")
    ax.set_title("(c) BIST Overlap Ratio by Topology", loc="left", fontweight="bold")
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    ax.set_ylim(0, 0.55)


def add_annotation_box(fig, data: dict) -> None:
    """Add a text box explaining topology differences."""
    text_lines = [
        "Topology Differences:",
        "",
        "2.5D Interposer: More FPP lanes (interposer has more metal resources),",
        "  weaker thermal coupling between dies (horizontal adjacency only).",
        "  FPP can offload more data, but overhead from interposer routing.",
        "",
        "3D Stack: TAP bottleneck deeper (more STAPs to traverse per access),",
        "  stronger vertical thermal coupling limits concurrent high-power execution.",
        "  FPP lanes limited by TSV count; BIST overlap limited by thermal.",
        "",
        "5.5D Multi-tower: Mixed 2.5D/3D characteristics; tower groupings affect",
        "  both FPP reachability and thermal isolation.",
    ]
    # Place annotation at the bottom of the figure
    fig.text(0.5, 0.01, "\n".join(text_lines), ha="center", va="bottom",
             fontsize=7.5, style="italic", color="#555555",
             bbox=dict(boxstyle="round,pad=0.5", facecolor="#f8f8f8", edgecolor="#cccccc", alpha=0.85))


def main() -> None:
    configure_matplotlib()

    rows = read_csv(CSV_PATH)
    filtered = filter_data(rows)
    print(f"Loaded {len(rows)} rows, filtered to {len(filtered)} rows (m5_cpsat + bist_fpp + ok)")

    data = collect_topology_data(filtered)
    available = [t for t in TOPOLOGY_ORDER if data.get(t) is not None]
    print(f"Topologies with data: {[TOPOLOGY_SHORT[t] for t in available]}")
    for topo in available:
        d = data[topo]
        print(f"  {TOPOLOGY_SHORT[topo]}: cases={d['case_ids']}, makespan_mean={d['makespan_us_mean']:.0f}us, "
              f"fpp_util_mean={d['fpp_util_mean']:.4f}, bist_overlap_mean={d['bist_overlap_mean']:.3f}")

    output_dir = PROJECT_ROOT / OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(18, 7))
    gs = fig.add_gridspec(1, 3, wspace=0.35)

    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[0, 2])

    panel_a_makespan(ax_a, data)
    panel_b_fpp_util(ax_b, data)
    panel_c_bist_overlap(ax_c, data)

    fig.suptitle("Fig. 7  Topology Impact on Test Access Scheduling (v4, CP-SAT, bist_fpp)",
                 y=0.99, fontsize=16, fontweight="bold")

    add_annotation_box(fig, data)

    fig.subplots_adjust(wspace=0.35, top=0.85, bottom=0.28)

    output_path = PROJECT_ROOT / OUTPUT_PATH
    fig.savefig(output_path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"\nFigure 7 saved to: {output_path}")


if __name__ == "__main__":
    main()
