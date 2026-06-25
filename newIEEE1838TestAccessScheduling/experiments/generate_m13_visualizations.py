from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


FIGURE_FIELDS = ["figure_id", "path", "title", "source", "notes"]


@dataclass(frozen=True)
class FigureEntry:
    figure_id: str
    path: str
    title: str
    source: str
    notes: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate M13 visualization artifacts from existing experiment outputs.")
    parser.add_argument("--m10-table", default="results/tables/m10_benchmark_sweep.csv")
    parser.add_argument("--m11-table", default="results/tables/m11_algorithm_comparison.csv")
    parser.add_argument("--m12b-table", default="results/tables/m12_hotspot_validation_summary.csv")
    parser.add_argument("--schedule", default="results/schedules/m8_m4_greedy_schedule.csv")
    parser.add_argument(
        "--hotspot-trace",
        default="results/hotspot/m12b_outputs/m10_medium_p22810_3d_stack__m4_greedy.ttrace",
    )
    parser.add_argument("--figure-dir", default="results/figures/m13")
    parser.add_argument("--index-output", default="results/tables/m13_figure_index.csv")
    parser.add_argument("--report-output", default="results/reports/m13_visual_summary.md")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    figure_dir = Path(args.figure_dir)
    figure_dir.mkdir(parents=True, exist_ok=True)

    entries = [
        plot_m10_speedup(Path(args.m10_table), figure_dir),
        plot_m11_algorithm_makespan(Path(args.m11_table), figure_dir),
        plot_hotspot_proxy_comparison(Path(args.m12b_table), figure_dir),
        plot_hotspot_trace_heatmap(Path(args.hotspot_trace), figure_dir),
        plot_schedule_gantt(Path(args.schedule), figure_dir),
    ]

    write_figure_index(entries, Path(args.index_output))
    write_report(entries, Path(args.report_output))
    print(f"figures={len(entries)}")
    print(f"figure_dir={figure_dir.as_posix()}")
    print(f"index_output={args.index_output}")
    print(f"report_output={args.report_output}")


def plot_m10_speedup(table_path: Path, figure_dir: Path) -> FigureEntry:
    rows = [
        row
        for row in read_csv(table_path)
        if row.get("status") == "ok"
        and row.get("method_id") == "m4_greedy"
        and row.get("power_profile") == "nominal"
        and row.get("lane_count") == "8"
    ]
    if not rows:
        raise ValueError("no M10 nominal lane_count=8 m4_greedy rows available")

    rows.sort(key=lambda row: (scale_order(row.get("scale", "")), row.get("topology_type", ""), row.get("case_id", "")))
    labels = [compact_case_label(row) for row in rows]
    speedups = [to_float(row["speedup_vs_serial"]) for row in rows]

    fig, ax = plt.subplots(figsize=(12, 5.4))
    ax.bar(range(len(rows)), speedups, color="#3f6b75")
    ax.set_title("M10 benchmark speedup over pure serial")
    ax.set_ylabel("Speedup vs serial (x)")
    ax.set_xticks(range(len(rows)))
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.grid(axis="y", alpha=0.25)
    annotate_bars(ax, speedups, "{:.1f}x")
    fig.tight_layout()

    path = figure_dir / "m13_m10_speedup_nominal_lane8.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return FigureEntry(
        "m13_m10_speedup_nominal_lane8",
        path.as_posix(),
        "M10 nominal lane-8 speedup",
        table_path.as_posix(),
        "Uses m4_greedy rows at power_profile=nominal and lane_count=8.",
    )


def plot_m11_algorithm_makespan(table_path: Path, figure_dir: Path) -> FigureEntry:
    rows = [row for row in read_csv(table_path) if row.get("status") == "ok"]
    grouped: dict[str, list[float]] = defaultdict(list)
    labels: dict[str, str] = {}
    for row in rows:
        method = row["method_id"]
        grouped[method].append(to_float(row["normalized_makespan"]))
        labels[method] = row.get("method_label", method)
    if not grouped:
        raise ValueError("no successful M11 rows available")

    method_order = ["pure_serial", "fixed_fastest", "tam_like", "low_power", "m4_all_recipes", "m4_greedy", "m5_cpsat", "m6_alns"]
    methods = [method for method in method_order if method in grouped]
    values = [sum(grouped[method]) / len(grouped[method]) for method in methods]
    display = [short_method_label(method, labels.get(method, method)) for method in methods]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(range(len(methods)), values, color="#7a5c58")
    ax.axhline(1.0, color="#444444", linewidth=1.0, linestyle="--", alpha=0.7)
    ax.set_title("M11 algorithm comparison")
    ax.set_ylabel("Mean normalized makespan")
    ax.set_xticks(range(len(methods)))
    ax.set_xticklabels(display, rotation=25, ha="right")
    ax.grid(axis="y", alpha=0.25)
    annotate_bars(ax, values, "{:.3f}")
    fig.tight_layout()

    path = figure_dir / "m13_m11_algorithm_makespan.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return FigureEntry(
        "m13_m11_algorithm_makespan",
        path.as_posix(),
        "M11 mean normalized makespan by algorithm",
        table_path.as_posix(),
        "Averages successful rows across M11 representative cases; lower is better.",
    )


def plot_hotspot_proxy_comparison(table_path: Path, figure_dir: Path) -> FigureEntry:
    rows = [row for row in read_csv(table_path) if row.get("status") == "ok"]
    if not rows:
        raise ValueError("no successful M12b HotSpot rows available")

    labels = [f"{row['case_id'].replace('m10_', '')}\n{row['schedule_id']}" for row in rows]
    proxy_values = [to_float(row["proxy_peak_temperature_c"]) for row in rows]
    hotspot_values = [to_float(row["hotspot_peak_temperature_c"]) for row in rows]

    fig, axes = plt.subplots(2, 1, figsize=(12, 7.2), sharex=True)
    axes[0].bar(range(len(rows)), proxy_values, color="#6f8f72")
    axes[0].set_title("Thermal proxy peak temperature")
    axes[0].set_ylabel("Proxy peak (C)")
    axes[0].grid(axis="y", alpha=0.25)

    axes[1].bar(range(len(rows)), hotspot_values, color="#b65f3a")
    axes[1].set_title("HotSpot peak temperature")
    axes[1].set_ylabel("HotSpot peak (C)")
    axes[1].set_xticks(range(len(rows)))
    axes[1].set_xticklabels(labels, rotation=30, ha="right")
    axes[1].grid(axis="y", alpha=0.25)
    fig.suptitle("M12b proxy vs HotSpot representative validation", y=0.995)
    fig.tight_layout()

    path = figure_dir / "m13_m12b_proxy_hotspot_peak_comparison.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return FigureEntry(
        "m13_m12b_proxy_hotspot_peak_comparison",
        path.as_posix(),
        "M12b proxy and HotSpot peak comparison",
        table_path.as_posix(),
        "Two-panel plot avoids implying direct numeric equivalence between proxy and HotSpot temperatures.",
    )


def plot_hotspot_trace_heatmap(trace_path: Path, figure_dir: Path) -> FigureEntry:
    headers, samples = read_ttrace(trace_path)
    if not headers or not samples:
        raise ValueError(f"empty HotSpot trace: {trace_path}")
    block_series = list(zip(*samples))

    fig, ax = plt.subplots(figsize=(10, 4.6))
    image = ax.imshow(block_series, aspect="auto", interpolation="nearest", cmap="inferno")
    ax.set_title("HotSpot block temperature trace")
    ax.set_xlabel("Sample index")
    ax.set_ylabel("Thermal block")
    ax.set_yticks(range(len(headers)))
    ax.set_yticklabels(headers)
    cbar = fig.colorbar(image, ax=ax)
    cbar.set_label("Temperature (C)")
    fig.tight_layout()

    path = figure_dir / "m13_hotspot_trace_heatmap_medium_3d_m4_greedy.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return FigureEntry(
        "m13_hotspot_trace_heatmap_medium_3d_m4_greedy",
        path.as_posix(),
        "HotSpot block-level temperature heatmap",
        trace_path.as_posix(),
        "Uses the representative medium 3D m4_greedy HotSpot .ttrace output.",
    )


def plot_schedule_gantt(schedule_path: Path, figure_dir: Path) -> FigureEntry:
    rows = [row for row in read_csv(schedule_path) if row.get("phase_name") in {"FPP_SHIFT_IN", "FPP_SHIFT_OUT", "SERIAL_SHIFT_IN", "SERIAL_SHIFT_OUT", "CAPTURE"}]
    if not rows:
        raise ValueError("no plottable schedule phases available")

    target_order = sorted({row["target_id"] for row in rows})
    target_to_y = {target: index for index, target in enumerate(target_order)}
    color_by_type = {"F": "#3f6b75", "S": "#7a5c58", "I": "#6f8f72"}

    fig_height = max(4.0, min(8.5, 0.42 * len(target_order) + 1.6))
    fig, ax = plt.subplots(figsize=(11, fig_height))
    for row in rows:
        y = target_to_y[row["target_id"]]
        start = to_float(row["start_s"]) * 1e6
        duration = max((to_float(row["end_s"]) - to_float(row["start_s"])) * 1e6, 0.001)
        color = color_by_type.get(row.get("recipe_type", ""), "#999999")
        ax.barh(y, duration, left=start, height=0.62, color=color, alpha=0.88)

    ax.set_title("Representative M4 greedy schedule Gantt view")
    ax.set_xlabel("Time (us)")
    ax.set_ylabel("Target")
    ax.set_yticks(range(len(target_order)))
    ax.set_yticklabels(target_order)
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()

    path = figure_dir / "m13_representative_m4_greedy_gantt.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return FigureEntry(
        "m13_representative_m4_greedy_gantt",
        path.as_posix(),
        "Representative M4 greedy Gantt view",
        schedule_path.as_posix(),
        "Plots scan/capture phases from the existing representative schedule CSV.",
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"missing input table: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_ttrace(path: Path) -> tuple[list[str], list[list[float]]]:
    if not path.exists():
        raise FileNotFoundError(f"missing HotSpot trace: {path}")
    lines = [line.split() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return [], []
    headers = lines[0]
    samples = []
    for tokens in lines[1:]:
        if len(tokens) != len(headers):
            continue
        values = [to_celsius(float(token)) for token in tokens]
        samples.append(values)
    return headers, samples


def write_figure_index(entries: list[FigureEntry], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIGURE_FIELDS)
        writer.writeheader()
        for entry in entries:
            writer.writerow(entry.__dict__)


def write_report(entries: list[FigureEntry], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# M13 Visualization Summary",
        "",
        "M13 converts existing M10/M11/M12b outputs into a small fixed set of publication-oriented figures.",
        "It does not rerun scheduling or HotSpot.",
        "",
        "## Figure Index",
        "",
        "| figure | path | purpose |",
        "| --- | --- | --- |",
    ]
    for entry in entries:
        lines.append(f"| `{entry.figure_id}` | `{entry.path}` | {entry.notes} |")
    lines.extend(
        [
            "",
            "## Interpretation Notes",
            "",
            "- M10 and M11 figures support algorithm and scale comparison.",
            "- M12b figures support representative offline HotSpot validation.",
            "- Proxy and HotSpot values should be discussed as trend validation, not as numerically identical models.",
            "- The HotSpot heatmap is block-level and simplified; it is not industrial thermal signoff.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def annotate_bars(ax: Any, values: list[float], fmt: str) -> None:
    if not values:
        return
    offset = max(values) * 0.015 if max(values) > 0 else 0.01
    for index, value in enumerate(values):
        ax.text(index, value + offset, fmt.format(value), ha="center", va="bottom", fontsize=8)


def compact_case_label(row: dict[str, str]) -> str:
    source = row.get("source_soc", "")
    scale = row.get("scale", "")
    topology = row.get("topology_type", "").replace("_", ".")
    return f"{scale}\n{source}\n{topology}"


def short_method_label(method: str, label: str) -> str:
    overrides = {
        "pure_serial": "serial",
        "fixed_fastest": "fastest",
        "tam_like": "TAM-like",
        "low_power": "low-power",
        "m4_all_recipes": "M4 all",
        "m4_greedy": "M4",
        "m5_cpsat": "M5",
        "m6_alns": "M6",
    }
    return overrides.get(method, label)


def scale_order(scale: str) -> int:
    return {"small": 0, "medium": 1, "large": 2, "xlarge": 3}.get(scale, 99)


def to_float(value: str | float | int) -> float:
    return float(value)


def to_celsius(value: float) -> float:
    return value - 273.15 if value > 200.0 else value


if __name__ == "__main__":
    main()
