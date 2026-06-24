from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.model import SystemModel

from .cpsat import CpSatSolveInfo, CpSatUnavailableError, solve_cpsat_schedule
from .greedy import (
    ScheduleResult,
    ScheduledPhase,
    _peak_fpp_lanes,
    _peak_power,
    _schedule_recipe,
    greedy_schedule,
    write_schedule_csv,
)


EPSILON = 1e-12


@dataclass(frozen=True)
class RefinementMove:
    iteration: int
    move_type: str
    detail: str
    before_makespan_s: float
    after_makespan_s: float


@dataclass(frozen=True)
class RefinementResult:
    baseline: ScheduleResult
    refined: ScheduleResult
    moves: list[RefinementMove]
    backend: str = "local"
    solve_info: CpSatSolveInfo | None = None

    @property
    def improvement_s(self) -> float:
        return self.baseline.makespan_s - self.refined.makespan_s

    @property
    def improvement_percent(self) -> float:
        if self.baseline.makespan_s <= EPSILON:
            return 0.0
        return 100.0 * self.improvement_s / self.baseline.makespan_s


def refine_schedule(
    model: SystemModel,
    recipe_rows: list[dict[str, object]],
    max_iterations: int = 20,
    enable_recipe_moves: bool = False,
    backend: str = "auto",
    time_limit_s: float = 10.0,
    workers: int = 8,
) -> RefinementResult:
    baseline = greedy_schedule(model, recipe_rows)
    if backend not in {"auto", "ortools", "local"}:
        raise ValueError(f"unknown M5 backend: {backend}")
    if backend in {"auto", "ortools"}:
        try:
            refined, solve_info = solve_cpsat_schedule(
                model,
                recipe_rows,
                time_limit_s=time_limit_s,
                workers=workers,
            )
            moves = [
                RefinementMove(
                    iteration=0,
                    move_type="cp_sat",
                    detail=f"OR-Tools CP-SAT status={solve_info.status_name}, wall_time_s={solve_info.wall_time_s:.3f}",
                    before_makespan_s=baseline.makespan_s,
                    after_makespan_s=refined.makespan_s,
                )
            ]
            return RefinementResult(
                baseline=baseline,
                refined=refined,
                moves=moves,
                backend="ortools",
                solve_info=solve_info,
            )
        except CpSatUnavailableError:
            if backend == "ortools":
                raise

    candidates_by_target = _group_by_target(recipe_rows)
    selected_by_target = {str(row["target_id"]): row for row in baseline.selected_rows}
    order = _best_initial_order(model, selected_by_target, baseline)
    current = _build_result(model, selected_by_target, order)
    moves: list[RefinementMove] = []
    if current.makespan_s < baseline.makespan_s - EPSILON:
        moves.append(
            RefinementMove(
                iteration=0,
                move_type="initial_order",
                detail="multi-start order refinement",
                before_makespan_s=baseline.makespan_s,
                after_makespan_s=current.makespan_s,
            )
        )

    for iteration in range(1, max_iterations + 1):
        order_candidate = _best_order_neighbor(model, selected_by_target, order, current.makespan_s)
        if order_candidate is not None:
            new_order, new_result, detail = order_candidate
            moves.append(
                RefinementMove(
                    iteration=iteration,
                    move_type="order",
                    detail=detail,
                    before_makespan_s=current.makespan_s,
                    after_makespan_s=new_result.makespan_s,
                )
            )
            order = new_order
            current = new_result
            continue

        recipe_candidate = None
        if enable_recipe_moves:
            recipe_candidate = _best_recipe_neighbor(
                model,
                candidates_by_target,
                selected_by_target,
                order,
                current.makespan_s,
            )
        if recipe_candidate is None:
            break

        new_selected, new_order, new_result, detail = recipe_candidate
        moves.append(
            RefinementMove(
                iteration=iteration,
                move_type="recipe",
                detail=detail,
                before_makespan_s=current.makespan_s,
                after_makespan_s=new_result.makespan_s,
            )
        )
        selected_by_target = new_selected
        order = new_order
        current = new_result

    return RefinementResult(baseline=baseline, refined=current, moves=moves, backend="local")


def write_refined_schedule_csv(result: RefinementResult, output_path: str | Path) -> None:
    write_schedule_csv(result.refined, output_path)


def write_refinement_report_markdown(result: RefinementResult, output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# M5 Schedule Refinement Report",
        "",
        f"- Case: {result.refined.case_id}",
        f"- Backend: {result.backend}",
        f"- Baseline M4 makespan: {result.baseline.makespan_s:.9f} s",
        f"- Refined M5 makespan: {result.refined.makespan_s:.9f} s",
        f"- Improvement: {result.improvement_s:.9f} s ({result.improvement_percent:.2f}%)",
        f"- Selected recipes: {len(result.refined.selected_rows)}",
        f"- Scheduled phases: {len(result.refined.phases)}",
        f"- Peak scheduled power: {result.refined.peak_power_w:.6f} W",
        f"- Peak FPP lanes used: {result.refined.max_fpp_lanes_used}",
    ]
    if result.solve_info is not None:
        lines.extend(
            [
                f"- CP-SAT status: {result.solve_info.status_name}",
                f"- CP-SAT wall time: {result.solve_info.wall_time_s:.6f} s",
            ]
        )
    lines.extend(["", "## Refinement Moves", ""])
    if result.moves:
        lines.extend(
            [
                "| iteration | type | before_s | after_s | detail |",
                "| ---: | --- | ---: | ---: | --- |",
            ]
        )
        for move in result.moves:
            lines.append(
                f"| {move.iteration} | {move.move_type} | {move.before_makespan_s:.9f} | "
                f"{move.after_makespan_s:.9f} | {move.detail} |"
            )
    else:
        lines.append("No improving local refinement move was found.")

    lines.extend(
        [
            "",
            "## Selected Recipes",
            "",
            "| target_id | recipe_id | type | total_time_s | peak_power_w |",
            "| --- | --- | --- | ---: | ---: |",
        ]
    )
    for row in result.refined.selected_rows:
        lines.append(
            "| {target_id} | {recipe_id} | {recipe_type} | {total_time_s} | {peak_power_w} |".format(
                target_id=row.get("target_id", ""),
                recipe_id=row.get("recipe_id", ""),
                recipe_type=row.get("recipe_type", ""),
                total_time_s=row.get("total_time_s", ""),
                peak_power_w=row.get("peak_power_w", ""),
            )
        )

    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _group_by_target(rows: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    groups: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        groups.setdefault(str(row["target_id"]), []).append(row)
    return {
        target_id: sorted(group, key=lambda row: (float(row.get("total_time_s", 0.0)), str(row.get("recipe_id", ""))))
        for target_id, group in groups.items()
    }


def _best_initial_order(
    model: SystemModel,
    selected_by_target: dict[str, dict[str, object]],
    baseline: ScheduleResult,
) -> list[str]:
    baseline_order = _order_from_phases(baseline.phases)
    starts = [
        baseline_order,
        sorted(selected_by_target),
        sorted(selected_by_target, key=lambda target_id: -float(selected_by_target[target_id].get("total_time_s", 0.0))),
        sorted(selected_by_target, key=lambda target_id: -float(selected_by_target[target_id].get("thermal_risk", 0.0))),
    ]
    best_result: ScheduleResult | None = None
    best_order: list[str] | None = None
    for start in starts:
        order, result = _local_order_search(model, selected_by_target, start)
        if best_result is None or result.makespan_s < best_result.makespan_s - EPSILON:
            best_order = order
            best_result = result
    return best_order or baseline_order


def _local_order_search(
    model: SystemModel,
    selected_by_target: dict[str, dict[str, object]],
    initial_order: list[str],
) -> tuple[list[str], ScheduleResult]:
    order = list(initial_order)
    current = _build_result(model, selected_by_target, order)
    while True:
        candidate = _best_order_neighbor(model, selected_by_target, order, current.makespan_s)
        if candidate is None:
            return order, current
        order, current, _detail = candidate


def _best_order_neighbor(
    model: SystemModel,
    selected_by_target: dict[str, dict[str, object]],
    order: list[str],
    current_makespan: float,
) -> tuple[list[str], ScheduleResult, str] | None:
    best_result: ScheduleResult | None = None
    best_order: list[str] | None = None
    best_detail = ""
    for next_order, detail in _order_neighbors(order):
        result = _build_result(model, selected_by_target, next_order)
        if result.makespan_s >= current_makespan - EPSILON:
            continue
        if best_result is None or result.makespan_s < best_result.makespan_s - EPSILON:
            best_result = result
            best_order = next_order
            best_detail = detail
    if best_result is None or best_order is None:
        return None
    return best_order, best_result, best_detail


def _best_recipe_neighbor(
    model: SystemModel,
    candidates_by_target: dict[str, list[dict[str, object]]],
    selected_by_target: dict[str, dict[str, object]],
    order: list[str],
    current_makespan: float,
) -> tuple[dict[str, dict[str, object]], list[str], ScheduleResult, str] | None:
    best_selected: dict[str, dict[str, object]] | None = None
    best_order: list[str] | None = None
    best_result: ScheduleResult | None = None
    best_detail = ""

    for target_id in sorted(candidates_by_target):
        current_recipe_id = str(selected_by_target[target_id]["recipe_id"])
        for candidate in candidates_by_target[target_id]:
            if str(candidate["recipe_id"]) == current_recipe_id:
                continue
            trial_selected = dict(selected_by_target)
            trial_selected[target_id] = candidate
            trial_order, trial_result = _local_order_search(model, trial_selected, order)
            if trial_result.makespan_s >= current_makespan - EPSILON:
                continue
            if best_result is None or trial_result.makespan_s < best_result.makespan_s - EPSILON:
                best_selected = trial_selected
                best_order = trial_order
                best_result = trial_result
                best_detail = f"{target_id}: {current_recipe_id} -> {candidate['recipe_id']}"

    if best_selected is None or best_order is None or best_result is None:
        return None
    return best_selected, best_order, best_result, best_detail


def _build_result(
    model: SystemModel,
    selected_by_target: dict[str, dict[str, object]],
    order: list[str],
) -> ScheduleResult:
    scheduled: list[ScheduledPhase] = []
    for target_id in order:
        scheduled.extend(_schedule_recipe(model, selected_by_target[target_id], scheduled))
    phases = sorted(scheduled, key=lambda phase: (phase.start_s, phase.end_s, phase.target_id, phase.phase_index))
    return ScheduleResult(
        case_id=model.case_id,
        selected_rows=sorted(selected_by_target.values(), key=lambda row: str(row["target_id"])),
        phases=phases,
        makespan_s=max((phase.end_s for phase in phases), default=0.0),
        peak_power_w=_peak_power(phases),
        max_fpp_lanes_used=_peak_fpp_lanes(phases),
        serial_busy_time_s=sum(phase.duration_s for phase in phases if phase.serial_required),
        fpp_lane_time_s=sum(phase.duration_s * phase.fpp_lanes_required for phase in phases),
    )


def _order_from_phases(phases: list[ScheduledPhase]) -> list[str]:
    ordered = sorted((phase for phase in phases if phase.phase_index == 0), key=lambda phase: phase.start_s)
    return [phase.target_id for phase in ordered]


def _order_neighbors(order: list[str]) -> list[tuple[list[str], str]]:
    neighbors: list[tuple[list[str], str]] = []
    size = len(order)
    for source in range(size):
        for target in range(size):
            if source == target:
                continue
            next_order = list(order)
            item = next_order.pop(source)
            next_order.insert(target, item)
            neighbors.append((next_order, f"insert {item} from {source} to {target}"))
    for left in range(size):
        for right in range(left + 1, size):
            next_order = list(order)
            next_order[left], next_order[right] = next_order[right], next_order[left]
            neighbors.append((next_order, f"swap {order[left]} and {order[right]}"))
    return neighbors
