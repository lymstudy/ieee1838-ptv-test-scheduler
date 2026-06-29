from __future__ import annotations

import csv
import sys
from collections import defaultdict
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


M22_TABLE = "results/tables/m22_mechanism_ablation_detail.csv"
M21_TABLE = "results/tables/m21_topology_pressure_summary.csv"
FIGURE_DIR = "results/figures/revised"
FIGURE_PATH = "results/figures/revised/fig7_topology_analysis.png"

TOPOLOGY_ORDER = ["2_5d_interposer", "3d_stack", "5_5d_multi_tower"]
TOPOLOGY_LABELS = ["2.5D Interposer", "3D Stack", "5.5D\nMulti-tower"]
TOPOLOGY_SHORT = ["2.5D", "3D", "5.5D"]

ANNOTATIONS = {
    "2_5d_interposer": "More FPP lanes,\nweaker thermal coupling\n-> milder bottleneck",
    "3d_stack": "Fewer FPP lanes\n(TSV-limited),\nstrong thermal coupling\n-> severe bottleneck",
    "5_5d_multi_tower": "Multi-tower grouping,\nmixed characteristics\n-> intermediate",
}


def read_csv(path_str: str) -> list[dict[str, str]]:
    path = PROJECT_ROOT / path_str
    if not path.exists():
        raise FileNotFoundError(f"missing input table: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def filter_m22_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Filter for ablation_id == shared_bist_with_parallel_escape and status == ok."""
    return [
        row
        for row in rows
        if row["ablation_id"] == "shared_bist_with_parallel_escape"
        and row["status"] == "ok"
    ]


def collect_topology_data(m22_rows: list[dict[str, str]], m21_rows: list[dict[str, str]]) -> dict:
    """Build per-topology data dictionary from M22 detail and M21 summary."""
    # Group M22 rows by topology_type, filter for method_family == "joint"
    grouped = defaultdict(list)
    grouped_fixed = defaultdict(list)
    for row in m22_rows:
        topo = row["topology_type"]
        if row["method_family"] == "joint":
            grouped[topo].append(row)
        elif row["method_id"] == "fixed_fastest":
            grouped_fixed[topo].append(row)

    # M21 summary data by topology
    m21_by_topo = {row["topology_type"]: row for row in m21_rows}

    result = {}
    for topo in TOPOLOGY_ORDER:
        joint_rows = grouped.get(topo, [])
        fixed_rows = grouped_fixed.get(topo, [])
        m21_row = m21_by_topo.get(topo, {})

        # Gain values from joint rows (positive only, real gains)
        gains = [float(r["gain_vs_fixed_fastest_percent"]) for r in joint_rows]
        gains = [g for g in gains if g > 0]

        # Per-case data for scatter points
        case_gains = {}
        for r in joint_rows:
            case_id_base = r["case_id"]
            g = float(r["gain_vs_fixed_fastest_percent"])
            if g > 0:
                case_gains[case_id_base] = g

        # FPP utilization from joint rows
        fpp_utils = [float(r["fpp_utilization"]) for r in joint_rows]

        # BIST counts from fixed and joint
        fixed_b_counts = [int(r["selected_b_count"]) for r in fixed_rows]
        joint_b_counts = [int(r["selected_b_count"]) for r in joint_rows if float(r["gain_vs_fixed_fastest_percent"]) > 0]

        # F counts from joint
        joint_f_counts = [int(r["selected_f_count"]) for r in joint_rows if float(r["gain_vs_fixed_fastest_percent"]) > 0]

        # Temperature spread from M21
        temp_spread = float(m21_row.get("avg_temperature_spread_c", 0)) if m21_row else 0

        # Shared BIST group count from M21
        bist_groups = float(m21_row.get("avg_shared_bist_group_count", 0)) if m21_row else 0

        result[topo] = {
            "avg_gain": float(m21_row["avg_joint_gain_percent"]) if m21_row else np.mean(gains) if gains else 0,
            "min_gain": float(m21_row["min_joint_gain_percent"]) if m21_row else min(gains) if gains else 0,
            "max_gain": float(m21_row["max_joint_gain_percent"]) if m21_row else max(gains) if gains else 0,
            "gains": gains,
            "case_gains": case_gains,
            "avg_fpp_util": np.mean(fpp_utils) if fpp_utils else 0,
            "avg_fixed_b": np.mean(fixed_b_counts) if fixed_b_counts else 0,
            "avg_joint_b": np.mean(joint_b_counts) if joint_b_counts else 0,
            "avg_joint_f": np.mean(joint_f_counts) if joint_f_counts else 0,
            "temp_spread": temp_spread,
            "bist_groups": bist_groups,
        }

    return result


def configure_matplotlib() -> None:
    available = {font.name for font in fm.fontManager.ttflist}
    candidates = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS", "DejaVu Sans"]
    chosen = next((font for font in candidates if font in available), "DejaVu Sans")
    plt.rcParams.update(
        {
            "font.family": chosen,
            "axes.unicode_minus": False,
            "axes.titlesize": 13,
            "axes.labelsize": 11,
            "xtick.labelsize": 10,
            "ytick.labelsize": 9,
        }
    )


def panel_a_gain_by_topology(ax: Any, data: dict, colors: dict) -> None:
    """Grouped bar chart: joint gain by topology with error bars and scatter points."""
    topologies = TOPOLOGY_ORDER
    x = np.arange(len(topologies))
    width = 0.5

    avg_gains = [data[t]["avg_gain"] for t in topologies]
    min_gains = [data[t]["min_gain"] for t in topologies]
    max_gains = [data[t]["max_gain"] for t in topologies]

    yerr_lower = [avg - lo for avg, lo in zip(avg_gains, min_gains)]
    yerr_upper = [hi - avg for avg, hi in zip(avg_gains, max_gains)]
    yerr = [yerr_lower, yerr_upper]

    bars = ax.bar(
        x,
        avg_gains,
        width,
        color=colors["bar"],
        edgecolor="#333333",
        linewidth=0.8,
        yerr=yerr,
        capsize=8,
        error_kw={"linewidth": 1.5, "ecolor": "#555555"},
        zorder=2,
    )

    # Overlay individual case points as small dots
    for i, topo in enumerate(topologies):
        case_gains = data[topo]["case_gains"]
        # Jitter the scatter x positions slightly
        n_cases = len(case_gains)
        if n_cases > 0:
            jitter = np.random.default_rng(42).uniform(-0.18, 0.18, n_cases)
            ax.scatter(
                x[i] + jitter,
                list(case_gains.values()),
                color=colors["scatter"],
                edgecolor="#333333",
                linewidth=0.4,
                s=48,
                zorder=4,
                alpha=0.85,
            )

    # Annotate the average value on or above each bar
    for i, (avg, mx) in enumerate(zip(avg_gains, max_gains)):
        ax.text(
            x[i],
            mx + 1.5,
            f"{avg:.1f}%",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
            color="#222222",
        )

    ax.set_xticks(x)
    ax.set_xticklabels(TOPOLOGY_LABELS)
    ax.set_ylabel("Joint Gain vs Fixed-Fastest (%)")
    ax.set_title("(a) Gain by Topology", loc="left", fontweight="bold")
    ax.set_ylim(0, max(max_gains) * 1.25)
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)


def panel_b_resource_annotation(ax: Any, data: dict, colors: dict) -> None:
    """Visual annotation panel explaining why gains differ across topologies."""
    topologies = TOPOLOGY_ORDER
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_title("(b) Resource Feature Annotation", loc="left", fontweight="bold")

    # Layout: three columns for the three topologies
    col_centers = [1.8, 5.0, 8.2]
    col_width = 2.2

    for i, topo in enumerate(topologies):
        cx = col_centers[i]
        d = data[topo]

        # Topology name badge
        ax.add_patch(
            plt.Rectangle(
                (cx - col_width / 2, 8.0),
                col_width,
                1.2,
                facecolor=colors["badge"][i],
                edgecolor="#333333",
                linewidth=1.0,
                alpha=0.85,
            )
        )
        ax.text(
            cx,
            8.6,
            TOPOLOGY_SHORT[i],
            ha="center",
            va="center",
            fontsize=11,
            fontweight="bold",
            color="white",
        )

        # Resource metrics as text rows
        metrics = [
            (f"FPP util: {d['avg_fpp_util']:.1%}", 7.0),
            (f"BIST groups: {d['bist_groups']:.1f}", 5.8),
            (f"Joint B count: {d['avg_joint_b']:.1f}", 4.6),
            (f"Joint F count: {d['avg_joint_f']:.1f}", 3.4),
            (f"Temp spread: {d['temp_spread']:.1f}°C", 2.2),
        ]
        for text, y_pos in metrics:
            ax.text(cx, y_pos, text, ha="center", va="center", fontsize=9, color="#333333")

        # Physical annotation text below
        annotation = ANNOTATIONS[topo]
        ax.text(
            cx,
            0.5,
            annotation,
            ha="center",
            va="center",
            fontsize=8,
            color=colors["annotation_text"],
            style="italic",
            bbox=dict(boxstyle="round,pad=0.4", facecolor=colors["ann_bg"], edgecolor="#999999", alpha=0.7),
        )


def panel_c_thermal_spread(ax: Any, data: dict, colors: dict) -> None:
    """Box chart or bar chart showing temperature spread across dies by topology."""
    topologies = TOPOLOGY_ORDER
    x = np.arange(len(topologies))
    width = 0.5

    temp_spreads = [data[t]["temp_spread"] for t in topologies]
    bar_colors = [colors["bar"], "#e15759", "#f28e2b"]

    # Draw bars with clear visual emphasis
    bars = ax.bar(
        x,
        temp_spreads,
        width,
        color=bar_colors,
        edgecolor="#333333",
        linewidth=0.8,
        zorder=2,
    )

    # Annotate values on top of bars
    for i, val in enumerate(temp_spreads):
        ax.text(
            x[i],
            val + 0.3,
            f"{val:.1f}°C",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
            color="#222222",
        )

    ax.set_xticks(x)
    ax.set_xticklabels(TOPOLOGY_LABELS)
    ax.set_ylabel("Temperature Spread (max-min, °C)")
    ax.set_title("(c) Thermal Spread by Topology", loc="left", fontweight="bold")
    ax.set_ylim(0, max(temp_spreads) * 1.25)
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)

    # Add a horizontal span to highlight the region
    ax.axhspan(0, max(temp_spreads), alpha=0.04, color="#e15759")
    ax.axhline(np.mean(temp_spreads), color="#888888", linestyle="--", linewidth=1.0, alpha=0.6)
    ax.text(
        len(topologies) - 0.5,
        np.mean(temp_spreads) + 0.4,
        f"Mean: {np.mean(temp_spreads):.1f}°C",
        fontsize=8,
        color="#888888",
        ha="right",
    )


def main() -> None:
    configure_matplotlib()

    m22_rows = read_csv(M22_TABLE)
    m21_rows = read_csv(M21_TABLE)
    filtered = filter_m22_rows(m22_rows)
    data = collect_topology_data(filtered, m21_rows)

    figure_dir = PROJECT_ROOT / FIGURE_DIR
    figure_dir.mkdir(parents=True, exist_ok=True)

    colors = {
        "bar": "#4e79a7",
        "scatter": "#e15759",
        "badge": ["#4e79a7", "#e15759", "#f28e2b"],
        "annotation_text": "#555555",
        "ann_bg": "#f5f5f5",
    }

    fig = plt.figure(figsize=(16, 6))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.0, 1.2, 0.85], wspace=0.35)

    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[0, 2])

    panel_a_gain_by_topology(ax_a, data, colors)
    panel_b_resource_annotation(ax_b, data, colors)
    panel_c_thermal_spread(ax_c, data, colors)

    fig.suptitle(
        "Fig. 7  Topology Impact on Joint Scheduling Effectiveness",
        y=0.995,
        fontsize=16,
        fontweight="bold",
    )

    fig.subplots_adjust(wspace=0.35, top=0.88, bottom=0.1)

    output_path = PROJECT_ROOT / FIGURE_PATH
    fig.savefig(output_path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Figure saved to: {output_path}")

    # Print summary for verification
    for topo in TOPOLOGY_ORDER:
        d = data[topo]
        print(f"\n{topo}:")
        print(f"  avg_gain={d['avg_gain']:.2f}%, min={d['min_gain']:.2f}%, max={d['max_gain']:.2f}%")
        print(f"  cases={list(d['case_gains'].values())}")
        print(f"  temp_spread={d['temp_spread']:.2f}C, bist_groups={d['bist_groups']:.1f}")
        print(f"  avg_fpp_util={d['avg_fpp_util']:.3f}")


if __name__ == "__main__":
    main()
