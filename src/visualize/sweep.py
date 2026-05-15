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
    x_field: str = "fpp_lanes",
    x_label: str = "FPP lanes",
) -> None:
    """Plot one sweep metric as scheduler curves over a sweep parameter."""

    if not rows:
        raise ValueError("cannot plot an empty sweep")

    fig, ax = plt.subplots(figsize=(8, 3.8))
    for scheduler_name in SCHEDULER_ORDER:
        scheduler_rows = [row for row in rows if row["scheduler_name"] == scheduler_name]
        scheduler_rows.sort(key=lambda row: float(row[x_field]))
        if not scheduler_rows:
            continue
        x_values = [float(row[x_field]) for row in scheduler_rows]
        y_values = [float(row[metric_name]) for row in scheduler_rows]
        ax.plot(x_values, y_values, marker="o", label=scheduler_name)

    ax.set_title(title)
    ax.set_xlabel(x_label)
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
    plot_sweep_metric(rows, outputs["peak_ir_drop_vs_fpp_lanes"], "peak_ir_drop", "Peak IR-drop vs FPP lanes", "IR drop (V)")
    plot_sweep_metric(rows, outputs["peak_temperature_vs_fpp_lanes"], "peak_temperature", "Peak temperature vs FPP lanes", "temperature (C)")
    plot_sweep_metric(rows, outputs["voltage_violations_vs_fpp_lanes"], "voltage_violation_count", "Voltage violations vs FPP lanes", "violation count")
    plot_sweep_metric(rows, outputs["temperature_violations_vs_fpp_lanes"], "temperature_violation_count", "Temperature violations vs FPP lanes", "violation count")
    return outputs


def plot_voltage_limit_sweep(rows: Sequence[dict], output_dir: Path) -> dict[str, Path]:
    """Write the standard voltage-limit sweep plots."""

    outputs = {
        "tat_vs_voltage_limit": output_dir / "tat_vs_voltage_limit.svg",
        "peak_ir_drop_vs_voltage_limit": output_dir / "peak_ir_drop_vs_voltage_limit.svg",
        "voltage_violations_vs_voltage_limit": output_dir / "voltage_violations_vs_voltage_limit.svg",
    }
    kwargs = {"x_field": "voltage_limit", "x_label": "IR-drop limit (V)"}
    plot_sweep_metric(rows, outputs["tat_vs_voltage_limit"], "tat", "TAT vs IR-drop limit", "time (s)", **kwargs)
    plot_sweep_metric(rows, outputs["peak_ir_drop_vs_voltage_limit"], "peak_ir_drop", "Peak IR-drop vs IR-drop limit", "IR drop (V)", **kwargs)
    plot_sweep_metric(rows, outputs["voltage_violations_vs_voltage_limit"], "voltage_violation_count", "Voltage violations vs IR-drop limit", "violation count", **kwargs)
    return outputs


def plot_thermal_limit_sweep(rows: Sequence[dict], output_dir: Path) -> dict[str, Path]:
    """Write the standard thermal-limit sweep plots."""

    outputs = {
        "tat_vs_thermal_limit": output_dir / "tat_vs_thermal_limit.svg",
        "peak_temperature_vs_thermal_limit": output_dir / "peak_temperature_vs_thermal_limit.svg",
        "temperature_violations_vs_thermal_limit": output_dir / "temperature_violations_vs_thermal_limit.svg",
        "dummy_cycles_vs_thermal_limit": output_dir / "dummy_cycles_vs_thermal_limit.svg",
    }
    kwargs = {"x_field": "thermal_limit", "x_label": "thermal limit (C)"}
    plot_sweep_metric(rows, outputs["tat_vs_thermal_limit"], "tat", "TAT vs thermal limit", "time (s)", **kwargs)
    plot_sweep_metric(rows, outputs["peak_temperature_vs_thermal_limit"], "peak_temperature", "Peak temperature vs thermal limit", "temperature (C)", **kwargs)
    plot_sweep_metric(rows, outputs["temperature_violations_vs_thermal_limit"], "temperature_violation_count", "Temperature violations vs thermal limit", "violation count", **kwargs)
    plot_sweep_metric(rows, outputs["dummy_cycles_vs_thermal_limit"], "dummy_cycle_count", "Dummy cycles vs thermal limit", "dummy cycle count", **kwargs)
    return outputs

def plot_workload_scale_sweep(rows: Sequence[dict], output_dir: Path) -> dict[str, Path]:
    """Write workload-scale sweep plots with die-count/density labels."""

    outputs = {
        "tat_vs_workload_scale": output_dir / "tat_vs_workload_scale.svg",
        "peak_ir_drop_vs_workload_scale": output_dir / "peak_ir_drop_vs_workload_scale.svg",
        "peak_temperature_vs_workload_scale": output_dir / "peak_temperature_vs_workload_scale.svg",
        "voltage_violations_vs_workload_scale": output_dir / "voltage_violations_vs_workload_scale.svg",
        "temperature_violations_vs_workload_scale": output_dir / "temperature_violations_vs_workload_scale.svg",
        "task_count_vs_workload_scale": output_dir / "task_count_vs_workload_scale.svg",
    }
    plot_workload_scale_metric(rows, outputs["tat_vs_workload_scale"], "tat", "TAT vs workload scale", "time (s)")
    plot_workload_scale_metric(rows, outputs["peak_ir_drop_vs_workload_scale"], "peak_ir_drop", "Peak IR-drop vs workload scale", "IR drop (V)")
    plot_workload_scale_metric(rows, outputs["peak_temperature_vs_workload_scale"], "peak_temperature", "Peak temperature vs workload scale", "temperature (C)")
    plot_workload_scale_metric(rows, outputs["voltage_violations_vs_workload_scale"], "voltage_violation_count", "Voltage violations vs workload scale", "violation count")
    plot_workload_scale_metric(rows, outputs["temperature_violations_vs_workload_scale"], "temperature_violation_count", "Temperature violations vs workload scale", "violation count")
    plot_workload_scale_metric(rows, outputs["task_count_vs_workload_scale"], "num_tasks", "Task count vs workload scale", "task count")
    return outputs


def plot_workload_scale_metric(
    rows: Sequence[dict],
    output_path: Path,
    metric_name: str,
    title: str,
    ylabel: str,
) -> None:
    """Plot one workload-scale metric by die-count/density categories."""

    if not rows:
        raise ValueError("cannot plot an empty sweep")

    labels = _workload_scale_labels(rows)
    x_positions = list(range(len(labels)))
    fig, ax = plt.subplots(figsize=(10, 4.2))
    for scheduler_name in SCHEDULER_ORDER:
        scheduler_rows = { _workload_label(row): row for row in rows if row["scheduler_name"] == scheduler_name }
        y_values = [float(scheduler_rows[label][metric_name]) for label in labels]
        ax.plot(x_positions, y_values, marker="o", label=scheduler_name)

    ax.set_title(title)
    ax.set_xlabel("workload scale")
    ax.set_ylabel(ylabel)
    ax.set_xticks(x_positions)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, format="svg")
    plt.close(fig)


def _workload_scale_labels(rows: Sequence[dict]) -> list[str]:
    density_order = {"small": 0, "medium": 1, "large": 2}
    pairs = sorted(
        {(int(row["die_count"]), row["task_density"]) for row in rows},
        key=lambda item: (item[0], density_order[item[1]]),
    )
    return [f"{die_count}-{density}" for die_count, density in pairs]


def _workload_label(row: dict) -> str:
    return f"{int(row['die_count'])}-{row['task_density']}"
