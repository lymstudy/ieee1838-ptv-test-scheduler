"""Serial IEEE 1838-style baseline scheduler."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from src.model.task import TaskType, TestTask
from src.scheduler.base import BaseScheduler, ScheduleEntry, ScheduleResult
from src.scheduler.evaluator import evaluate_schedule


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
            dwr_segment = self._dwr_segment_name(task)
            entries.append(
                ScheduleEntry(
                    task_id=task.id,
                    task_type=task.task_type.value,
                    die_id=task.die_id,
                    start_time=current_time,
                    end_time=current_time + duration,
                    duration=duration,
                    power=task.power_w,
                    fpp_lanes_used=self._fpp_lanes_used(task),
                    access_resource=self._access_resource(task),
                    dwr_segment=dwr_segment,
                    is_capture_phase=bool(getattr(task, "is_capture_phase", False)),
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
            return "PTAP_STAP_DWR_SERIAL"
        return "PTAP_STAP_SERIAL"

    @staticmethod
    def _fpp_lanes_used(task: TestTask) -> int:
        for attribute in ("fpp_lanes_used", "fpp_lanes_required", "required_fpp_lanes"):
            value = getattr(task, attribute, None)
            if value is not None:
                return int(value)
        return 0

    def _dwr_segment_name(self, task: TestTask) -> str:
        explicit = getattr(task, "dwr_segment", None)
        if explicit:
            return explicit
        try:
            return self.access.dwr_for_die(task.die_id).name
        except KeyError:
            return "DWR_NONE"

    def _evaluate(self, entries: Sequence[ScheduleEntry]) -> ScheduleResult:
        return evaluate_schedule(
            scheduler_name=self.scheduler_name,
            entries=entries,
            stack=self.stack,
            access=self.access,
            thermal_model=self.thermal_model,
            voltage_model=self.voltage_model,
            time_step_s=self.time_step_s,
        )


