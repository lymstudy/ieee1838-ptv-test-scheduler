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
    vertical_adj = _build_vertical_adjacency(model, regions)
    thermal_model = model.raw.get("thermal_model", {})

    # Die-to-die coupling parameters from thermal_model config
    r_inter_die = float(thermal_model.get("R_inter_die", 0.35))
    c_inter_die = float(thermal_model.get("C_inter_die", 0.08))
    # Heat sink distance factor (VHDF) gamma
    gamma = float(thermal_model.get("layer_distance_decay", 0.5))
    # Coupling strength scaling
    die_coupling_alpha = float(thermal_model.get("die_coupling_alpha", 0.20))
    die_coupling_beta = float(thermal_model.get("die_coupling_beta", 0.12))
    # Timescale calibration: schedules are in ms range, RC constants need to match.
    # resistance_multiplier scales up R to produce meaningful temperature rise;
    # capacitance_divider scales down C to make thermal response fast enough
    # for sub-second schedule makespans.
    resistance_multiplier = float(thermal_model.get("proxy_resistance_multiplier", 25.0))
    capacitance_divider = float(thermal_model.get("proxy_capacitance_divider", 1.0))

    # Compute effective distance ranks -- if all dies have the same heat_sink_distance_rank,
    # use graph distance from primary die as a fallback (important for 2.5D topologies)
    primary_die = model.primary_die_id
    primary_region = None
    for region_id, spec in regions.items():
        if spec["die_id"] == primary_die:
            primary_region = region_id
            break

    all_adj = _build_all_adjacency(model, regions)
    if primary_region is not None:
        graph_distance = _compute_graph_distances(primary_region, all_adj)
    else:
        graph_distance = {region_id: 0 for region_id in regions}

    # Check if heat_sink_distance_rank is uniform
    ranks = {spec.get("heat_sink_distance_rank", 1) for spec in regions.values()}
    if len(ranks) <= 1:
        # All dies have same heat sink distance -- use graph distance from primary die
        max_dist = max(graph_distance.values()) if graph_distance else 1
        for region_id in regions:
            dist = graph_distance.get(region_id, 0)
            regions[region_id]["effective_distance_rank"] = max(1, dist + 1)
            # Also adjust cooling factor: closer to primary die = more heat from TAP
            regions[region_id]["cooling_factor"] = max(0.80, 0.95 - 0.04 * dist)
    else:
        for region_id in regions:
            regions[region_id]["effective_distance_rank"] = regions[region_id].get("heat_sink_distance_rank", 1)

    ambient = float(model.raw["package"].get("ambient_temperature_c", 25.0))
    temperatures = {region_id: ambient for region_id in regions}

    # Auto-calibrate capacitance divider based on schedule makespan.
    # The thermal time constant tau should be ~ makespan/10 so that
    # temperature reaches near steady-state within the schedule duration.
    makespan = max((phase.end_s for phase in phases), default=1.0)
    # Average base RC: avg(R) * avg(C) / capacitance_divider
    avg_r = sum(spec["thermal_resistance_c_per_w"] for spec in regions.values()) / max(len(regions), 1)
    avg_c = sum(spec["thermal_capacitance_j_per_c"] for spec in regions.values()) / max(len(regions), 1)
    target_tau = makespan / 10.0
    # Compute divider needed to achieve target_tau with scaled R
    scaled_r = avg_r * resistance_multiplier
    auto_capacitance_divider = max(capacitance_divider, avg_c / max(target_tau / scaled_r, EPSILON))
    # Blend: use the larger of the configured divider and the auto-calibrated one
    effective_capacitance_divider = max(capacitance_divider, auto_capacitance_divider)

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

        # Compute serial relay power penalty for dies that forward TAP traffic
        serial_relay_power = _compute_serial_relay_power(regions, active)

        # Phase 1: Compute individual RC temperatures
        new_temps = {}
        for region_id, spec in regions.items():
            base_resistance = spec["thermal_resistance_c_per_w"]
            # Apply heat sink distance factor (VHDF)
            distance_rank = spec.get("effective_distance_rank", spec.get("heat_sink_distance_rank", 1))
            distance_factor = 1.0 + gamma * (distance_rank - 1)
            # Scale resistance up for meaningful temp rise, capacitance down for fast response
            effective_resistance = base_resistance * distance_factor * resistance_multiplier

            base_capacitance = spec["thermal_capacitance_j_per_c"]
            effective_capacitance = max(base_capacitance / effective_capacitance_divider, 1e-6)

            total_power = effective_power[region_id] + serial_relay_power.get(region_id, 0.0)
            steady_state = ambient + total_power * effective_resistance
            tau = max(effective_resistance * effective_capacitance, EPSILON)
            new_temps[region_id] = steady_state + (temperatures[region_id] - steady_state) * math.exp(-dt / tau)

        # Phase 2: Apply die-to-die vertical thermal coupling
        coupled_temps = dict(new_temps)
        for region_id in regions:
            neighbors = vertical_adj.get(region_id, [])
            if not neighbors:
                continue
            # Heat flows from hotter to cooler dies
            coupling_delta = 0.0
            for neighbor_id in neighbors:
                # Coupling coefficient depends on direction:
                # alpha for heat flowing from neighbor below (lower layer_index),
                # beta for heat flowing from neighbor above (higher layer_index)
                neighbor_rank = regions[neighbor_id].get("effective_distance_rank", regions[neighbor_id].get("heat_sink_distance_rank", 1))
                self_rank = regions[region_id].get("effective_distance_rank", regions[region_id].get("heat_sink_distance_rank", 1))
                coeff = die_coupling_beta if neighbor_rank < self_rank else die_coupling_alpha
                # Heat contribution: only if neighbor is hotter, heat flows in
                if new_temps[neighbor_id] > new_temps[region_id]:
                    coupling_delta += coeff * (new_temps[neighbor_id] - new_temps[region_id])
                # Also add R_inter_die based steady coupling (using scaled resistance)
                coupled_power = own_power.get(neighbor_id, 0.0) * r_inter_die
                base_res = regions[region_id]["thermal_resistance_c_per_w"]
                coupling_delta += coupled_power * base_res * resistance_multiplier * coeff
            coupled_temps[region_id] += coupling_delta

        temperatures = coupled_temps

        for region_id, spec in regions.items():
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
        "# Thermal Proxy Report",
        "",
        "This report uses an upgraded first-order RC thermal proxy with die-to-die vertical coupling and heat sink distance factors (VHDF).",
        "",
        "## Schedule Summary",
        "",
        "| schedule | makespan_s | peak_temp_c | peak_region | over_limit_s | violations |",
        "| --- | ---: | ---: | --- | ---: | ---: |",
    ]
    for result in results:
        lines.append(
            f"| {result.schedule_id} | {result.makespan_s:.9f} | {result.peak_temperature_c:.2f} | "
            f"{result.peak_region} | {result.over_limit_duration_s:.9f} | {result.violation_count} |"
        )
    if best_peak is not None:
        lines.extend(
            [
                "",
                f"- Lowest proxy peak temperature: `{best_peak.schedule_id}` at {best_peak.peak_temperature_c:.2f} C.",
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
                    f"{hotspot.peak_temperature_c:.2f} | {hotspot.peak_time_s:.9f} | {hotspot.limit_c:.2f} |"
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
        exclusive_resource=row.get("exclusive_resource", ""),
        power_w=float(row["power_w"]),
        thermal_region=row["thermal_region"],
        resource_notes=row["resource_notes"],
    )


def _region_specs(model: SystemModel) -> dict[str, dict[str, float | str | int]]:
    region_limits = {
        str(region["region_id"]): float(region.get("max_temperature_c", model.resource_limits.get("max_temperature_c", 85.0)))
        for region in model.raw["resource_groups"].get("thermal_regions", [])
    }
    specs: dict[str, dict[str, float | str | int]] = {}
    for die in model.dies:
        thermal = die.get("thermal", {})
        region_id = str(thermal["region_id"])
        specs[region_id] = {
            "die_id": str(die["die_id"]),
            "thermal_resistance_c_per_w": float(thermal.get("thermal_resistance_c_per_w", 1.0)),
            "thermal_capacitance_j_per_c": float(thermal.get("thermal_capacitance_j_per_c", 1.0)),
            "limit_c": region_limits.get(region_id, float(model.resource_limits.get("max_temperature_c", 85.0))),
            "layer_index": int(die.get("layer_index", 0)),
            "heat_sink_distance_rank": int(thermal.get("heat_sink_distance_rank", 1)),
            "cooling_factor": float(thermal.get("cooling_factor", 0.95)),
            "access_parent_die": str(die.get("access_parent_die", "")),
            "tower_id": str(die.get("tower_id", "")),
        }
    return specs


def _build_vertical_adjacency(
    model: SystemModel,
    regions: dict[str, dict[str, float | str | int]],
) -> dict[str, list[str]]:
    """Build vertical adjacency map from thermal_adjacency edges.

    Returns a mapping from region_id to list of vertically adjacent region_ids.
    Only includes edges with coupling_type == 'vertical'.
    """
    adj: dict[str, list[str]] = {region_id: [] for region_id in regions}
    for edge in model.raw.get("thermal_adjacency", []):
        if edge.get("coupling_type") != "vertical":
            continue
        source = str(edge["source_region"])
        target = str(edge["target_region"])
        if source in adj and target in adj:
            adj[source].append(target)
            adj[target].append(source)
    return adj


def _build_all_adjacency(
    model: SystemModel,
    regions: dict[str, dict[str, float | str | int]],
) -> dict[str, list[str]]:
    """Build full adjacency map from all thermal_adjacency edges (all coupling types)."""
    adj: dict[str, list[str]] = {region_id: [] for region_id in regions}
    for edge in model.raw.get("thermal_adjacency", []):
        source = str(edge["source_region"])
        target = str(edge["target_region"])
        if source in adj and target in adj:
            adj[source].append(target)
            adj[target].append(source)
    return adj


def _compute_graph_distances(
    start_region: str,
    adj: dict[str, list[str]],
) -> dict[str, int]:
    """BFS distances from start_region in the thermal adjacency graph."""
    distances: dict[str, int] = {start_region: 0}
    queue = [start_region]
    while queue:
        current = queue.pop(0)
        for neighbor in adj.get(current, []):
            if neighbor not in distances:
                distances[neighbor] = distances[current] + 1
                queue.append(neighbor)
    # Default distances for unreachable nodes
    for region_id in adj:
        if region_id not in distances:
            distances[region_id] = len(adj)
    return distances


def _compute_serial_relay_power(
    regions: dict[str, dict[str, float | str | int]],
    active: list[ScheduledPhase],
) -> dict[str, float]:
    """Compute additional thermal power from serial TAP relay activity.

    When a die relays serial TAP traffic to deeper dies through the IEEE 1838
    serial access chain, the relay die dissipates extra power from STAP logic
    and TAP controller interface circuits.

    Uses the actual access_parent_die chain to determine which dies relay
    for which others. Also uses tower_id for multi-tower (5.5D) topologies
    where each tower has an independent access chain.
    """
    # Build access parent chain: die_id -> parent_die_id
    die_parent: dict[str, str | None] = {}
    die_to_region: dict[str, str] = {}
    die_tower: dict[str, str] = {}
    die_effective_rank: dict[str, int] = {}
    for region_id, spec in regions.items():
        die_id = spec["die_id"]
        die_to_region[die_id] = region_id
        parent = spec.get("access_parent_die", "")
        die_parent[die_id] = str(parent) if parent and str(parent) != "None" and str(parent) != "null" else None
        die_tower[die_id] = str(spec.get("tower_id", ""))
        die_effective_rank[die_id] = int(spec.get("effective_distance_rank", spec.get("heat_sink_distance_rank", 1)))

    # Build descendants: for each die, which dies are in its access subtree?
    descendants: dict[str, set[str]] = {spec["die_id"]: set() for spec in regions.values()}
    for die_id in descendants:
        # Walk up the parent chain to find ancestors
        current = die_parent.get(die_id)
        while current is not None and current in descendants:
            descendants[current].add(die_id)
            current = die_parent.get(current)

    # Count active serial phases per die
    serial_dies: set[str] = set()
    for phase in active:
        if phase.serial_required:
            if phase.die_id in die_to_region:
                serial_dies.add(phase.die_id)

    relay_power: dict[str, float] = {region_id: 0.0 for region_id in regions}
    # Relay power: each serial-active descendant contributes 0.08W
    # Dies that are active serially themselves contribute less relay (they do their own work)
    RELAY_POWER_PER_FORWARDED_DIE_W = 0.10
    # Direct serial activity on this die also generates extra controller power
    DIRECT_SERIAL_OVERHEAD_W = 0.05

    for region_id, spec in regions.items():
        die_id = spec["die_id"]
        # Count forwarded serial dies (descendants that are active in serial mode)
        descendant_serial = descendants.get(die_id, set()) & serial_dies
        forwarded_count = len(descendant_serial)
        relay_power[region_id] = forwarded_count * RELAY_POWER_PER_FORWARDED_DIE_W

        # If this die itself has active serial phases, add TAP controller overhead
        if die_id in serial_dies:
            relay_power[region_id] += DIRECT_SERIAL_OVERHEAD_W

    return relay_power


def _region_power(regions: dict[str, dict[str, float | str | int]], active: list[ScheduledPhase]) -> dict[str, float]:
    power = {region_id: 0.0 for region_id in regions}
    for phase in active:
        if phase.thermal_region in power:
            power[phase.thermal_region] += phase.power_w
    return power


def _effective_region_power(
    model: SystemModel,
    regions: dict[str, dict[str, float | str | int]],
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
