from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from .generator import TestAccessRecipe


NUMERIC_FIELDS = {
    "total_time_s",
    "access_time_s",
    "data_time_s",
    "local_execution_time_s",
    "readback_time_s",
    "peak_power_w",
    "access_power_w",
    "thermal_risk",
    "fpp_lanes_required",
    "estimated_bits",
}

PARETO_METRICS = (
    "total_time_s",
    "peak_power_w",
    "fpp_lanes_required",
    "serial_resource_time_s",
    "thermal_risk",
)


@dataclass(frozen=True)
class ParetoPruningResult:
    kept_rows: list[dict[str, object]]
    removed_rows: list[dict[str, object]]
    summary_rows: list[dict[str, object]]


def rows_from_recipes(recipes: Iterable[TestAccessRecipe]) -> list[dict[str, object]]:
    return [normalize_recipe_row(asdict(recipe)) for recipe in recipes]


def read_recipe_rows_csv(path: str | Path) -> list[dict[str, object]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return [normalize_recipe_row(row) for row in csv.DictReader(handle)]


def write_recipe_rows_csv(rows: list[dict[str, object]], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = _ordered_fieldnames(rows)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def write_pruning_summary_csv(rows: list[dict[str, object]], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "target_id",
        "target_kind",
        "before_count",
        "after_count",
        "removed_count",
        "kept_recipe_ids",
        "removed_recipe_ids",
        "dominance_notes",
    ]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def normalize_recipe_row(row: dict[str, object]) -> dict[str, object]:
    normalized = dict(row)
    for field in NUMERIC_FIELDS:
        if field in normalized:
            normalized[field] = _to_number(normalized[field])

    if "serial_access_required" in normalized:
        normalized["serial_access_required"] = _to_bool(normalized["serial_access_required"])

    normalized["serial_resource_time_s"] = serial_resource_time_s(normalized)
    return normalized


def serial_resource_time_s(row: dict[str, object]) -> float:
    recipe_type = str(row.get("recipe_type", ""))
    access_time = float(row.get("access_time_s", 0.0))
    data_time = float(row.get("data_time_s", 0.0))
    readback_time = float(row.get("readback_time_s", 0.0))

    if not _to_bool(row.get("serial_access_required", False)):
        return 0.0
    if recipe_type in {"S", "I"}:
        return access_time + data_time
    if recipe_type in {"B", "H"}:
        return access_time + readback_time
    return access_time


def pareto_prune(rows: list[dict[str, object]], tolerance: float = 1e-12) -> ParetoPruningResult:
    normalized_rows = [normalize_recipe_row(row) for row in rows]
    kept_rows: list[dict[str, object]] = []
    removed_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []

    for target_id in sorted({str(row["target_id"]) for row in normalized_rows}):
        group = [row for row in normalized_rows if str(row["target_id"]) == target_id]
        group_removed: list[dict[str, object]] = []
        group_kept: list[dict[str, object]] = []
        notes: list[str] = []

        for candidate in group:
            dominator = _find_dominator(candidate, group, tolerance)
            if dominator is None:
                group_kept.append(candidate)
            else:
                removed = dict(candidate)
                removed["dominated_by"] = dominator["recipe_id"]
                removed["dominance_reason"] = _dominance_reason(dominator, candidate, tolerance)
                group_removed.append(removed)
                notes.append(
                    f"{candidate['recipe_id']} dominated by {dominator['recipe_id']} "
                    f"({removed['dominance_reason']})"
                )

        kept_rows.extend(sorted(group_kept, key=lambda row: str(row["recipe_id"])))
        removed_rows.extend(sorted(group_removed, key=lambda row: str(row["recipe_id"])))
        summary_rows.append(
            {
                "target_id": target_id,
                "target_kind": str(group[0].get("target_kind", "")),
                "before_count": len(group),
                "after_count": len(group_kept),
                "removed_count": len(group_removed),
                "kept_recipe_ids": ";".join(str(row["recipe_id"]) for row in sorted(group_kept, key=lambda r: str(r["recipe_id"]))),
                "removed_recipe_ids": ";".join(str(row["recipe_id"]) for row in sorted(group_removed, key=lambda r: str(r["recipe_id"]))),
                "dominance_notes": " | ".join(notes),
            }
        )

    return ParetoPruningResult(
        kept_rows=sorted(kept_rows, key=lambda row: (str(row["target_kind"]), str(row["target_id"]), str(row["recipe_id"]))),
        removed_rows=sorted(removed_rows, key=lambda row: (str(row["target_kind"]), str(row["target_id"]), str(row["recipe_id"]))),
        summary_rows=sorted(summary_rows, key=lambda row: str(row["target_id"])),
    )


def dominates(left: dict[str, object], right: dict[str, object], tolerance: float = 1e-12) -> bool:
    if str(left.get("recipe_id")) == str(right.get("recipe_id")):
        return False
    if str(left.get("target_id")) != str(right.get("target_id")):
        return False

    no_worse = all(float(left[metric]) <= float(right[metric]) + tolerance for metric in PARETO_METRICS)
    strictly_better = any(float(left[metric]) < float(right[metric]) - tolerance for metric in PARETO_METRICS)
    return no_worse and strictly_better


def _find_dominator(
    candidate: dict[str, object],
    group: list[dict[str, object]],
    tolerance: float,
) -> dict[str, object] | None:
    dominators = [other for other in group if dominates(other, candidate, tolerance)]
    if not dominators:
        return None
    return sorted(
        dominators,
        key=lambda row: tuple(float(row[metric]) for metric in PARETO_METRICS),
    )[0]


def _dominance_reason(
    dominator: dict[str, object],
    dominated: dict[str, object],
    tolerance: float,
) -> str:
    better = []
    equal = []
    for metric in PARETO_METRICS:
        left = float(dominator[metric])
        right = float(dominated[metric])
        if left < right - tolerance:
            better.append(metric)
        else:
            equal.append(metric)
    return "better=" + ",".join(better) + "; equal_or_tied=" + ",".join(equal)


def _ordered_fieldnames(rows: list[dict[str, object]]) -> list[str]:
    preferred = [
        "recipe_id",
        "target_id",
        "target_kind",
        "die_id",
        "recipe_type",
        "variant",
        "phases",
        "total_time_s",
        "access_time_s",
        "data_time_s",
        "local_execution_time_s",
        "readback_time_s",
        "serial_resource_time_s",
        "peak_power_w",
        "access_power_w",
        "thermal_risk",
        "serial_access_required",
        "fpp_lanes_required",
        "fpp_channel",
        "dwr_segments",
        "route_resource",
        "estimated_bits",
        "notes",
        "dominated_by",
        "dominance_reason",
    ]
    present = set().union(*(row.keys() for row in rows)) if rows else set(preferred)
    return [field for field in preferred if field in present] + sorted(present - set(preferred))


def _to_number(value: object) -> float | int:
    if isinstance(value, (int, float)):
        return value
    text = str(value)
    if text == "":
        return 0
    number = float(text)
    if number.is_integer() and "." not in text and "e" not in text.lower():
        return int(number)
    return number


def _to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}
