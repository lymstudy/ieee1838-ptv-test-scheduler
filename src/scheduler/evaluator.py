"""Schedule-based physical and utilization evaluator."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from src.model.access import AccessConfig
from src.model.stack import DieStack
from src.model.thermal import RCThermalModel, TemperatureState
from src.model.voltage import EquivalentPdnModel
from src.scheduler.base import ScheduleEntry, ScheduleResult


def evaluate_schedule(
    *,
    scheduler_name: str,
    entries: Sequence[ScheduleEntry],
    stack: DieStack,
    access: AccessConfig,
    thermal_model: RCThermalModel,
    voltage_model: EquivalentPdnModel,
    time_step_s: float,
    dummy_intervals: Sequence[tuple[float, float]] = (),
    extra_metrics: dict[str, Any] | None = None,
) -> ScheduleResult:
    """Evaluate one schedule using active tasks at each event interval."""

    if time_step_s <= 0:
        raise ValueError("time_step_s must be positive")

    ordered_entries = tuple(sorted(entries, key=lambda entry: (entry.start_time, entry.end_time, entry.task_id)))
    tat = max([0.0, *(entry.end_time for entry in ordered_entries), *(end for _, end in dummy_intervals)])

    current_state = TemperatureState({die.id: die.initial_temp_c for die in stack.dies})
    zero_power = _zero_power(stack)
    zero_voltage = voltage_model.estimate(zero_power)
    temperature_trace = [_temperature_trace_row(0.0, current_state, stack)]
    ir_drop_trace = [_voltage_trace_row(0.0, zero_voltage.ir_drop_by_die_v, stack, zero_voltage.total_power_w, zero_voltage.total_current_a, 0)]

    peak_temperature = current_state.peak_temp_c()
    peak_ir_drop = zero_voltage.peak_ir_drop_v()
    temperature_violation_count = 0
    voltage_violation_count = 0
    max_parallelism = 0

    for start_time, end_time in _event_intervals(ordered_entries, dummy_intervals):
        interval = end_time - start_time
        if interval <= 0:
            continue

        active_entries = _active_entries(ordered_entries, start_time)
        active_power = _active_power_by_die(active_entries, stack)
        active_count = len(active_entries)
        max_parallelism = max(max_parallelism, active_count)
        voltage_state = voltage_model.estimate(active_power)
        peak_ir_drop = max(peak_ir_drop, voltage_state.peak_ir_drop_v())
        voltage_violates = voltage_model.violates_limit(voltage_state)

        elapsed = 0.0
        while elapsed < interval:
            step = min(time_step_s, interval - elapsed)
            current_state = thermal_model.step(current_state, active_power, step)
            sample_time = start_time + elapsed + step
            temperature_trace.append(_temperature_trace_row(sample_time, current_state, stack))
            ir_drop_trace.append(
                _voltage_trace_row(
                    sample_time,
                    voltage_state.ir_drop_by_die_v,
                    stack,
                    voltage_state.total_power_w,
                    voltage_state.total_current_a,
                    active_count,
                )
            )

            if thermal_model.violates_limit(current_state):
                temperature_violation_count += 1
            if voltage_violates:
                voltage_violation_count += 1
            peak_temperature = max(peak_temperature, current_state.peak_temp_c())
            elapsed += step

    total_task_time = sum(entry.duration for entry in ordered_entries)
    lane_time = sum(entry.duration * entry.fpp_lanes_used for entry in ordered_entries)
    lane_capacity = _fpp_lane_capacity(access)
    average_parallelism = total_task_time / tat if tat > 0 else 0.0
    fpp_lane_utilization_average = lane_time / (tat * lane_capacity) if tat > 0 and lane_capacity > 0 else 0.0

    metrics: dict[str, Any] = {
        "scheduler_name": scheduler_name,
        "tat": tat,
        "peak_temperature": peak_temperature,
        "peak_ir_drop": peak_ir_drop,
        "temperature_violation_count": temperature_violation_count,
        "voltage_violation_count": voltage_violation_count,
        "num_tasks": len(ordered_entries),
        "average_parallelism": average_parallelism,
        "max_parallelism": max_parallelism,
        "fpp_lane_utilization_average": fpp_lane_utilization_average,
        "voltage_model_mode": voltage_model.config.mode,
    }
    if extra_metrics:
        metrics.update(extra_metrics)

    return ScheduleResult(
        scheduler_name=scheduler_name,
        entries=ordered_entries,
        tat=tat,
        peak_temperature=peak_temperature,
        peak_ir_drop=peak_ir_drop,
        temperature_trace=tuple(temperature_trace),
        ir_drop_trace=tuple(ir_drop_trace),
        metrics=metrics,
    )


def _event_intervals(
    entries: Sequence[ScheduleEntry],
    dummy_intervals: Sequence[tuple[float, float]],
) -> list[tuple[float, float]]:
    event_times = sorted(
        {
            0.0,
            *(entry.start_time for entry in entries),
            *(entry.end_time for entry in entries),
            *(time for interval in dummy_intervals for time in interval),
        }
    )
    return [(start, end) for start, end in zip(event_times, event_times[1:]) if end > start]


def _active_entries(entries: Sequence[ScheduleEntry], time_s: float) -> list[ScheduleEntry]:
    return [entry for entry in entries if entry.start_time <= time_s + 1e-15 and entry.end_time > time_s + 1e-15]


def _zero_power(stack: DieStack) -> dict[int, float]:
    return {die.id: 0.0 for die in stack.dies}


def _active_power_by_die(active_entries: Sequence[ScheduleEntry], stack: DieStack) -> dict[int, float]:
    power_by_die = _zero_power(stack)
    for entry in active_entries:
        power_by_die[entry.die_id] += entry.power
    return power_by_die


def _fpp_lane_capacity(access: AccessConfig) -> int:
    if not access.fpp.enabled:
        return 0
    return access.fpp.lanes


def _temperature_trace_row(time_s: float, state: TemperatureState, stack: DieStack) -> dict[str, float]:
    row = {"time": time_s}
    row.update({f"die_{die_id}": state.by_die_id[die_id] for die_id in stack.die_ids()})
    row["peak_temperature"] = state.peak_temp_c()
    return row


def _voltage_trace_row(
    time_s: float,
    ir_drop_by_die_v: dict[int, float],
    stack: DieStack,
    total_power_w: float,
    total_current_a: float,
    active_task_count: int,
) -> dict[str, float]:
    row = {"time": time_s}
    row.update({f"die_{die_id}": ir_drop_by_die_v.get(die_id, 0.0) for die_id in stack.die_ids()})
    row["peak_ir_drop"] = max(row[f"die_{die_id}"] for die_id in stack.die_ids())
    row["total_power"] = total_power_w
    row["total_current"] = total_current_a
    row["active_task_count"] = active_task_count
    return row
