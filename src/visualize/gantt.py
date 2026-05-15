"""Gantt chart rendering for schedule results."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt

from src.scheduler.base import ScheduleResult


def plot_gantt(result: ScheduleResult, output_path: Path) -> None:
    """Write a Gantt chart SVG for a schedule result."""

    if not result.entries:
        raise ValueError("cannot plot an empty schedule")

    die_ids = sorted({entry.die_id for entry in result.entries})
    die_to_y = {die_id: index for index, die_id in enumerate(die_ids)}

    fig, ax = plt.subplots(figsize=(8, 3.8))
    for entry in result.entries:
        y = die_to_y[entry.die_id]
        ax.barh(y, entry.duration, left=entry.start_time, height=0.55, label=entry.task_type)
        ax.text(
            entry.start_time + entry.duration / 2,
            y,
            entry.task_id,
            ha="center",
            va="center",
            fontsize=8,
        )

    ax.set_title(f"{result.scheduler_name} schedule")
    ax.set_xlabel("time (s)")
    ax.set_ylabel("die")
    ax.set_yticks(list(die_to_y.values()), [f"die {die_id}" for die_id in die_ids])
    ax.set_xlim(left=0, right=max(result.tat, 1e-12))
    handles, labels = ax.get_legend_handles_labels()
    unique = dict(zip(labels, handles))
    ax.legend(unique.values(), unique.keys(), loc="best", fontsize=8)
    ax.grid(True, axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, format="svg")
    plt.close(fig)
