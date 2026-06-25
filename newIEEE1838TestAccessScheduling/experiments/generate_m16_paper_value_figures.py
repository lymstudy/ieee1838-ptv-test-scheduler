from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from dataclasses import asdict
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

from experiments.run_m10_benchmark_sweep import resource_variant
from src.model import load_system_model
from src.recipes import RecipeGenerator, pareto_prune, rows_from_recipes
from src.schedulers import ScheduleResult, ScheduledPhase, greedy_schedule, write_schedule_csv


FIGURE_FIELDS = ["figure_id", "path", "title", "source", "notes"]
DEFAULT_CASE = "configs/cases/m10/m10_xlarge_p93791_5_5d_multi_tower.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate M16 paper-value figures from formal M10-M12 results.")
    parser.add_argument("--case", default=DEFAULT_CASE, help="Large representative case for the resource Gantt figure.")
    parser.add_argument("--lane-count", type=int, default=16)
    parser.add_argument("--power-profile", default="nominal", choices=["tight", "nominal", "relaxed"])
    parser.add_argument("--m10-table", default="results/tables/m10_benchmark_sweep.csv")
    parser.add_argument("--m11-table", default="results/tables/m11_algorithm_comparison.csv")
    parser.add_argument("--m12-summary", default="results/tables/m12_thermal_validation_summary.csv")
    parser.add_argument("--m12-trace", default="results/tables/m12_temperature_trace.csv")
    parser.add_argument("--m12b-table", default="results/tables/m12_hotspot_validation_summary.csv")
    parser.add_argument("--figure-dir", default="results/figures/m16")
    parser.add_argument("--schedule-output", default="results/schedules/m16_xlarge_5_5d_m4_greedy_schedule.csv")
    parser.add_argument("--index-output", default="results/tables/m16_figure_index.csv")
    parser.add_argument("--report-output", default="results/reports/m16_paper_value_figures_report.md")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_matplotlib()
    figure_dir = Path(args.figure_dir)
    figure_dir.mkdir(parents=True, exist_ok=True)

    schedule = build_representative_schedule(args.case, args.lane_count, args.power_profile)
    write_schedule_csv(schedule, args.schedule_output)

    entries = [
        plot_resource_gantt(schedule, Path(args.schedule_output), figure_dir),
        plot_power_temperature_hotspots(Path(args.m12_summary), Path(args.m12_trace), Path(args.m12b_table), figure_dir),
        plot_method_comparison(Path(args.m11_table), figure_dir),
        plot_benchmark_coverage(Path(args.m10_table), figure_dir),
    ]
    write_figure_index(entries, Path(args.index_output))
    write_report(entries, Path(args.report_output), schedule, args)
    print(f"figures={len(entries)}")
    print(f"schedule_output={args.schedule_output}")
    print(f"index_output={args.index_output}")
    print(f"report_output={args.report_output}")


def build_representative_schedule(case_path: str, lane_count: int, power_profile: str) -> ScheduleResult:
    base_model = load_system_model(case_path)
    model = resource_variant(base_model, lane_count=lane_count, power_profile=power_profile)
    all_rows = rows_from_recipes(RecipeGenerator(model).generate_all())
    pareto_rows = pareto_prune(all_rows).kept_rows
    return greedy_schedule(model, pareto_rows)


def plot_resource_gantt(schedule: ScheduleResult, schedule_path: Path, figure_dir: Path) -> dict[str, str]:
    phases = sorted(schedule.phases, key=lambda p: (p.start_s, p.end_s, p.target_id))
    makespan_us = schedule.makespan_s * 1e6
    selected_targets = longest_targets(phases, limit=12)
    rows = ["PTAP/STAP\n(serial)"] + [f"FPP Lane {i}" for i in range(8)] + ["DWR/scan\nsegments", "BIST/local\nexecution"]
    rows.extend(selected_targets)
    y_by_row = {name: idx for idx, name in enumerate(rows)}

    colors = {
        "serial": "#8d62c8",
        "fpp": "#f28e2b",
        "dwr": "#4e79a7",
        "bist": "#59a14f",
        "target": "#bab0ac",
    }

    fig, ax = plt.subplots(figsize=(15.5, 8.5))
    target_intervals = target_total_intervals(phases, selected_targets)
    for target_id, (start_s, end_s) in target_intervals.items():
        start = start_s * 1e6
        width = max((end_s - start_s) * 1e6, makespan_us * 0.0015)
        draw_bar(ax, y_by_row[target_id], start, width, colors["target"], target_id.replace("core_", ""))

    for phase in phases:
        start = phase.start_s * 1e6
        width = max((phase.end_s - phase.start_s) * 1e6, makespan_us * 0.0015)
        label = short_phase_label(phase)
        if phase.serial_required:
            draw_bar(ax, y_by_row["PTAP/STAP\n(serial)"], start, width, colors["serial"], label)
        if phase.fpp_lanes_required > 0:
            for lane in range(min(phase.fpp_lanes_required, 8)):
                draw_bar(ax, y_by_row[f"FPP Lane {lane}"], start, width, colors["fpp"], label if lane == 0 else "")
        if phase.dwr_segments and phase.phase_name not in {"CONFIG_ACCESS_PATH", "CONFIG_FPP"}:
            draw_bar(ax, y_by_row["DWR/scan\nsegments"], start, width, colors["dwr"], label)
        if "BIST" in phase.phase_name or "EXECUTE" in phase.phase_name or phase.recipe_type == "B":
            draw_bar(ax, y_by_row["BIST/local\nexecution"], start, width, colors["bist"], label)

    ax.set_title("Fig. 6 IEEE 1838-aware test scheduling Gantt chart")
    ax.set_xlabel("Time (us)")
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(rows)
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.25)
    ax.set_xlim(0, makespan_us * 1.02)
    add_gantt_legend(ax, colors)
    fig.tight_layout()

    path = figure_dir / "m16_ieee1838_resource_gantt_xlarge.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return {
        "figure_id": "m16_ieee1838_resource_gantt_xlarge",
        "path": path.as_posix(),
        "title": "IEEE 1838 resource-layer Gantt chart on xlarge 5.5D case",
        "source": schedule_path.as_posix(),
        "notes": "Formal xlarge p93791 5.5D schedule, showing PTAP/STAP, FPP lanes, DWR/scan, local/BIST, and representative target activity.",
    }


def plot_power_temperature_hotspots(m12_summary: Path, m12_trace: Path, m12b_table: Path, figure_dir: Path) -> dict[str, str]:
    summary_rows = read_csv(m12_summary)
    trace_rows = read_csv(m12_trace)
    hotspot_rows = [row for row in read_csv(m12b_table) if row.get("status") == "ok" and row["case_id"] == "m10_medium_p22810_3d_stack"]
    case_id = "m10_medium_p22810_3d_stack"
    baseline_method = "thermal_min_risk"
    proposed_method = "m4_greedy"
    profile = "stress_proxy"
    baseline_id = f"{case_id}::{profile}::{baseline_method}"
    proposed_id = f"{case_id}::{profile}::{proposed_method}"

    power_base = system_power_series(trace_rows, baseline_id)
    power_prop = system_power_series(trace_rows, proposed_id)
    temp_base = peak_temp_series(trace_rows, baseline_id)
    temp_prop = peak_temp_series(trace_rows, proposed_id)
    hotspot_base = hotspot_block_peaks(hotspot_rows, baseline_method)
    hotspot_prop = hotspot_block_peaks(hotspot_rows, proposed_method)

    fig = plt.figure(figsize=(15.5, 6.8))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.05, 1.05, 1.25], wspace=0.32)
    ax_power = fig.add_subplot(gs[0, 0])
    ax_temp = fig.add_subplot(gs[0, 1])
    right = gs[0, 2].subgridspec(1, 3, width_ratios=[1, 1, 0.06], wspace=0.24)
    ax_h0 = fig.add_subplot(right[0, 0])
    ax_h1 = fig.add_subplot(right[0, 1])
    ax_cb = fig.add_subplot(right[0, 2])

    draw_series(ax_power, power_base, "--", "#d62728", "Thermal-risk")
    draw_series(ax_power, power_prop, "-", "#1f77b4", "M4 greedy")
    ax_power.set_title("(a) System active power")
    ax_power.set_xlabel("Time (us)")
    ax_power.set_ylabel("Power (W)")
    ax_power.grid(alpha=0.25)
    ax_power.legend(frameon=False)

    draw_series(ax_temp, temp_base, "--", "#d62728", "Thermal-risk")
    draw_series(ax_temp, temp_prop, "-", "#1f77b4", "M4 greedy")
    ax_temp.set_title("(b) Peak proxy temperature")
    ax_temp.set_xlabel("Time (us)")
    ax_temp.set_ylabel("Temperature (C)")
    ax_temp.grid(alpha=0.25)
    ax_temp.legend(frameon=False)

    matrix_base = block_peak_matrix(hotspot_base)
    matrix_prop = block_peak_matrix(hotspot_prop)
    vmin = min(float(np.min(matrix_base)), float(np.min(matrix_prop)))
    vmax = max(float(np.max(matrix_base)), float(np.max(matrix_prop)))
    image0 = ax_h0.imshow(matrix_base, cmap="turbo", vmin=vmin, vmax=vmax)
    ax_h1.imshow(matrix_prop, cmap="turbo", vmin=vmin, vmax=vmax)
    for ax, title in [(ax_h0, "Thermal-risk\nHotSpot peak"), (ax_h1, "M4 greedy\nHotSpot peak")]:
        ax.set_title(title)
        ax.set_xticks(range(matrix_base.shape[1]))
        ax.set_yticks(range(matrix_base.shape[0]))
        ax.set_xticklabels([str(i + 1) for i in range(matrix_base.shape[1])])
        ax.set_yticklabels(["bottom", "mid", "top"][: matrix_base.shape[0]])
    ax_h1.set_yticklabels([])
    fig.colorbar(image0, cax=ax_cb, label="C")
    fig.suptitle("Fig. 7 Power, temperature and HotSpot hotspot distribution", y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.94])

    path = figure_dir / "m16_power_temperature_hotspot_composite.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return {
        "figure_id": "m16_power_temperature_hotspot_composite",
        "path": path.as_posix(),
        "title": "Power, proxy temperature, and HotSpot hotspot distribution",
        "source": f"{m12_summary.as_posix()};{m12_trace.as_posix()};{m12b_table.as_posix()}",
        "notes": "Composite view for medium p22810 3D stack, using proxy traces for curves and HotSpot block peaks for hotspot maps.",
    }


def plot_method_comparison(m11_table: Path, figure_dir: Path) -> dict[str, str]:
    rows = [row for row in read_csv(m11_table) if row.get("status") == "ok"]
    methods = ["pure_serial", "fixed_fastest", "tam_like", "low_power", "m4_greedy", "m5_cpsat"]
    labels = ["Serial-only", "Fixed-path", "TAM-like", "Power-aware", "M4 greedy", "M5 CP-SAT"]
    colors = ["#e15759", "#f28e2b", "#edc948", "#59a14f", "#4e79a7", "#8d62c8"]
    grouped = {method: [row for row in rows if row["method_id"] == method] for method in methods}
    serial_power = avg(grouped["pure_serial"], "peak_power_w")
    serial_temp = avg(grouped["pure_serial"], "peak_temperature_c")
    metrics = [
        ("(a) Test time\n(lower is better)", [avg(grouped[m], "normalized_makespan") for m in methods], "{:.2f}"),
        ("(b) Peak temp.\n(relative, lower)", [avg(grouped[m], "peak_temperature_c") / serial_temp * 100.0 for m in methods], "{:.1f}"),
        ("(c) Peak power\n(relative, lower)", [avg(grouped[m], "peak_power_w") / serial_power * 100.0 for m in methods], "{:.0f}"),
        ("(d) FPP utilization\n(higher is better)", [avg(grouped[m], "fpp_utilization") * 100.0 for m in methods], "{:.1f}"),
    ]

    fig, axes = plt.subplots(1, 4, figsize=(15.8, 5.8))
    for ax, (title, values, fmt) in zip(axes, metrics):
        ax.bar(range(len(methods)), values, color=colors, edgecolor="#333333", linewidth=0.6)
        ax.set_title(title)
        ax.set_xticks([])
        ax.grid(axis="y", alpha=0.25)
        annotate(ax, values, fmt)
    axes[0].set_ylim(0, max(metrics[0][1]) * 1.25)
    axes[1].set_ylabel("Normalized / percentage")
    handles = [plt.Rectangle((0, 0), 1, 1, color=color, label=label) for color, label in zip(colors, labels)]
    fig.legend(handles=handles, loc="lower center", ncol=6, frameon=True, bbox_to_anchor=(0.5, -0.01))
    fig.suptitle("Fig. 8 Multi-metric comparison of scheduling methods", y=0.98)
    fig.tight_layout(rect=[0, 0.12, 1, 0.92])

    path = figure_dir / "m16_method_comparison_normalized.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return {
        "figure_id": "m16_method_comparison_normalized",
        "path": path.as_posix(),
        "title": "Multi-metric method tradeoff comparison",
        "source": m11_table.as_posix(),
        "notes": "Multi-metric tradeoff view using M11 successful rows. It shows time reduction, thermal/power side effects, and FPP utilization rather than claiming every metric improves.",
    }


def plot_benchmark_coverage(m10_table: Path, figure_dir: Path) -> dict[str, str]:
    rows = read_csv(m10_table)
    unique = {}
    for row in rows:
        unique.setdefault(row["case_id"], row)
    scales = ["small", "medium", "large", "xlarge"]
    topologies = ["2_5d_interposer", "3d_stack", "5_5d_multi_tower"]
    fig, ax = plt.subplots(figsize=(10.8, 5.8))
    ax.set_title("Benchmark coverage matrix")
    ax.set_xticks(range(len(topologies)))
    ax.set_xticklabels(["2.5D", "3D", "5.5D"])
    ax.set_yticks(range(len(scales)))
    ax.set_yticklabels(scales)
    ax.set_xlim(-0.5, len(topologies) - 0.5)
    ax.set_ylim(-0.5, len(scales) - 0.5)
    ax.invert_yaxis()
    for y, scale in enumerate(scales):
        for x, topology in enumerate(topologies):
            row = next(item for item in unique.values() if item["scale"] == scale and item["topology_type"] == topology)
            speed = avg([r for r in rows if r["case_id"] == row["case_id"] and r["method_id"] == "m4_greedy"], "speedup_vs_serial")
            color = plt.cm.YlGnBu(min(speed / 70.0, 1.0))
            ax.add_patch(plt.Rectangle((x - 0.46, y - 0.42), 0.92, 0.84, facecolor=color, edgecolor="#333333", linewidth=0.8))
            text = f"{row['source_soc']}\n{row['die_count']} dies, {row['target_count']} targets\n{row['recipe_count']} recipes\n{speed:.1f}x avg"
            ax.text(x, y, text, ha="center", va="center", fontsize=9)
    ax.set_xlabel("Package topology")
    ax.set_ylabel("Benchmark scale")
    fig.tight_layout()

    path = figure_dir / "m16_benchmark_coverage_matrix.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return {
        "figure_id": "m16_benchmark_coverage_matrix",
        "path": path.as_posix(),
        "title": "Benchmark coverage matrix",
        "source": m10_table.as_posix(),
        "notes": "Shows that the formal benchmark spans 4/6/8/12 dies, three package topologies, target counts, recipe counts, and average M4 speedup.",
    }


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"missing input table: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_figure_index(entries: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIGURE_FIELDS)
        writer.writeheader()
        for entry in entries:
            writer.writerow({field: entry.get(field, "") for field in FIGURE_FIELDS})


def write_report(entries: list[dict[str, str]], output_path: Path, schedule: ScheduleResult, args: argparse.Namespace) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# M16 Paper Value Figures Report",
        "",
        "M16 replaces the weak small-case Gantt view with paper-oriented figures that emphasize the project value.",
        "",
        f"- Representative schedule case: `{schedule.case_id}`",
        f"- Selected recipes: {len(schedule.selected_rows)}",
        f"- Scheduled phases: {len(schedule.phases)}",
        f"- Makespan: {schedule.makespan_s:.9f} s",
        f"- Peak scheduled power: {schedule.peak_power_w:.4f} W",
        "",
        "## Figures",
        "",
        "| figure | path | role |",
        "| --- | --- | --- |",
    ]
    for entry in entries:
        lines.append(f"| `{entry['figure_id']}` | `{entry['path']}` | {entry['notes']} |")
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- The Gantt chart is generated from a formal xlarge M10 case, not the early 4-die M1 example.",
            "- The power and temperature curves use M12 proxy traces, while hotspot maps use M12b HotSpot outputs.",
            "- M16 figures are intended as main paper figures; the M13 representative Gantt should be treated as an explanatory appendix figure.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def configure_matplotlib() -> None:
    available = {font.name for font in fm.fontManager.ttflist}
    candidates = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS", "DejaVu Sans"]
    chosen = next((font for font in candidates if font in available), "DejaVu Sans")
    plt.rcParams.update(
        {
            "font.family": chosen,
            "axes.unicode_minus": False,
            "axes.titlesize": 14,
            "axes.labelsize": 11,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
        }
    )


def draw_bar(ax: Any, y: int, start: float, width: float, color: str, label: str) -> None:
    ax.barh(y, width, left=start, height=0.62, color=color, edgecolor="#333333", linewidth=0.45, alpha=0.88)
    if label and width > 150.0:
        ax.text(start + width / 2, y, label, ha="center", va="center", fontsize=7.5)


def add_gantt_legend(ax: Any, colors: dict[str, str]) -> None:
    handles = [
        plt.Rectangle((0, 0), 1, 1, color=colors["serial"], label="Serial config/read"),
        plt.Rectangle((0, 0), 1, 1, color=colors["fpp"], label="FPP transfer"),
        plt.Rectangle((0, 0), 1, 1, color=colors["dwr"], label="DWR/scan/capture"),
        plt.Rectangle((0, 0), 1, 1, color=colors["bist"], label="BIST/local phase"),
        plt.Rectangle((0, 0), 1, 1, color=colors["target"], label="Target execution"),
    ]
    ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, -0.17), ncol=5, frameon=True)


def longest_targets(phases: list[ScheduledPhase], limit: int) -> list[str]:
    durations: dict[str, float] = defaultdict(float)
    kind_by_target: dict[str, str] = {}
    for phase in phases:
        durations[phase.target_id] += phase.duration_s
        kind_by_target[phase.target_id] = phase.target_kind
    ordered = [target for target, _duration in sorted(durations.items(), key=lambda item: item[1], reverse=True)]
    non_link = [target for target in ordered if kind_by_target.get(target) != "interconnect" and not target.startswith("link_")]
    fill = [target for target in ordered if target not in non_link]
    return (non_link + fill)[:limit]


def target_total_intervals(phases: list[ScheduledPhase], targets: list[str]) -> dict[str, tuple[float, float]]:
    intervals = {}
    for target_id in targets:
        target_phases = [phase for phase in phases if phase.target_id == target_id]
        if target_phases:
            intervals[target_id] = (min(phase.start_s for phase in target_phases), max(phase.end_s for phase in target_phases))
    return intervals


def short_phase_label(phase: ScheduledPhase) -> str:
    name = phase.phase_name
    if name.startswith("CONFIG"):
        return "Cfg"
    if "SHIFT" in name:
        return "Shift"
    if "READ" in name:
        return "Read"
    if "CAPTURE" in name:
        return "Cap"
    if "EXECUTE" in name:
        return "Exec"
    return name[:8]


def system_power_series(rows: list[dict[str, str]], schedule_id: str) -> list[tuple[float, float]]:
    by_time: dict[float, float] = defaultdict(float)
    for row in rows:
        if row["schedule_id"] == schedule_id:
            by_time[float(row["time_s"])] += float(row["active_power_w"])
    return [(time * 1e6, power) for time, power in sorted(by_time.items())]


def peak_temp_series(rows: list[dict[str, str]], schedule_id: str) -> list[tuple[float, float]]:
    by_time: dict[float, float] = {}
    for row in rows:
        if row["schedule_id"] == schedule_id:
            time = float(row["time_s"])
            by_time[time] = max(by_time.get(time, 0.0), float(row["temperature_c"]))
    return [(time * 1e6, temp) for time, temp in sorted(by_time.items())]


def draw_series(ax: Any, series: list[tuple[float, float]], linestyle: str, color: str, label: str) -> None:
    if not series:
        return
    xs, ys = zip(*series)
    ax.plot(xs, ys, linestyle=linestyle, color=color, linewidth=2.0, label=label)


def hotspot_block_peaks(rows: list[dict[str, str]], schedule_id: str) -> dict[str, float]:
    output_path = next((row["hotspot_output_path"] for row in rows if row["schedule_id"] == schedule_id), "")
    if not output_path:
        return {}
    path = Path(output_path)
    tokens = [line.split() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not tokens:
        return {}
    headers = tokens[0]
    peaks = {header: 0.0 for header in headers}
    for values in tokens[1:]:
        for header, value in zip(headers, values):
            temp = float(value)
            if temp > 200.0:
                temp -= 273.15
            peaks[header] = max(peaks[header], temp)
    return peaks


def block_peak_matrix(peaks: dict[str, float]) -> np.ndarray:
    ordered = [peaks[key] for key in sorted(peaks, key=lambda item: int(item.replace("thermal_die", "")))]
    if not ordered:
        return np.zeros((1, 1))
    columns = 2 if len(ordered) <= 6 else 3
    rows = int(np.ceil(len(ordered) / columns))
    matrix = np.full((rows, columns), min(ordered))
    for index, value in enumerate(ordered):
        matrix[index // columns, index % columns] = value
    return matrix


def avg(rows: list[dict[str, str]], field: str) -> float:
    values = [float(row[field]) for row in rows if row.get(field) not in {"", None}]
    return sum(values) / len(values) if values else 0.0


def annotate(ax: Any, values: list[float], fmt: str) -> None:
    offset = max(values) * 0.025 if values else 0.0
    for index, value in enumerate(values):
        ax.text(index, value + offset, fmt.format(value), ha="center", va="bottom", fontsize=8)


if __name__ == "__main__":
    main()
