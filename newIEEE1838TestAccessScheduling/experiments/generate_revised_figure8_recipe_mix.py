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
from scipy import stats


ABLATION_ID = "shared_bist_with_parallel_escape"

TOPOLOGY_COLORS = {
    "2_5d_interposer": "#4e79a7",  # blue
    "3d_stack": "#e15759",  # red
    "5_5d_multi_tower": "#8d62c8",  # purple
}

TOPOLOGY_SHORT = {
    "2_5d_interposer": "2.5D",
    "3d_stack": "3D",
    "5_5d_multi_tower": "5.5D",
}

BIST_COLOR = "#59a14f"
FPP_COLOR = "#f28e2b"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate revised Figure 8: Recipe Selection Strategy Evolution."
    )
    parser.add_argument(
        "--m22-table",
        default="results/tables/m22_mechanism_ablation_detail.csv",
        help="Path to M22 mechanism ablation detail CSV.",
    )
    parser.add_argument(
        "--figure-dir",
        default="results/figures/revised",
        help="Output directory for the figure.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_matplotlib()

    table_path = Path(args.m22_table)
    figure_dir = Path(args.figure_dir)
    figure_dir.mkdir(parents=True, exist_ok=True)

    all_rows = read_csv(table_path)
    ablation_rows = [
        row for row in all_rows
        if row.get("ablation_id") == ABLATION_ID and row.get("status") == "ok"
    ]

    if not ablation_rows:
        raise SystemExit(
            f"No rows found for ablation_id={ABLATION_ID} with status=ok"
        )

    cases = gather_cases(ablation_rows)
    ordered = sorted(
        cases,
        key=lambda c: (
            scale_order(c["scale"]),
            topology_order(c["topology_type"]),
        ),
    )

    fig, (ax_bars, ax_scatter) = plt.subplots(
        1, 2, figsize=(16, 6), gridspec_kw={"width_ratios": [1.1, 1]}
    )

    plot_recipe_bars(ax_bars, ordered)
    plot_fpp_gain_scatter(ax_scatter, ordered)

    fig.tight_layout()
    output_path = figure_dir / "m8_recipe_selection_mix.png"
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
    print(f"output_path={output_path.as_posix()}")


def gather_cases(rows: list[dict[str, str]]) -> list[dict]:
    """Group rows by (source_soc, topology_type, scale), extract key method rows."""
    cases = []
    by_case: dict[tuple[str, str, str], dict[str, dict[str, str]]] = {}
    for row in rows:
        key = (row["source_soc"], row["topology_type"], row["scale"])
        by_case.setdefault(key, {})
        by_case[key][row["method_id"]] = row

    for (soc, topo, scale), methods in by_case.items():
        if "fixed_fastest" not in methods or "m4_greedy" not in methods:
            continue
        fixed = methods["fixed_fastest"]
        joint = methods["m4_greedy"]
        target_count = int(fixed["target_count"])
        fixed_b = int(fixed["selected_b_count"])
        fixed_f = int(fixed["selected_f_count"])
        joint_b = int(joint["selected_b_count"])
        joint_f = int(joint["selected_f_count"])
        cases.append({
            "soc": soc,
            "topology_type": topo,
            "topology_label": TOPOLOGY_SHORT.get(topo, topo),
            "scale": scale,
            "target_count": target_count,
            "fixed_b": fixed_b,
            "fixed_f": fixed_f,
            "joint_b": joint_b,
            "joint_f": joint_f,
            "fpp_ratio": joint_f / target_count if target_count > 0 else 0.0,
            "gain_percent": float(joint.get("gain_vs_fixed_fastest_percent", 0.0)),
        })
    return cases


def plot_recipe_bars(ax, cases: list[dict]) -> None:
    n = len(cases)
    x = np.arange(n)
    width = 0.34

    labels = [
        f"{c['soc']}\n{c['topology_label']}"
        for c in cases
    ]

    # Fixed bars: all BIST (no FPP)
    fixed_b_vals = [c["fixed_b"] for c in cases]
    fixed_f_vals = [c["fixed_f"] for c in cases]
    ax.bar(
        x - width / 2, fixed_b_vals, width,
        label="BIST", color=BIST_COLOR, edgecolor="#333333", linewidth=0.5,
    )
    # If any fixed case has FPP targets, stack them
    if any(v > 0 for v in fixed_f_vals):
        ax.bar(
            x - width / 2, fixed_f_vals, width,
            bottom=fixed_b_vals,
            label="FPP (fixed)", color=FPP_COLOR, edgecolor="#333333",
            linewidth=0.5, alpha=0.5,
        )

    # Joint bars: stacked BIST + FPP
    joint_b_vals = [c["joint_b"] for c in cases]
    joint_f_vals = [c["joint_f"] for c in cases]
    ax.bar(
        x + width / 2, joint_b_vals, width,
        color=BIST_COLOR, edgecolor="#333333", linewidth=0.5,
    )
    ax.bar(
        x + width / 2, joint_f_vals, width,
        bottom=joint_b_vals,
        label="FPP", color=FPP_COLOR, edgecolor="#333333", linewidth=0.5,
    )

    # Add Fixed/Joint labels below each pair
    for i in range(n):
        ax.text(
            i - width / 2, -max(fixed_b_vals + joint_b_vals + joint_f_vals) * 0.03,
            "Fixed", ha="center", va="top", fontsize=8, fontstyle="italic",
            color="#666666",
        )
        ax.text(
            i + width / 2, -max(fixed_b_vals + joint_b_vals + joint_f_vals) * 0.03,
            "Joint", ha="center", va="top", fontsize=8, fontstyle="italic",
            color="#666666",
        )

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Number of Targets")
    ax.set_title("(a) Recipe Selection: Fixed vs Joint", loc="left")
    ax.legend(frameon=False, fontsize=9)
    ax.grid(axis="y", alpha=0.25)

    # Ensure y=0 is visible
    ax.set_ylim(bottom=0)
    ymax = max(
        max(fixed_b_vals) + max(fixed_f_vals),
        max(joint_b_vals) + max(joint_f_vals),
    )
    ax.set_ylim(top=ymax * 1.12)


def plot_fpp_gain_scatter(ax, cases: list[dict]) -> None:
    fpp_ratios = np.array([c["fpp_ratio"] for c in cases])
    gains = np.array([c["gain_percent"] for c in cases])
    topologies = [c["topology_type"] for c in cases]
    socs = [c["soc"] for c in cases]

    unique_topos = sorted(set(topologies), key=topology_order)

    for topo in unique_topos:
        mask = [t == topo for t in topologies]
        xs = fpp_ratios[mask]
        ys = gains[mask]
        color = TOPOLOGY_COLORS.get(topo, "#333333")
        label = TOPOLOGY_SHORT.get(topo, topo)
        ax.scatter(
            xs, ys,
            s=80, color=color, edgecolors="#333333",
            linewidths=0.5, zorder=3, label=label,
        )
        # Annotate points with SOC name
        for idx in np.where(mask)[0]:
            ax.annotate(
                socs[idx],
                (fpp_ratios[idx], gains[idx]),
                textcoords="offset points",
                xytext=(5, 5),
                fontsize=7,
                color=color,
            )

    # Fit linear trend line
    slope, intercept, r_value, _p_value, _std_err = stats.linregress(
        fpp_ratios, gains
    )
    r_squared = r_value ** 2

    xline = np.linspace(fpp_ratios.min() * 0.8, fpp_ratios.max() * 1.15, 100)
    yline = slope * xline + intercept
    ax.plot(
        xline, yline,
        "--", color="#333333", linewidth=1.5, alpha=0.7,
        label=f"Trend (R$^2$={r_squared:.3f})",
    )

    # Confidence band (95% CI)
    n = len(fpp_ratios)
    x_mean = np.mean(fpp_ratios)
    residuals = gains - (slope * fpp_ratios + intercept)
    residual_std = np.sqrt(np.sum(residuals ** 2) / (n - 2))
    t_val = stats.t.ppf(0.975, n - 2)
    se_line = residual_std * np.sqrt(
        1 / n + (xline - x_mean) ** 2 / np.sum((fpp_ratios - x_mean) ** 2)
    )
    ci_upper = yline + t_val * se_line
    ci_lower = yline - t_val * se_line
    ax.fill_between(
        xline, ci_lower, ci_upper,
        color="#333333", alpha=0.08, zorder=1, label="95% CI",
    )

    ax.set_xlabel("FPP Selection Ratio in Joint Schedule")
    ax.set_ylabel("Joint Gain vs Fixed-Fastest (%)")
    ax.set_title("(b) FPP Mix Ratio vs. Scheduling Gain", loc="left")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False, fontsize=8)

    # Ensure axes start at 0
    ax.set_xlim(left=max(xline[0] - 0.02, 0))
    ax.set_ylim(bottom=min(0, gains.min() * 1.1))


def scale_order(scale: str) -> int:
    order = {"small": 0, "medium": 1, "large": 2, "xlarge": 3}
    return order.get(scale, 99)


def topology_order(topo: str) -> int:
    order = {"2_5d_interposer": 0, "3d_stack": 1, "5_5d_multi_tower": 2}
    return order.get(topo, 99)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"missing input table: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


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
        "axes.titlesize": 13,
        "axes.labelsize": 11,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
    })


if __name__ == "__main__":
    main()
