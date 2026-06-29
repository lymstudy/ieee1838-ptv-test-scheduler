"""Generate all 10 figures from v4_final_experiment data.

Reads results/tables/v4_final_experiment.csv and schedule CSVs from
results/schedules/v4_final/ to produce publication-ready figures.

Figures:
  1. Makespan comparison across conditions (grouped bar, per-case)
  2. Speedup vs serial_baseline (grouped bar, per-case)
  3. TAP (serial) utilization across conditions
  4. FPP utilization across conditions
  5. BIST overlap ratio across conditions
  6. Max concurrent BIST engines
  7. Peak temperature across conditions
  8. Makespan vs die count / topology scaling
  9. CP-SAT vs Greedy comparison
  10. Gantt chart for best-condition schedule

Usage:
  python experiments/run_v4_final_figures.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CSV_PATH = "results/tables/v4_final_experiment.csv"
SCHEDULE_DIR = Path("results/schedules/v4_final")
OUTPUT_DIR = Path("results/figures/v4_final")

# Color scheme
CONDITION_COLORS = {
    "serial_baseline": "#d62728",    # red
    "bist_only": "#ff7f0e",          # orange
    "fpp_only": "#1f77b4",           # blue
    "bist_fpp": "#2ca02c",           # green
    "bist_fpp_thermal": "#9467bd",   # purple
}

METHOD_STYLES = {
    "m5_cpsat": {"marker": "o", "linestyle": "-", "label": "CP-SAT"},
    "m4_greedy": {"marker": "s", "linestyle": "--", "label": "Greedy"},
}

CONDITION_LABELS = {
    "serial_baseline": "Serial\nBaseline",
    "bist_only": "BIST\nOnly",
    "fpp_only": "FPP\nOnly",
    "bist_fpp": "BIST\n+FPP",
    "bist_fpp_thermal": "BIST+FPP\n+Thermal",
}

# Figure size and style
FIG_W = 10
FIG_H = 6
plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "font.size": 11,
    "axes.titlesize": 14,
    "axes.labelsize": 12,
    "legend.fontsize": 9,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
})


def load_data(csv_path: str | Path) -> list[dict[str, Any]]:
    """Load the experiment CSV."""
    rows: list[dict[str, Any]] = []
    with open(csv_path, "r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            for key in (
                "makespan_s", "makespan_us", "serial_busy_ratio",
                "fpp_utilization", "bist_overlap_ratio",
                "max_concurrent_bist", "peak_temperature_c",
                "thermal_violations", "peak_power_w",
                "solver_wall_time_s", "die_count", "fpp_lane_count",
                "bist_engine_count", "task_count", "variant_count",
                "scheduled_task_count",
            ):
                try:
                    row[key] = float(row[key])
                except (ValueError, TypeError):
                    pass
            for key in ("max_concurrent_bist", "thermal_violations",
                        "die_count", "fpp_lane_count",
                        "bist_engine_count", "task_count",
                        "variant_count", "scheduled_task_count"):
                try:
                    row[key] = int(float(row[key]))
                except (ValueError, TypeError):
                    pass
            rows.append(row)
    return rows


def filter_cpsat(rows: list[dict]) -> list[dict]:
    """Return only CP-SAT results."""
    return [r for r in rows if r.get("method_id") == "m5_cpsat" and r.get("status") == "ok"]


def filter_ok(rows: list[dict]) -> list[dict]:
    """Return only successful results."""
    return [r for r in rows if r.get("status") == "ok"]


def get_case_order(rows: list[dict]) -> list[str]:
    """Unique case_ids in consistent order."""
    seen: set[str] = set()
    order: list[str] = []
    for r in rows:
        cid = str(r["case_id"])
        if cid not in seen:
            seen.add(cid)
            order.append(cid)
    return sorted(order)


def get_condition_order() -> list[str]:
    """Consistent condition order."""
    return ["serial_baseline", "bist_only", "fpp_only", "bist_fpp", "bist_fpp_thermal"]


def short_case_label(case_id: str) -> str:
    """Short label for display."""
    return case_id.replace("v4_", "").replace("_3d_stack", "\n3D").replace("_2_5d_interposer", "\n2.5D")


# ---------------------------------------------------------------------------
# Figure 1: Makespan comparison across conditions (grouped bar)
# ---------------------------------------------------------------------------

def fig1_makespan_comparison(rows: list[dict]) -> None:
    """Grouped bar chart: makespan per case per condition (CP-SAT only)."""
    data = filter_cpsat(rows)
    cases = get_case_order(data)
    conditions = get_condition_order()

    x = np.arange(len(cases))
    width = 0.15
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))

    for i, cond in enumerate(conditions):
        makespans_us = []
        for case in cases:
            match = [r for r in data if r["case_id"] == case and r["condition_id"] == cond]
            makespans_us.append(match[0]["makespan_us"] if match else 0)
        bars = ax.bar(
            x + i * width, makespans_us, width,
            color=CONDITION_COLORS[cond],
            label=CONDITION_LABELS[cond],
            edgecolor="white", linewidth=0.5,
        )

    ax.set_xlabel("Case")
    ax.set_ylabel("Makespan (us)")
    ax.set_title("Figure 1: Makespan Comparison Across Conditions (CP-SAT)")
    ax.set_xticks(x + width * (len(conditions) - 1) / 2)
    ax.set_xticklabels([short_case_label(c) for c in cases])
    ax.legend(loc="upper left", ncol=1)
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_DIR / "fig1_makespan_comparison.png")
    fig.savefig(OUTPUT_DIR / "fig1_makespan_comparison.pdf")
    plt.close(fig)
    print("  Figure 1 saved.")


# ---------------------------------------------------------------------------
# Figure 2: Speedup vs serial_baseline
# ---------------------------------------------------------------------------

def fig2_speedup(rows: list[dict]) -> None:
    """Speedup relative to serial_baseline for each condition (CP-SAT only)."""
    data = filter_cpsat(rows)
    cases = get_case_order(data)
    conditions = [c for c in get_condition_order() if c != "serial_baseline"]

    # Find serial baseline makespans
    baseline = {}
    for case in cases:
        match = [r for r in data if r["case_id"] == case and r["condition_id"] == "serial_baseline"]
        baseline[case] = match[0]["makespan_us"] if match else 1.0

    x = np.arange(len(cases))
    width = 0.2
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))

    for i, cond in enumerate(conditions):
        speedups = []
        for case in cases:
            match = [r for r in data if r["case_id"] == case and r["condition_id"] == cond]
            if match and baseline[case] > 0:
                speedups.append(baseline[case] / match[0]["makespan_us"])
            else:
                speedups.append(0)
        bars = ax.bar(
            x + i * width, speedups, width,
            color=CONDITION_COLORS[cond],
            label=CONDITION_LABELS[cond],
            edgecolor="white", linewidth=0.5,
        )
        # Annotate
        for bar, val in zip(bars, speedups):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                        f"{val:.1f}x", ha="center", va="bottom", fontsize=8)

    ax.axhline(y=1.0, color="gray", linestyle=":", alpha=0.7, label="Serial Baseline")
    ax.set_xlabel("Case")
    ax.set_ylabel("Speedup vs Serial Baseline")
    ax.set_title("Figure 2: Speedup vs Serial Baseline (CP-SAT)")
    ax.set_xticks(x + width * (len(conditions) - 1) / 2)
    ax.set_xticklabels([short_case_label(c) for c in cases])
    ax.legend(loc="upper left", ncol=1)
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig2_speedup.png")
    fig.savefig(OUTPUT_DIR / "fig2_speedup.pdf")
    plt.close(fig)
    print("  Figure 2 saved.")


# ---------------------------------------------------------------------------
# Figure 3: TAP (serial) utilization
# ---------------------------------------------------------------------------

def fig3_tap_utilization(rows: list[dict]) -> None:
    """TAP utilization across conditions and cases."""
    data = filter_ok(rows)
    cases = get_case_order(data)
    conditions = get_condition_order()

    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))

    x = np.arange(len(conditions))
    width = 0.25
    for i, case in enumerate(cases):
        taps = []
        for cond in conditions:
            match = [r for r in data if r["case_id"] == case and r["condition_id"] == cond and r["method_id"] == "m5_cpsat"]
            taps.append(match[0]["serial_busy_ratio"] if match else 0)
        ax.bar(x + i * width, taps, width, label=short_case_label(case), edgecolor="white", linewidth=0.5)

    ax.set_xlabel("Condition")
    ax.set_ylabel("TAP (Serial) Busy Ratio")
    ax.set_title("Figure 3: TAP Utilization Across Conditions (CP-SAT)")
    ax.set_xticks(x + width)
    ax.set_xticklabels([CONDITION_LABELS[c] for c in conditions])
    ax.legend(loc="upper right")
    ax.grid(axis="y", alpha=0.3)
    ax.set_ylim(0, 1.1)
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig3_tap_utilization.png")
    fig.savefig(OUTPUT_DIR / "fig3_tap_utilization.pdf")
    plt.close(fig)
    print("  Figure 3 saved.")


# ---------------------------------------------------------------------------
# Figure 4: FPP utilization
# ---------------------------------------------------------------------------

def fig4_fpp_utilization(rows: list[dict]) -> None:
    """FPP utilization across conditions and cases."""
    data = filter_ok(rows)
    cases = get_case_order(data)
    conditions = get_condition_order()

    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
    x = np.arange(len(conditions))
    width = 0.25

    for i, case in enumerate(cases):
        fpps = []
        for cond in conditions:
            match = [r for r in data if r["case_id"] == case and r["condition_id"] == cond and r["method_id"] == "m5_cpsat"]
            fpps.append(match[0]["fpp_utilization"] if match else 0)
        ax.bar(x + i * width, fpps, width, label=short_case_label(case), edgecolor="white", linewidth=0.5)

    ax.set_xlabel("Condition")
    ax.set_ylabel("FPP Lane Utilization")
    ax.set_title("Figure 4: FPP Utilization Across Conditions (CP-SAT)")
    ax.set_xticks(x + width)
    ax.set_xticklabels([CONDITION_LABELS[c] for c in conditions])
    ax.legend(loc="upper right")
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig4_fpp_utilization.png")
    fig.savefig(OUTPUT_DIR / "fig4_fpp_utilization.pdf")
    plt.close(fig)
    print("  Figure 4 saved.")


# ---------------------------------------------------------------------------
# Figure 5: BIST overlap ratio
# ---------------------------------------------------------------------------

def fig5_bist_overlap(rows: list[dict]) -> None:
    """BIST overlap ratio across conditions (CP-SAT only)."""
    data = filter_cpsat(rows)
    cases = get_case_order(data)
    conditions = get_condition_order()

    x = np.arange(len(cases))
    width = 0.12
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))

    for i, cond in enumerate(conditions):
        overlaps = []
        for case in cases:
            match = [r for r in data if r["case_id"] == case and r["condition_id"] == cond]
            overlaps.append(match[0]["bist_overlap_ratio"] if match else 0)
        bars = ax.bar(
            x + i * width, overlaps, width,
            color=CONDITION_COLORS[cond],
            label=CONDITION_LABELS[cond],
            edgecolor="white", linewidth=0.5,
        )
        # Annotate
        for bar, val in zip(bars, overlaps):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                        f"{val:.2f}", ha="center", va="bottom", fontsize=7, rotation=90)

    ax.set_xlabel("Case")
    ax.set_ylabel("BIST Overlap Ratio")
    ax.set_title("Figure 5: BIST Overlap Ratio (CP-SAT)")
    ax.set_xticks(x + width * (len(conditions) - 1) / 2)
    ax.set_xticklabels([short_case_label(c) for c in cases])
    ax.legend(loc="upper left", ncol=2)
    ax.grid(axis="y", alpha=0.3)
    ax.set_ylim(0, 1.1)
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig5_bist_overlap.png")
    fig.savefig(OUTPUT_DIR / "fig5_bist_overlap.pdf")
    plt.close(fig)
    print("  Figure 5 saved.")


# ---------------------------------------------------------------------------
# Figure 6: Max concurrent BIST engines
# ---------------------------------------------------------------------------

def fig6_max_concurrent_bist(rows: list[dict]) -> None:
    """Max concurrent BIST across conditions."""
    data = filter_cpsat(rows)
    cases = get_case_order(data)
    conditions = get_condition_order()

    x = np.arange(len(cases))
    width = 0.12
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))

    for i, cond in enumerate(conditions):
        max_bists = []
        for case in cases:
            match = [r for r in data if r["case_id"] == case and r["condition_id"] == cond]
            max_bists.append(int(match[0]["max_concurrent_bist"]) if match else 0)
        bars = ax.bar(
            x + i * width, max_bists, width,
            color=CONDITION_COLORS[cond],
            label=CONDITION_LABELS[cond],
            edgecolor="white", linewidth=0.5,
        )
        for bar, val in zip(bars, max_bists):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                        str(val), ha="center", va="bottom", fontsize=8)

    ax.set_xlabel("Case")
    ax.set_ylabel("Max Concurrent BIST Engines")
    ax.set_title("Figure 6: Max Concurrent BIST Engines (CP-SAT)")
    ax.set_xticks(x + width * (len(conditions) - 1) / 2)
    ax.set_xticklabels([short_case_label(c) for c in cases])
    ax.legend(loc="upper left", ncol=2)
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig6_max_concurrent_bist.png")
    fig.savefig(OUTPUT_DIR / "fig6_max_concurrent_bist.pdf")
    plt.close(fig)
    print("  Figure 6 saved.")


# ---------------------------------------------------------------------------
# Figure 7: Peak temperature
# ---------------------------------------------------------------------------

def fig7_peak_temperature(rows: list[dict]) -> None:
    """Peak temperature across conditions (CP-SAT only)."""
    data = filter_cpsat(rows)
    cases = get_case_order(data)
    conditions = get_condition_order()

    x = np.arange(len(cases))
    width = 0.12
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))

    for i, cond in enumerate(conditions):
        temps = []
        for case in cases:
            match = [r for r in data if r["case_id"] == case and r["condition_id"] == cond]
            temps.append(match[0]["peak_temperature_c"] if match else 0)
        bars = ax.bar(
            x + i * width, temps, width,
            color=CONDITION_COLORS[cond],
            label=CONDITION_LABELS[cond],
            edgecolor="white", linewidth=0.5,
        )
        for bar, val in zip(bars, temps):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                        f"{val:.0f}", ha="center", va="bottom", fontsize=6, rotation=90)

    ax.axhline(y=85.0, color="red", linestyle="--", alpha=0.7, label="Thermal Limit (85C)")
    ax.set_xlabel("Case")
    ax.set_ylabel("Peak Temperature (C)")
    ax.set_title("Figure 7: Peak Temperature Across Conditions (CP-SAT)")
    ax.set_xticks(x + width * (len(conditions) - 1) / 2)
    ax.set_xticklabels([short_case_label(c) for c in cases])
    ax.legend(loc="upper left", ncol=2)
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig7_peak_temperature.png")
    fig.savefig(OUTPUT_DIR / "fig7_peak_temperature.pdf")
    plt.close(fig)
    print("  Figure 7 saved.")


# ---------------------------------------------------------------------------
# Figure 8: Makespan vs die count / topology scaling
# ---------------------------------------------------------------------------

def fig8_scaling(rows: list[dict]) -> None:
    """Makespan vs die count, colored by topology (bist_fpp_thermal only, CP-SAT)."""
    data = [r for r in filter_cpsat(rows) if r["condition_id"] == "bist_fpp_thermal"]

    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
    # Group by topology
    topologies: dict[str, list[tuple[int, float, str]]] = {}
    for r in data:
        topo = str(r["topology"])
        topologies.setdefault(topo, []).append((int(r["die_count"]), r["makespan_us"], str(r["case_id"])))

    colors = {"3d_stack": "#1f77b4", "2_5d_interposer": "#ff7f0e"}
    markers = {"3d_stack": "o", "2_5d_interposer": "s"}

    for topo, points in topologies.items():
        points.sort()
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        labels = [p[2] for p in points]
        ax.plot(xs, ys, marker=markers.get(topo, "o"), linestyle="-",
                color=colors.get(topo, "gray"), label=topo, markersize=10)
        for x, y, label in zip(xs, ys, labels):
            ax.annotate(short_case_label(label), (x, y),
                       textcoords="offset points", xytext=(5, 5), fontsize=8)

    ax.set_xlabel("Die Count")
    ax.set_ylabel("Makespan (us)")
    ax.set_title("Figure 8: Makespan Scaling by Topology (bist_fpp_thermal, CP-SAT)")
    ax.legend()
    ax.grid(alpha=0.3)
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig8_scaling.png")
    fig.savefig(OUTPUT_DIR / "fig8_scaling.pdf")
    plt.close(fig)
    print("  Figure 8 saved.")


# ---------------------------------------------------------------------------
# Figure 9: CP-SAT vs Greedy comparison
# ---------------------------------------------------------------------------

def fig9_cpsat_vs_greedy(rows: list[dict]) -> None:
    """Scatter plot: CP-SAT makespan vs Greedy makespan."""
    data = filter_ok(rows)
    cases = get_case_order(data)
    conditions = get_condition_order()

    pairs: list[dict] = []
    for case in cases:
        for cond in conditions:
            cpsat = [r for r in data if r["case_id"] == case and r["condition_id"] == cond and r["method_id"] == "m5_cpsat"]
            greedy = [r for r in data if r["case_id"] == case and r["condition_id"] == cond and r["method_id"] == "m4_greedy"]
            if cpsat and greedy:
                pairs.append({
                    "case": case,
                    "condition": cond,
                    "cpsat_us": cpsat[0]["makespan_us"],
                    "greedy_us": greedy[0]["makespan_us"],
                })

    if not pairs:
        print("  Figure 9: No data for CP-SAT vs Greedy comparison.")
        return

    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))

    for p in pairs:
        color = CONDITION_COLORS.get(p["condition"], "gray")
        ax.scatter(p["greedy_us"], p["cpsat_us"], c=color, s=80,
                   label=p["condition"] if p == pairs[0] or
                   p["condition"] != pairs[list(pairs).index(p)-1]["condition"] else "",
                   alpha=0.7, edgecolors="black", linewidth=0.5)

    # Diagonal line (CP-SAT = Greedy)
    all_vals = [p["cpsat_us"] for p in pairs] + [p["greedy_us"] for p in pairs]
    max_val = max(all_vals)
    ax.plot([0, max_val], [0, max_val], "k--", alpha=0.3, label="CP-SAT = Greedy")
    ax.set_xlabel("Greedy Makespan (us)")
    ax.set_ylabel("CP-SAT Makespan (us)")
    ax.set_title("Figure 9: CP-SAT vs Greedy Comparison")
    ax.legend(loc="upper left", fontsize=8)

    # Compute CP-SAT/Greedy ratio stats
    ratios = [p["cpsat_us"] / p["greedy_us"] for p in pairs if p["greedy_us"] > 0]
    if ratios:
        ax.text(0.05, 0.95,
                f"Mean CP-SAT/Greedy ratio: {np.mean(ratios):.4f}\n"
                f"Median: {np.median(ratios):.4f}\n"
                f"Min: {np.min(ratios):.4f}  Max: {np.max(ratios):.4f}",
                transform=ax.transAxes, fontsize=9, va="top",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))

    ax.grid(alpha=0.3)
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig9_cpsat_vs_greedy.png")
    fig.savefig(OUTPUT_DIR / "fig9_cpsat_vs_greedy.pdf")
    plt.close(fig)
    print("  Figure 9 saved.")


# ---------------------------------------------------------------------------
# Figure 10: Gantt chart for best-condition schedule
# ---------------------------------------------------------------------------

def fig10_gantt(rows: list[dict]) -> None:
    """Gantt chart for v4_4die_3d_stack / bist_fpp_thermal / CP-SAT."""
    # Find the schedule CSV
    schedule_file = SCHEDULE_DIR / "v4_4die_3d_stack__bist_fpp_thermal__cpsat.csv"
    if not schedule_file.exists():
        print(f"  Figure 10: Schedule file not found: {schedule_file}")
        return

    # Read schedule CSV
    phases: list[dict] = []
    with open(schedule_file, "r", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            phases.append({
                "target_id": row["target_id"],
                "die_id": row["die_id"],
                "phase_name": row["phase_name"],
                "start_s": float(row["start_s"]),
                "end_s": float(row["end_s"]),
                "duration_s": float(row["duration_s"]),
                "recipe_type": row["recipe_type"],
                "serial_required": row["serial_required"].strip().lower() in ("1", "true", "yes"),
                "fpp_lanes_required": int(row["fpp_lanes_required"]),
            })

    # Get makespan
    makespan = max(p["end_s"] for p in phases)

    # Create a unique color per die_id
    die_ids = sorted(set(p["die_id"] for p in phases))
    die_colors = plt.cm.tab10(np.linspace(0, 1, max(len(die_ids), 3)))
    die_color_map = {die: die_colors[i % len(die_colors)] for i, die in enumerate(die_ids)}

    # Get unique target_ids for y-axis
    target_ids = sorted(set(p["target_id"] for p in phases))

    fig, ax = plt.subplots(figsize=(14, max(8, len(target_ids) * 0.4)))

    for i, tid in enumerate(target_ids):
        tid_phases = [p for p in phases if p["target_id"] == tid]
        for p in tid_phases:
            color = die_color_map[p["die_id"]]
            ax.barh(i, p["duration_s"], left=p["start_s"], height=0.7,
                    color=color, edgecolor="black", linewidth=0.3, alpha=0.85)
            # Label phase name for significant phases
            if p["duration_s"] > makespan * 0.02:
                mid = p["start_s"] + p["duration_s"] / 2
                short_name = p["phase_name"].replace("CONFIG_", "C_").replace("SERIAL_", "S_").replace("FPP_", "F_")
                ax.text(mid, i, short_name[:12], ha="center", va="center", fontsize=5)

    ax.set_yticks(range(len(target_ids)))
    ax.set_yticklabels(target_ids, fontsize=8)
    ax.set_xlabel("Time (s)")
    ax.set_title("Figure 10: Gantt Chart -- v4_4die_3d_stack / bist_fpp_thermal / CP-SAT")

    # Die legend
    legend_patches = [mpatches.Patch(color=die_color_map[d], label=d) for d in die_ids]
    ax.legend(handles=legend_patches, loc="upper right", fontsize=8, title="Dies")

    ax.grid(axis="x", alpha=0.3)
    ax.set_xlim(0, makespan * 1.02)
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig10_gantt.png")
    fig.savefig(OUTPUT_DIR / "fig10_gantt.pdf")
    plt.close(fig)
    print("  Figure 10 saved.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    csv_path = Path(PROJECT_ROOT) / CSV_PATH
    if not csv_path.exists():
        print(f"ERROR: CSV not found at {csv_path}")
        print("Run the experiment first: python experiments/run_v4_final_experiment.py")
        sys.exit(1)

    rows = load_data(csv_path)
    print(f"Loaded {len(rows)} experiment runs from {csv_path}")
    ok_runs = len([r for r in rows if r.get("status") == "ok"])
    print(f"  Successful: {ok_runs}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\nGenerating figures...")
    fig1_makespan_comparison(rows)
    fig2_speedup(rows)
    fig3_tap_utilization(rows)
    fig4_fpp_utilization(rows)
    fig5_bist_overlap(rows)
    fig6_max_concurrent_bist(rows)
    fig7_peak_temperature(rows)
    fig8_scaling(rows)
    fig9_cpsat_vs_greedy(rows)
    fig10_gantt(rows)

    print(f"\nAll figures saved to: {OUTPUT_DIR}/")
    print(f"Files: {sorted(f.name for f in OUTPUT_DIR.glob('*'))}")


if __name__ == "__main__":
    main()
