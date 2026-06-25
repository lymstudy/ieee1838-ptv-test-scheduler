from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.generate_m10_benchmark_suite import _topology
from experiments.generate_m9_cases import _case, _dwr, write_json
from src.model import load_system_model


MANIFEST_FIELDS = [
    "case_id",
    "topology_type",
    "die_count",
    "tower_count",
    "target_count",
    "shared_bist_engine",
    "fpp_lanes",
    "fpp_lane_bandwidth_bps",
    "case_path",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate M18 resource-pressure cases.")
    parser.add_argument("--case-dir", default="configs/cases/m18", help="Output directory for M18 case JSON files.")
    parser.add_argument(
        "--manifest-output",
        default="data/derived/m18_pressure_case_manifest.csv",
        help="Output CSV manifest path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = generate_pressure_cases(Path(args.case_dir), Path(args.manifest_output))
    print(f"generated_cases={len(rows)}")
    print(f"manifest_output={args.manifest_output}")


def generate_pressure_cases(case_dir: Path, manifest_output: Path) -> list[dict[str, Any]]:
    case_dir.mkdir(parents=True, exist_ok=True)
    specs = [
        ("m18_shared_bist_8die_3d_stack", "3d_stack", 8),
        ("m18_shared_bist_12die_5_5d_multi_tower", "5_5d_multi_tower", 12),
    ]
    rows = []
    for case_id, topology_type, die_count in specs:
        payload = build_shared_bist_pressure_case(case_id, topology_type, die_count)
        output_path = case_dir / f"{case_id}.json"
        write_json(payload, output_path)
        load_system_model(output_path)
        rows.append(_manifest_row(payload, output_path))
    write_manifest(rows, manifest_output)
    return rows


def build_shared_bist_pressure_case(case_id: str, topology_type: str, die_count: int) -> dict[str, Any]:
    topology = _topology(topology_type, die_count)
    dies = topology["dies"]
    die_ids = [die["die_id"] for die in dies]
    dwr_segments = [_dwr(f"dwr_{die_id}", die_id, 320 + 8 * index) for index, die_id in enumerate(die_ids)]
    dwr_by_die = {segment["die_id"]: [segment["segment_id"]] for segment in dwr_segments}
    objects = [
        _pressure_memory_object(index=index, die_id=die_id, dwr_segments=dwr_by_die[die_id])
        for index, die_id in enumerate(die_ids)
    ]
    payload = _case(
        case_id=case_id,
        description=(
            f"M18 resource-pressure case for path/schedule co-optimization on {topology_type}. "
            "Each target has a fast local BIST option that shares one global BIST engine, plus slower FPP alternatives "
            "that can use package lanes concurrently."
        ),
        topology_type=topology_type,
        tower_count=topology["tower_count"],
        dies=dies,
        dwr_segments=dwr_segments,
        fpp_channel_id="fpp_m18",
        fpp_bandwidth_bps=1_000_000_000,
        fpp_lanes=8,
        test_objects=objects,
        interconnects=[],
        thermal_adjacency=topology["thermal_adjacency"],
        provenance_notes=[
            "M18 is a synthetic resource-pressure benchmark derived from the existing M10 topology generator.",
            "The shared BIST engine is intentionally modeled to stress fixed fastest-path selection.",
            "Scan size, BIST cycles, and power values are controlled assumptions for algorithm ablation.",
        ],
    )
    payload["resource_limits"]["max_total_power_w"] = 80.0
    payload["resource_limits"]["max_concurrent_capture"] = 2
    payload["resource_groups"]["power_domains"][0]["max_power_w"] = 80.0
    payload["resource_groups"]["bist_engine_groups"] = [
        {
            "group_id": "shared_m18_bist_engine",
            "capacity": 1,
            "members": [obj["object_id"] for obj in objects],
        }
    ]
    payload["benchmark_source"] = {
        "milestone": "M18",
        "source": "SYNTHETIC_RESOURCE_PRESSURE",
        "soc_name": "m18_pressure",
        "scale": "pressure",
        "selected_module_count": len(objects),
        "selected_module_ids": [obj["object_id"] for obj in objects],
    }
    return payload


def _pressure_memory_object(index: int, die_id: str, dwr_segments: list[str]) -> dict[str, Any]:
    object_id = f"m18_mem{index:02d}_{die_id}"
    return {
        "object_id": object_id,
        "object_type": "memory",
        "die_id": die_id,
        "area_mm2": 2.0,
        "scan": {
            "chain_count": 16,
            "max_chain_length_bits": 160_000,
            "pattern_count": 160,
            "requires_capture": True,
            "response_bits_per_pattern": 160_000,
        },
        "bist": {
            "enabled": True,
            "engine_id": "shared_m18_bist_engine",
            "config_bits": 96,
            "local_cycles": 600_000,
            "readout_bits": 128,
            "bist_clock_hz": 100_000_000,
        },
        "power": {
            "shift_power_w": 0.60,
            "capture_power_w": 1.00,
            "access_power_w": 0.05,
            "bist_power_w": 1.20,
        },
        "thermal_region": f"thermal_{die_id}",
        "supported_recipes": ["S", "F", "B", "H"],
        "required_resources": {
            "dwr_segments": dwr_segments,
            "preferred_fpp_channel": "fpp_m18",
            "bist_engine": "shared_m18_bist_engine",
        },
    }


def write_manifest(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _manifest_row(payload: dict[str, Any], output_path: Path) -> dict[str, Any]:
    return {
        "case_id": payload["case_id"],
        "topology_type": payload["package"]["topology_type"],
        "die_count": payload["package"]["die_count"],
        "tower_count": payload["package"]["tower_count"],
        "target_count": len(payload["test_objects"]) + len(payload["interconnects"]),
        "shared_bist_engine": "shared_m18_bist_engine",
        "fpp_lanes": payload["resource_limits"]["total_fpp_lanes"],
        "fpp_lane_bandwidth_bps": payload["timing"]["default_fpp_lane_bandwidth_bps"],
        "case_path": output_path.as_posix(),
    }


if __name__ == "__main__":
    main()
