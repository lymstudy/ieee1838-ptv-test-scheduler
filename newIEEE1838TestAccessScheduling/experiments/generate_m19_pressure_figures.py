from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
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

from experiments.run_m11_algorithm_study import _fastest_recipe_rows
from src.model import SystemModel, load_system_model
from src.recipes import RecipeGenerator, pareto_prune, rows_from_recipes
from src.schedulers import ScheduleResult, ScheduledPhase, greedy_schedule, solve_cpsat_schedule, write_schedule_csv


DEFAULT_CASE = "configs/cases/m18/m18_shared_bist_8die_3d_stack.json"
FIGURE_FIELDS = ["figure_id", "path", "title", "source", "notes"]


@dataclass(frozen=True)
class FigureEntry:
    figure_id: str
    path: str
    title: str
    source: str
    notes: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate M19 paper figures for M18 resource-pressure results.")
    parser.add_argument("--case", default=DEFAULT_CASE, help="Representative M18 case for schedule figures.")
    parser.add_argument("--m18-table", default="results/tables/m18_pressure_study.csv")
    parser.add_argument("--time-limit-s", type=float, default=5.0, help="CP-SAT time limit for the representative schedule.")
    parser.add_argument("--figure-dir", default="results/figures/m19")
    parser.add_argument("--schedule-dir", default="results/schedules/m19")
    parser.add_argument("--index-output", default="results/tables/m19_figure_index.csv")
    parser.add_argument("--report-output", default="results/reports/m19_pressure_figures_report.md")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_matplotlib()
    figure_dir = Path(args.figure_dir)
    schedule_dir = Path(args.schedule_dir)
    figure_dir.mkdir(parents=True, exist_ok=True)
    schedule_dir.mkdir(parents=True, exist_ok=True)

    model = load_system_model(args.case)
    schedules = build_pressure_schedules(model, time_limit_s=args.time_limit_s)
    fixed_schedule_path = schedule_dir / f"{model.case_id}__fixed_fastest_schedule.csv"
    joint_schedule_path = schedule_dir / f"{model.case_id}__m5_cpsat_schedule.csv"
    write_schedule_csv(schedules["fixed_fastest"], fixed_schedule_path)
    write_schedule_csv(schedules["m5_cpsat"], joint_schedule_path)

    entries = [
        plot_pressure_gantt(
            model,
            schedules["fixed_fastest"],
            schedules["m5_cpsat"],
            fixed_schedule_path,
            joint_schedule_path,
            figure_dir,
        ),
        plot_resource_occupancy(
            model,
            schedules["fixed_fastest"],
            schedules["m5_cpsat"],
            fixed_schedule_path,
            joint_schedule_path,
            figure_dir,
        ),
        plot_m18_pressure_summary(Path(args.m18_table), figure_dir),
    ]
    write_figure_index(entries, Path(args.index_output))
    write_report(entries, Path(args.report_output), model, schedules, Path(args.m18_table))

    print(f"figures={len(entries)}")
    print(f"schedule_dir={args.schedule_dir}")
    print(f"index_output={args.index_output}")
    print(f"report_output={args.report_output}")


def build_pressure_schedules(model: SystemModel, time_limit_s: float = 5.0) -> dict[str, ScheduleResult]:
    all_rows = rows_from_recipes(RecipeGenerator(model).generate_all())
    pareto_rows = pareto_prune(all_rows).kept_rows
    fixed = greedy_schedule(model, _fastest_recipe_rows(pareto_rows))
    m4 = greedy_schedule(model, pareto_rows)
    m5, _info = solve_cpsat_schedule(model, pareto_rows, time_limit_s=time_limit_s)
    return {"fixed_fastest": fixed, "m4_greedy": m4, "m5_cpsat": m5}


def plot_pressure_gantt(
    model: SystemModel,
    fixed: ScheduleResult,
    joint: ScheduleResult,
    fixed_schedule_path: Path,
    joint_schedule_path: Path,
    figure_dir: Path,
) -> FigureEntry:
    fig, axes = plt.subplots(2, 1, figsize=(15.5, 9.0), sharex=True)
    xmax = max(fixed.makespan_s, joint.makespan_s) * 1e6
    draw_pressure_gantt_panel(axes[0], fixed, "Fixed-fastest: every target chooses local BIST", xmax)
    draw_pressure_gantt_panel(axes[1], joint, "Joint selection: BIST/FPP mix keeps resources busy", xmax)
    axes[1].set_xlabel("Time (us)")
    fig.suptitle("M19 controlled resource-pressure Gantt: fixed path vs joint recipe scheduling", y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    path = figure_dir / "m19_pressure_gantt_fixed_vs_joint.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return FigureEntry(
        "m19_pressure_gantt_fixed_vs_joint",
        path.as_posix(),
        "Controlled resource-pressure Gantt: fixed fastest path vs joint recipe scheduling",
        f"{fixed_schedule_path.as_posix()};{joint_schedule_path.as_posix()}",
        "Shows shared BIST serialization in fixed-fastest and BIST/FPP overlap in joint scheduling.",
    )


def draw_pressure_gantt_panel(ax: Any, schedule: ScheduleResult, title: str, xmax_us: float) -> None:
    targets = selected_target_order(schedule)
    rows = ["Shared BIST\nengine", "FPP lanes\n(aggregate)", "PTAP/STAP\nserial"] + targets
    y_by_row = {row: index for index, row in enumerate(rows)}
    colors = {"bist": "#59a14f", "fpp": "#f28e2b", "serial": "#8d62c8", "target": "#b7b7b7"}

    for target_id, (start_s, end_s) in target_intervals(schedule.phases).items():
        if target_id not in y_by_row:
            continue
        draw_bar(ax, y_by_row[target_id], start_s * 1e6, (end_s - start_s) * 1e6, colors["target"], compact_target(target_id), alpha=0.34)

    for phase in sorted(schedule.phases, key=lambda item: (item.start_s, item.end_s, item.target_id)):
        start = phase.start_s * 1e6
        width = max((phase.end_s - phase.start_s) * 1e6, xmax_us * 0.001)
        if phase.phase_name == "LOCAL_BIST_RUN":
            draw_bar(ax, y_by_row["Shared BIST\nengine"], start, width, colors["bist"], compact_target(phase.target_id))
        if phase.fpp_lanes_required > 0:
            label = f"{compact_target(phase.target_id)} ({phase.fpp_lanes_required}L)"
            draw_bar(ax, y_by_row["FPP lanes\n(aggregate)"], start, width, colors["fpp"], label)
        if phase.serial_required:
            draw_bar(ax, y_by_row["PTAP/STAP\nserial"], start, width, colors["serial"], "cfg/read")

    ax.set_title(title, loc="left")
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(rows)
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.25)
    ax.set_xlim(0, xmax_us * 1.03)


def plot_resource_occupancy(
    model: SystemModel,
    fixed: ScheduleResult,
    joint: ScheduleResult,
    fixed_schedule_path: Path,
    joint_schedule_path: Path,
    figure_dir: Path,
) -> FigureEntry:
    total_lanes = int(model.resource_limits["total_fpp_lanes"])
    fig, axes = plt.subplots(1, 2, figsize=(14.2, 5.6), sharey=True)
    for ax, schedule, title in [
        (axes[0], fixed, "Fixed-fastest"),
        (axes[1], joint, "Joint M5 CP-SAT"),
    ]:
        fpp = occupancy_intervals(schedule.phases, "fpp_lanes")
        bist = occupancy_intervals(schedule.phases, "bist_engine")
        draw_step_area(ax, fpp, "#f28e2b", "FPP lanes used")
        draw_step_area(ax, bist, "#59a14f", "Shared BIST engine busy")
        ax.axhline(total_lanes, color="#666666", linestyle="--", linewidth=1.0, label="FPP capacity")
        ax.set_title(title)
        ax.set_xlabel("Time (us)")
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("Resource demand")
    axes[1].legend(frameon=False, loc="upper right")
    fig.suptitle("M19 resource occupancy explains the 46% gain", y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    path = figure_dir / "m19_resource_occupancy_fixed_vs_joint.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return FigureEntry(
        "m19_resource_occupancy_fixed_vs_joint",
        path.as_posix(),
        "Shared BIST engine and FPP lane occupancy",
        f"{fixed_schedule_path.as_posix()};{joint_schedule_path.as_posix()}",
        "Explains that fixed-fastest underuses FPP lanes while serializing on BIST; joint scheduling overlaps both resources.",
    )


def plot_m18_pressure_summary(m18_table: Path, figure_dir: Path) -> FigureEntry:
    rows = [row for row in read_csv(m18_table) if row.get("status") == "ok"]
    case_ids = sorted({row["case_id"] for row in rows})
    labels = [case_label(case_id) for case_id in case_ids]
    fixed = [method_row(rows, case_id, "fixed_fastest") for case_id in case_ids]
    joint = [best_joint_row(rows, case_id) for case_id in case_ids]

    fixed_time = np.array([float(row["makespan_s"]) for row in fixed])
    joint_time = np.array([float(row["makespan_s"]) for row in joint])
    gains = np.array([float(row["gain_vs_fixed_fastest_percent"]) for row in joint])
    fixed_b = np.array([int(row["selected_b_count"]) for row in fixed])
    fixed_f = np.array([int(row["selected_f_count"]) for row in fixed])
    joint_b = np.array([int(row["selected_b_count"]) for row in joint])
    joint_f = np.array([int(row["selected_f_count"]) for row in joint])

    fig, axes = plt.subplots(1, 3, figsize=(15.6, 5.4))
    x = np.arange(len(case_ids))
    width = 0.34
    axes[0].bar(x - width / 2, fixed_time / fixed_time, width, label="Fixed-fastest", color="#e15759")
    axes[0].bar(x + width / 2, joint_time / fixed_time, width, label="Best joint", color="#4e79a7")
    axes[0].set_title("(a) Test time normalized to fixed-fastest")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(labels)
    axes[0].set_ylabel("Normalized time")
    annotate_bars(axes[0], x + width / 2, joint_time / fixed_time, "{:.2f}")

    axes[1].bar(x, gains, color="#59a14f", edgecolor="#333333", linewidth=0.6)
    axes[1].set_title("(b) Joint gain vs fixed-fastest")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels)
    axes[1].set_ylabel("Gain (%)")
    annotate_bars(axes[1], x, gains, "{:.1f}%")

    axes[2].bar(x - width / 2, fixed_b, width, label="Fixed BIST", color="#86bc86")
    axes[2].bar(x - width / 2, fixed_f, width, bottom=fixed_b, label="Fixed FPP", color="#f2b36d")
    axes[2].bar(x + width / 2, joint_b, width, label="Joint BIST", color="#2f7d32")
    axes[2].bar(x + width / 2, joint_f, width, bottom=joint_b, label="Joint FPP", color="#f28e2b")
    axes[2].set_title("(c) Selected recipe mix")
    axes[2].set_xticks(x)
    axes[2].set_xticklabels(labels)
    axes[2].set_ylabel("Target count")
    axes[2].legend(frameon=False, fontsize=8)

    for ax in axes:
        ax.grid(axis="y", alpha=0.25)
    axes[0].legend(frameon=False, loc="upper right")
    fig.suptitle("M19 controlled ablation results on M18 pressure cases", y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    path = figure_dir / "m19_pressure_summary_gain_and_mix.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return FigureEntry(
        "m19_pressure_summary_gain_and_mix",
        path.as_posix(),
        "M18 pressure-case gain and selected recipe mix",
        m18_table.as_posix(),
        "Summarizes the 46% gain and shows that joint schedules deliberately mix BIST and FPP recipes.",
    )


def occupancy_intervals(phases: list[ScheduledPhase], resource: str) -> list[tuple[float, float, float]]:
    boundaries = sorted({time for phase in phases for time in (phase.start_s, phase.end_s)})
    intervals = []
    for left, right in zip(boundaries, boundaries[1:]):
        if right <= left:
            continue
        active = [phase for phase in phases if phase.start_s < right and left < phase.end_s]
        if resource == "fpp_lanes":
            value = float(sum(phase.fpp_lanes_required for phase in active))
        elif resource == "bist_engine":
            value = float(sum(1 for phase in active if phase.phase_name == "LOCAL_BIST_RUN"))
        elif resource == "serial":
            value = float(sum(1 for phase in active if phase.serial_required))
        else:
            raise ValueError(f"unknown resource: {resource}")
        intervals.append((left * 1e6, right * 1e6, value))
    return intervals


def selected_target_order(schedule: ScheduleResult) -> list[str]:
    return [str(row["target_id"]) for row in sorted(schedule.selected_rows, key=lambda row: str(row["target_id"]))]


def target_intervals(phases: list[ScheduledPhase]) -> dict[str, tuple[float, float]]:
    intervals = {}
    for target_id in sorted({phase.target_id for phase in phases}):
        target_phases = [phase for phase in phases if phase.target_id == target_id]
        intervals[target_id] = (min(phase.start_s for phase in target_phases), max(phase.end_s for phase in target_phases))
    return intervals


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"missing input table: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_figure_index(entries: list[FigureEntry], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIGURE_FIELDS)
        writer.writeheader()
        for entry in entries:
            writer.writerow(entry.__dict__)


def write_report(
    entries: list[FigureEntry],
    output_path: Path,
    model: SystemModel,
    schedules: dict[str, ScheduleResult],
    m18_table: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fixed = schedules["fixed_fastest"]
    joint = schedules["m5_cpsat"]
    gain = (fixed.makespan_s - joint.makespan_s) / fixed.makespan_s * 100.0
    lines = [
        "# M19 Pressure Figures Report",
        "",
        "M19 turns the M18 controlled pressure ablation into paper-facing figures.",
        "",
        f"- Representative case: `{model.case_id}`",
        f"- Fixed-fastest makespan: {fixed.makespan_s:.9f} s",
        f"- M5 CP-SAT joint makespan: {joint.makespan_s:.9f} s",
        f"- Joint gain vs fixed-fastest: {gain:.2f}%",
        f"- M18 table source: `{m18_table.as_posix()}`",
        "",
        "## Figures",
        "",
        "| figure | path | purpose |",
        "| --- | --- | --- |",
    ]
    for entry in entries:
        lines.append(f"| `{entry.figure_id}` | `{entry.path}` | {entry.notes} |")
    lines.extend(
        [
            "",
            "## Paper Use",
            "",
            "Use these figures to support a controlled claim: under shared-resource pressure, path selection must be coupled with scheduling.",
            "Do not use them to claim universal dominance on every benchmark; M17 keeps that limitation explicit.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def method_row(rows: list[dict[str, str]], case_id: str, method_id: str) -> dict[str, str]:
    return next(row for row in rows if row["case_id"] == case_id and row["method_id"] == method_id)


def best_joint_row(rows: list[dict[str, str]], case_id: str) -> dict[str, str]:
    candidates = [row for row in rows if row["case_id"] == case_id and row["method_family"] == "joint"]
    return max(candidates, key=lambda row: float(row["gain_vs_fixed_fastest_percent"]))


def case_label(case_id: str) -> str:
    if "12die_5_5d_multi_tower" in case_id:
        return "12-die\n5.5D multi-tower"
    if "8die_3d_stack" in case_id:
        return "8-die\n3D stack"
    return case_id.replace("m18_shared_bist_", "").replace("_", " ")


def draw_bar(ax: Any, y: int, start: float, width: float, color: str, label: str, alpha: float = 0.86) -> None:
    ax.barh(y, width, left=start, height=0.62, color=color, edgecolor="#333333", linewidth=0.45, alpha=alpha)
    if label and width > 900.0:
        ax.text(start + width / 2, y, label, ha="center", va="center", fontsize=7.0)


def draw_step_area(ax: Any, intervals: list[tuple[float, float, float]], color: str, label: str) -> None:
    if not intervals:
        return
    xs = []
    ys = []
    for left, right, value in intervals:
        xs.extend([left, right])
        ys.extend([value, value])
    ax.fill_between(xs, ys, step="post", alpha=0.26, color=color)
    ax.plot(xs, ys, color=color, linewidth=2.0, label=label)


def annotate_bars(ax: Any, xs: Any, values: Any, fmt: str) -> None:
    offset = max(values) * 0.03 if len(values) else 0.0
    for x, value in zip(xs, values):
        ax.text(x, value + offset, fmt.format(value), ha="center", va="bottom", fontsize=8)


def compact_target(target_id: str) -> str:
    return target_id.replace("m18_", "").replace("_die", "\ndie")


def configure_matplotlib() -> None:
    available = {font.name for font in fm.fontManager.ttflist}
    candidates = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS", "DejaVu Sans"]
    chosen = next((font for font in candidates if font in available), "DejaVu Sans")
    plt.rcParams.update(
        {
            "font.family": chosen,
            "axes.unicode_minus": False,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
        }
    )


if __name__ == "__main__":
    main()
