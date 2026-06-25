from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from src.model import SystemModel
from src.schedulers import ScheduledPhase


@dataclass(frozen=True)
class HotSpotExportRow:
    case_id: str
    schedule_id: str
    floorplan_path: str
    power_trace_path: str
    sample_period_s: float
    sample_count: int
    region_count: int
    notes: str


def write_hotspot_floorplan(model: SystemModel, output_path: str | Path) -> None:
    """Write a simple HotSpot-style floorplan using one block per thermal region."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for region_id, die in _region_die_pairs(model):
        size = die.get("size_um", {})
        position = die.get("position_um", {})
        width_m = max(float(size.get("width", 1.0)) * 1e-6, 1e-9)
        height_m = max(float(size.get("height", 1.0)) * 1e-6, 1e-9)
        x_m = float(position.get("x", 0.0)) * 1e-6
        y_m = float(position.get("y", 0.0)) * 1e-6
        lines.append(f"{region_id}\t{width_m:.12g}\t{height_m:.12g}\t{x_m:.12g}\t{y_m:.12g}")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_hotspot_power_trace(
    model: SystemModel,
    phases: list[ScheduledPhase],
    output_path: str | Path,
    sample_period_s: float = 0.00001,
) -> int:
    """Write a HotSpot-style .ptrace file with uniform sample rows."""
    if sample_period_s <= 0:
        raise ValueError("sample_period_s must be positive")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    regions = [region_id for region_id, _die in _region_die_pairs(model)]
    makespan = max((phase.end_s for phase in phases), default=0.0)
    sample_count = max(1, int(makespan / sample_period_s) + 1)

    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(regions)
        for index in range(sample_count):
            time_s = min(index * sample_period_s, makespan)
            writer.writerow([f"{_region_power_at(phases, region_id, time_s):.9g}" for region_id in regions])
    return sample_count


def write_hotspot_export_manifest(rows: list[HotSpotExportRow], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(HotSpotExportRow.__dataclass_fields__)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)


def _region_die_pairs(model: SystemModel) -> list[tuple[str, dict[str, object]]]:
    pairs = []
    for die in model.dies:
        region_id = str(die.get("thermal", {}).get("region_id", f"thermal_{die['die_id']}"))
        pairs.append((region_id, die))
    return pairs


def _region_power_at(phases: list[ScheduledPhase], region_id: str, time_s: float) -> float:
    return sum(
        phase.power_w
        for phase in phases
        if phase.thermal_region == region_id and phase.start_s <= time_s < phase.end_s
    )
