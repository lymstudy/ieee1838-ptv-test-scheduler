from __future__ import annotations

import csv
import math
from dataclasses import asdict, dataclass
from pathlib import Path

from src.model import SystemModel
from src.schedulers import ScheduledPhase


EPSILON = 1e-12


@dataclass(frozen=True)
class TemperatureSample:
    schedule_id: str
    time_s: float
    thermal_region: str
    die_id: str
    temperature_c: float
    active_power_w: float
    coupled_power_w: float


@dataclass(frozen=True)
class HotspotRow:
    schedule_id: str
    thermal_region: str
    die_id: str
    peak_temperature_c: float
    peak_time_s: float
    limit_c: float
    over_limit_duration_s: float
    violation_count: int


@dataclass(frozen=True)
class ThermalEvaluationResult:
    schedule_id: str
    samples: list[TemperatureSample]
    hotspots: list[HotspotRow]
    makespan_s: float
    peak_temperature_c: float
    peak_region: str
    peak_time_s: float
    over_limit_duration_s: float
    violation_count: int


def read_schedule_csv(path: str | Path) -> list[ScheduledPhase]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return [_scheduled_phase_from_row(row) for row in csv.DictReader(handle)]


def evaluate_schedule_thermal(
    model: SystemModel,
    phases: list[ScheduledPhase],
    schedule_id: str,
) -> ThermalEvaluationResult:
    regions = _region_specs(model)
    temperatures = {
        region_id: float(model.raw["package"].get("ambient_temperature_c", 25.0))
        for region_id in regions
    }
    samples: list[TemperatureSample] = []
    boundaries = sorted({0.0, *(phase.start_s for phase in phases), *(phase.end_s for phase in phases)})
    region_peak = {region_id: (temperatures[region_id], 0.0) for region_id in regions}
    over_limit_duration = {region_id: 0.0 for region_id in regions}
    violation_count = {region_id: 0 for region_id in regions}
    was_over_limit = {region_id: False for region_id in regions}

    for region_id, spec in regions.items():
        samples.append(
            TemperatureSample(
                schedule_id=schedule_id,
                time_s=0.0,
                thermal_region=region_id,
                die_id=spec["die_id"],
                temperature_c=temperatures[region_id],
                active_power_w=0.0,
                coupled_power_w=0.0,
            )
        )

    for start, end in zip(boundaries, boundaries[1:]):
        dt = end - start
        if dt <= EPSILON:
            continue
        active = [phase for phase in phases if phase.start_s < end - EPSILON and start < phase.end_s - EPSILON]
        own_power = _region_power(regions, active)
        effective_power = _effective_region_power(model, regions, own_power)

        for region_id, spec in regions.items():
            resistance = spec["thermal_resistance_c_per_w"]
            capacitance = spec["thermal_capacitance_j_per_c"]
            ambient = float(model.raw["package"].get("ambient_temperature_c", 25.0))
            steady_state = ambient + effective_power[region_id] * resistance
            tau = max(resistance * capacitance, EPSILON)
            temperatures[region_id] = steady_state + (temperatures[region_id] - steady_state) * math.exp(-dt / tau)

            peak_temp, _peak_time = region_peak[region_id]
            if temperatures[region_id] > peak_temp:
                region_peak[region_id] = (temperatures[region_id], end)

            limit = spec["limit_c"]
            is_over_limit = temperatures[region_id] > limit + EPSILON
            if is_over_limit:
                over_limit_duration[region_id] += dt
            if is_over_limit and not was_over_limit[region_id]:
                violation_count[region_id] += 1
            was_over_limit[region_id] = is_over_limit

            samples.append(
                TemperatureSample(
                    schedule_id=schedule_id,
                    time_s=end,
                    thermal_region=region_id,
                    die_id=spec["die_id"],
                    temperature_c=temperatures[region_id],
                    active_power_w=own_power[region_id],
                    coupled_power_w=max(0.0, effective_power[region_id] - own_power[region_id]),
                )
            )

    hotspots = [
        HotspotRow(
            schedule_id=schedule_id,
            thermal_region=region_id,
            die_id=regions[region_id]["die_id"],
            peak_temperature_c=region_peak[region_id][0],
            peak_time_s=region_peak[region_id][1],
            limit_c=regions[region_id]["limit_c"],
            over_limit_duration_s=over_limit_duration[region_id],
            violation_count=violation_count[region_id],
        )
        for region_id in sorted(regions)
    ]
    peak = max(hotspots, key=lambda row: row.peak_temperature_c)
    return ThermalEvaluationResult(
        schedule_id=schedule_id,
        samples=samples,
        hotspots=hotspots,
        makespan_s=max((phase.end_s for phase in phases), default=0.0),
        peak_temperature_c=peak.peak_temperature_c,
        peak_region=peak.thermal_region,
        peak_time_s=peak.peak_time_s,
        over_limit_duration_s=sum(row.over_limit_duration_s for row in hotspots),
        violation_count=sum(row.violation_count for row in hotspots),
    )


def write_temperature_trace_csv(results: list[ThermalEvaluationResult], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(TemperatureSample.__dataclass_fields__)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            for sample in result.samples:
                writer.writerow(asdict(sample))


def write_hotspots_csv(results: list[ThermalEvaluationResult], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(HotspotRow.__dataclass_fields__)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            for hotspot in result.hotspots:
                writer.writerow(asdict(hotspot))


def write_thermal_summary_csv(results: list[ThermalEvaluationResult], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "schedule_id",
        "makespan_s",
        "peak_temperature_c",
        "peak_region",
        "peak_time_s",
        "over_limit_duration_s",
        "violation_count",
    ]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow({field: getattr(result, field) for field in fieldnames})


def write_thermal_report_markdown(results: list[ThermalEvaluationResult], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    best_peak = min(results, key=lambda result: result.peak_temperature_c) if results else None
    lines = [
        "# M7 Thermal Proxy Report",
        "",
        "This report uses a first-order RC thermal proxy. It is not a HotSpot replacement.",
        "",
        "## Schedule Summary",
        "",
        "| schedule | makespan_s | peak_temp_c | peak_region | over_limit_s | violations |",
        "| --- | ---: | ---: | --- | ---: | ---: |",
    ]
    for result in results:
        lines.append(
            f"| {result.schedule_id} | {result.makespan_s:.9f} | {result.peak_temperature_c:.6f} | "
            f"{result.peak_region} | {result.over_limit_duration_s:.9f} | {result.violation_count} |"
        )
    if best_peak is not None:
        lines.extend(
            [
                "",
                f"- Lowest proxy peak temperature: `{best_peak.schedule_id}` at {best_peak.peak_temperature_c:.6f} C.",
                "",
                "## Hotspots",
                "",
                "| schedule | region | die | peak_temp_c | peak_time_s | limit_c |",
                "| --- | --- | --- | ---: | ---: | ---: |",
            ]
        )
        for result in results:
            for hotspot in sorted(result.hotspots, key=lambda row: -row.peak_temperature_c):
                lines.append(
                    f"| {hotspot.schedule_id} | {hotspot.thermal_region} | {hotspot.die_id} | "
                    f"{hotspot.peak_temperature_c:.6f} | {hotspot.peak_time_s:.9f} | {hotspot.limit_c:.2f} |"
                )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _scheduled_phase_from_row(row: dict[str, str]) -> ScheduledPhase:
    return ScheduledPhase(
        case_id=row["case_id"],
        target_id=row["target_id"],
        target_kind=row["target_kind"],
        die_id=row["die_id"],
        recipe_id=row["recipe_id"],
        recipe_type=row["recipe_type"],
        phase_index=int(row["phase_index"]),
        phase_name=row["phase_name"],
        start_s=float(row["start_s"]),
        end_s=float(row["end_s"]),
        duration_s=float(row["duration_s"]),
        serial_required=_to_bool(row["serial_required"]),
        fpp_lanes_required=int(row["fpp_lanes_required"]),
        fpp_channel=row["fpp_channel"],
        dwr_segments=row["dwr_segments"],
        route_resource=row["route_resource"],
        power_w=float(row["power_w"]),
        thermal_region=row["thermal_region"],
        resource_notes=row["resource_notes"],
    )


def _region_specs(model: SystemModel) -> dict[str, dict[str, float | str]]:
    region_limits = {
        str(region["region_id"]): float(region.get("max_temperature_c", model.resource_limits.get("max_temperature_c", 85.0)))
        for region in model.raw["resource_groups"].get("thermal_regions", [])
    }
    specs: dict[str, dict[str, float | str]] = {}
    for die in model.dies:
        thermal = die.get("thermal", {})
        region_id = str(thermal["region_id"])
        specs[region_id] = {
            "die_id": str(die["die_id"]),
            "thermal_resistance_c_per_w": float(thermal.get("thermal_resistance_c_per_w", 1.0)),
            "thermal_capacitance_j_per_c": float(thermal.get("thermal_capacitance_j_per_c", 1.0)),
            "limit_c": region_limits.get(region_id, float(model.resource_limits.get("max_temperature_c", 85.0))),
        }
    return specs


def _region_power(regions: dict[str, dict[str, float | str]], active: list[ScheduledPhase]) -> dict[str, float]:
    power = {region_id: 0.0 for region_id in regions}
    for phase in active:
        if phase.thermal_region in power:
            power[phase.thermal_region] += phase.power_w
    return power


def _effective_region_power(
    model: SystemModel,
    regions: dict[str, dict[str, float | str]],
    own_power: dict[str, float],
) -> dict[str, float]:
    thermal_model = model.raw.get("thermal_model", {})
    self_weight = float(thermal_model.get("self_heating_weight", 1.0))
    vertical_weight = float(thermal_model.get("vertical_coupling_weight", 0.35))
    horizontal_weight = float(thermal_model.get("horizontal_coupling_weight", 0.2))
    effective = {region_id: self_weight * power for region_id, power in own_power.items()}
    for edge in model.raw.get("thermal_adjacency", []):
        source = str(edge["source_region"])
        target = str(edge["target_region"])
        if source not in regions or target not in regions:
            continue
        base_weight = float(edge.get("coupling_weight", 0.0))
        type_weight = vertical_weight if edge.get("coupling_type") == "vertical" else horizontal_weight
        coupling = base_weight * type_weight
        effective[source] += own_power[target] * coupling
        effective[target] += own_power[source] * coupling
    return effective


def _to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}
