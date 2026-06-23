"""Deterministic synthetic workloads for mechanism-validation experiments."""

from __future__ import annotations

from dataclasses import dataclass


DENSITY_ORDER = ("small", "medium", "large")


@dataclass(frozen=True)
class DensityProfile:
    """Per-die task counts for a synthetic workload density."""

    scan_shift_per_die: int
    capture_per_die: int
    bist_per_die: int
    instrument_per_die: int
    dwr_extest_per_adjacent_pair: int


DENSITY_PROFILES = {
    "small": DensityProfile(
        scan_shift_per_die=1,
        capture_per_die=1,
        bist_per_die=1,
        instrument_per_die=1,
        dwr_extest_per_adjacent_pair=1,
    ),
    "medium": DensityProfile(
        scan_shift_per_die=2,
        capture_per_die=1,
        bist_per_die=1,
        instrument_per_die=2,
        dwr_extest_per_adjacent_pair=1,
    ),
    "large": DensityProfile(
        scan_shift_per_die=4,
        capture_per_die=2,
        bist_per_die=2,
        instrument_per_die=2,
        dwr_extest_per_adjacent_pair=2,
    ),
}


def generate_synthetic_case(die_count: int, task_density: str) -> dict:
    """Generate a deterministic synthetic mechanism-validation case."""

    if die_count <= 1:
        raise ValueError("die_count must be greater than one")
    if task_density not in DENSITY_PROFILES:
        raise ValueError(f"unknown task_density: {task_density}")

    profile = DENSITY_PROFILES[task_density]
    return {
        "case": {
            "name": f"synthetic_{die_count}die_{task_density}",
            "description": "Deterministic synthetic mechanism-validation workload, not a real benchmark.",
            "generator": "src.workload.synthetic.generate_synthetic_case",
            "deterministic": True,
        },
        "simulation": {
            "time_step_s": 0.0002,
            "clock_hz": 1_000_000,
        },
        "thermal": {
            "ambient_temp_c": 25.0,
            "thermal_resistance_c_per_w": 1.0,
            "thermal_capacitance_j_per_c": 0.012,
            "max_temp_c": 27.0,
        },
        "voltage": {
            "nominal_voltage_v": 0.80,
            "pdn_resistance_ohm": 0.050,
            "mode": "shared",
            "max_ir_drop_v": 0.24,
        },
        "scheduler": {
            "max_concurrent_capture": 1,
            "dummy_cycle_duration_s": 0.0002,
            "max_dummy_cycles_per_block": 80,
        },
        "stack": {"dies": _generate_dies(die_count)},
        "access": _generate_access(die_count),
        "tasks": _generate_tasks(die_count, profile),
    }


def expected_task_count(die_count: int, task_density: str) -> int:
    """Return the deterministic task count for a generated workload."""

    if task_density not in DENSITY_PROFILES:
        raise ValueError(f"unknown task_density: {task_density}")
    profile = DENSITY_PROFILES[task_density]
    per_die = (
        profile.scan_shift_per_die
        + profile.capture_per_die
        + profile.bist_per_die
        + profile.instrument_per_die
    )
    adjacent_pairs = die_count - 1
    return die_count * per_die + adjacent_pairs * profile.dwr_extest_per_adjacent_pair


def _generate_dies(die_count: int) -> list[dict]:
    dies = []
    for die_id in range(die_count):
        dies.append(
            {
                "id": die_id,
                "name": f"synthetic_die{die_id}",
                "layer_index": die_id,
                "area_mm2": 38.0 + float(die_id % 4) * 2.0,
                "initial_temp_c": 25.35 + float(die_id % 3) * 0.02,
                "nominal_power_w": 0.35 + float(die_id % 5) * 0.02,
            }
        )
    return dies


def _generate_access(die_count: int) -> dict:
    return {
        "ptap_width_bits": 1,
        "stap_count": die_count,
        "fpp_enabled": True,
        "fpp_lanes": 4,
        "fpp_lane_width_bits": 1,
        "dwr_segments": [
            {
                "die_id": die_id,
                "name": f"dwr_die{die_id}",
                "length_bits": 256 + 16 * (die_id % 4),
            }
            for die_id in range(die_count)
        ],
    }


def _generate_tasks(die_count: int, profile: DensityProfile) -> list[dict]:
    tasks: list[dict] = []
    for die_id in range(die_count):
        shift_ids = []
        for index in range(profile.instrument_per_die):
            tasks.append(_instrument_task(die_id, index))
        for index in range(profile.bist_per_die):
            tasks.append(_bist_task(die_id, index))
        for index in range(profile.scan_shift_per_die):
            task = _scan_shift_task(die_id, index)
            shift_ids.append(task["id"])
            tasks.append(task)
        for index in range(profile.capture_per_die):
            tasks.append(_capture_task(die_id, index, shift_ids))

    for die_id in range(die_count - 1):
        for index in range(profile.dwr_extest_per_adjacent_pair):
            tasks.append(_dwr_extest_task(die_id, die_id + 1, index))
    return tasks


def _instrument_task(die_id: int, index: int) -> dict:
    return {
        "id": f"instrument_access_die{die_id}_{index}",
        "die_id": die_id,
        "task_type": "instrument_access",
        "duration_cycles": 350 + 25 * index,
        "access_width_bits": 1,
        "power_w": 0.18 + 0.01 * (die_id % 3),
        "fpp_lanes_required": 0,
        "dwr_segment": "DWR_NONE",
    }


def _bist_task(die_id: int, index: int) -> dict:
    return {
        "id": f"bist_die{die_id}_{index}",
        "die_id": die_id,
        "task_type": "bist",
        "duration_cycles": 2200 + 250 * index,
        "access_width_bits": 1,
        "power_w": 1.12 + 0.04 * (die_id % 4) + 0.05 * index,
        "fpp_lanes_required": 0,
        "dwr_segment": "DWR_NONE",
    }


def _scan_shift_task(die_id: int, index: int) -> dict:
    return {
        "id": f"scan_shift_die{die_id}_{index}",
        "die_id": die_id,
        "task_type": "scan",
        "duration_cycles": 2200 + 220 * index,
        "access_width_bits": 1,
        "power_w": 1.05 + 0.03 * (die_id % 4) + 0.04 * index,
        "fpp_lanes_required": 1,
        "dwr_segment": f"dwr_die{die_id}",
    }


def _capture_task(die_id: int, index: int, shift_ids: list[str]) -> dict:
    return {
        "id": f"scan_capture_die{die_id}_{index}",
        "die_id": die_id,
        "task_type": "scan",
        "duration_cycles": 900 + 100 * index,
        "access_width_bits": 1,
        "power_w": 1.32 + 0.03 * (die_id % 4) + 0.05 * index,
        "fpp_lanes_required": 1,
        "dwr_segment": f"dwr_die{die_id}",
        "is_capture_phase": True,
        "dependencies": tuple(shift_ids),
    }


def _dwr_extest_task(first_die_id: int, second_die_id: int, index: int) -> dict:
    return {
        "id": f"dwr_extest_die{first_die_id}_die{second_die_id}_{index}",
        "die_id": first_die_id,
        "task_type": "dwr_extest",
        "duration_cycles": 1500 + 150 * index,
        "access_width_bits": 1,
        "power_w": 0.88 + 0.03 * ((first_die_id + second_die_id) % 4),
        "fpp_lanes_required": 1,
        "dwr_segment": f"dwr_die{first_die_id}_die{second_die_id}",
    }
