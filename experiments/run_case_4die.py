"""Run the 4-die serial IEEE 1838-style baseline experiment."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.model.access import AccessConfig
from src.model.stack import DieStack
from src.model.task import build_tasks
from src.model.thermal import RCThermalModel, ThermalConfig
from src.model.voltage import EquivalentPdnModel, VoltageConfig
from src.scheduler.serial import SerialScheduler
from src.visualize.curves import plot_ir_drop_curve, plot_temperature_curve
from src.visualize.gantt import plot_gantt


CONFIG_DIR = ROOT / "configs"
RESULT_DIR = ROOT / "results" / "case_4die"


def load_yaml(path: Path) -> dict:
    """Load a YAML file into a mapping."""

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"YAML file must contain a mapping: {path}")
    return data


def write_dict_rows(path: Path, rows: list[dict]) -> None:
    """Write a list of dictionaries as a CSV file."""

    if not rows:
        raise ValueError("cannot write an empty CSV")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def run() -> dict[str, Path]:
    """Run the serial baseline for the 4-die case and write result artifacts."""

    defaults = load_yaml(CONFIG_DIR / "default_params.yaml")
    case = load_yaml(CONFIG_DIR / "case_4die.yaml")

    stack = DieStack.from_config(case["stack"])
    access = AccessConfig.from_config(case["access"])
    tasks = build_tasks(case["tasks"])
    thermal_config = ThermalConfig.from_config(defaults["thermal"])
    voltage_config = VoltageConfig.from_config(defaults["voltage"])
    time_step_s = float(defaults["simulation"]["time_step_s"])
    clock_hz = float(defaults["simulation"]["clock_hz"])

    if len(stack.dies) != 4:
        raise ValueError("case_4die must contain exactly four dies")
    for task in tasks:
        stack.get_die(task.die_id)
        access.dwr_for_die(task.die_id)

    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    scheduler = SerialScheduler(
        stack=stack,
        access=access,
        thermal_model=RCThermalModel(thermal_config),
        voltage_model=EquivalentPdnModel(voltage_config),
        clock_hz=clock_hz,
        time_step_s=time_step_s,
    )
    result = scheduler.schedule(tasks)

    schedule_path = RESULT_DIR / "serial_schedule.csv"
    write_dict_rows(
        schedule_path,
        [entry.to_row() for entry in result.entries],
    )

    metrics_path = RESULT_DIR / "serial_metrics.csv"
    write_dict_rows(
        metrics_path,
        [{"metric": key, "value": value} for key, value in result.metrics.items()],
    )

    gantt_path = RESULT_DIR / "serial_gantt.svg"
    temperature_curve_path = RESULT_DIR / "serial_temperature_curve.svg"
    ir_drop_curve_path = RESULT_DIR / "serial_ir_drop_curve.svg"
    plot_gantt(result, gantt_path)
    plot_temperature_curve(result, temperature_curve_path)
    plot_ir_drop_curve(result, ir_drop_curve_path)

    return {
        "serial_schedule": schedule_path,
        "serial_metrics": metrics_path,
        "serial_gantt": gantt_path,
        "serial_temperature_curve": temperature_curve_path,
        "serial_ir_drop_curve": ir_drop_curve_path,
    }


if __name__ == "__main__":
    outputs = run()
    print("4-die serial baseline experiment completed.")
    for name, path in outputs.items():
        print(f"{name}: {path.relative_to(ROOT)}")
