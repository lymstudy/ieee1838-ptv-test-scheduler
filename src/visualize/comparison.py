"""Comparison plot helpers for scheduler-level metrics."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt

from src.scheduler.base import ScheduleResult


def plot_metric_comparison(
    results: Sequence[ScheduleResult],
    output_path: Path,
    metric_name: str,
    title: str,
    ylabel: str,
) -> None:
    """Write a bar chart comparing one metric across schedulers."""

    if not results:
        raise ValueError("cannot plot comparison for empty results")

    labels = [result.scheduler_name for result in results]
    values = [_metric_value(result, metric_name) for result in results]

    fig, ax = plt.subplots(figsize=(8, 3.8))
    ax.bar(labels, values)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(True, axis="y", alpha=0.3)
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(output_path, format="svg")
    plt.close(fig)


def plot_basic_comparisons(results: Sequence[ScheduleResult], output_dir: Path) -> dict[str, Path]:
    """Write the MVP comparison plots for TAT, peak temperature, and peak IR drop."""

    outputs = {
        "tat_comparison": output_dir / "tat_comparison.svg",
        "peak_temperature_comparison": output_dir / "peak_temperature_comparison.svg",
        "peak_ir_drop_comparison": output_dir / "peak_ir_drop_comparison.svg",
    }
    plot_metric_comparison(results, outputs["tat_comparison"], "tat", "TAT comparison", "time (s)")
    plot_metric_comparison(
        results,
        outputs["peak_temperature_comparison"],
        "peak_temperature",
        "Peak temperature comparison",
        "temperature (C)",
    )
    plot_metric_comparison(
        results,
        outputs["peak_ir_drop_comparison"],
        "peak_ir_drop",
        "Peak IR-drop comparison",
        "IR drop (V)",
    )
    return outputs


def _metric_value(result: ScheduleResult, metric_name: str) -> float:
    if metric_name == "tat":
        return result.tat
    if metric_name == "peak_temperature":
        return result.peak_temperature
    if metric_name == "peak_ir_drop":
        return result.peak_ir_drop
    value = result.metrics[metric_name]
    if isinstance(value, bool):
        return float(value)
    return float(value)
