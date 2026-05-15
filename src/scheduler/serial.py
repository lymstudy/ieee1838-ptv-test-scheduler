"""Serial IEEE 1838-style baseline scheduler."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from src.model.task import TaskType, TestTask
from src.model.thermal import TemperatureState
from src.scheduler.base import BaseScheduler, ScheduleEntry, ScheduleResult


TASK_TYPE_PRIORITY = {
    TaskType.INSTRUMENT_ACCESS: 0,
    TaskType.BIST: 1,
    TaskType.DWR_EXTEST: 2,
    TaskType.SCAN: 3,
}


class SerialScheduler(BaseScheduler):
    """Schedule tasks one at a time through the serial IEEE 1838-style path."""

    scheduler_name = "serial_ieee1838_style"

    def schedule(self, tasks: Sequence[TestTask]) -> ScheduleResult:
        """Build a non-overlapping serial schedule and evaluate PTV traces."""

        ordered_tasks = self._order_tasks(tasks)
        entries: list[ScheduleEntry] = []
        current_time = 0.0

        for task in ordered_tasks:
            duration = task.duration_s(self.clock_hz)
            dwr_segment = self.access.dwr_for_die(task.die_id)
            entries.append(
                ScheduleEntry(
                    task_id=task.id,
                    task_type=task.task_type.value,
                    die_id=task.die_id,
                    start_time=current_time,
                    end_time=current_time + duration,
                    duration=duration,
                    power=task.power_w,
                    fpp_lanes_used=0,
                    access_resource=self._access_resource(task),
                    dwr_segment=dwr_segment.name,
                    is_capture_phase=False,
                )
            )
            current_time += duration

        return self._evaluate(entries)

    def _order_tasks(self, tasks: Sequence[TestTask]) -> tuple[TestTask, ...]:
        ordered = sorted(tasks, key=self._sort_key)
        dependencies = {task.id: self._dependencies_for(task) for task in ordered}
        known_task_ids = {task.id for task in ordered}

        for task_id, task_dependencies in dependencies.items():
            unknown = task_dependencies - known_task_ids
            if unknown:
                raise ValueError(f"task {task_id} has unknown dependencies: {sorted(unknown)}")

        result: list[TestTask] = []
        scheduled_ids: set[str] = set()
        remaining = list(ordered)

        while remaining:
            ready = [task for task in remaining if dependencies[task.id].issubset(scheduled_ids)]
            if not ready:
                unresolved = {task.id: sorted(dependencies[task.id] - scheduled_ids) for task in remaining}
                raise ValueError(f"task dependencies contain a cycle or unsatisfied dependency: {unresolved}")
            task = ready[0]
            result.append(task)
            scheduled_ids.add(task.id)
            remaining.remove(task)

        return tuple(result)

    def _sort_key(self, task: TestTask) -> tuple[int, int, str]:
        die_order = {die_id: index for index, die_id in enumerate(self.stack.die_ids())}
        if task.die_id not in die_order:
            raise ValueError(f"task {task.id} references unknown die id {task.die_id}")
        return (
            die_order[task.die_id],
            TASK_TYPE_PRIORITY[task.task_type],
            task.id,
        )

    @staticmethod
    def _dependencies_for(task: TestTask) -> set[str]:
        dependency_values = (
            getattr(task, "dependencies", None)
            or getattr(task, "depends_on_task_ids", None)
            or getattr(task, "depends_on", None)
            or ()
        )
        if isinstance(dependency_values, str):
            return {dependency_values}
        if isinstance(dependency_values, Iterable):
            return {str(value) for value in dependency_values}
        raise TypeError(f"dependencies for task {task.id} must be iterable")

    @staticmethod
    def _access_resource(task: TestTask) -> str:
        if task.task_type == TaskType.DWR_EXTEST:
            return "PTAP/STAP/DWR serial path"
        return "PTAP/STAP serial path"

    def _evaluate(self, entries: Sequence[ScheduleEntry]) -> ScheduleResult:
        current_state = TemperatureState({die.id: die.initial_temp_c for die in self.stack.dies})
        temperature_trace = [self._temperature_trace_row(0.0, current_state)]
        zero_power = {die.id: 0.0 for die in self.stack.dies}
        zero_voltage = self.voltage_model.estimate(zero_power)
        ir_drop_trace = [self._voltage_trace_row(0.0, zero_voltage.ir_drop_by_die_v)]

        temperature_violation_count = 0
        voltage_violation_count = 0
        peak_temperature = current_state.peak_temp_c()
        peak_ir_drop = 0.0

        for entry in entries:
            active_power = {die.id: 0.0 for die in self.stack.dies}
            active_power[entry.die_id] = entry.power
            voltage_state = self.voltage_model.estimate(active_power)
            if self.voltage_model.violates_limit(voltage_state):
                voltage_violation_count += 1
            peak_ir_drop = max(peak_ir_drop, voltage_state.peak_ir_drop_v())

            elapsed = 0.0
            while elapsed < entry.duration:
                step = min(self.time_step_s, entry.duration - elapsed)
                current_state = self.thermal_model.step(current_state, active_power, step)
                sample_time = entry.start_time + elapsed + step
                temperature_trace.append(self._temperature_trace_row(sample_time, current_state))
                ir_drop_trace.append(self._voltage_trace_row(sample_time, voltage_state.ir_drop_by_die_v))

                if self.thermal_model.violates_limit(current_state):
                    temperature_violation_count += 1
                peak_temperature = max(peak_temperature, current_state.peak_temp_c())
                elapsed += step

        tat = entries[-1].end_time if entries else 0.0
        metrics: dict[str, float | int] = {
            "task_count": len(entries),
            "tat": tat,
            "peak_temperature": peak_temperature,
            "peak_ir_drop": peak_ir_drop,
            "temperature_violation_count": temperature_violation_count,
            "voltage_violation_count": voltage_violation_count,
        }
        return ScheduleResult(
            scheduler_name=self.scheduler_name,
            entries=tuple(entries),
            tat=tat,
            peak_temperature=peak_temperature,
            peak_ir_drop=peak_ir_drop,
            temperature_trace=tuple(temperature_trace),
            ir_drop_trace=tuple(ir_drop_trace),
            metrics=metrics,
        )

    def _temperature_trace_row(self, time_s: float, state: TemperatureState) -> dict[str, float]:
        row = {"time": time_s}
        row.update({f"die_{die_id}": state.by_die_id[die_id] for die_id in self.stack.die_ids()})
        row["peak_temperature"] = state.peak_temp_c()
        return row

    def _voltage_trace_row(self, time_s: float, ir_drop_by_die_v: dict[int, float]) -> dict[str, float]:
        row = {"time": time_s}
        row.update({f"die_{die_id}": ir_drop_by_die_v.get(die_id, 0.0) for die_id in self.stack.die_ids()})
        row["peak_ir_drop"] = max(row[f"die_{die_id}"] for die_id in self.stack.die_ids())
        return row
