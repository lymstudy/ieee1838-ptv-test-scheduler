"""Curve rendering for thermal and voltage traces."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt

from src.scheduler.base import ScheduleResult


def plot_temperature_curve(result: ScheduleResult, output_path: Path) -> None:
    """Write a temperature trace SVG for a schedule result."""

    _plot_trace(
        result.temperature_trace,
        output_path,
        title=f"{result.scheduler_name} temperature trace",
        ylabel="temperature (C)",
        peak_key="peak_temperature",
    )


def plot_ir_drop_curve(result: ScheduleResult, output_path: Path) -> None:
    """Write an IR-drop trace SVG for a schedule result."""

    _plot_trace(
        result.ir_drop_trace,
        output_path,
        title=f"{result.scheduler_name} IR-drop trace",
        ylabel="IR drop (V)",
        peak_key="peak_ir_drop",
    )


def _plot_trace(
    trace: Sequence[dict[str, float]],
    output_path: Path,
    title: str,
    ylabel: str,
    peak_key: str,
) -> None:
    if not trace:
        raise ValueError("cannot plot an empty trace")

    times = [row["time"] for row in trace]
    series_keys = sorted(key for key in trace[0] if key.startswith("die_"))

    fig, ax = plt.subplots(figsize=(8, 3.8))
    for key in series_keys:
        ax.plot(times, [row[key] for row in trace], label=key)
    ax.plot(times, [row[peak_key] for row in trace], linewidth=2.2, label=peak_key)

    ax.set_title(title)
    ax.set_xlabel("time (s)")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, format="svg")
    plt.close(fig)
