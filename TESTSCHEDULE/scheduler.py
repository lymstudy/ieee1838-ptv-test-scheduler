"""Core greedy event-driven scheduler + stack-level thermal simulator + pure serial baseline.

Implements:
  - StackThermalSimulator: first-order RC thermal model per stack
  - greedy_schedule(): event-driven scheduler with thermal throttling,
    BIST-engine parallelism, FPP lane sharing, and task prioritization
  - pure_serial_schedule(): naive serial baseline (TAP-only, no parallelism)
"""

from __future__ import annotations

import math
from typing import Callable

from model import (
    Chiplet,
    Stack,
    Task,
    TaskPhase,
    Case,
    ScheduledPhase,
    ScheduleResult,
)

EPSILON = 1e-12

# ── task-type priority: higher = scheduled first ───────────────────────────────
_TASK_TYPE_PRIORITY: dict[str, int] = {
    "MBIST": 5,
    "LBIST": 4,
    "scan": 3,
    "EXTEST": 2,
    "INTEST": 1,
}


# =============================================================================
# Part A: Stack-Level Thermal Simulator
# =============================================================================

class StackThermalSimulator:
    """Tracks per-stack temperature with a simple first-order RC model.

    Each stack is one thermal node::

        T(t+dt) = T_steady + (T(t) - T_steady) * exp(-dt / tau)

    where ``T_steady = T_ambient + P_active * R_eq``.

    * ``R_eq`` = average of chiplet ``thermal_resistance_c_per_w`` in the stack,
      with an upper-layer multiplier ``(1.0 + 0.5 * layer_index)``.
    * ``C_eq`` = average of chiplet ``thermal_capacitance_j_per_c`` in the stack.
    * ``tau = R_eq * C_eq``

    Also records per-stack temperature time-series for later plotting.
    """

    def __init__(self, stacks: list[Stack], ambient_c: float, max_temp_c: float) -> None:
        self.ambient = ambient_c
        self.max_temp = max_temp_c

        # Per-stack thermal parameters
        self._r_eq: dict[str, float] = {}
        self._c_eq: dict[str, float] = {}
        self._tau: dict[str, float] = {}
        self._temps: dict[str, float] = {}
        self._last_update: float = 0.0

        # Time-series traces: stack_id -> list[(time_s, temperature_c)]
        self._traces: dict[str, list[tuple[float, float]]] = {}

        for stack in stacks:
            if not stack.chiplets:
                continue
            sid = stack.stack_id

            # R_eq with layer-distance factor
            r_values = [
                c.thermal_resistance_c_per_w * (1.0 + 0.5 * c.layer_index)
                for c in stack.chiplets
            ]
            c_values = [c.thermal_capacitance_j_per_c for c in stack.chiplets]
            r_avg = sum(r_values) / len(r_values)
            c_avg = sum(c_values) / len(c_values)

            self._r_eq[sid] = r_avg
            self._c_eq[sid] = c_avg
            self._tau[sid] = r_avg * c_avg
            self._temps[sid] = ambient_c
            self._traces[sid] = [(0.0, ambient_c)]

    # -- public API -------------------------------------------------------------

    def active_power_on_stack(
        self, stack_id: str, active_phases: list[ScheduledPhase]
    ) -> float:
        """Sum ``power_w`` of all currently active phases on *stack_id*."""
        return sum(
            p.power_w for p in active_phases if p.stack_id == stack_id
        )

    def update(
        self, time_s: float, active_phases: list[ScheduledPhase]
    ) -> None:
        """Step temperature from ``last_update_time`` to *time_s* using RC decay.

        Records ``(time_s, temperature_c)`` to the trace of each stack.
        """
        if time_s <= self._last_update + EPSILON:
            return

        dt = time_s - self._last_update

        for sid in self._temps:
            p_active = self.active_power_on_stack(sid, active_phases)
            r = self._r_eq.get(sid, 1.0)
            tau = self._tau.get(sid, 1.0)
            t_steady = self.ambient + p_active * r

            t_prev = self._temps[sid]
            if tau > EPSILON:
                t_new = t_steady + (t_prev - t_steady) * math.exp(-dt / tau)
            else:
                t_new = t_steady

            self._temps[sid] = t_new
            self._traces[sid].append((time_s, t_new))

        self._last_update = time_s

    def is_throttled(self, stack_id: str, margin_c: float = 5.0) -> bool:
        """Return ``True`` if stack temperature >= ``max_temp - margin``."""
        return self._temps.get(stack_id, self.ambient) >= self.max_temp - margin_c

    def get_traces(self) -> dict[str, list[tuple[float, float]]]:
        """Return recorded temperature traces."""
        return dict(self._traces)

    def finalize(self, makespan_s: float, active_phases: list[ScheduledPhase]) -> None:
        """Fill dense temperature samples from last update to *makespan_s*.

        Samples at ~1 ms intervals (or 50 points, whichever is denser) so the
        T-t plot has a smooth curve even when scheduling decisions are sparse.
        """
        n_points = max(50, int(makespan_s / 0.001))
        for sid in self._temps:
            existing = self._traces.get(sid, [])
            last_t = existing[-1][0] if existing else 0.0
            last_temp = existing[-1][1] if existing else self.ambient

            r = self._r_eq.get(sid, 1.0)
            tau = self._tau.get(sid, 1.0)
            for i in range(1, n_points + 1):
                t = i * makespan_s / n_points
                if t <= last_t + EPSILON:
                    continue
                # Compute active power at this time
                p_active = sum(
                    p.power_w for p in active_phases
                    if p.stack_id == sid and p.start_s <= t < p.end_s
                )
                # RC step from last sample
                dt = t - last_t
                t_steady = self.ambient + p_active * r
                if tau > EPSILON:
                    temp = t_steady + (last_temp - t_steady) * math.exp(-dt / tau)
                else:
                    temp = t_steady
                self._traces[sid].append((t, temp))
                last_t = t
                last_temp = temp

    @property
    def current_temps(self) -> dict[str, float]:
        """Snapshot of current per-stack temperatures."""
        return dict(self._temps)


# =============================================================================
# Part B: Greedy Event-Driven Scheduler
# =============================================================================

def greedy_schedule(case: Case) -> tuple[ScheduleResult, dict]:
    """Build a schedule using greedy event-driven placement with thermal awareness.

    Algorithm outline:

    1. Update thermal simulator to current time.
    2. Filter out tasks on thermally-throttled stacks.
    3. Sort ready tasks by priority (BIST first, hottest stack, shortest job,
       then by task-type).
    4. Try to place the best-fitting ready task at current time.
    5. If none fit, jump time to the earliest phase end; otherwise re-evaluate.
    6. Repeat until all tasks are scheduled.

    Returns:
        (ScheduleResult, thermal_traces) where thermal_traces is
        dict[str, list[tuple[float, float]]] mapping stack_id -> [(time_s, temp_c), ...]
    """
    scheduled: list[ScheduledPhase] = []
    pending: list[Task] = list(case.tasks)
    thermal = StackThermalSimulator(case.stacks, case.ambient_temperature_c, case.max_temperature_c)

    # Resource timelines — each list is sorted by start time
    tap_intervals: list[tuple[float, float]] = []            # (start, end)
    fpp_intervals: list[tuple[float, float, int]] = []       # (start, end, lanes_used)
    bist_intervals: list[tuple[float, float, str]] = []      # (start, end, chiplet_id)
    chiplet_intervals: list[tuple[float, float, str]] = []   # (start, end, chiplet_id) — mutex per chiplet

    time = 0.0

    while pending:
        # 1. Update thermal state
        thermal.update(time, scheduled)

        # 2. Filter throttled stacks
        ready = [
            t for t in pending
            if not thermal.is_throttled(t.stack_id)
        ]
        if not ready:
            time = _jump_to_next_event(scheduled, time)
            continue

        # 3. Sort by priority (higher score = schedule first)
        def _key(task: Task) -> tuple[int, float, float, float]:
            # We want BIST first (higher score), then hottest stack, then shortest duration
            is_bist = 1 if task.task_type in ("MBIST", "LBIST") else 0
            temp = thermal.current_temps.get(task.stack_id, case.ambient_temperature_c)
            total_dur = sum(p.duration_s for p in task.phases)
            type_prio = _TASK_TYPE_PRIORITY.get(task.task_type, 0)
            return (is_bist, temp, -total_dur, type_prio)

        ready.sort(key=_key, reverse=True)

        # 4. Try to place each ready task
        placed = False
        for task in ready:
            phases = _try_place_phases(
                task, time, scheduled, case, thermal,
                tap_intervals, fpp_intervals, bist_intervals, chiplet_intervals,
            )
            if phases is not None:
                scheduled.extend(phases)
                pending.remove(task)
                _update_resource_intervals(phases, tap_intervals, fpp_intervals, bist_intervals, chiplet_intervals)
                placed = True
                break  # re-evaluate ready list after this placement

        # 5. Advance time if nothing was placed
        if not placed:
            time = _jump_to_next_event(scheduled, time)

    makespan = max((p.end_s for p in scheduled), default=0.0)
    peak_power = _compute_peak_power(scheduled)
    thermal.finalize(makespan, scheduled)
    return ScheduleResult(
        case_id=case.case_id,
        method="greedy",
        phases=scheduled,
        makespan_s=makespan,
        peak_power_w=peak_power,
    ), thermal.get_traces()


# ── Phase placement ────────────────────────────────────────────────────────────

def _try_place_phases(
    task: Task,
    earliest_start: float,
    committed: list[ScheduledPhase],
    case: Case,
    thermal: StackThermalSimulator,
    tap_intervals: list[tuple[float, float]],
    fpp_intervals: list[tuple[float, float, int]],
    bist_intervals: list[tuple[float, float, str]],
    chiplet_intervals: list[tuple[float, float, str]],
) -> list[ScheduledPhase] | None:
    """Try to place all phases of *task* sequentially.

    Returns a list of ``ScheduledPhase`` if successful, or ``None`` if the
    task cannot be placed within reasonable bounds.
    """
    result: list[ScheduledPhase] = []
    current_t = earliest_start

    for phase in task.phases:
        placed_phase = _place_one_phase(
            task, phase, current_t, committed, result, case,
            tap_intervals, fpp_intervals, bist_intervals, chiplet_intervals,
        )
        if placed_phase is None:
            return None
        result.append(placed_phase)
        current_t = placed_phase.end_s  # phases are strictly sequential

    return result


def _place_one_phase(
    task: Task,
    phase: TaskPhase,
    earliest: float,
    committed: list[ScheduledPhase],
    already_placed: list[ScheduledPhase],
    case: Case,
    tap_intervals: list[tuple[float, float]],
    fpp_intervals: list[tuple[float, float, int]],
    bist_intervals: list[tuple[float, float, str]],
    chiplet_intervals: list[tuple[float, float, str]],
) -> ScheduledPhase | None:
    """Place a single phase by scanning forward in time from *earliest*.

    Jumps to the resolution of the earliest resource conflict at each step,
    analogous to the interval-packing pattern in the old greedy scheduler.
    """
    all_committed = committed + already_placed
    t = earliest
    max_iterations = 10_000  # safety bound
    iteration = 0

    while True:
        iteration += 1
        if iteration > max_iterations:
            return None

        end = t + phase.duration_s
        conflicts: list[float] = []  # sorted list of earliest conflict-resolution times

        # --- TAP conflict ----------------------------------------------------
        if phase.needs_tap:
            overlapped = _overlap_end_interval(t, end, tap_intervals)
            if overlapped is not None and overlapped > t + EPSILON:
                conflicts.append(overlapped)

        # --- FPP lane conflict -----------------------------------------------
        if phase.needs_fpp_lanes > 0:
            lanes_in_use = _fpp_lanes_used_at(t, end, fpp_intervals)
            if lanes_in_use + phase.needs_fpp_lanes > case.total_fpp_lanes:
                conflict = _earliest_fpp_lane_release(t, end, fpp_intervals, case.total_fpp_lanes - phase.needs_fpp_lanes)
                if conflict is not None:
                    conflicts.append(conflict)

        # --- BIST engine conflict (per-chiplet) ------------------------------
        if phase.needs_bist_engine:
            overlapped = _overlap_end_bist(t, end, bist_intervals, task.chiplet_id)
            if overlapped is not None and overlapped > t + EPSILON:
                conflicts.append(overlapped)

        # --- Chiplet mutex (one test at a time per die) ----------------------
        overlapped = _overlap_end_chiplet(t, end, chiplet_intervals, task.chiplet_id)
        if overlapped is not None and overlapped > t + EPSILON:
            conflicts.append(overlapped)

        # --- Power budget ----------------------------------------------------
        active_power = _active_power_on_interval(t, end, all_committed)
        if active_power + phase.power_w > case.max_power_w + EPSILON:
            if active_power < EPSILON:
                # Phase alone exceeds budget — must allow it, but block overlap
                pass  # no conflict to wait for; just don't add more on top
            else:
                conflict = _earliest_power_relief(t, end, all_committed)
                if conflict is not None:
                    conflicts.append(conflict)

        # --- Feasible? -------------------------------------------------------
        if not conflicts:
            break

        t = min(conflicts) + EPSILON

    return ScheduledPhase(
        task_id=task.task_id,
        chiplet_id=task.chiplet_id,
        stack_id=task.stack_id,
        task_type=task.task_type,
        phase_index=phase.phase_index,
        phase_name=phase.phase_name,
        start_s=t,
        end_s=t + phase.duration_s,
        duration_s=phase.duration_s,
        needs_tap=phase.needs_tap,
        needs_fpp_lanes=phase.needs_fpp_lanes,
        needs_bist_engine=phase.needs_bist_engine,
        power_w=phase.power_w,
    )


# ── Resource helpers ───────────────────────────────────────────────────────────

def _interval_overlaps(
    start: float, end: float, intervals: list[tuple[float, float]]
) -> bool:
    """True if ``[start, end)`` overlaps any interval in *intervals*."""
    for a, b in intervals:
        if a < end - EPSILON and start < b - EPSILON:
            return True
    return False


def _overlap_end_interval(
    start: float, end: float, intervals: list[tuple[float, float]]
) -> float | None:
    """Earliest end time among intervals that overlap ``[start, end)``.

    Returns ``None`` if there is no overlap.
    """
    best: float | None = None
    for a, b in intervals:
        if a < end - EPSILON and start < b - EPSILON:
            if best is None or b < best:
                best = b
    return best


def _overlap_end_bist(
    start: float,
    end: float,
    intervals: list[tuple[float, float, str]],
    chiplet_id: str,
) -> float | None:
    """Earliest end time among BIST intervals on *chiplet_id* that overlap."""
    best: float | None = None
    for a, b, cid in intervals:
        if cid == chiplet_id and a < end - EPSILON and start < b - EPSILON:
            if best is None or b < best:
                best = b
    return best


def _overlap_end_chiplet(
    start: float,
    end: float,
    intervals: list[tuple[float, float, str]],
    chiplet_id: str,
) -> float | None:
    """Earliest end time among chiplet-mutex intervals for *chiplet_id* that overlap.

    A chiplet can only execute one test phase at a time.
    """
    best: float | None = None
    for a, b, cid in intervals:
        if cid == chiplet_id and a < end - EPSILON and start < b - EPSILON:
            if best is None or b < best:
                best = b
    return best


def _fpp_lanes_used_at(
    start: float, end: float, intervals: list[tuple[float, float, int]]
) -> int:
    """Sum of ``lanes_used`` for intervals that overlap ``[start, end)``."""
    total = 0
    for a, b, lanes in intervals:
        if a < end - EPSILON and start < b - EPSILON:
            total += lanes
    return total


def _earliest_fpp_lane_release(
    start: float,
    end: float,
    intervals: list[tuple[float, float, int]],
    free_lanes_needed: int,
) -> float | None:
    """Earliest time when enough FPP lanes become free for this interval.

    Simulates: for each endpoint of overlapping intervals, compute the total
    lanes in use beyond that endpoint.  Returns the earliest time at which
    lanes_in_use <= free_lanes_needed.
    """
    # Collect all candidate end-points
    candidates: set[float] = {start}
    for a, b, lanes in intervals:
        if a < end - EPSILON and start < b - EPSILON:
            candidates.add(b)

    for t_candidate in sorted(candidates):
        lanes_sum = 0
        for a, b, lanes in intervals:
            if a < t_candidate + EPSILON and t_candidate < b - EPSILON:
                lanes_sum += lanes
        if lanes_sum <= free_lanes_needed:
            return t_candidate

    # If still not resolved, return the maximum end time among overlapping intervals
    ends = [b for a, b, _ in intervals if a < end - EPSILON and start < b - EPSILON]
    if ends:
        return max(ends)
    return None


def _active_power_on_interval(
    start: float, end: float, phases: list[ScheduledPhase]
) -> float:
    """Sum of ``power_w`` for phases overlapping ``[start, end)``."""
    total = 0.0
    for p in phases:
        if p.start_s < end - EPSILON and start < p.end_s - EPSILON:
            total += p.power_w
    return total


def _earliest_power_relief(
    start: float, end: float, phases: list[ScheduledPhase]
) -> float | None:
    """Earliest end time of any phase overlapping ``[start, end)``."""
    best: float | None = None
    for p in phases:
        if p.start_s < end - EPSILON and start < p.end_s - EPSILON:
            if best is None or p.end_s < best:
                best = p.end_s
    return best


def _jump_to_next_event(
    scheduled: list[ScheduledPhase], current_time: float
) -> float:
    """Advance to the minimum end time among committed phases that is > *current_time*."""
    candidates = [p.end_s for p in scheduled if p.end_s > current_time + EPSILON]
    if not candidates:
        return current_time + EPSILON
    return min(candidates)


def _update_resource_intervals(
    phases: list[ScheduledPhase],
    tap_intervals: list[tuple[float, float]],
    fpp_intervals: list[tuple[float, float, int]],
    bist_intervals: list[tuple[float, float, str]],
    chiplet_intervals: list[tuple[float, float, str]],
) -> None:
    """Add committed phases to the resource interval lists."""
    for p in phases:
        if p.needs_tap:
            tap_intervals.append((p.start_s, p.end_s))
        if p.needs_fpp_lanes > 0:
            fpp_intervals.append((p.start_s, p.end_s, p.needs_fpp_lanes))
        if p.needs_bist_engine:
            bist_intervals.append((p.start_s, p.end_s, p.chiplet_id))
        # Every phase locks its chiplet (one test at a time per die)
        chiplet_intervals.append((p.start_s, p.end_s, p.chiplet_id))

    # Keep lists sorted by start time.
    tap_intervals.sort(key=lambda x: x[0])
    fpp_intervals.sort(key=lambda x: x[0])
    bist_intervals.sort(key=lambda x: x[0])
    chiplet_intervals.sort(key=lambda x: x[0])


def _compute_peak_power(phases: list[ScheduledPhase]) -> float:
    """Maximum sum of overlapping phase powers (sweep-line)."""
    if not phases:
        return 0.0

    events: list[tuple[float, int, float]] = []
    for p in phases:
        events.append((p.start_s, +1, p.power_w))
        events.append((p.end_s, -1, p.power_w))
    events.sort(key=lambda e: (e[0], e[1]))  # process removals before adds at same time

    peak = 0.0
    current = 0.0
    for time, delta, pw in events:
        current += delta * pw
        if current > peak:
            peak = current

    return peak


# =============================================================================
# Part C: Pure Serial Baseline
# =============================================================================

def pure_serial_schedule(case: Case) -> tuple[ScheduleResult, dict]:
    """Baseline: all tasks executed serially through TAP only.

    * No FPP usage.
    * No parallel BIST execution — BIST phases go through the TAP as if
      no BIST engine exists (serial scan semantics).
    * Tasks are ordered by type priority (MBIST first, then LBIST, scan,
      EXTEST, INTEST), then by total duration ascending.
    * Every phase is laid out end-to-end on a single virtual TAP.

    Returns:
        (ScheduleResult, {}) — empty dict for thermal traces since serial
        baseline has no meaningful thermal simulation.
    """
    # Sort tasks by type priority descending, then by total duration ascending
    def _sort_key(task: Task) -> tuple[int, float]:
        prio = _TASK_TYPE_PRIORITY.get(task.task_type, 0)
        dur = sum(p.duration_s for p in task.phases)
        return (-prio, dur)

    ordered = sorted(case.tasks, key=_sort_key)

    phases: list[ScheduledPhase] = []
    current_time = 0.0

    for task in ordered:
        for phase in task.phases:
            # Recompute duration for TAP-only execution.
            # SHIFT phases that use FPP must be re-scaled to TAP speed.
            if phase.needs_fpp_lanes > 0:
                # FPP duration = bits / (bw * lanes)  →  bits = FPP_dur * bw * lanes
                # TAP duration = bits / ptap_tck  =  FPP_dur * bw * lanes / ptap_tck
                tap_dur = (phase.duration_s * case.fpp_lane_bandwidth_bps
                           * phase.needs_fpp_lanes / case.ptap_tck_hz)
            else:
                tap_dur = phase.duration_s

            start = current_time
            end = start + tap_dur

            sp = ScheduledPhase(
                task_id=task.task_id,
                chiplet_id=task.chiplet_id,
                stack_id=task.stack_id,
                task_type=task.task_type,
                phase_index=phase.phase_index,
                phase_name=phase.phase_name,
                start_s=start,
                end_s=end,
                duration_s=tap_dur,
                needs_tap=True,
                needs_fpp_lanes=0,
                needs_bist_engine=False,
                power_w=phase.power_w,
            )
            phases.append(sp)
            current_time = end

    makespan = current_time
    peak_power = max((p.power_w for p in phases), default=0.0)

    return ScheduleResult(
        case_id=case.case_id,
        method="pure_serial",
        phases=phases,
        makespan_s=makespan,
        peak_power_w=peak_power,
    ), {}
