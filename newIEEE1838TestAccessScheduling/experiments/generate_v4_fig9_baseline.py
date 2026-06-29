from __future__ import annotations

"""Figure 9 - Baseline Comparison (v4 experiment data vs literature baselines).

Compares our methods against Sen Gupta PO and Habiby PBO baselines.
Since literature baselines were not run on v4 cases, we use a two-panel approach:

  Panel A: Literature baseline data from M10/M21 cases (original baselines)
           showing Sen Gupta PO and Habiby PBO performance vs our methods
           on the cases they were designed for.

  Panel B: v4 experiment results showing pure_serial, m4_greedy, and m5_cpsat
           performance, with a note that the literature baselines would need
           adaptation to run on v4's task-based model.

Output: results/figures/v4_final/fig9_baseline.png
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

V4_CSV = "results/tables/v4_final_experiment.csv"
SEN_GUPTA_CSV = "results/tables/sen_gupta_po_baseline.csv"
HABIBY_CSV = "results/tables/habiby_pbo_baseline.csv"
OUTPUT_DIR = "results/figures/v4_final"
OUTPUT_PATH = "results/figures/v4_final/fig9_baseline.png"

METHOD_ORDER = ["pure_serial", "sen_gupta_po", "habiby_pbo", "m4_greedy", "m5_cpsat"]
METHOD_LABELS = {
    "pure_serial": "Serial\nP1838",
    "sen_gupta_po": "Sen Gupta\n2011 PO",
    "habiby_pbo": "Habiby\n2022 PBO",
    "m4_greedy": "M4\nGreedy",
    "m5_cpsat": "M5\nCP-SAT",
}
METHOD_COLORS = {
    "pure_serial": "#999999",
    "sen_gupta_po": "#a6cee3",
    "habiby_pbo": "#6baed6",
    "m4_greedy": "#fdbf6f",
    "m5_cpsat": "#2ca02c",
}
HATCH_STYLES = {
    "pure_serial": None,
    "sen_gupta_po": "///",
    "habiby_pbo": "\\\\\\",
    "m4_greedy": None,
    "m5_cpsat": None,
}

# Literature baseline cases
M10_CASES = ["m10_small_d695_3d_stack", "m10_medium_p22810_3d_stack", "m10_large_p34392_3d_stack"]
M21_CASES = ["m21_pressure_medium_p22810_3d_stack", "m21_pressure_large_p34392_3d_stack"]

CASE_SHORT = {
    "m10_small_d695_3d_stack": "d695\n(small)",
    "m10_medium_p22810_3d_stack": "p22810\n(medium)",
    "m10_large_p34392_3d_stack": "p34392\n(large)",
    "m21_pressure_medium_p22810_3d_stack": "p22810\n(medium)",
    "m21_pressure_large_p34392_3d_stack": "p34392\n(large)",
}

# v4 cases
V4_CASES = ["v4_small_3d_stack", "v4_4die_3d_stack", "v4_4die_2_5d_interposer"]
V4_SHORT = {
    "v4_small_3d_stack": "Small\n3D",
    "v4_4die_3d_stack": "4-die\n3D",
    "v4_4die_2_5d_interposer": "4-die\n2.5D",
}


def read_csv(path_str: str) -> list[dict[str, str]]:
    path = PROJECT_ROOT / path_str
    if not path.exists():
        raise FileNotFoundError(f"missing input: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def configure_matplotlib() -> None:
    available = {font.name for font in fm.fontManager.ttflist}
    candidates = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS", "DejaVu Sans"]
    chosen = next((font for font in candidates if font in available), "DejaVu Sans")
    plt.rcParams.update({
        "font.family": chosen,
        "axes.unicode_minus": False,
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
    })


def load_literature_data() -> dict[str, dict[str, float | None]]:
    """Load Sen Gupta and Habiby baseline data, normalized to pure_serial."""
    sg_rows = read_csv(SEN_GUPTA_CSV)
    hb_rows = read_csv(HABIBY_CSV)

    # Build data by (case_id, method_id)
    raw: dict[tuple[str, str], float] = {}

    # Sen Gupta data
    for row in sg_rows:
        if row.get("status") == "ok":
            case_id = row["case_id"].strip()
            method_id = row["method_id"].strip()
            if method_id == "po_sen_gupta_2011":
                method_id = "sen_gupta_po"
            raw[(case_id, method_id)] = float(row["makespan_s"])

    # Habiby data
    for row in hb_rows:
        case_id = row["case_id"].strip()
        if row.get("solver_status") == "OPTIMAL":
            raw[(case_id, "habiby_pbo")] = float(row["makespan_s"])

    # Normalize to pure_serial
    result: dict[str, dict[str, float | None]] = {}
    all_cases = M10_CASES + M21_CASES

    for case_id in all_cases:
        pure_serial = raw.get((case_id, "pure_serial"))
        if pure_serial is None or pure_serial <= 0:
            print(f"  [WARN] {case_id}: no pure_serial baseline, skipping")
            continue

        methods: dict[str, float | None] = {"pure_serial": 1.0}
        for method_id in METHOD_ORDER[1:]:
            ms = raw.get((case_id, method_id))
            if ms is not None:
                methods[method_id] = ms / pure_serial
            else:
                methods[method_id] = None
        result[case_id] = methods

    return result


def load_v4_data() -> dict[str, dict[str, float | None]]:
    """Load v4 data, normalized to pure_serial per case."""
    rows = read_csv(V4_CSV)

    # Get unique v4 cases and their pure_serial baselines
    serial_baselines: dict[str, float] = {}
    methods_data: dict[tuple[str, str], float] = {}

    for row in rows:
        if row.get("status") != "ok":
            continue
        case_id = row["case_id"].strip()
        method_id = row["method_id"].strip()
        condition_id = row["condition_id"].strip()
        ms = float(row["makespan_s"])

        # For baseline comparison, we use bist_fpp condition (representative)
        if condition_id in ("serial_baseline", "bist_fpp"):
            if method_id == "m5_cpsat" and condition_id == "serial_baseline":
                serial_baselines[case_id] = ms
            key = (case_id, condition_id, method_id)
            methods_data[key] = ms

    # Build normalized data
    result: dict[str, dict[str, float | None]] = {}
    for case_id in V4_CASES:
        baseline = serial_baselines.get(case_id)
        if baseline is None or baseline <= 0:
            print(f"  [WARN] {case_id}: no serial baseline, skipping")
            continue

        methods: dict[str, float | None] = {"pure_serial": 1.0}

        # M4 greedy (bist_fpp)
        key_m4 = (case_id, "bist_fpp", "m4_greedy")
        if key_m4 in methods_data:
            methods["m4_greedy"] = methods_data[key_m4] / baseline
        else:
            methods["m4_greedy"] = None

        # M5 CP-SAT (bist_fpp)
        key_m5 = (case_id, "bist_fpp", "m5_cpsat")
        if key_m5 in methods_data:
            methods["m5_cpsat"] = methods_data[key_m5] / baseline
        else:
            methods["m5_cpsat"] = None

        # Literature baselines -- not available for v4
        methods["sen_gupta_po"] = None
        methods["habiby_pbo"] = None

        result[case_id] = methods

    return result


def plot_grouped_bars(ax, case_ids: list[str], data: dict[str, dict[str, float | None]],
                      case_labels: dict[str, str], title: str, annotation: str,
                      use_log: bool = False) -> None:
    """Draw grouped bar chart for methods across cases."""
    n_cases = len(case_ids)
    n_methods = len(METHOD_ORDER)
    bar_width = 0.13
    group_spacing = 0.1

    x_positions = np.arange(n_cases) * (n_methods * bar_width + group_spacing)
    x_offsets = np.arange(n_methods) * bar_width
    x_offsets -= x_offsets.mean()

    all_values = []
    missing_notes = []

    for j, case_id in enumerate(case_ids):
        case_data = data.get(case_id, {})
        for i, method_id in enumerate(METHOD_ORDER):
            value = case_data.get(method_id)
            if value is None:
                if method_id in ("sen_gupta_po", "habiby_pbo") and "v4" in case_id:
                    # Expected missing -- baselines not run on v4
                    pass
                else:
                    missing_notes.append(f"{case_labels.get(case_id, case_id)}: {method_id} missing")
                continue

            x = x_positions[j] + x_offsets[i]
            color = METHOD_COLORS[method_id]
            hatch = HATCH_STYLES[method_id]
            bar_floor = min(all_values) * 0.5 if use_log and all_values else 0

            plot_val = value
            if use_log and plot_val < max(bar_floor, 1e-5):
                plot_val = max(bar_floor, 1e-5)

            ax.bar(x, plot_val, bar_width, color=color, edgecolor="#333333",
                   linewidth=0.5, hatch=hatch, zorder=3)

            if value is not None and value > 0 and not use_log:
                ax.text(x, value + (max(all_values) if all_values else 1) * 0.02,
                        f"{value:.3f}", ha="center", va="bottom", fontsize=6, rotation=90,
                        color="#333333")

            if value is not None:
                all_values.append(value)

    if missing_notes:
        print(f"\n[MISSING DATA for '{title}']")
        for note in missing_notes[:5]:
            print(f"  {note}")

    ax.set_xticks(x_positions)
    ax.set_xticklabels([case_labels.get(c, c) for c in case_ids])

    if use_log:
        ax.set_yscale("log")
        if all_values:
            ax.set_ylim(min(all_values) * 0.5, 1.5)

    # Reference line at 1.0 (pure_serial)
    ax.axhline(y=1.0, color="#999999", linewidth=1.0, linestyle="--", alpha=0.7, zorder=2)

    ax.set_ylabel("Normalized Makespan\n(lower is better)")
    ax.set_title(title, loc="left", fontweight="bold")
    ax.grid(axis="y", alpha=0.25, zorder=0)

    # Annotation
    ax.text(0.5, -0.22, annotation, transform=ax.transAxes,
            ha="center", va="top", fontsize=7, fontstyle="italic", color="#555555")


def build_legend(fig, ax) -> None:
    """Shared legend."""
    from matplotlib.patches import Patch
    elements = [
        Patch(facecolor=METHOD_COLORS["pure_serial"], edgecolor="#333333", label="Serial P1838"),
        Patch(facecolor=METHOD_COLORS["sen_gupta_po"], edgecolor="#333333", hatch="///",
              label="Sen Gupta 2011 PO (lit.)"),
        Patch(facecolor=METHOD_COLORS["habiby_pbo"], edgecolor="#333333", hatch="\\\\\\",
              label="Habiby 2022 PBO (lit.)"),
        Patch(facecolor=METHOD_COLORS["m4_greedy"], edgecolor="#333333", label="M4 Greedy (ours)"),
        Patch(facecolor=METHOD_COLORS["m5_cpsat"], edgecolor="#333333", label="M5 CP-SAT (ours)"),
    ]
    fig.legend(handles=elements, loc="lower center", ncol=5, frameon=False, fontsize=7.5)


def main() -> None:
    configure_matplotlib()

    output_dir = PROJECT_ROOT / OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load literature baseline data
    print("Loading literature baseline data...")
    lit_data = load_literature_data()
    for case_id in lit_data:
        print(f"  {case_id}: {lit_data[case_id]}")

    # Load v4 data
    print("\nLoading v4 experiment data...")
    v4_data = load_v4_data()
    for case_id in v4_data:
        print(f"  {case_id}: {v4_data[case_id]}")

    # Two-panel figure
    fig = plt.figure(figsize=(18, 8))

    gs = fig.add_gridspec(1, 2, wspace=0.35)

    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])

    # Panel A: Literature baselines on M10/M21 cases (normalized)
    lit_cases = M10_CASES + M21_CASES
    plot_grouped_bars(
        ax_a, lit_cases, lit_data, CASE_SHORT,
        title="(a) Literature Baselines on M10/M21 Cases",
        annotation="M10: A-class coverage benches. M21: B-class pressure benches. "
                   "All methods normalized to pure_serial. "
                   "Sen Gupta PO and Habiby PBO achieve 1-2 orders of magnitude speedup.",
        use_log=False,
    )

    # Panel B: Our v4 results (bist_fpp condition, m5 CP-SAT vs m4 Greedy)
    # Since literature baselines cannot easily run on v4 task-based model,
    # we show our methods and note this.
    plot_grouped_bars(
        ax_b, V4_CASES, v4_data, V4_SHORT,
        title="(b) Our Methods on v4 Task-Based Cases",
        annotation="v4 task model: mandatory INTEST/BIST/EXTEST/IJTAG, FPP optional per die. "
                   "Literature baselines (Sen Gupta PO, Habiby PBO) not directly applicable -- "
                   "they use recipe-based fixed-path selection; v4 uses task-based scheduling. "
                   "M5 CP-SAT significantly outperforms M4 Greedy.",
        use_log=False,
    )

    # Add text about baseline applicability
    fig.text(0.5, -0.02,
             "NOTE: Sen Gupta PO and Habiby PBO baselines were designed for recipe-based (M10/M21) cases. "
             "They cannot be directly applied to v4 task-based model without significant adaptation. "
             "The v4 results demonstrate our scheduler's performance on the corrected IEEE 1838 model.",
             ha="center", va="top", fontsize=7, fontstyle="italic", color="#cc3333",
             bbox=dict(boxstyle="round,pad=0.4", facecolor="#fff5f5", edgecolor="#cc3333", alpha=0.8),
             transform=fig.transFigure)

    fig.suptitle("Fig. 9  Baseline Comparison -- Method Performance",
                 y=0.99, fontsize=16, fontweight="bold")

    build_legend(fig, ax_b)

    fig.subplots_adjust(top=0.90, bottom=0.15, wspace=0.35)

    output_path = PROJECT_ROOT / OUTPUT_PATH
    fig.savefig(output_path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"\nFigure 9 saved to: {output_path}")


if __name__ == "__main__":
    main()
