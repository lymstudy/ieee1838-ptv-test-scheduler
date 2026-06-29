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
# Figure 9 - Method Comparison with Literature Baselines
# ---------------------------------------------------------------------------
# Left panel (a): A-class coverage benchmarks (M10, 3d_stack) - 3 cases
# Right panel (b): B-class pressure benchmarks (M21, 3d_stack) - 3 cases
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# The six method IDs in bar-grouping order (left to right within each group)
METHOD_ORDER = [
    "pure_serial",
    "sen_gupta_po",
    "habiby_pbo",
    "fixed_fastest",
    "m4_greedy",
    "m5_cpsat",
]

METHOD_LABELS = {
    "pure_serial": "Serial\nP1838",
    "sen_gupta_po": "Sen Gupta\n2011",
    "habiby_pbo": "Habiby\n2022",
    "fixed_fastest": "Fixed\nFastest",
    "m4_greedy": "M4\nGreedy",
    "m5_cpsat": "M5\nCP-SAT",
}

# Color palette: literature baselines vs our methods
METHOD_COLORS = {
    "pure_serial": "#999999",      # gray - reference baseline
    "sen_gupta_po": "#a6cee3",     # light blue - literature baseline
    "habiby_pbo": "#6baed6",       # medium blue - literature baseline
    "fixed_fastest": "#fdbf6f",    # orange - our simple baseline
    "m4_greedy": "#66c2a5",        # green - our greedy method
    "m5_cpsat": "#2ca02c",         # dark green - our CP-SAT method
}

# Method families to apply hatching (literature baselines)
HATCH_STYLES = {
    "pure_serial": None,           # no hatch
    "sen_gupta_po": "///",         # literature baseline
    "habiby_pbo": "\\\\\\",        # literature baseline
    "fixed_fastest": None,         # our method - solid
    "m4_greedy": None,             # our method - solid
    "m5_cpsat": None,              # our method - solid
}

# Case ordering for each panel
LEFT_CASES = [
    "m10_small_d695_3d_stack",
    "m10_medium_p22810_3d_stack",
    "m10_large_p34392_3d_stack",
]

RIGHT_CASES = [
    "m21_pressure_small_d695_3d_stack",
    "m21_pressure_medium_p22810_3d_stack",
    "m21_pressure_large_p34392_3d_stack",
]

CASE_SHORT_LABELS = {
    "m10_small_d695_3d_stack": "d695\n(small)",
    "m10_medium_p22810_3d_stack": "p22810\n(medium)",
    "m10_large_p34392_3d_stack": "p34392\n(large)",
    "m21_pressure_small_d695_3d_stack": "d695\n(small)",
    "m21_pressure_medium_p22810_3d_stack": "p22810\n(medium)",
    "m21_pressure_large_p34392_3d_stack": "p34392\n(large)",
}

# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a CSV file and return rows as list of dicts."""
    if not path.exists():
        raise FileNotFoundError(f"missing input table: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_m11_data(m11_path: Path) -> dict[tuple[str, str], float]:
    """
    Load M11 algorithm comparison data.
    Returns mapping (case_id, method_id) -> makespan_s.
    """
    data: dict[tuple[str, str], float] = {}
    for row in read_csv(m11_path):
        case_id = row["case_id"].strip()
        method_id = row["method_id"].strip()
        status = row.get("status", "").strip()
        if status == "ok" or status == "FEASIBLE":
            data[(case_id, method_id)] = float(row["makespan_s"])
    return data


def load_sen_gupta_data(sg_path: Path) -> dict[tuple[str, str], float]:
    """
    Load Sen Gupta 2011 Partial Overlapping baseline data.
    Returns mapping (case_id, method_id) -> makespan_s.
    We map 'po_sen_gupta_2011' -> 'sen_gupta_po'.
    We also pick up 'pure_serial' and 'fixed_fastest' from this file
    as supplementary data for cases where M11 is missing.
    """
    data: dict[tuple[str, str], float] = {}
    for row in read_csv(sg_path):
        case_id = row["case_id"].strip()
        method_id = row["method_id"].strip()
        status = row.get("status", "").strip()
        if status != "ok":
            continue
        mapped_method = method_id
        if method_id == "po_sen_gupta_2011":
            mapped_method = "sen_gupta_po"
        data[(case_id, mapped_method)] = float(row["makespan_s"])
    return data


def load_habiby_data(hb_path: Path) -> dict[tuple[str, str], float]:
    """
    Load Habiby 2022 PBO baseline data.
    Returns mapping (case_id, 'habiby_pbo') -> makespan_s.
    """
    data: dict[tuple[str, str], float] = {}
    for row in read_csv(hb_path):
        case_id = row["case_id"].strip()
        # Only keep OPTIMAL solutions
        if row.get("solver_status", "").strip() == "OPTIMAL":
            data[(case_id, "habiby_pbo")] = float(row["makespan_s"])
    return data


def load_m21_data(m21_path: Path) -> dict[tuple[str, str], float]:
    """
    Load M21 innovation pressure detail data.
    Returns mapping (case_id, method_id) -> makespan_s.
    Maps method_id values: 'pure_serial', 'fixed_fastest', 'm4_greedy', 'm5_cpsat'.
    """
    data: dict[tuple[str, str], float] = {}
    for row in read_csv(m21_path):
        case_id = row["case_id"].strip()
        method_id = row["method_id"].strip()
        status = row.get("status", "").strip()
        if status in ("ok", "FEASIBLE", "OPTIMAL"):
            data[(case_id, method_id)] = float(row["makespan_s"])
    return data


def load_m10_sweep_data(m10_path: Path) -> dict[tuple[str, str], float]:
    """
    Load M10 benchmark sweep data for large cases where M11 is missing.
    Filter to lane_count=8, power_profile=nominal for consistency.
    Returns mapping (case_id, method_id) -> makespan_s.
    """
    data: dict[tuple[str, str], float] = {}
    for row in read_csv(m10_path):
        case_id = row["case_id"].strip()
        method_id = row["method_id"].strip()
        status = row.get("status", "").strip()
        if status != "ok":
            continue
        # Only keep rows with lane_count=8 and power_profile=nominal
        # (matches the M11 convention for small/medium)
        if row.get("lane_count", "").strip() != "8":
            continue
        if row.get("power_profile", "").strip() != "nominal":
            continue
        if method_id in ("pure_serial", "m4_greedy"):
            # Only store if we don't already have data from M11
            key = (case_id, method_id)
            if key not in data:
                data[key] = float(row["makespan_s"])
    return data


# ---------------------------------------------------------------------------
# Data assembly
# ---------------------------------------------------------------------------

def assemble_data(
    m11: dict[tuple[str, str], float],
    sen_gupta: dict[tuple[str, str], float],
    habiby: dict[tuple[str, str], float],
    m21: dict[tuple[str, str], float],
    m10_sweep: dict[tuple[str, str], float],
) -> dict[str, dict[str, float | None]]:
    """
    Build a dictionary keyed by case_id, value is dict of
    method_id -> normalized_makespan (or None if missing).

    Normalization: normalized = makespan_s / pure_serial_makespan_s.
    pure_serial is always normalized to exactly 1.0.
    """
    # Collect all case_ids we care about
    all_cases = LEFT_CASES + RIGHT_CASES

    result: dict[str, dict[str, float | None]] = {}

    for case_id in all_cases:
        methods: dict[str, float | None] = {}

        # --- 1. Get pure_serial makespan (required for normalization) ---
        pure_serial_makespan = None

        # Try M11 first (for M10 coverage cases)
        pure_serial_makespan = m11.get((case_id, "pure_serial"))
        if pure_serial_makespan is None:
            # Try Sen Gupta CSV
            pure_serial_makespan = sen_gupta.get((case_id, "pure_serial"))
        if pure_serial_makespan is None:
            # Try M21 CSV
            pure_serial_makespan = m21.get((case_id, "pure_serial"))

        if pure_serial_makespan is None or pure_serial_makespan <= 0:
            print(f"  [WARN] {case_id}: no pure_serial makespan found, skipping")
            continue

        print(f"\n--- {case_id} ---")
        print(f"  pure_serial makespan_s = {pure_serial_makespan:.6f}")

        # pure_serial itself
        methods["pure_serial"] = 1.0

        # --- 2. Collect makespan for each non-serial method ---
        for method_id in METHOD_ORDER[1:]:  # skip pure_serial
            makespan = None

            # Try M21 first for M21 cases
            if "m21_pressure" in case_id and method_id in ("fixed_fastest", "m4_greedy", "m5_cpsat"):
                makespan = m21.get((case_id, method_id))

            # Try M11 (for M10 cases)
            if makespan is None:
                makespan = m11.get((case_id, method_id))

            # Try Sen Gupta (for literature baseline and supplementary)
            if makespan is None:
                makespan = sen_gupta.get((case_id, method_id))

            # Try Habiby
            if makespan is None:
                makespan = habiby.get((case_id, method_id))

            # Try M10 sweep (for large M10 cases missing from M11)
            if makespan is None:
                makespan = m10_sweep.get((case_id, method_id))

            # Try M21
            if makespan is None:
                makespan = m21.get((case_id, method_id))

            if makespan is not None:
                normalized = makespan / pure_serial_makespan
                methods[method_id] = normalized
                print(f"  {method_id:20s} makespan_s = {makespan:.6f}, normalized = {normalized:.6f}")
            else:
                methods[method_id] = None
                print(f"  {method_id:20s} MISSING")

        result[case_id] = methods

    return result


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_panel(
    ax: plt.Axes,
    case_ids: list[str],
    data: dict[str, dict[str, float | None]],
    title: str,
    annotation: str,
    use_log: bool = False,
) -> None:
    """
    Draw a grouped bar chart on the given axes.

    Parameters
    ----------
    use_log : bool
        If True, use logarithmic y-axis (for pressure benchmarks where
        makespan spans several orders of magnitude).
    """
    n_cases = len(case_ids)
    n_methods = len(METHOD_ORDER)
    bar_width = 0.12
    group_spacing = 0.08  # extra space between groups

    x_positions = np.arange(n_cases) * (n_methods * bar_width + group_spacing)

    # Prepare x offsets for each method within a group
    x_offsets = np.arange(n_methods) * bar_width
    x_offsets -= x_offsets.mean()  # center around 0

    missing_notes: list[str] = []

    # Collect all values to determine y-axis range
    all_values = []
    for case_id in case_ids:
        case_data = data.get(case_id, {})
        for v in case_data.values():
            if v is not None and v > 0:
                all_values.append(v)

    if use_log:
        # For log scale, use a small positive floor so bars with value=0
        # or very tiny values are still visible. The pure_serial=1.0 bar
        # is always present and provides the top anchor.
        min_val = min(all_values) if all_values else 1e-4
        # Floor: ensure nothing is exactly zero
        bar_floor = max(min_val * 0.6, 1e-5)

    for j, case_id in enumerate(case_ids):
        case_data = data.get(case_id, {})
        for i, method_id in enumerate(METHOD_ORDER):
            value = case_data.get(method_id)
            if value is None:
                missing_notes.append(f"{CASE_SHORT_LABELS.get(case_id, case_id).replace(chr(10), ' ')}: "
                                     f"{METHOD_LABELS.get(method_id, method_id).replace(chr(10), ' ')} missing")
                continue

            x = x_positions[j] + x_offsets[i]
            color = METHOD_COLORS.get(method_id, "#333333")
            hatch = HATCH_STYLES.get(method_id, None)
            edgecolor = "#333333"
            linewidth = 0.6

            plot_value = value
            if use_log and plot_value < bar_floor:
                plot_value = bar_floor

            ax.bar(
                x, plot_value, bar_width,
                color=color,
                edgecolor=edgecolor,
                linewidth=linewidth,
                hatch=hatch,
                zorder=3,
            )

            # Add value label above tall bars on log scale
            if use_log and value is not None and value > 0.005:
                ax.text(
                    x, plot_value * 1.15,
                    f"{value:.3f}",
                    ha="center", va="bottom",
                    fontsize=6, rotation=90,
                    color="#333333",
                )

    # Print missing notes to console
    if missing_notes:
        print(f"\n[MISSING DATA for '{title}']")
        for note in missing_notes:
            print(f"  {note}")

    # X-axis labels
    ax.set_xticks(x_positions)
    ax.set_xticklabels([CASE_SHORT_LABELS.get(cid, cid) for cid in case_ids])

    # Add note about missing bars on the figure
    if missing_notes:
        note_text = "Missing: " + "; ".join(missing_notes)
        ax.text(
            0.5, -0.10, note_text,
            transform=ax.transAxes,
            ha="center", va="top",
            fontsize=6, color="#cc3333", fontstyle="italic",
        )

    # Y-axis
    ylabel = "Normalized Makespan\n(relative to Serial P1838, lower is better)"
    ax.set_ylabel(ylabel)

    if use_log:
        ax.set_yscale("log")
        if all_values:
            min_val = min(all_values)
            ymin = min_val * 0.25
            ymax = 1.6  # pure_serial=1.0, give headroom
            ax.set_ylim(ymin, ymax)
        # Use cleaner log tick labels with decimal notation
        ax.yaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(
                lambda y, _: (
                    "1.0" if y >= 0.99
                    else f"{y:.4f}" if y < 0.01 and y >= 0.0001
                    else f"{y:.3f}"
                )
            )
        )
    else:
        ax.set_ylim(bottom=0)
        if all_values:
            ymax = max(all_values) * 1.15
            ymax = max(ymax, 1.05)
            ax.set_ylim(top=ymax)

    # Horizontal reference line for serial baseline (y=1.0)
    ax.axhline(y=1.0, color="#999999", linewidth=1.0, linestyle="--", alpha=0.7, zorder=2)
    ax.text(
        1.01, 1.0,
        "Serial\nP1838",
        transform=ax.get_yaxis_transform(),
        va="center", ha="left",
        fontsize=7, color="#999999", fontstyle="italic",
    )

    ax.grid(axis="y", alpha=0.25, zorder=0)

    # Title and annotation
    ax.set_title(title, loc="left", fontweight="bold")
    ax.text(
        0.5, -0.18, annotation,
        transform=ax.transAxes,
        ha="center", va="top",
        fontsize=8, fontstyle="italic", color="#555555",
        wrap=True,
    )


def build_legend(ax: plt.Axes) -> None:
    """
    Build a custom legend that shows both literature baselines and our methods.
    """
    from matplotlib.patches import Patch

    legend_elements = [
        Patch(facecolor=METHOD_COLORS["pure_serial"], edgecolor="#333333",
              linewidth=0.6, label="Serial P1838 (baseline)"),
        Patch(facecolor=METHOD_COLORS["sen_gupta_po"], edgecolor="#333333",
              linewidth=0.6, hatch="///", label="Sen Gupta 2011 (lit.)"),
        Patch(facecolor=METHOD_COLORS["habiby_pbo"], edgecolor="#333333",
              linewidth=0.6, hatch="\\\\\\", label="Habiby 2022 (lit.)"),
        Patch(facecolor=METHOD_COLORS["fixed_fastest"], edgecolor="#333333",
              linewidth=0.6, label="Fixed Fastest (our baseline)"),
        Patch(facecolor=METHOD_COLORS["m4_greedy"], edgecolor="#333333",
              linewidth=0.6, label="M4 Greedy (ours)"),
        Patch(facecolor=METHOD_COLORS["m5_cpsat"], edgecolor="#333333",
              linewidth=0.6, label="M5 CP-SAT (ours)"),
    ]
    ax.legend(
        handles=legend_elements,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.35),
        ncol=3,
        frameon=False,
        fontsize=8,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Figure 9: Method Comparison with Literature Baselines."
    )
    parser.add_argument(
        "--m11-table",
        default="results/tables/m11_algorithm_comparison.csv",
        help="Path to M11 algorithm comparison CSV.",
    )
    parser.add_argument(
        "--sen-gupta-table",
        default="results/tables/sen_gupta_po_baseline.csv",
        help="Path to Sen Gupta 2011 PO baseline CSV.",
    )
    parser.add_argument(
        "--habiby-table",
        default="results/tables/habiby_pbo_baseline.csv",
        help="Path to Habiby 2022 PBO baseline CSV.",
    )
    parser.add_argument(
        "--m21-table",
        default="results/tables/m21_innovation_pressure_detail.csv",
        help="Path to M21 innovation pressure detail CSV.",
    )
    parser.add_argument(
        "--m10-table",
        default="results/tables/m10_benchmark_sweep.csv",
        help="Path to M10 benchmark sweep CSV (for large case supplementary data).",
    )
    parser.add_argument(
        "--figure-dir",
        default="results/figures/revised",
        help="Output directory for the figure.",
    )
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
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
    })


def main() -> None:
    args = parse_args()
    configure_matplotlib()

    figure_dir = Path(args.figure_dir)
    figure_dir.mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------------------------
    # Load all data sources
    # -----------------------------------------------------------------------
    print("Loading data sources...")

    m11_path = PROJECT_ROOT / args.m11_table
    sg_path = PROJECT_ROOT / args.sen_gupta_table
    hb_path = PROJECT_ROOT / args.habiby_table
    m21_path = PROJECT_ROOT / args.m21_table
    m10_path = PROJECT_ROOT / args.m10_table

    print(f"  M11: {m11_path}")
    m11_data = load_m11_data(m11_path)
    print(f"    loaded {len(m11_data)} entries")

    print(f"  Sen Gupta: {sg_path}")
    sg_data = load_sen_gupta_data(sg_path)
    print(f"    loaded {len(sg_data)} entries")

    print(f"  Habiby: {hb_path}")
    hb_data = load_habiby_data(hb_path)
    print(f"    loaded {len(hb_data)} entries")

    print(f"  M21: {m21_path}")
    m21_data = load_m21_data(m21_path)
    print(f"    loaded {len(m21_data)} entries")

    print(f"  M10 sweep: {m10_path}")
    m10_sweep_data = load_m10_sweep_data(m10_path)
    print(f"    loaded {len(m10_sweep_data)} entries")

    # -----------------------------------------------------------------------
    # Assemble normalized data
    # -----------------------------------------------------------------------
    print("\nAssembling and normalizing data...")
    combined = assemble_data(m11_data, sg_data, hb_data, m21_data, m10_sweep_data)

    # -----------------------------------------------------------------------
    # Plot
    # -----------------------------------------------------------------------
    fig, (ax_left, ax_right) = plt.subplots(
        1, 2, figsize=(16, 7),
    )

    plot_panel(
        ax_left, LEFT_CASES, combined,
        title="(a) Coverage Benchmarks (A-class)",
        annotation=(
            "All methods converge on ordinary benchmarks "
            "(consistent with Habiby 2022, Sen Gupta 2011)"
        ),
        use_log=True,
    )

    plot_panel(
        ax_right, RIGHT_CASES, combined,
        title="(b) Pressure Benchmarks (B-class)",
        annotation=(
            "Joint recipe scheduling outperforms fixed-path baselines "
            "under shared-resource pressure"
        ),
        use_log=True,
    )

    # Shared legend at bottom
    build_legend(ax_right)

    fig.tight_layout(rect=[0, 0.1, 1, 1])
    output_path = figure_dir / "fig9_baseline_comparison.png"
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"\noutput_path={output_path.as_posix()}")


if __name__ == "__main__":
    main()
