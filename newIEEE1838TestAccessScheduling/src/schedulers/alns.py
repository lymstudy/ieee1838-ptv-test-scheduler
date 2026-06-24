from __future__ import annotations

import csv
import random
from dataclasses import asdict, dataclass
from pathlib import Path

from src.model import SystemModel

from .cpsat import CpSatSolveInfo, CpSatUnavailableError, solve_cpsat_schedule
from .greedy import ScheduleResult, greedy_schedule, write_schedule_csv


EPSILON = 1e-12


@dataclass(frozen=True)
class AlnsIteration:
    iteration: int
    destroy_operator: str
    destroyed_targets: str
    candidate_makespan_s: float
    incumbent_makespan_s: float
    best_makespan_s: float
    accepted: bool
    improved: bool
    repair_backend: str


@dataclass(frozen=True)
class AlnsResult:
    initial: ScheduleResult
    best: ScheduleResult
    iterations: list[AlnsIteration]
    backend: str
    seed: int

    @property
    def improvement_s(self) -> float:
        return self.initial.makespan_s - self.best.makespan_s

    @property
    def improvement_percent(self) -> float:
        if self.initial.makespan_s <= EPSILON:
            return 0.0
        return 100.0 * self.improvement_s / self.initial.makespan_s


def run_alns(
    model: SystemModel,
    recipe_rows: list[dict[str, object]],
    iterations: int = 20,
    destroy_fraction: float = 0.35,
    seed: int = 1838,
    repair_time_limit_s: float = 2.0,
    workers: int = 8,
    backend: str = "ortools",
) -> AlnsResult:
    if not recipe_rows:
        raise ValueError("no recipe rows supplied")
    if backend not in {"ortools", "greedy"}:
        raise ValueError(f"unknown ALNS repair backend: {backend}")

    rng = random.Random(seed)
    target_ids = sorted({str(row["target_id"]) for row in recipe_rows})
    destroy_size = max(1, min(len(target_ids), round(len(target_ids) * destroy_fraction)))

    initial, backend_used = _repair(model, recipe_rows, backend, repair_time_limit_s, workers)
    incumbent = initial
    best = initial
    history: list[AlnsIteration] = []
    operators = ["critical_path", "resource_congestion", "thermal_hotspot", "random"]

    for iteration in range(1, iterations + 1):
        operator = operators[(iteration - 1) % len(operators)]
        destroyed = _destroy_targets(operator, incumbent, recipe_rows, destroy_size, rng)
        neighborhood = _neighborhood_rows(recipe_rows, incumbent.selected_rows, destroyed)
        candidate, backend_used = _repair(model, neighborhood, backend, repair_time_limit_s, workers)

        improved = candidate.makespan_s < best.makespan_s - EPSILON
        accepted = candidate.makespan_s <= incumbent.makespan_s + EPSILON or improved
        if accepted:
            incumbent = candidate
        if improved:
            best = candidate

        history.append(
            AlnsIteration(
                iteration=iteration,
                destroy_operator=operator,
                destroyed_targets=";".join(destroyed),
                candidate_makespan_s=candidate.makespan_s,
                incumbent_makespan_s=incumbent.makespan_s,
                best_makespan_s=best.makespan_s,
                accepted=accepted,
                improved=improved,
                repair_backend=backend_used,
            )
        )

    return AlnsResult(initial=initial, best=best, iterations=history, backend=backend, seed=seed)


def write_alns_schedule_csv(result: AlnsResult, output_path: str | Path) -> None:
    write_schedule_csv(result.best, output_path)


def write_alns_convergence_csv(result: AlnsResult, output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(asdict(result.iterations[0]).keys()) if result.iterations else list(AlnsIteration.__dataclass_fields__)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in result.iterations:
            writer.writerow(asdict(row))


def write_alns_report_markdown(result: AlnsResult, output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    improved_count = sum(int(row.improved) for row in result.iterations)
    accepted_count = sum(int(row.accepted) for row in result.iterations)
    lines = [
        "# M6 ALNS Schedule Report",
        "",
        f"- Case: {result.best.case_id}",
        f"- Repair backend: {result.backend}",
        f"- Seed: {result.seed}",
        f"- Iterations: {len(result.iterations)}",
        f"- Initial makespan: {result.initial.makespan_s:.9f} s",
        f"- Best makespan: {result.best.makespan_s:.9f} s",
        f"- Improvement: {result.improvement_s:.9f} s ({result.improvement_percent:.2f}%)",
        f"- Accepted moves: {accepted_count}",
        f"- Improving moves: {improved_count}",
        f"- Peak scheduled power: {result.best.peak_power_w:.6f} W",
        f"- Peak FPP lanes used: {result.best.max_fpp_lanes_used}",
        "",
        "## Convergence",
        "",
        "| iteration | operator | candidate_s | incumbent_s | best_s | accepted | improved |",
        "| ---: | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for row in result.iterations:
        lines.append(
            f"| {row.iteration} | {row.destroy_operator} | {row.candidate_makespan_s:.9f} | "
            f"{row.incumbent_makespan_s:.9f} | {row.best_makespan_s:.9f} | {row.accepted} | {row.improved} |"
        )

    lines.extend(
        [
            "",
            "## Selected Recipes",
            "",
            "| target_id | recipe_id | type | total_time_s | peak_power_w |",
            "| --- | --- | --- | ---: | ---: |",
        ]
    )
    for row in result.best.selected_rows:
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


def _repair(
    model: SystemModel,
    recipe_rows: list[dict[str, object]],
    backend: str,
    time_limit_s: float,
    workers: int,
) -> tuple[ScheduleResult, str]:
    if backend == "ortools":
        try:
            result, _info = solve_cpsat_schedule(model, recipe_rows, time_limit_s=time_limit_s, workers=workers)
            return result, "ortools"
        except CpSatUnavailableError:
            result = greedy_schedule(model, recipe_rows)
            return result, "greedy_fallback"
    return greedy_schedule(model, recipe_rows), "greedy"


def _neighborhood_rows(
    all_rows: list[dict[str, object]],
    selected_rows: list[dict[str, object]],
    destroyed_targets: list[str],
) -> list[dict[str, object]]:
    destroyed = set(destroyed_targets)
    selected_recipe_by_target = {str(row["target_id"]): str(row["recipe_id"]) for row in selected_rows}
    rows = []
    for row in all_rows:
        target_id = str(row["target_id"])
        if target_id in destroyed or str(row["recipe_id"]) == selected_recipe_by_target[target_id]:
            rows.append(row)
    return rows


def _destroy_targets(
    operator: str,
    schedule: ScheduleResult,
    recipe_rows: list[dict[str, object]],
    destroy_size: int,
    rng: random.Random,
) -> list[str]:
    if operator == "critical_path":
        ranked = _critical_path_targets(schedule)
    elif operator == "resource_congestion":
        ranked = _resource_congestion_targets(schedule)
    elif operator == "thermal_hotspot":
        ranked = _thermal_hotspot_targets(schedule, recipe_rows)
    elif operator == "random":
        ranked = sorted({phase.target_id for phase in schedule.phases})
        rng.shuffle(ranked)
    else:
        ranked = sorted({phase.target_id for phase in schedule.phases})

    for target_id in sorted({phase.target_id for phase in schedule.phases}):
        if target_id not in ranked:
            ranked.append(target_id)
    return ranked[:destroy_size]


def _critical_path_targets(schedule: ScheduleResult) -> list[str]:
    cutoff = schedule.makespan_s - max(schedule.makespan_s * 0.15, 1e-9)
    ranked = [
        phase.target_id
        for phase in sorted(schedule.phases, key=lambda phase: (-phase.end_s, phase.start_s))
        if phase.end_s >= cutoff
    ]
    return _unique(ranked)


def _resource_congestion_targets(schedule: ScheduleResult) -> list[str]:
    boundaries = sorted({time for phase in schedule.phases for time in (phase.start_s, phase.end_s)})
    best_score = -1.0
    best_active: list[str] = []
    for left, right in zip(boundaries, boundaries[1:]):
        if right - left <= EPSILON:
            continue
        active = [phase for phase in schedule.phases if phase.start_s < right - EPSILON and left < phase.end_s - EPSILON]
        score = sum(phase.power_w for phase in active) + 0.25 * sum(phase.fpp_lanes_required for phase in active)
        if score > best_score:
            best_score = score
            best_active = [phase.target_id for phase in active]
    return _unique(best_active)


def _thermal_hotspot_targets(schedule: ScheduleResult, recipe_rows: list[dict[str, object]]) -> list[str]:
    selected = {str(row["target_id"]): row for row in schedule.selected_rows}
    fallback = {str(row["target_id"]): row for row in recipe_rows}
    target_ids = sorted({phase.target_id for phase in schedule.phases})
    return sorted(
        target_ids,
        key=lambda target_id: -float(selected.get(target_id, fallback[target_id]).get("thermal_risk", 0.0)),
    )


def _unique(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
