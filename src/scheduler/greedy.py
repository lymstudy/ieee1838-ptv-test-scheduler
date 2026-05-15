"""Bandwidth-greedy baseline scheduler."""

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

DEFAULT_FPP_LANES_BY_TASK_TYPE = {
    TaskType.SCAN: 1,
    TaskType.BIST: 0,
    TaskType.DWR_EXTEST: 1,
    TaskType.INSTRUMENT_ACCESS: 0,
}


class BandwidthGreedyScheduler(BaseScheduler):
    """Aggressively parallel scheduler constrained by access bandwidth only."""

    scheduler_name = "bandwidth_greedy"

    def schedule(self, tasks: Sequence[TestTask]) -> ScheduleResult:
        """Build a deterministic bandwidth-greedy schedule and evaluate PTV traces."""

        pending = list(sorted(tasks, key=self._sort_key))
        known_task_ids = {task.id for task in pending}
        dependencies = {task.id: self._dependencies_for(task) for task in pending}
        for task_id, task_dependencies in dependencies.items():
            unknown = task_dependencies - known_task_ids
            if unknown:
                raise ValueError(f"task {task_id} has unknown dependencies: {sorted(unknown)}")

        current_time = 0.0
        completed_ids: set[str] = set()
        running: list[ScheduleEntry] = []
        entries: list[ScheduleEntry] = []

        while pending or running:
            finished = [entry for entry in running if entry.end_time <= current_time + 1e-15]
            if finished:
                completed_ids.update(entry.task_id for entry in finished)
                running = [entry for entry in running if entry.end_time > current_time + 1e-15]

            ready = [task for task in pending if dependencies[task.id].issubset(completed_ids)]
            ready.sort(key=self._sort_key)

            resources = self._used_resources(running)
            started_any = False
            for task in ready:
                if not self._can_start(task, resources):
                    continue
                entry = self._entry_for_task(task, current_time)
                entries.append(entry)
                running.append(entry)
                pending.remove(task)
                self._reserve(entry, resources)
                started_any = True

            if running:
                current_time = min(entry.end_time for entry in running)
                continue

            if pending and not started_any:
                unresolved = {task.id: sorted(dependencies[task.id] - completed_ids) for task in pending}
                raise ValueError(f"no schedulable task remains; unresolved dependencies: {unresolved}")

        entries.sort(key=self._entry_sort_key)
        return self._evaluate(entries)


    def _entry_sort_key(self, entry: ScheduleEntry) -> tuple[float, int, int, str]:
        die_order = {die_id: index for index, die_id in enumerate(self.stack.die_ids())}
        return (
            entry.start_time,
            die_order.get(entry.die_id, entry.die_id),
            TASK_TYPE_PRIORITY[TaskType(entry.task_type)],
            entry.task_id,
        )
    def _entry_for_task(self, task: TestTask, start_time: float) -> ScheduleEntry:
        duration = task.duration_s(self.clock_hz)
        return ScheduleEntry(
            task_id=task.id,
            task_type=task.task_type.value,
            die_id=task.die_id,
            start_time=start_time,
            end_time=start_time + duration,
            duration=duration,
            power=task.power_w,
            fpp_lanes_used=self._fpp_lanes_required(task),
            access_resource=self._access_resource(task),
            dwr_segment=self._dwr_segment_name(task),
            is_capture_phase=bool(getattr(task, "is_capture_phase", False)),
        )

    def _sort_key(self, task: TestTask) -> tuple[int, int, str]:
        die_order = {die_id: index for index, die_id in enumerate(self.stack.die_ids())}
        if task.die_id not in die_order:
            raise ValueError(f"task {task.id} references unknown die id {task.die_id}")
        return (die_order[task.die_id], TASK_TYPE_PRIORITY[task.task_type], task.id)

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

    def _fpp_lane_capacity(self) -> int:
        if not self.access.fpp.enabled:
            return 0
        return self.access.fpp.lanes

    def _fpp_lanes_required(self, task: TestTask) -> int:
        for attribute in ("fpp_lanes_required", "required_fpp_lanes", "fpp_lanes_used"):
            explicit = getattr(task, attribute, None)
            if explicit is not None:
                return int(explicit)
        return DEFAULT_FPP_LANES_BY_TASK_TYPE[task.task_type]

    @staticmethod
    def _access_resource(task: TestTask) -> str:
        if task.task_type == TaskType.INSTRUMENT_ACCESS:
            return "PTAP_STAP_SERIAL"
        if task.task_type == TaskType.BIST:
            return "BIST_LOCAL"
        if task.task_type == TaskType.DWR_EXTEST:
            return "FPP_DWR"
        return "FPP_SCAN"

    def _exclusive_access_resource(self, task_or_entry: TestTask | ScheduleEntry) -> str | None:
        task_type = task_or_entry.task_type
        if isinstance(task_type, str):
            task_type = TaskType(task_type)
        if task_type == TaskType.INSTRUMENT_ACCESS:
            return "PTAP_STAP_SERIAL"
        return None

    def _dwr_segment_name(self, task: TestTask) -> str:
        explicit = getattr(task, "dwr_segment", None)
        if explicit:
            return explicit
        try:
            return self.access.dwr_for_die(task.die_id).name
        except KeyError:
            return "DWR_NONE"

    def _used_resources(self, running: Sequence[ScheduleEntry]) -> dict[str, object]:
        return {
            "fpp_lanes": sum(entry.fpp_lanes_used for entry in running),
            "dwr_segments": {entry.dwr_segment for entry in running if entry.dwr_segment and entry.dwr_segment != "DWR_NONE"},
            "exclusive_access": {
                resource
                for entry in running
                for resource in [self._exclusive_access_resource(entry)]
                if resource is not None
            },
        }

    def _can_start(self, task: TestTask, resources: dict[str, object]) -> bool:
        lanes_required = self._fpp_lanes_required(task)
        capacity = self._fpp_lane_capacity()
        if lanes_required > capacity:
            return False
        if int(resources["fpp_lanes"]) + lanes_required > capacity:
            return False

        dwr_segment = self._dwr_segment_name(task)
        if dwr_segment != "DWR_NONE" and dwr_segment in resources["dwr_segments"]:
            return False

        exclusive_resource = self._exclusive_access_resource(task)
        if exclusive_resource is not None and exclusive_resource in resources["exclusive_access"]:
            return False
        return True

    def _reserve(self, entry: ScheduleEntry, resources: dict[str, object]) -> None:
        resources["fpp_lanes"] = int(resources["fpp_lanes"]) + entry.fpp_lanes_used
        if entry.dwr_segment and entry.dwr_segment != "DWR_NONE":
            resources["dwr_segments"].add(entry.dwr_segment)
        exclusive_resource = self._exclusive_access_resource(entry)
        if exclusive_resource is not None:
            resources["exclusive_access"].add(exclusive_resource)

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
