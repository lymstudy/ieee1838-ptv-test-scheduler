"""Publication-quality figures + CSV output for IEEE 1838 test scheduling.

Uses only model.py, stdlib, and matplotlib.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.gridspec import GridSpec

from model import ScheduledPhase, ScheduleResult


# ---------------------------------------------------------------------------
# Matplotlib configuration
# ---------------------------------------------------------------------------

def configure_matplotlib():
    """Set up matplotlib for CJK-capable headless rendering."""
    matplotlib.use("Agg")

    # Try CJK-capable fonts in descending preference, falling back to DejaVu Sans
    _candidate_fonts = [
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "DejaVu Sans",
    ]
    _available = {f.name for f in matplotlib.font_manager.fontManager.ttflist}
    _font = "DejaVu Sans"
    for _c in _candidate_fonts:
        if _c in _available:
            _font = _c
            break

    matplotlib.rcParams.update(
        {
            "figure.dpi": 150,
            "savefig.dpi": 150,
            "savefig.bbox": "tight",
            "font.family": _font,
            "font.size": 10,
        }
    )


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

# Phase-type colour mapping
# TAP-SHIFT and FPP-SHIFT get distinct colours so the chart shows
# which chiplets actually have high-speed parallel access.
_PHASE_COLORS = {
    "CONFIG":     "#3498db",   # blue
    "SHIFT_IN_TAP":   "#1e8449",   # dark green  — serial TAP shift-in
    "SHIFT_IN_FPP":   "#1abc9c",   # teal/cyan   — parallel FPP shift-in
    "SHIFT_OUT_TAP":  "#145a32",   # darker green — serial TAP shift-out
    "SHIFT_OUT_FPP":  "#16a085",   # darker teal — parallel FPP shift-out
    "EXECUTE":    "#e67e22",   # orange — BIST local execution
    "CAPTURE":    "#e74c3c",   # red
    "READOUT":    "#9b59b6",   # purple
}

def _phase_color(phase_name: str, needs_fpp_lanes: int) -> str:
    """Return the display colour for a scheduled phase."""
    if phase_name == "SHIFT_IN":
        return _PHASE_COLORS["SHIFT_IN_FPP"] if needs_fpp_lanes > 0 else _PHASE_COLORS["SHIFT_IN_TAP"]
    if phase_name == "SHIFT_OUT":
        return _PHASE_COLORS["SHIFT_OUT_FPP"] if needs_fpp_lanes > 0 else _PHASE_COLORS["SHIFT_OUT_TAP"]
    if phase_name == "SHIFT":  # legacy
        return _PHASE_COLORS["SHIFT_IN_FPP"] if needs_fpp_lanes > 0 else _PHASE_COLORS["SHIFT_IN_TAP"]
    return _PHASE_COLORS.get(phase_name, "#7f8c8d")

def _phase_label(phase_name: str, needs_fpp_lanes: int) -> str:
    """Return the legend label for a phase."""
    if phase_name in ("SHIFT_IN", "SHIFT"):
        return "SHIFT-FPP" if needs_fpp_lanes > 0 else "SHIFT-TAP"
    if phase_name == "SHIFT_OUT":
        return "SHIFT-OUT-FPP" if needs_fpp_lanes > 0 else "SHIFT-OUT-TAP"
    return phase_name


def _s_to_us(values: list[float]) -> list[float]:
    """Convert seconds to microseconds."""
    return [v * 1e6 for v in values]


def _short_label(case_id: str) -> str:
    """Heuristic short case label for comparison charts.

    E.g. ``m21_pressure_small_d695_2_5d_interposer`` → ``d695\n2.5D``
    """
    if not case_id:
        return "?"
    parts = case_id.split("_")
    # Try to find a leading "d<digits>" token
    die_idx = None
    for i, p in enumerate(parts):
        if p.startswith("d") and p[1:].isdigit():
            die_idx = i
            break

    if die_idx is not None:
        label = parts[die_idx]
        # Look for topology hints after the die token
        rest = "_".join(parts[die_idx + 1 :])
        if "interposer" in rest:
            label += "\n2.5D"
        elif "multi_tower" in rest:
            label += "\n5.5D"
        elif "3d" in rest.lower():
            label += "\n3D"
        elif "stack" in rest:
            label += "\n3D"
        else:
            label += "\n" + parts[-1][:8] if parts[-1] else ""
        return label

    # Fallback: last two meaningful tokens
    meaningful = [p for p in parts if p and not p.startswith("m")]
    if len(meaningful) >= 2:
        return meaningful[-2][:10] + "\n" + meaningful[-1][:10]
    return parts[-1][:16] if parts[-1] else "?"


def _build_power_profile(
    phases: list[ScheduledPhase],
) -> tuple[list[float], list[float]]:
    """Return (time_us, power_w) arrays by stepping through sorted phase edges."""
    if not phases:
        return [0.0, 0.0], [0.0, 0.0]

    events: list[tuple[float, float]] = []  # (time_s, delta_power_w)
    for p in phases:
        events.append((p.start_s, p.power_w))
        events.append((p.end_s, -p.power_w))

    events.sort(key=lambda e: e[0])

    times: list[float] = []
    powers: list[float] = []
    current = 0.0
    for t, dp in events:
        if times and t == times[-1]:
            # same timestamp — accumulate delta, keep last power point
            current += dp
            powers[-1] = current
        else:
            # end previous segment with previous power
            if times:
                times.append(t)
                powers.append(current)
            current += dp
            times.append(t)
            powers.append(current)

    return _s_to_us(times), powers


# ---------------------------------------------------------------------------
# Figure 1 — Power vs Time
# ---------------------------------------------------------------------------

def plot_power_time(
    result: ScheduleResult, output_path: str, max_power_w: float
) -> None:
    """P-t plot: stacked per-chiplet power, with total line overlay.

    Each chiplet is a distinct colour band so you can see which die is
    consuming power at which time.
    """
    chiplets = sorted(set(p.chiplet_id for p in result.phases))
    n_c = len(chiplets)
    colors = plt.cm.tab20.colors if n_c <= 20 else plt.cm.tab20b.colors

    # Build per-chiplet step profiles on a shared timeline
    events: list[tuple[float, str, float]] = []  # (time_s, chiplet_id, delta_w)
    for p in result.phases:
        events.append((p.start_s, p.chiplet_id, +p.power_w))
        events.append((p.end_s,   p.chiplet_id, -p.power_w))
    events.sort(key=lambda e: e[0])

    times: list[float] = []
    cur = {c: 0.0 for c in chiplets}
    profiles = {c: [] for c in chiplets}
    last_t = events[0][0] if events else 0.0

    i = 0
    while i < len(events):
        t = events[i][0]
        # push last state
        times.append(last_t)
        for c in chiplets:
            profiles[c].append(cur[c])
        # apply all events at this instant
        while i < len(events) and abs(events[i][0] - t) < 1e-15:
            _, cid, dp = events[i]
            cur[cid] += dp
            i += 1
        times.append(t)
        for c in chiplets:
            profiles[c].append(cur[c])
        last_t = t

    times_us = [t * 1e6 for t in times]

    fig, ax = plt.subplots(figsize=(14, 6))

    bottom = [0.0] * len(times)
    for idx, cid in enumerate(chiplets):
        pw = profiles[cid]
        ax.fill_between(
            times_us, bottom, [b + p for b, p in zip(bottom, pw)],
            step="post", alpha=0.70, color=colors[idx % len(colors)],
            label=cid, linewidth=0.5, edgecolor="white",
        )
        bottom = [b + p for b, p in zip(bottom, pw)]

    # Total power as a black step line on top
    ax.step(times_us, bottom, where="post", linewidth=1.5,
            color="black", label="Total")

    ax.axhline(y=max_power_w, color="red", linestyle="--", linewidth=1.2,
               label=f"Pmax = {max_power_w:.1f} W")

    ax.set_xlabel("Time (μs)")
    ax.set_ylabel("Power (W)")
    ax.set_title(f"{result.case_id} — Power vs. Time (stacked by chiplet)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right", fontsize=8, ncol=max(1, n_c // 6))

    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 2 — Temperature per Stack
# ---------------------------------------------------------------------------

def plot_temperature_time(
    traces: dict[str, list[tuple[float, float]]],
    case_id: str,
    max_temp_c: float,
    output_path: str,
) -> None:
    """T-t plot: per-stack temperature time series.

    Parameters
    ----------
    traces:
        dict mapping ``stack_id`` → list of ``(time_s, temperature_c)`` tuples.
    """
    fig, ax = plt.subplots(figsize=(12, 5))

    cmap = plt.cm.tab10
    for idx, (stack_id, trace) in enumerate(traces.items()):
        if not trace:
            continue
        times_us = _s_to_us([t[0] for t in trace])
        temps = [t[1] for t in trace]
        color = cmap(idx % 10)
        ax.plot(times_us, temps, linewidth=1.2, color=color, label=stack_id)

    ax.axhline(
        y=max_temp_c,
        color="red",
        linestyle="--",
        linewidth=1.2,
        label=f"Tmax = {max_temp_c:.0f} °C",
    )

    # Shaded red zone (last 5 °C before limit)
    y_min = ax.get_ylim()[0] if ax.get_ylim()[0] > 0 else 0
    ax.axhspan(max_temp_c - 5, max_temp_c, alpha=0.1, color="red")

    ax.set_xlabel("Time (μs)")
    ax.set_ylabel("Temperature (°C)")
    ax.set_title(f"{case_id} — Stack Temperature")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right", title="Stacks")

    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 3 — Gantt Chart
# ---------------------------------------------------------------------------

def plot_gantt(result: ScheduleResult, output_path: str) -> None:
    """Gantt chart showing task scheduling over time.

    Layout (top → bottom):
      1. Resource rows: TAP, FPP (all lanes), BIST Engines
      2. Task rows: one per unique task_id
    """
    if not result.phases:
        fig, ax = plt.subplots(figsize=(16, 4))
        ax.text(0.5, 0.5, "No phases to display", ha="center", va="center",
                transform=ax.transAxes, fontsize=14, color="gray")
        ax.set_title(f"{result.case_id} — {result.method} Schedule Gantt")
        fig.tight_layout()
        fig.savefig(output_path)
        plt.close(fig)
        return

    # Collect unique task ids (preserve appearance order)
    task_ids: list[str] = []
    seen: set[str] = set()
    for p in result.phases:
        if p.task_id not in seen:
            seen.add(p.task_id)
            task_ids.append(p.task_id)

    resource_rows = ["TAP", "FPP (all lanes)", "BIST Engines"]
    n_rows = len(resource_rows) + len(task_ids)
    height_per_row = 0.4
    fig_height = max(8, n_rows * height_per_row)
    fig, ax = plt.subplots(figsize=(16, fig_height))

    # Build y-axis labels and positions
    y_labels: list[str] = []
    y_positions: list[int] = []
    current_y = 0

    # Resource rows (top, each separated by 1 unit)
    for r in resource_rows:
        y_labels.append(r)
        y_positions.append(current_y)
        current_y -= 1

    # Small gap between resources and tasks
    current_y -= 0.5

    # Task rows
    for task_id in task_ids:
        y_labels.append(task_id)
        y_positions.append(current_y)
        current_y -= 1

    # Draw bars — ensure minimum visual width for short phases
    total_span = max(p.end_s for p in result.phases) - min(p.start_s for p in result.phases)
    min_width_us = total_span * 1e6 * 0.001  # 0.1 % of total span, so CONFIG/READOUT are visible
    if min_width_us < 0.01:
        min_width_us = 0.01

    bar_height = 0.6

    for p in result.phases:
        color = _phase_color(p.phase_name, p.needs_fpp_lanes)
        t_start_us = p.start_s * 1e6
        t_end_us = p.end_s * 1e6
        width = max(t_end_us - t_start_us, min_width_us)

        # Resource row: TAP
        if p.needs_tap:
            y = y_positions[0]
            ax.barh(
                y,
                width,
                height=bar_height,
                left=t_start_us,
                color=color,
                alpha=0.85,
                edgecolor="none",
            )

        # Resource row: FPP
        if p.needs_fpp_lanes > 0:
            y = y_positions[1]
            ax.barh(
                y,
                width,
                height=bar_height,
                left=t_start_us,
                color=color,
                alpha=0.85,
                edgecolor="none",
                label=f"Lanes={p.needs_fpp_lanes}" if p.needs_fpp_lanes else None,
            )

        # Resource row: BIST
        if p.needs_bist_engine:
            y = y_positions[2]
            ax.barh(
                y,
                width,
                height=bar_height,
                left=t_start_us,
                color=color,
                alpha=0.85,
                edgecolor="none",
            )

        # Task row
        try:
            task_idx = task_ids.index(p.task_id)
            task_y = y_positions[len(resource_rows) + task_idx]
            ax.barh(
                task_y,
                width,
                height=bar_height,
                left=t_start_us,
                color=color,
                alpha=0.85,
                edgecolor="none",
            )
        except ValueError:
            pass

    ax.set_yticks(y_positions)
    ax.set_yticklabels(y_labels, fontsize=7)
    ax.set_xlabel("Time (μs)")
    ax.set_title(f"{result.case_id} — {result.method} Schedule Gantt")

    # Legend — one entry per distinct colour (simplified: TAP vs FPP for shift)
    legend_colors: list[tuple[str, str]] = [
        ("CONFIG",     _PHASE_COLORS["CONFIG"]),
        ("SHIFT-TAP",  _PHASE_COLORS["SHIFT_IN_TAP"]),
        ("SHIFT-FPP",  _PHASE_COLORS["SHIFT_IN_FPP"]),
        ("EXECUTE",    _PHASE_COLORS["EXECUTE"]),
        ("CAPTURE",    _PHASE_COLORS["CAPTURE"]),
        ("READOUT",    _PHASE_COLORS["READOUT"]),
    ]
    legend_handles = [
        plt.Rectangle((0, 0), 1, 1, color=c, alpha=0.85)
        for _, c in legend_colors
    ]
    ax.legend(
        legend_handles,
        [n for n, _ in legend_colors],
        loc="lower center",
        bbox_to_anchor=(0.5, -0.15),
        ncol=len(legend_colors),
        fontsize=8,
    )

    ax.grid(True, axis="x", alpha=0.3)
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 4 — Comparison Bar Chart
# ---------------------------------------------------------------------------

def plot_comparison(
    results: list[tuple[str, ScheduleResult, ScheduleResult]],
    output_path: str,
) -> None:
    """Grouped bar chart comparing greedy vs pure_serial across all cases.

    Parameters
    ----------
    results:
        list of ``(case_label, greedy_result, serial_result)`` tuples.
    """
    if not results:
        fig, ax = plt.subplots(figsize=(16, 7))
        ax.text(0.5, 0.5, "No results to compare", ha="center", va="center",
                transform=ax.transAxes, fontsize=14, color="gray")
        fig.tight_layout()
        fig.savefig(output_path)
        plt.close(fig)
        return

    fig = plt.figure(figsize=(16, 7))
    gs = GridSpec(1, 2, figure=fig)

    ax_left = fig.add_subplot(gs[0, 0])
    ax_right = fig.add_subplot(gs[0, 1])

    # ------------------------------------------------------------------
    # Extract data
    # ------------------------------------------------------------------
    labels = [_short_label(r[0]) for r in results]
    greedy_us = [r[1].makespan_s * 1e6 for r in results]
    serial_us = [r[2].makespan_s * 1e6 for r in results]
    speedups = [s / g if g > 0 else 1.0 for g, s in zip(greedy_us, serial_us)]

    n = len(results)
    x = list(range(n))
    bar_width = 0.35

    # ------------------------------------------------------------------
    # Left subplot: grouped bar chart (log scale)
    # ------------------------------------------------------------------
    bars_greedy = ax_left.bar(
        [xi - bar_width / 2 for xi in x],
        greedy_us,
        width=bar_width,
        color="#3498db",
        alpha=0.9,
        label="Greedy",
    )
    bars_serial = ax_left.bar(
        [xi + bar_width / 2 for xi in x],
        serial_us,
        width=bar_width,
        color="#e74c3c",
        alpha=0.9,
        label="Pure Serial",
    )

    ax_left.set_yscale("log")
    ax_left.set_ylabel("Makespan (μs)")
    ax_left.set_title("Makespan Comparison (log scale)")
    ax_left.set_xticks(x)
    ax_left.set_xticklabels(labels, fontsize=7, rotation=30, ha="right")
    ax_left.legend(loc="upper left", fontsize=8)
    ax_left.grid(True, axis="y", alpha=0.3)

    # Speedup annotations above bar pairs
    for i in range(n):
        max_y = max(greedy_us[i], serial_us[i])
        offset = 0.05 * max_y  # 5% above tallest bar in log space
        ax_left.annotate(
            f"{speedups[i]:.1f}x",
            xy=(x[i], max_y + offset),
            ha="center",
            va="bottom",
            fontsize=7,
            fontweight="bold",
            color="#2c3e50",
        )

    # ------------------------------------------------------------------
    # Right subplot: speedup ratio bar chart
    # ------------------------------------------------------------------
    bar_colors = []
    for s in speedups:
        if s > 2.0:
            bar_colors.append("#27ae60")  # green
        elif s > 1.2:
            bar_colors.append("#f39c12")  # orange
        else:
            bar_colors.append("#95a5a6")  # gray

    ax_right.bar(x, speedups, width=bar_width * 1.5, color=bar_colors, alpha=0.9)

    ax_right.axhline(y=1.0, color="black", linestyle="--", linewidth=0.8, alpha=0.5)
    ax_right.set_ylabel("Speedup (serial / greedy)")
    ax_right.set_title("Speedup Ratio")
    ax_right.set_xticks(x)
    ax_right.set_xticklabels(labels, fontsize=7, rotation=30, ha="right")
    ax_right.grid(True, axis="y", alpha=0.3)

    for i, s in enumerate(speedups):
        ax_right.annotate(
            f"{s:.2f}x",
            xy=(x[i], s),
            ha="center",
            va="bottom",
            fontsize=8,
            fontweight="bold",
            color="#2c3e50",
        )

    fig.suptitle(
        "Greedy vs. Pure Serial — Test Time Comparison",
        fontsize=13,
        fontweight="bold",
    )
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(output_path)
    plt.close(fig)


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------

def write_schedule_csv(result: ScheduleResult, output_path: str) -> None:
    """Write schedule phases to CSV.

    Columns
    -------
    case_id, method, task_id, chiplet_id, stack_id, task_type,
    phase_index, phase_name, start_s, end_s, duration_s,
    needs_tap, needs_fpp_lanes, needs_bist_engine, power_w
    """
    columns = [
        "case_id",
        "method",
        "task_id",
        "chiplet_id",
        "stack_id",
        "task_type",
        "phase_index",
        "phase_name",
        "start_s",
        "end_s",
        "duration_s",
        "needs_tap",
        "needs_fpp_lanes",
        "needs_bist_engine",
        "power_w",
    ]

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(columns)
        for p in result.phases:
            writer.writerow(
                [
                    result.case_id,
                    result.method,
                    p.task_id,
                    p.chiplet_id,
                    p.stack_id,
                    p.task_type,
                    p.phase_index,
                    p.phase_name,
                    f"{p.start_s:.9f}",
                    f"{p.end_s:.9f}",
                    f"{p.duration_s:.9f}",
                    p.needs_tap,
                    p.needs_fpp_lanes,
                    p.needs_bist_engine,
                    f"{p.power_w:.9f}",
                ]
            )


# ---------------------------------------------------------------------------
# Convenience: generate all standard outputs for a single ScheduleResult
# ---------------------------------------------------------------------------

def generate_all_figures(
    result: ScheduleResult,
    output_dir: str,
    *,
    max_power_w: float | None = None,
    temperature_traces: dict[str, list[tuple[float, float]]] | None = None,
    max_temp_c: float | None = None,
) -> list[str]:
    """Generate the standard suite of figures and CSV for one result.

    Returns a list of paths written.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    # Power-time
    pw = max_power_w if max_power_w is not None else result.peak_power_w
    path_pt = str(out / f"{result.case_id}_{result.method}_power_time.png")
    plot_power_time(result, path_pt, pw)
    written.append(path_pt)

    # Temperature-time (only if traces provided)
    if temperature_traces and max_temp_c is not None:
        path_tt = str(out / f"{result.case_id}_{result.method}_temperature_time.png")
        plot_temperature_time(temperature_traces, result.case_id, max_temp_c, path_tt)
        written.append(path_tt)

    # Gantt
    path_gantt = str(out / f"{result.case_id}_{result.method}_gantt.png")
    plot_gantt(result, path_gantt)
    written.append(path_gantt)

    # CSV
    path_csv = str(out / f"{result.case_id}_{result.method}_schedule.csv")
    write_schedule_csv(result, path_csv)
    written.append(path_csv)

    return written
