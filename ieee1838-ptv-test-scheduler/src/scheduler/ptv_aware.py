"""PTV-aware scheduler for the MVP 4-die prototype."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from src.model.task import TaskType, TestTask
from src.model.thermal import TemperatureState
from src.scheduler.base import BaseScheduler, ScheduleEntry, ScheduleResult
from src.scheduler.evaluator import evaluate_schedule
from src.scheduler.greedy import DEFAULT_FPP_LANES_BY_TASK_TYPE, TASK_TYPE_PRIORITY


class PTVAwareScheduler(BaseScheduler):
    """Schedule tasks with access, power, thermal, voltage, and capture checks."""

    scheduler_name = "ptv_aware"

    def __init__(
        self,
        *args,
        max_concurrent_capture: int = 1,
        dummy_cycle_duration_s: float = 0.0001,
        max_dummy_cycles_per_block: int = 10,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        if max_concurrent_capture <= 0:
            raise ValueError("max_concurrent_capture must be positive")
        if dummy_cycle_duration_s <= 0:
            raise ValueError("dummy_cycle_duration_s must be positive")
        if max_dummy_cycles_per_block < 0:
            raise ValueError("max_dummy_cycles_per_block must be non-negative")
        self.max_concurrent_capture = max_concurrent_capture
        self.dummy_cycle_duration_s = dummy_cycle_duration_s
        self.max_dummy_cycles_per_block = max_dummy_cycles_per_block

    def schedule(self, tasks: Sequence[TestTask]) -> ScheduleResult:
        """Build a deterministic PTV-aware schedule and evaluate PTV traces."""

        pending = list(sorted(tasks, key=self._sort_key))
        known_task_ids = {task.id for task in pending}
        dependencies = {task.id: self._dependencies_for(task) for task in pending}
        for task_id, task_dependencies in dependencies.items():
            unknown = task_dependencies - known_task_ids
            if unknown:
                raise ValueError(f"task {task_id} has unknown dependencies: {sorted(unknown)}")

        current_time = 0.0
        current_state = TemperatureState({die.id: die.initial_temp_c for die in self.stack.dies})
        completed_ids: set[str] = set()
        running: list[ScheduleEntry] = []
        entries: list[ScheduleEntry] = []
        dummy_intervals: list[tuple[float, float]] = []
        dummy_cycle_count = 0
        dummy_time_total = 0.0
        forced_ptv_start_count = 0
        constraints_were_binding = False
        consecutive_dummy_cycles = 0
        capture_tasks_seen = any(self._is_capture_task(task) for task in pending)

        while pending or running:
            finished = [entry for entry in running if entry.end_time <= current_time + 1e-15]
            if finished:
                completed_ids.update(entry.task_id for entry in finished)
                running = [entry for entry in running if entry.end_time > current_time + 1e-15]

            ready = [task for task in pending if dependencies[task.id].issubset(completed_ids)]
            ready.sort(key=self._sort_key)

            resources = self._used_resources(running)
            started_any = False
            ptv_blocked_any = False
            capture_blocked_any = False

            while True:
                scored_candidates = []
                for task in ready:
                    if task not in pending:
                        continue
                    resource_ok, capture_ok = self._resource_and_capture_ok(task, resources)
                    if not resource_ok:
                        continue
                    if not capture_ok:
                        capture_blocked_any = True
                        constraints_were_binding = True
                        continue
                    prediction = self._predict_task(task, current_state, running)
                    if prediction["allowed"]:
                        scored_candidates.append((self._priority_score(task, prediction, resources), task))
                    else:
                        ptv_blocked_any = True
                        constraints_were_binding = True

                if not scored_candidates:
                    break

                scored_candidates.sort(key=lambda item: (-item[0], self._sort_key(item[1])))
                task = scored_candidates[0][1]
                entry = self._entry_for_task(task, current_time)
                entries.append(entry)
                running.append(entry)
                pending.remove(task)
                self._reserve(entry, resources)
                started_any = True
                consecutive_dummy_cycles = 0

            if running:
                next_time = min(entry.end_time for entry in running)
                current_state = self._advance_state(current_state, running, next_time - current_time)
                current_time = next_time
                consecutive_dummy_cycles = 0
                continue

            if pending and not ready:
                unresolved = {task.id: sorted(dependencies[task.id] - completed_ids) for task in pending}
                raise ValueError(f"no schedulable task remains; unresolved dependencies: {unresolved}")

            if pending and not started_any and (ptv_blocked_any or capture_blocked_any):
                resource_ready = [task for task in ready if self._resource_and_capture_ok(task, resources)[0]]
                if ptv_blocked_any and consecutive_dummy_cycles < self.max_dummy_cycles_per_block:
                    start = current_time
                    end = current_time + self.dummy_cycle_duration_s
                    current_state = self._advance_state(current_state, (), self.dummy_cycle_duration_s)
                    dummy_intervals.append((start, end))
                    current_time = end
                    dummy_cycle_count += 1
                    dummy_time_total += self.dummy_cycle_duration_s
                    consecutive_dummy_cycles += 1
                    constraints_were_binding = True
                    continue

                forceable = [task for task in resource_ready if self._resource_and_capture_ok(task, resources)[1]]
                if forceable:
                    forceable.sort(key=self._sort_key)
                    task = forceable[0]
                    entry = self._entry_for_task(task, current_time)
                    entries.append(entry)
                    running.append(entry)
                    pending.remove(task)
                    self._reserve(entry, resources)
                    forced_ptv_start_count += 1
                    constraints_were_binding = True
                    consecutive_dummy_cycles = 0
                    continue

            if pending:
                unresolved = {task.id: sorted(dependencies[task.id] - completed_ids) for task in pending}
                raise ValueError(f"unable to make scheduling progress: {unresolved}")

        entries.sort(key=self._entry_sort_key)
        return self._evaluate(
            entries,
            dummy_intervals=dummy_intervals,
            dummy_cycle_count=dummy_cycle_count,
            dummy_time_total=dummy_time_total,
            forced_ptv_start_count=forced_ptv_start_count,
            capture_staggering_applied=capture_tasks_seen,
            constraints_were_binding=constraints_were_binding,
        )

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
            is_capture_phase=self._is_capture_task(task),
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

    @staticmethod
    def _is_capture_task(task: TestTask) -> bool:
        return bool(getattr(task, "is_capture_phase", False))

    @staticmethod
    def _is_capture_entry(entry: ScheduleEntry) -> bool:
        return bool(entry.is_capture_phase)

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
            "capture_count": sum(1 for entry in running if self._is_capture_entry(entry)),
        }

    def _resource_and_capture_ok(self, task: TestTask, resources: dict[str, object]) -> tuple[bool, bool]:
        lanes_required = self._fpp_lanes_required(task)
        capacity = self._fpp_lane_capacity()
        if lanes_required > capacity:
            return False, True
        if int(resources["fpp_lanes"]) + lanes_required > capacity:
            return False, True

        dwr_segment = self._dwr_segment_name(task)
        if dwr_segment != "DWR_NONE" and dwr_segment in resources["dwr_segments"]:
            return False, True

        exclusive_resource = self._exclusive_access_resource(task)
        if exclusive_resource is not None and exclusive_resource in resources["exclusive_access"]:
            return False, True

        if self._is_capture_task(task) and int(resources["capture_count"]) >= self.max_concurrent_capture:
            return True, False
        return True, True

    def _reserve(self, entry: ScheduleEntry, resources: dict[str, object]) -> None:
        resources["fpp_lanes"] = int(resources["fpp_lanes"]) + entry.fpp_lanes_used
        if entry.dwr_segment and entry.dwr_segment != "DWR_NONE":
            resources["dwr_segments"].add(entry.dwr_segment)
        exclusive_resource = self._exclusive_access_resource(entry)
        if exclusive_resource is not None:
            resources["exclusive_access"].add(exclusive_resource)
        if self._is_capture_entry(entry):
            resources["capture_count"] = int(resources["capture_count"]) + 1

    def _predict_task(
        self,
        task: TestTask,
        current_state: TemperatureState,
        running: Sequence[ScheduleEntry],
    ) -> dict[str, float | bool]:
        active_power = self._active_power(running)
        active_power[task.die_id] += task.power_w
        prediction_window = min(self.time_step_s, task.duration_s(self.clock_hz))
        predicted_state = self.thermal_model.step(current_state, active_power, prediction_window)
        predicted_peak_temperature = predicted_state.peak_temp_c()
        voltage_state = self.voltage_model.estimate(active_power)
        predicted_peak_ir_drop = voltage_state.peak_ir_drop_v()
        allowed = (
            predicted_peak_temperature <= self.thermal_model.config.max_temp_c
            and predicted_peak_ir_drop <= self.voltage_model.config.max_ir_drop_v
        )
        return {
            "allowed": allowed,
            "predicted_peak_temperature": predicted_peak_temperature,
            "predicted_peak_ir_drop": predicted_peak_ir_drop,
        }

    def _priority_score(
        self,
        task: TestTask,
        prediction: dict[str, float | bool],
        resources: dict[str, object],
    ) -> float:
        duration = task.duration_s(self.clock_hz)
        lanes_required = self._fpp_lanes_required(task)
        lane_capacity = max(self._fpp_lane_capacity(), 1)
        benefit = duration * (1.0 + lanes_required)
        predicted_temperature_ratio = float(prediction["predicted_peak_temperature"]) / self.thermal_model.config.max_temp_c
        ir_limit = self.voltage_model.config.max_ir_drop_v
        predicted_ir_drop_ratio = float("inf") if ir_limit <= 0 else float(prediction["predicted_peak_ir_drop"]) / ir_limit
        fpp_pressure = lanes_required / lane_capacity
        capture_pressure = 0.0
        if self._is_capture_task(task):
            capture_pressure = (int(resources["capture_count"]) + 1) / self.max_concurrent_capture
        risk = predicted_temperature_ratio + predicted_ir_drop_ratio + fpp_pressure + capture_pressure
        return benefit / max(risk, 1e-12)

    def _active_power(self, active_entries: Sequence[ScheduleEntry]) -> dict[int, float]:
        power_by_die = {die.id: 0.0 for die in self.stack.dies}
        for entry in active_entries:
            power_by_die[entry.die_id] += entry.power
        return power_by_die

    def _advance_state(
        self,
        state: TemperatureState,
        active_entries: Sequence[ScheduleEntry],
        duration: float,
    ) -> TemperatureState:
        current_state = state
        active_power = self._active_power(active_entries)
        elapsed = 0.0
        while elapsed < duration:
            step = min(self.time_step_s, duration - elapsed)
            current_state = self.thermal_model.step(current_state, active_power, step)
            elapsed += step
        return current_state

    def _evaluate(
        self,
        entries: Sequence[ScheduleEntry],
        dummy_intervals: Sequence[tuple[float, float]],
        dummy_cycle_count: int,
        dummy_time_total: float,
        forced_ptv_start_count: int,
        capture_staggering_applied: bool,
        constraints_were_binding: bool,
    ) -> ScheduleResult:
        return evaluate_schedule(
            scheduler_name=self.scheduler_name,
            entries=entries,
            stack=self.stack,
            access=self.access,
            thermal_model=self.thermal_model,
            voltage_model=self.voltage_model,
            time_step_s=self.time_step_s,
            dummy_intervals=dummy_intervals,
            extra_metrics={
                "dummy_cycle_count": dummy_cycle_count,
                "dummy_time_total": dummy_time_total,
                "capture_staggering_applied": capture_staggering_applied,
                "constraints_were_binding": constraints_were_binding,
                "forced_ptv_start_count": forced_ptv_start_count,
            },
        )
