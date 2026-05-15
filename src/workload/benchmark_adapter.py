"""Adapter from benchmark statistics YAML to abstract scheduler workloads."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class DieBenchmarkStats:
    """Statistics for one benchmark partition mapped to one die."""

    die_id: int
    module_name: str
    flip_flop_count: int
    scan_chain_count: int
    scan_chain_length: int
    estimated_shift_power: float
    estimated_capture_power: float
    estimated_bist_power: float
    estimated_instrument_power: float
    bist_task_count: int
    instrument_task_count: int


@dataclass(frozen=True)
class InterconnectStats:
    """Statistics for one inter-die DWR EXTEST workload item."""

    src_die: int
    dst_die: int
    dwr_length: int
    estimated_extest_power: float


@dataclass(frozen=True)
class PowerModelStats:
    """Simplified power and shared-PDN parameters."""

    vdd: float
    shared_resistance: float
    power_scale: float = 1.0


@dataclass(frozen=True)
class ThermalModelStats:
    """Simplified per-die thermal model parameters."""

    ambient_temperature: float
    initial_temperature: float
    thermal_alpha: float
    cooling_beta: float


@dataclass(frozen=True)
class SimulationStats:
    """Simulation timing parameters for a benchmark-derived workload."""

    clock_hz: float
    time_step_s: float


@dataclass(frozen=True)
class BenchmarkStats:
    """Benchmark statistics used to generate abstract test tasks."""

    benchmark_name: str
    die_count: int
    fpp_lanes: int
    voltage_limit: float
    thermal_limit: float
    max_concurrent_capture: int
    dummy_cycle_duration: float
    simulation: SimulationStats
    dies: tuple[DieBenchmarkStats, ...]
    interconnects: tuple[InterconnectStats, ...]
    power_model: PowerModelStats
    thermal_model: ThermalModelStats


def load_benchmark_stats(path: str | Path) -> BenchmarkStats:
    """Load benchmark statistics YAML and return a normalized dataclass."""

    yaml_path = Path(path)
    with yaml_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"benchmark stats YAML must contain a mapping: {yaml_path}")
    return benchmark_stats_from_dict(data)


def benchmark_stats_from_dict(data: dict[str, Any]) -> BenchmarkStats:
    """Build benchmark statistics from a dictionary."""

    dies = tuple(DieBenchmarkStats(**entry) for entry in data.get("dies", ()))
    interconnects = tuple(InterconnectStats(**entry) for entry in data.get("interconnects", ()))
    stats = BenchmarkStats(
        benchmark_name=str(data["benchmark_name"]),
        die_count=int(data["die_count"]),
        fpp_lanes=int(data["fpp_lanes"]),
        voltage_limit=float(data["voltage_limit"]),
        thermal_limit=float(data["thermal_limit"]),
        max_concurrent_capture=int(data.get("max_concurrent_capture", 1)),
        dummy_cycle_duration=float(data.get("dummy_cycle_duration", 0.0001)),
        simulation=SimulationStats(**data["simulation"]),
        dies=dies,
        interconnects=interconnects,
        power_model=PowerModelStats(**data["power_model"]),
        thermal_model=ThermalModelStats(**data["thermal_model"]),
    )
    _validate_stats(stats)
    return stats


def generate_tasks_from_benchmark(stats: BenchmarkStats) -> list[dict[str, Any]]:
    """Generate scheduler-compatible task dictionaries from benchmark statistics."""

    tasks: list[dict[str, Any]] = []
    for die in sorted(stats.dies, key=lambda item: item.die_id):
        instrument_ids = []
        for index in range(die.instrument_task_count):
            task = _instrument_task(stats, die, index)
            instrument_ids.append(task["id"])
            tasks.append(task)

        for index in range(die.bist_task_count):
            tasks.append(_bist_task(stats, die, index))

        scan_shift = _scan_shift_task(stats, die)
        tasks.append(scan_shift)
        tasks.append(_capture_task(stats, die, scan_shift["id"], instrument_ids))

    for interconnect in sorted(stats.interconnects, key=lambda item: (item.src_die, item.dst_die, item.dwr_length)):
        tasks.append(_dwr_extest_task(stats, interconnect))
    return tasks


def generate_case_from_benchmark(stats: BenchmarkStats) -> dict[str, Any]:
    """Generate a config-like workload dictionary consumed by existing schedulers."""

    return {
        "case": {
            "name": stats.benchmark_name,
            "description": "Benchmark-statistics-derived workload example, not direct RTL parsing.",
            "source": "benchmarks statistics schema",
        },
        "simulation": {
            "time_step_s": float(stats.simulation.time_step_s),
            "clock_hz": float(stats.simulation.clock_hz),
        },
        "thermal": {
            "ambient_temp_c": float(stats.thermal_model.ambient_temperature),
            "thermal_resistance_c_per_w": float(stats.thermal_model.thermal_alpha),
            "thermal_capacitance_j_per_c": float(stats.thermal_model.cooling_beta),
            "max_temp_c": float(stats.thermal_limit),
        },
        "voltage": {
            "nominal_voltage_v": float(stats.power_model.vdd),
            "pdn_resistance_ohm": float(stats.power_model.shared_resistance),
            "mode": "shared",
            "max_ir_drop_v": float(stats.voltage_limit),
        },
        "scheduler": {
            "max_concurrent_capture": int(stats.max_concurrent_capture),
            "dummy_cycle_duration_s": float(stats.dummy_cycle_duration),
            "max_dummy_cycles_per_block": 80,
        },
        "stack": {"dies": _stack_dies(stats)},
        "access": _access_config(stats),
        "tasks": generate_tasks_from_benchmark(stats),
    }


def _validate_stats(stats: BenchmarkStats) -> None:
    if stats.die_count <= 0:
        raise ValueError("die_count must be positive")
    if len(stats.dies) != stats.die_count:
        raise ValueError("die_count must match the number of die entries")
    if stats.fpp_lanes < 0:
        raise ValueError("fpp_lanes must be non-negative")
    die_ids = [die.die_id for die in stats.dies]
    if len(die_ids) != len(set(die_ids)):
        raise ValueError("die_id values must be unique")
    for die in stats.dies:
        if die.flip_flop_count <= 0:
            raise ValueError("flip_flop_count must be positive")
        if die.scan_chain_count <= 0:
            raise ValueError("scan_chain_count must be positive")
        if die.scan_chain_length <= 0:
            raise ValueError("scan_chain_length must be positive")
        if die.bist_task_count < 0 or die.instrument_task_count < 0:
            raise ValueError("task counts must be non-negative")
    known_die_ids = set(die_ids)
    for interconnect in stats.interconnects:
        if interconnect.src_die not in known_die_ids or interconnect.dst_die not in known_die_ids:
            raise ValueError("interconnect endpoints must reference known dies")
        if interconnect.src_die == interconnect.dst_die:
            raise ValueError("interconnect endpoints must be distinct dies")
        if interconnect.dwr_length <= 0:
            raise ValueError("dwr_length must be positive")


def _stack_dies(stats: BenchmarkStats) -> list[dict[str, Any]]:
    dies = []
    for index, die in enumerate(sorted(stats.dies, key=lambda item: item.die_id)):
        nominal_power = (
            die.estimated_shift_power
            + die.estimated_capture_power
            + die.estimated_bist_power
            + die.estimated_instrument_power
        ) / 4.0
        dies.append(
            {
                "id": die.die_id,
                "name": die.module_name,
                "layer_index": index,
                "area_mm2": 35.0 + die.flip_flop_count / 2000.0,
                "initial_temp_c": float(stats.thermal_model.initial_temperature),
                "nominal_power_w": _scaled_power(stats, nominal_power),
            }
        )
    return dies


def _access_config(stats: BenchmarkStats) -> dict[str, Any]:
    return {
        "ptap_width_bits": 1,
        "stap_count": stats.die_count,
        "fpp_enabled": stats.fpp_lanes > 0,
        "fpp_lanes": stats.fpp_lanes,
        "fpp_lane_width_bits": 1,
        "dwr_segments": [
            {
                "die_id": die.die_id,
                "name": f"dwr_die{die.die_id}",
                "length_bits": max(64, die.scan_chain_count * 16),
            }
            for die in sorted(stats.dies, key=lambda item: item.die_id)
        ],
    }


def _instrument_task(stats: BenchmarkStats, die: DieBenchmarkStats, index: int) -> dict[str, Any]:
    return {
        "id": f"instrument_access_die{die.die_id}_{index}",
        "die_id": die.die_id,
        "task_type": "instrument_access",
        "duration_cycles": _instrument_duration_cycles(die, index),
        "access_width_bits": 1,
        "power_w": _scaled_power(stats, die.estimated_instrument_power),
        "fpp_lanes_required": 0,
        "dwr_segment": "DWR_NONE",
    }


def _bist_task(stats: BenchmarkStats, die: DieBenchmarkStats, index: int) -> dict[str, Any]:
    return {
        "id": f"bist_die{die.die_id}_{index}",
        "die_id": die.die_id,
        "task_type": "bist",
        "duration_cycles": _bist_duration_cycles(die, index),
        "access_width_bits": 1,
        "power_w": _scaled_power(stats, die.estimated_bist_power),
        "fpp_lanes_required": 0,
        "dwr_segment": "DWR_NONE",
    }


def _scan_shift_task(stats: BenchmarkStats, die: DieBenchmarkStats) -> dict[str, Any]:
    return {
        "id": f"scan_shift_die{die.die_id}",
        "die_id": die.die_id,
        "task_type": "scan",
        "duration_cycles": _scan_shift_duration_cycles(stats, die),
        "access_width_bits": 1,
        "power_w": _scaled_power(stats, die.estimated_shift_power),
        "fpp_lanes_required": _scan_fpp_lanes(stats, die),
        "dwr_segment": f"dwr_die{die.die_id}",
    }


def _capture_task(
    stats: BenchmarkStats,
    die: DieBenchmarkStats,
    scan_shift_id: str,
    instrument_ids: list[str],
) -> dict[str, Any]:
    return {
        "id": f"scan_capture_die{die.die_id}",
        "die_id": die.die_id,
        "task_type": "scan",
        "duration_cycles": _capture_duration_cycles(die),
        "access_width_bits": 1,
        "power_w": _scaled_power(stats, die.estimated_capture_power),
        "fpp_lanes_required": min(1, stats.fpp_lanes) if stats.fpp_lanes > 0 else 0,
        "dwr_segment": f"dwr_die{die.die_id}",
        "is_capture_phase": True,
        "dependencies": tuple(instrument_ids + [scan_shift_id]),
    }


def _dwr_extest_task(stats: BenchmarkStats, interconnect: InterconnectStats) -> dict[str, Any]:
    return {
        "id": f"dwr_extest_die{interconnect.src_die}_die{interconnect.dst_die}",
        "die_id": interconnect.src_die,
        "task_type": "dwr_extest",
        "duration_cycles": max(100, int(ceil(interconnect.dwr_length * 2.0))),
        "access_width_bits": 1,
        "power_w": _scaled_power(stats, interconnect.estimated_extest_power),
        "fpp_lanes_required": min(1, stats.fpp_lanes) if stats.fpp_lanes > 0 else 0,
        "dwr_segment": f"dwr_die{interconnect.src_die}_die{interconnect.dst_die}",
    }


def _scan_shift_duration_cycles(stats: BenchmarkStats, die: DieBenchmarkStats) -> int:
    active_lanes = max(1, min(stats.fpp_lanes, die.scan_chain_count))
    chain_groups = ceil(die.scan_chain_count / active_lanes)
    return max(100, int(die.scan_chain_length * chain_groups))


def _capture_duration_cycles(die: DieBenchmarkStats) -> int:
    return max(100, int(ceil(die.scan_chain_length * 0.05 + die.scan_chain_count * 20)))


def _bist_duration_cycles(die: DieBenchmarkStats, index: int) -> int:
    base_cycles = die.scan_chain_length * 2 + die.flip_flop_count / max(1, die.scan_chain_count)
    return max(1000, int(ceil(base_cycles + index * die.scan_chain_length * 0.25)))


def _instrument_duration_cycles(die: DieBenchmarkStats, index: int) -> int:
    return max(200, int(ceil(die.scan_chain_count * 20 + die.scan_chain_length * 0.04 + index * 50)))


def _scan_fpp_lanes(stats: BenchmarkStats, die: DieBenchmarkStats) -> int:
    if stats.fpp_lanes <= 0:
        return 0
    return max(1, min(stats.fpp_lanes, ceil(die.scan_chain_count / 8)))


def _scaled_power(stats: BenchmarkStats, power_w: float) -> float:
    return float(power_w) * float(stats.power_model.power_scale)
