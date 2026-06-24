from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

from src.model import SystemModel
from src.schedulers import ScheduleResult

from .thermal import ThermalEvaluationResult, evaluate_schedule_thermal


@dataclass(frozen=True)
class ComparisonRow:
    case_id: str
    method_id: str
    method_label: str
    makespan_s: float
    normalized_makespan: float
    peak_power_w: float
    peak_temperature_c: float
    peak_thermal_region: str
    fpp_utilization: float
    serial_busy_ratio: float
    selected_recipe_types: str
    thermal_violations: int


def build_comparison_rows(
    model: SystemModel,
    schedules: list[tuple[str, str, ScheduleResult]],
    reference_method_id: str | None = None,
) -> tuple[list[ComparisonRow], list[ThermalEvaluationResult]]:
    thermal_results = [
        evaluate_schedule_thermal(model, schedule.phases, method_id)
        for method_id, _label, schedule in schedules
    ]
    thermal_by_method = {result.schedule_id: result for result in thermal_results}
    reference = _reference_makespan(schedules, reference_method_id)
    rows = []
    for method_id, label, schedule in schedules:
        thermal = thermal_by_method[method_id]
        rows.append(
            ComparisonRow(
                case_id=model.case_id,
                method_id=method_id,
                method_label=label,
                makespan_s=schedule.makespan_s,
                normalized_makespan=schedule.makespan_s / reference if reference > 0 else 0.0,
                peak_power_w=schedule.peak_power_w,
                peak_temperature_c=thermal.peak_temperature_c,
                peak_thermal_region=thermal.peak_region,
                fpp_utilization=_fpp_utilization(model, schedule),
                serial_busy_ratio=schedule.serial_busy_time_s / schedule.makespan_s if schedule.makespan_s > 0 else 0.0,
                selected_recipe_types=_recipe_type_counts(schedule),
                thermal_violations=thermal.violation_count,
            )
        )
    return rows, thermal_results


def write_comparison_csv(rows: list[ComparisonRow], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(ComparisonRow.__dataclass_fields__)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def write_comparison_report_markdown(rows: list[ComparisonRow], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    best_time = min(rows, key=lambda row: row.makespan_s) if rows else None
    best_temp = min(rows, key=lambda row: row.peak_temperature_c) if rows else None
    lines = [
        "# M8 Baseline Comparison Report",
        "",
        "| method | makespan_s | norm | peak_power_w | peak_temp_c | FPP util | serial busy | recipes |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row.method_label} | {row.makespan_s:.9f} | {row.normalized_makespan:.4f} | "
            f"{row.peak_power_w:.6f} | {row.peak_temperature_c:.6f} | "
            f"{row.fpp_utilization:.4f} | {row.serial_busy_ratio:.4f} | {row.selected_recipe_types} |"
        )
    if best_time is not None and best_temp is not None:
        lines.extend(
            [
                "",
                f"- Best makespan: `{best_time.method_id}` at {best_time.makespan_s:.9f} s.",
                f"- Lowest thermal proxy peak: `{best_temp.method_id}` at {best_temp.peak_temperature_c:.6f} C.",
                "",
                "Thermal values are first-order RC proxy results, not HotSpot outputs.",
            ]
        )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _reference_makespan(schedules: list[tuple[str, str, ScheduleResult]], reference_method_id: str | None) -> float:
    if reference_method_id:
        for method_id, _label, schedule in schedules:
            if method_id == reference_method_id:
                return schedule.makespan_s
    return schedules[0][2].makespan_s if schedules else 0.0


def _fpp_utilization(model: SystemModel, schedule: ScheduleResult) -> float:
    total_lanes = int(model.resource_limits.get("total_fpp_lanes", 0))
    if schedule.makespan_s <= 0 or total_lanes <= 0:
        return 0.0
    return schedule.fpp_lane_time_s / (schedule.makespan_s * total_lanes)


def _recipe_type_counts(schedule: ScheduleResult) -> str:
    counts: dict[str, int] = {}
    for row in schedule.selected_rows:
        recipe_type = str(row.get("recipe_type", ""))
        counts[recipe_type] = counts.get(recipe_type, 0) + 1
    return ";".join(f"{key}:{counts[key]}" for key in sorted(counts))
