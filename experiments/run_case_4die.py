"""Load and validate the 4-die scaffold experiment."""

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
from src.model.thermal import RCThermalModel, TemperatureState, ThermalConfig
from src.model.voltage import EquivalentPdnModel, VoltageConfig


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


def write_line_svg(path: Path, title: str, y_label: str, points: list[tuple[float, float]]) -> None:
    """Write a minimal SVG line chart for scaffold sanity curves."""

    if len(points) < 2:
        raise ValueError("line chart requires at least two points")

    width = 640
    height = 360
    margin_left = 70
    margin_right = 28
    margin_top = 42
    margin_bottom = 58
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom

    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    min_x = min(xs)
    max_x = max(xs)
    min_y = min(ys)
    max_y = max(ys)
    if min_y == max_y:
        min_y -= 1.0
        max_y += 1.0

    def sx(value: float) -> float:
        if min_x == max_x:
            return margin_left + plot_width / 2
        return margin_left + (value - min_x) / (max_x - min_x) * plot_width

    def sy(value: float) -> float:
        return margin_top + (max_y - value) / (max_y - min_y) * plot_height

    polyline = " ".join(f"{sx(x):.2f},{sy(y):.2f}" for x, y in points)
    last_x, last_y = points[-1]

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="white"/>
  <text x="{width / 2:.0f}" y="24" text-anchor="middle" font-family="Arial, sans-serif" font-size="18">{title}</text>
  <line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{height - margin_bottom}" stroke="#333" stroke-width="1"/>
  <line x1="{margin_left}" y1="{height - margin_bottom}" x2="{width - margin_right}" y2="{height - margin_bottom}" stroke="#333" stroke-width="1"/>
  <text x="{width / 2:.0f}" y="{height - 16}" text-anchor="middle" font-family="Arial, sans-serif" font-size="13">time (s)</text>
  <text x="18" y="{height / 2:.0f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" transform="rotate(-90 18 {height / 2:.0f})">{y_label}</text>
  <text x="{margin_left}" y="{height - margin_bottom + 20}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12">{min_x:.4g}</text>
  <text x="{width - margin_right}" y="{height - margin_bottom + 20}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12">{max_x:.4g}</text>
  <text x="{margin_left - 8}" y="{height - margin_bottom + 4}" text-anchor="end" font-family="Arial, sans-serif" font-size="12">{min_y:.4g}</text>
  <text x="{margin_left - 8}" y="{margin_top + 4}" text-anchor="end" font-family="Arial, sans-serif" font-size="12">{max_y:.4g}</text>
  <polyline points="{polyline}" fill="none" stroke="#2563eb" stroke-width="3"/>
  <circle cx="{sx(last_x):.2f}" cy="{sy(last_y):.2f}" r="4" fill="#2563eb"/>
</svg>
"""
    path.write_text(svg, encoding="utf-8")


def run() -> dict[str, Path]:
    """Run scaffold validation for the 4-die case and write result artifacts."""

    defaults = load_yaml(CONFIG_DIR / "default_params.yaml")
    case = load_yaml(CONFIG_DIR / "case_4die.yaml")

    stack = DieStack.from_config(case["stack"])
    access = AccessConfig.from_config(case["access"])
    tasks = build_tasks(case["tasks"])
    thermal_config = ThermalConfig.from_config(defaults["thermal"])
    voltage_config = VoltageConfig.from_config(defaults["voltage"])
    time_step_s = float(defaults["simulation"]["time_step_s"])

    if len(stack.dies) != 4:
        raise ValueError("case_4die must contain exactly four dies")
    for task in tasks:
        stack.get_die(task.die_id)
        access.dwr_for_die(task.die_id)

    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    model_summary_path = RESULT_DIR / "model_summary.csv"
    write_dict_rows(
        model_summary_path,
        [
            {
                "die_id": die.id,
                "die_name": die.name,
                "layer_index": die.layer_index,
                "area_mm2": die.area_mm2,
                "initial_temp_c": die.initial_temp_c,
                "nominal_power_w": die.nominal_power_w,
                "dwr_length_bits": access.dwr_for_die(die.id).length_bits,
            }
            for die in stack.dies
        ],
    )

    power_by_die_w = {task.die_id: task.power_w for task in tasks}
    initial_state = TemperatureState({die.id: die.initial_temp_c for die in stack.dies})
    next_state = RCThermalModel(thermal_config).step(initial_state, power_by_die_w, time_step_s)
    thermal_path = RESULT_DIR / "thermal_sanity.csv"
    write_dict_rows(
        thermal_path,
        [
            {
                "die_id": die_id,
                "initial_temp_c": initial_state.by_die_id[die_id],
                "next_temp_c": next_state.by_die_id[die_id],
                "time_step_s": time_step_s,
            }
            for die_id in stack.die_ids()
        ],
    )
    temperature_curve_path = RESULT_DIR / "temperature_curve.svg"
    write_line_svg(
        temperature_curve_path,
        "Peak temperature scaffold sanity",
        "peak temp (C)",
        [(0.0, initial_state.peak_temp_c()), (time_step_s, next_state.peak_temp_c())],
    )

    voltage_state = EquivalentPdnModel(voltage_config).estimate(power_by_die_w)
    voltage_path = RESULT_DIR / "voltage_sanity.csv"
    write_dict_rows(
        voltage_path,
        [
            {
                "die_id": die_id,
                "power_w": power_by_die_w[die_id],
                "ir_drop_v": voltage_state.ir_drop_by_die_v[die_id],
            }
            for die_id in stack.die_ids()
        ],
    )
    ir_drop_curve_path = RESULT_DIR / "ir_drop_curve.svg"
    write_line_svg(
        ir_drop_curve_path,
        "Peak IR-drop scaffold sanity",
        "peak IR drop (V)",
        [(0.0, 0.0), (time_step_s, voltage_state.peak_ir_drop_v())],
    )

    return {
        "model_summary": model_summary_path,
        "thermal_sanity": thermal_path,
        "temperature_curve": temperature_curve_path,
        "voltage_sanity": voltage_path,
        "ir_drop_curve": ir_drop_curve_path,
    }


if __name__ == "__main__":
    outputs = run()
    print("4-die scaffold experiment completed.")
    for name, path in outputs.items():
        print(f"{name}: {path.relative_to(ROOT)}")
