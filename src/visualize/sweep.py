"""Sweep plot helpers for scheduler experiments."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt


SCHEDULER_ORDER = ("serial_ieee1838_style", "bandwidth_greedy", "ptv_aware")


def plot_sweep_metric(
    rows: Sequence[dict],
    output_path: Path,
    metric_name: str,
    title: str,
    ylabel: str,
) -> None:
    """Plot one sweep metric as scheduler curves over FPP lane count."""

    if not rows:
        raise ValueError("cannot plot an empty sweep")

    fig, ax = plt.subplots(figsize=(8, 3.8))
    for scheduler_name in SCHEDULER_ORDER:
        scheduler_rows = [row for row in rows if row["scheduler_name"] == scheduler_name]
        scheduler_rows.sort(key=lambda row: int(row["fpp_lanes"]))
        if not scheduler_rows:
            continue
        x_values = [int(row["fpp_lanes"]) for row in scheduler_rows]
        y_values = [float(row[metric_name]) for row in scheduler_rows]
        ax.plot(x_values, y_values, marker="o", label=scheduler_name)

    ax.set_title(title)
    ax.set_xlabel("FPP lanes")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, format="svg")
    plt.close(fig)


def plot_fpp_lane_sweep(rows: Sequence[dict], output_dir: Path) -> dict[str, Path]:
    """Write the standard FPP-lane sweep plots."""

    outputs = {
        "tat_vs_fpp_lanes": output_dir / "tat_vs_fpp_lanes.svg",
        "peak_ir_drop_vs_fpp_lanes": output_dir / "peak_ir_drop_vs_fpp_lanes.svg",
        "peak_temperature_vs_fpp_lanes": output_dir / "peak_temperature_vs_fpp_lanes.svg",
        "voltage_violations_vs_fpp_lanes": output_dir / "voltage_violations_vs_fpp_lanes.svg",
        "temperature_violations_vs_fpp_lanes": output_dir / "temperature_violations_vs_fpp_lanes.svg",
    }
    plot_sweep_metric(rows, outputs["tat_vs_fpp_lanes"], "tat", "TAT vs FPP lanes", "time (s)")
    plot_sweep_metric(
        rows,
        outputs["peak_ir_drop_vs_fpp_lanes"],
        "peak_ir_drop",
        "Peak IR-drop vs FPP lanes",
        "IR drop (V)",
    )
    plot_sweep_metric(
        rows,
        outputs["peak_temperature_vs_fpp_lanes"],
        "peak_temperature",
        "Peak temperature vs FPP lanes",
        "temperature (C)",
    )
    plot_sweep_metric(
        rows,
        outputs["voltage_violations_vs_fpp_lanes"],
        "voltage_violation_count",
        "Voltage violations vs FPP lanes",
        "violation count",
    )
    plot_sweep_metric(
        rows,
        outputs["temperature_violations_vs_fpp_lanes"],
        "temperature_violation_count",
        "Temperature violations vs FPP lanes",
        "violation count",
    )
    return outputs
