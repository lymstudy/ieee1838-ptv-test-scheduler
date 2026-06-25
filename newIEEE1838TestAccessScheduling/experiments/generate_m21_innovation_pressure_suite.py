from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.model import SystemModel, load_system_model


MANIFEST_FIELDS = [
    "case_id",
    "source_case_id",
    "source_soc",
    "scale",
    "topology_type",
    "die_count",
    "tower_count",
    "target_count",
    "shared_bist_group_count",
    "fpp_lanes",
    "fpp_lane_bandwidth_bps",
    "pressure_intent",
    "case_path",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate M21 ITC'02-derived innovation pressure suite.")
    parser.add_argument("--source-case-dir", default="configs/cases/m10", help="Directory containing M10 case JSONs.")
    parser.add_argument("--case-dir", default="configs/cases/m21", help="Output directory for M21 pressure cases.")
    parser.add_argument(
        "--manifest-output",
        default="data/derived/m21_innovation_pressure_manifest.csv",
        help="Output CSV manifest path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = generate_suite(Path(args.source_case_dir), Path(args.case_dir), Path(args.manifest_output))
    print(f"generated_cases={len(rows)}")
    print(f"manifest_output={args.manifest_output}")


def generate_suite(source_case_dir: Path, case_dir: Path, manifest_output: Path) -> list[dict[str, Any]]:
    source_paths = sorted(source_case_dir.glob("*.json"))
    if not source_paths:
        raise FileNotFoundError(f"no source cases found: {source_case_dir}")
    case_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for source_path in source_paths:
        source_model = load_system_model(source_path)
        payload = build_pressure_case(source_model)
        output_path = case_dir / f"{payload['case_id']}.json"
        output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        load_system_model(output_path)
        rows.append(manifest_row(payload, source_model.case_id, output_path))
    write_manifest(rows, manifest_output)
    return rows


def build_pressure_case(source_model: SystemModel) -> dict[str, Any]:
    raw = deepcopy(source_model.raw)
    source_case_id = source_model.case_id
    raw["case_id"] = source_case_id.replace("m10_", "m21_pressure_", 1)
    raw["description"] = (
        "M21 ITC'02-derived innovation pressure case. It preserves the M10 workload/topology mapping "
        "but adds shared BIST engines, constrained FPP bandwidth, and stronger thermal RC parameters "
        "to expose path-schedule and topology effects."
    )
    raw["provenance_notes"] = list(raw.get("provenance_notes", [])) + [
        f"Derived from {source_case_id}; this is a controlled pressure benchmark, not a new public chip.",
        "Shared BIST engines and thermal RC amplification are experimental stress assumptions.",
    ]
    source = dict(raw.get("benchmark_source", {}))
    source.update(
        {
            "milestone": "M21",
            "source": "ITC02_SOC_PRESSURE_TRANSFORM",
            "source_case_id": source_case_id,
        }
    )
    raw["benchmark_source"] = source

    topology_type = str(raw["package"]["topology_type"])
    pressure = pressure_profile(topology_type)
    apply_fpp_pressure(raw, pressure)
    bist_groups = apply_bist_pressure(raw, pressure)
    apply_scan_and_power_pressure(raw, pressure)
    apply_thermal_pressure(raw, pressure)

    raw.setdefault("experimental_controls", {})
    raw["experimental_controls"]["m21_pressure_intent"] = (
        "make individually fastest BIST paths conflict on shared engines while FPP remains a viable concurrent alternative"
    )
    raw["experimental_controls"]["shared_bist_group_count"] = len(bist_groups)
    return raw


def pressure_profile(topology_type: str) -> dict[str, Any]:
    profiles = {
        "3d_stack": {
            "fpp_lanes": 8,
            "fpp_bandwidth_bps": 1_000_000_000,
            "bist_group_mode": "global",
            "bist_local_cycles": 600_000,
            "thermal_resistance_scale": 18.0,
            "thermal_capacitance_scale": 0.020,
            "vertical_coupling_scale": 4.0,
            "horizontal_coupling_scale": 2.0,
        },
        "2_5d_interposer": {
            "fpp_lanes": 8,
            "fpp_bandwidth_bps": 1_200_000_000,
            "bist_group_mode": "two_horizontal_banks",
            "bist_local_cycles": 520_000,
            "thermal_resistance_scale": 12.0,
            "thermal_capacitance_scale": 0.025,
            "vertical_coupling_scale": 1.5,
            "horizontal_coupling_scale": 4.0,
        },
        "5_5d_multi_tower": {
            "fpp_lanes": 8,
            "fpp_bandwidth_bps": 1_000_000_000,
            "bist_group_mode": "tower_banks",
            "bist_local_cycles": 580_000,
            "thermal_resistance_scale": 16.0,
            "thermal_capacitance_scale": 0.020,
            "vertical_coupling_scale": 4.0,
            "horizontal_coupling_scale": 3.0,
        },
    }
    return profiles[topology_type]


def apply_fpp_pressure(raw: dict[str, Any], pressure: dict[str, Any]) -> None:
    lanes = int(pressure["fpp_lanes"])
    bandwidth = int(pressure["fpp_bandwidth_bps"])
    raw["resource_limits"]["total_fpp_lanes"] = lanes
    raw["resource_limits"]["max_total_power_w"] = max(float(raw["resource_limits"].get("max_total_power_w", 10.0)), 120.0)
    for channel in raw["ieee1838_access"].get("fpp_channels", []):
        channel["max_lanes"] = lanes
    for lane in raw["ieee1838_access"].get("fpp_lanes", []):
        lane["bandwidth_bps"] = bandwidth
    raw["timing"]["default_fpp_lane_bandwidth_bps"] = bandwidth
    for group in raw.get("resource_groups", {}).get("fpp_capacity_groups", []):
        group["capacity"] = lanes
        group["members"] = list(group.get("members", []))[:lanes]
    for domain in raw.get("resource_groups", {}).get("power_domains", []):
        domain["max_power_w"] = raw["resource_limits"]["max_total_power_w"]


def apply_bist_pressure(raw: dict[str, Any], pressure: dict[str, Any]) -> list[dict[str, Any]]:
    objects = [obj for obj in raw["test_objects"] if obj.get("object_type") != "instrument"]
    groups: dict[str, list[str]] = {}
    for obj in objects:
        group_id = bist_group_id(raw, obj, pressure["bist_group_mode"])
        groups.setdefault(group_id, []).append(obj["object_id"])
        obj.setdefault("supported_recipes", [])
        if "B" not in obj["supported_recipes"]:
            obj["supported_recipes"].append("B")
        obj["bist"] = {
            "enabled": True,
            "engine_id": group_id,
            "config_bits": 96,
            "local_cycles": int(pressure["bist_local_cycles"]),
            "readout_bits": 128,
            "bist_clock_hz": raw["timing"].get("default_bist_clock_hz", 100_000_000),
        }
        obj.setdefault("required_resources", {})["bist_engine"] = group_id

    bist_groups = [
        {"group_id": group_id, "capacity": 1, "members": sorted(members)}
        for group_id, members in sorted(groups.items())
    ]
    raw["resource_groups"]["bist_engine_groups"] = bist_groups
    return bist_groups


def bist_group_id(raw: dict[str, Any], obj: dict[str, Any], mode: str) -> str:
    die = next(item for item in raw["dies"] if item["die_id"] == obj["die_id"])
    if mode == "global":
        return "m21_bist_global_stack"
    if mode == "two_horizontal_banks":
        die_index = int(re.sub(r"\D", "", str(die["die_id"])) or 0)
        return f"m21_bist_interposer_bank{die_index % 2}"
    if mode == "tower_banks":
        tower_id = str(die.get("tower_id", "tower0"))
        tower_index = int(re.sub(r"\D", "", tower_id) or 0)
        return f"m21_bist_tower_bank{tower_index % 3}"
    raise ValueError(f"unknown BIST pressure mode: {mode}")


def apply_scan_and_power_pressure(raw: dict[str, Any], pressure: dict[str, Any]) -> None:
    for index, obj in enumerate(raw["test_objects"]):
        if obj.get("object_type") == "instrument":
            continue
        scan = obj.setdefault("scan", {})
        scan["chain_count"] = max(int(scan.get("chain_count", 1)), 16)
        scan["max_chain_length_bits"] = max(int(scan.get("max_chain_length_bits", 0)), 160_000)
        scan["pattern_count"] = max(int(scan.get("pattern_count", 0)), 160)
        scan["response_bits_per_pattern"] = scan["max_chain_length_bits"]
        weight = 1.0 + 0.05 * (index % 5)
        obj["area_mm2"] = max(float(obj.get("area_mm2", 1.0)), 1.8)
        obj["power"] = {
            "shift_power_w": round(1.2 * weight, 4),
            "capture_power_w": round(2.0 * weight, 4),
            "access_power_w": 0.08,
            "bist_power_w": round(3.4 * weight, 4),
        }


def apply_thermal_pressure(raw: dict[str, Any], pressure: dict[str, Any]) -> None:
    raw["thermal_model"]["vertical_coupling_weight"] = float(raw["thermal_model"].get("vertical_coupling_weight", 0.35)) * float(
        pressure["vertical_coupling_scale"]
    )
    raw["thermal_model"]["horizontal_coupling_weight"] = float(raw["thermal_model"].get("horizontal_coupling_weight", 0.2)) * float(
        pressure["horizontal_coupling_scale"]
    )
    for die in raw["dies"]:
        thermal = die["thermal"]
        thermal["thermal_resistance_c_per_w"] = round(
            float(thermal.get("thermal_resistance_c_per_w", 1.0)) * float(pressure["thermal_resistance_scale"]),
            6,
        )
        thermal["thermal_capacitance_j_per_c"] = max(
            0.002,
            round(float(thermal.get("thermal_capacitance_j_per_c", 1.0)) * float(pressure["thermal_capacitance_scale"]), 6),
        )
        layer = int(die.get("layer_index", 0))
        thermal["cooling_factor"] = max(0.35, float(thermal.get("cooling_factor", 1.0)) - 0.04 * layer)


def write_manifest(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def manifest_row(payload: dict[str, Any], source_case_id: str, output_path: Path) -> dict[str, Any]:
    source = payload.get("benchmark_source", {})
    return {
        "case_id": payload["case_id"],
        "source_case_id": source_case_id,
        "source_soc": source.get("soc_name", ""),
        "scale": source.get("scale", ""),
        "topology_type": payload["package"]["topology_type"],
        "die_count": payload["package"]["die_count"],
        "tower_count": payload["package"]["tower_count"],
        "target_count": len(payload["test_objects"]) + len(payload["interconnects"]),
        "shared_bist_group_count": payload["experimental_controls"]["shared_bist_group_count"],
        "fpp_lanes": payload["resource_limits"]["total_fpp_lanes"],
        "fpp_lane_bandwidth_bps": payload["timing"]["default_fpp_lane_bandwidth_bps"],
        "pressure_intent": payload["experimental_controls"]["m21_pressure_intent"],
        "case_path": output_path.as_posix(),
    }


if __name__ == "__main__":
    main()
