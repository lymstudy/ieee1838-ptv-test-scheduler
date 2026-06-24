from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.model.itc02 import Itc02Module, parse_soc_file


UNITS = {
    "time": "s",
    "frequency": "Hz",
    "bandwidth": "bit/s",
    "length": "um",
    "area": "mm2",
    "power": "W",
    "temperature": "C",
    "voltage": "V",
    "resistance": "ohm",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate M9 public benchmark-derived case JSONs.")
    parser.add_argument(
        "--itc02-dir",
        default="docs/data/itc02_benchmarks",
        help="Directory containing ITC'02 .soc files.",
    )
    parser.add_argument(
        "--case-dir",
        default="configs/cases",
        help="Output directory for generated M9 case JSON files.",
    )
    parser.add_argument(
        "--derived-output",
        default="data/derived/m9_itc02_module_summary.csv",
        help="Output CSV path for parsed ITC'02 module summary.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    itc02_dir = Path(args.itc02_dir)
    case_dir = Path(args.case_dir)
    d695 = parse_soc_file(itc02_dir / "d695.soc")
    p22810 = parse_soc_file(itc02_dir / "p22810.soc")

    write_itc02_summary([d695, p22810], args.derived_output)

    case_dir.mkdir(parents=True, exist_ok=True)
    two_five_d = build_2_5d_case(d695.leaf_modules[:10])
    multi_tower = build_5_5d_case(_select_p22810_modules(p22810.leaf_modules))

    write_json(two_five_d, case_dir / "2_5d_interposer_m9_public.json")
    write_json(multi_tower, case_dir / "5_5d_multi_tower_m9_public.json")

    print(f"generated={case_dir / '2_5d_interposer_m9_public.json'}")
    print(f"generated={case_dir / '5_5d_multi_tower_m9_public.json'}")
    print(f"derived_output={args.derived_output}")


def build_2_5d_case(modules: tuple[Itc02Module, ...]) -> dict[str, Any]:
    dies = [
        _die("die0", "primary", "interposer0", 0, None, 0, 0, 0, 1000, 1000, 0.55, 0.16, 0.78),
        _die("die1", "secondary", "interposer0", 0, "die0", 1400, 0, 0, 800, 800, 0.60, 0.15, 0.84),
        _die("die2", "secondary", "interposer0", 0, "die0", 0, 1400, 0, 750, 750, 0.64, 0.14, 0.88),
        _die("die3", "secondary", "interposer0", 0, "die0", 1400, 1400, 0, 2500, 2500, 0.50, 0.28, 0.76),
    ]
    dwr_segments = [_dwr(f"dwr_die{i}", f"die{i}", 256 + 32 * i) for i in range(4)]
    objects = _objects_from_modules(
        modules,
        die_ids=["die0", "die1", "die2", "die3"],
        dwr_by_die={f"die{i}": [f"dwr_die{i}"] for i in range(4)},
        prefix="d695",
        bist_every=4,
    )
    return _case(
        case_id="2_5d_interposer_m9_public",
        description="2.5D interposer case derived from ITC'02 d695 modules, Open3DBench area/power references, and UCIe-like interposer link assumptions.",
        topology_type="2_5d_interposer",
        tower_count=1,
        dies=dies,
        dwr_segments=dwr_segments,
        fpp_channel_id="fpp_interposer",
        fpp_bandwidth_bps=32_000_000_000,
        fpp_lanes=8,
        test_objects=objects + [_instrument("sensor_die3_hotspot", "die3", "thermal_die3")],
        interconnects=[
            _link("link_die0_die1", "die0", "die1", "interposer_ucie_like", ["dwr_die0", "dwr_die1"], "ucie_adv_die0_die1", 8192, 0.25),
            _link("link_die0_die2", "die0", "die2", "interposer_ucie_like", ["dwr_die0", "dwr_die2"], "ucie_adv_die0_die2", 8192, 0.25),
            _link("link_die1_die3", "die1", "die3", "interposer_ucie_like", ["dwr_die1", "dwr_die3"], "ucie_adv_die1_die3", 12288, 0.30),
            _link("link_die2_die3", "die2", "die3", "interposer_ucie_like", ["dwr_die2", "dwr_die3"], "ucie_adv_die2_die3", 12288, 0.30),
        ],
        thermal_adjacency=[
            _thermal_edge("thermal_die0", "thermal_die1", "horizontal", 0.45),
            _thermal_edge("thermal_die0", "thermal_die2", "horizontal", 0.45),
            _thermal_edge("thermal_die1", "thermal_die3", "horizontal", 0.35),
            _thermal_edge("thermal_die2", "thermal_die3", "horizontal", 0.35),
        ],
        provenance_notes=[
            "ITC'02 d695 .soc provides module I/O, scan-chain lengths, and pattern counts.",
            "UCIe 32 GT/s public value is used as a package-link-derived FPP-like scheduler capacity, not as IEEE 1838 FPP itself.",
            "IEEE 1838 bit widths and per-phase power split are model assumptions.",
        ],
    )


def build_5_5d_case(modules: tuple[Itc02Module, ...]) -> dict[str, Any]:
    dies = [
        _die("die0", "primary", "tower0", 0, None, 0, 0, 0, 1000, 1000, 0.58, 0.16, 0.78),
        _die("die1", "secondary", "tower0", 1, "die0", 0, 0, 45, 850, 850, 0.72, 0.15, 0.94),
        _die("die2", "secondary", "tower1", 0, "die0", 1600, 0, 0, 900, 900, 0.58, 0.16, 0.80),
        _die("die3", "secondary", "tower1", 1, "die2", 1600, 0, 45, 850, 850, 0.74, 0.15, 0.96),
        _die("die4", "secondary", "tower2", 0, "die0", 800, 1500, 0, 1100, 1100, 0.55, 0.18, 0.82),
        _die("die5", "secondary", "tower2", 1, "die4", 800, 1500, 45, 950, 950, 0.78, 0.16, 1.02),
    ]
    dwr_segments = [_dwr(f"dwr_die{i}", f"die{i}", 256 + 16 * i) for i in range(6)]
    objects = _objects_from_modules(
        modules,
        die_ids=["die0", "die1", "die2", "die3", "die4", "die5"],
        dwr_by_die={f"die{i}": [f"dwr_die{i}"] for i in range(6)},
        prefix="p22810",
        bist_every=3,
    )
    return _case(
        case_id="5_5d_multi_tower_m9_public",
        description="5.5D multi-tower case derived from selected ITC'02 p22810 modules, Open3DBench 3D references, and UCIe/UCIe-3D link assumptions.",
        topology_type="5_5d_multi_tower",
        tower_count=3,
        dies=dies,
        dwr_segments=dwr_segments,
        fpp_channel_id="fpp_multitower",
        fpp_bandwidth_bps=4_000_000_000,
        fpp_lanes=8,
        test_objects=objects + [_instrument("sensor_tower2_top", "die5", "thermal_die5")],
        interconnects=[
            _link("link_t0_vertical", "die0", "die1", "hybrid_bond", ["dwr_die0", "dwr_die1"], "hbt_tower0", 8192, 0.35),
            _link("link_t1_vertical", "die2", "die3", "hybrid_bond", ["dwr_die2", "dwr_die3"], "hbt_tower1", 8192, 0.35),
            _link("link_t2_vertical", "die4", "die5", "hybrid_bond", ["dwr_die4", "dwr_die5"], "hbt_tower2", 8192, 0.35),
            _link("link_t0_t1_interposer", "die0", "die2", "interposer_ucie_like", ["dwr_die0", "dwr_die2"], "ucie_tower0_tower1", 16384, 0.45),
            _link("link_t1_t2_interposer", "die2", "die4", "interposer_ucie_like", ["dwr_die2", "dwr_die4"], "ucie_tower1_tower2", 16384, 0.45),
        ],
        thermal_adjacency=[
            _thermal_edge("thermal_die0", "thermal_die1", "vertical", 0.70),
            _thermal_edge("thermal_die2", "thermal_die3", "vertical", 0.72),
            _thermal_edge("thermal_die4", "thermal_die5", "vertical", 0.76),
            _thermal_edge("thermal_die0", "thermal_die2", "horizontal", 0.35),
            _thermal_edge("thermal_die2", "thermal_die4", "horizontal", 0.35),
            _thermal_edge("thermal_die1", "thermal_die3", "horizontal", 0.25),
            _thermal_edge("thermal_die3", "thermal_die5", "horizontal", 0.25),
        ],
        provenance_notes=[
            "Selected ITC'02 p22810 .soc modules provide scan-chain lengths and pattern counts.",
            "UCIe-3D 4 GT/s and HBT geometry are used as package-link references, mapped to scheduler capacity abstractions.",
            "IEEE 1838 controller bit widths, BIST availability, and operation-specific power are model assumptions.",
        ],
    )


def write_itc02_summary(socs: list[Any], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "soc_name",
        "module_id",
        "level",
        "inputs",
        "outputs",
        "bidirs",
        "scan_chain_count",
        "max_chain_length_bits",
        "total_chain_length_bits",
        "pattern_count",
        "test_count",
    ]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for soc in socs:
            for module in soc.modules:
                writer.writerow(
                    {
                        "soc_name": soc.soc_name,
                        "module_id": module.module_id,
                        "level": module.level,
                        "inputs": module.inputs,
                        "outputs": module.outputs,
                        "bidirs": module.bidirs,
                        "scan_chain_count": module.chain_count,
                        "max_chain_length_bits": module.max_chain_length_bits,
                        "total_chain_length_bits": module.total_chain_length_bits,
                        "pattern_count": module.pattern_count,
                        "test_count": len(module.tests),
                    }
                )


def _case(
    case_id: str,
    description: str,
    topology_type: str,
    tower_count: int,
    dies: list[dict[str, Any]],
    dwr_segments: list[dict[str, Any]],
    fpp_channel_id: str,
    fpp_bandwidth_bps: int,
    fpp_lanes: int,
    test_objects: list[dict[str, Any]],
    interconnects: list[dict[str, Any]],
    thermal_adjacency: list[dict[str, Any]],
    provenance_notes: list[str],
) -> dict[str, Any]:
    die_ids = [die["die_id"] for die in dies]
    dwr_ids = [segment["segment_id"] for segment in dwr_segments]
    return {
        "model_version": "m1-ieee1838-computable-v1",
        "case_id": case_id,
        "description": description,
        "provenance_notes": provenance_notes,
        "units": UNITS,
        "package": {
            "topology_type": topology_type,
            "tower_count": tower_count,
            "die_count": len(dies),
            "primary_entry_die": "die0",
            "thermal_boundary": "top_heat_sink",
            "ambient_temperature_c": 25.0,
        },
        "timing": {
            "ptap_tck_hz": 50_000_000,
            "default_bist_clock_hz": 100_000_000,
            "default_fpp_lane_bandwidth_bps": fpp_bandwidth_bps,
            "capture_time_s": 0.000001,
            "mode_update_time_s": 0.000001,
        },
        "resource_limits": {
            "ptap_ports": 1,
            "total_fpp_lanes": fpp_lanes,
            "max_total_power_w": 10.0 if len(dies) <= 4 else 14.0,
            "max_temperature_c": 85.0,
            "max_ir_drop_v": 0.12,
            "max_concurrent_capture": 1,
        },
        "thermal_model": {
            "self_heating_weight": 1.0,
            "vertical_coupling_weight": 0.35,
            "horizontal_coupling_weight": 0.20,
            "layer_distance_decay": 0.5,
        },
        "dies": dies,
        "ieee1838_access": {
            "ptap": {
                "ptap_id": "ptap0",
                "die_id": "die0",
                "tck_hz": 50_000_000,
                "exclusive": True,
                "control_bits_per_access": 64,
            },
            "staps": [
                {
                    "stap_id": f"stap_{die_id}",
                    "die_id": die_id,
                    "parent_die": _parent_die(dies, die_id),
                    "select_bits": 32,
                    "bypass_bits": 1,
                    "exclusive_path_group": "serial_access_path",
                }
                for die_id in die_ids
                if die_id != "die0"
            ],
            "three_dcrs": [
                {
                    "register_id": f"3dcr_{die_id}",
                    "die_id": die_id,
                    "bit_length": 32,
                    "controls": [segment["segment_id"] for segment in dwr_segments if segment["die_id"] == die_id],
                }
                for die_id in die_ids
            ],
            "dwr_segments": dwr_segments,
            "fpp_channels": [
                {
                    "channel_id": fpp_channel_id,
                    "source_die": "die0",
                    "target_scope": "package",
                    "config_bits": 64,
                    "max_lanes": fpp_lanes,
                }
            ],
            "fpp_lanes": [
                {
                    "lane_id": f"{fpp_channel_id}_lane{index}",
                    "channel_id": fpp_channel_id,
                    "direction": "bidirectional",
                    "bandwidth_bps": fpp_bandwidth_bps,
                    "registered": True,
                    "requires_clock_lane": index < 2,
                    "connects": {
                        "dies": die_ids,
                        "dwr_segments": dwr_ids,
                    },
                    "mutual_exclusion_group": f"{fpp_channel_id}_lane{index}_dir",
                }
                for index in range(fpp_lanes)
            ],
        },
        "test_objects": test_objects,
        "interconnects": interconnects,
        "resource_groups": {
            "serial_access_groups": [
                {
                    "group_id": "serial_access_path",
                    "capacity": 1,
                    "members": ["ptap0"] + [f"stap_{die_id}" for die_id in die_ids if die_id != "die0"],
                }
            ],
            "fpp_capacity_groups": [
                {
                    "group_id": f"{fpp_channel_id}_lanes",
                    "capacity": fpp_lanes,
                    "members": [f"{fpp_channel_id}_lane{index}" for index in range(fpp_lanes)],
                }
            ],
            "dwr_conflict_groups": [
                {
                    "group_id": f"dwr_group_{die_id}",
                    "capacity": 1,
                    "members": [segment["segment_id"] for segment in dwr_segments if segment["die_id"] == die_id],
                }
                for die_id in die_ids
            ],
            "bist_engine_groups": [
                {
                    "group_id": object_["required_resources"]["bist_engine"],
                    "capacity": 1,
                    "members": [object_["object_id"]],
                }
                for object_ in test_objects
                if object_.get("bist", {}).get("enabled", False)
            ],
            "power_domains": [
                {
                    "domain_id": "pdn_package",
                    "max_power_w": 10.0 if len(dies) <= 4 else 14.0,
                    "dies": die_ids,
                }
            ],
            "thermal_regions": [
                {
                    "region_id": die["thermal"]["region_id"],
                    "die_id": die["die_id"],
                    "max_temperature_c": 85.0,
                }
                for die in dies
            ],
        },
        "thermal_adjacency": thermal_adjacency,
    }


def _objects_from_modules(
    modules: tuple[Itc02Module, ...],
    die_ids: list[str],
    dwr_by_die: dict[str, list[str]],
    prefix: str,
    bist_every: int,
) -> list[dict[str, Any]]:
    weights = [max(1, module.total_chain_length_bits * max(1, module.pattern_count)) for module in modules]
    max_weight = max(weights)
    objects = []
    for index, module in enumerate(modules):
        die_id = die_ids[index % len(die_ids)]
        object_type = "memory" if (index + 1) % bist_every == 0 else "core"
        weight = weights[index] / max_weight
        shift_power = round(0.18 + 0.85 * weight, 4)
        capture_power = round(0.42 + 1.65 * weight, 4)
        access_power = round(0.05 + 0.06 * weight, 4)
        bist_enabled = object_type == "memory"
        object_id = f"{prefix}_m{module.module_id}_die{die_id[-1]}"
        obj: dict[str, Any] = {
            "object_id": object_id,
            "object_type": object_type,
            "die_id": die_id,
            "area_mm2": round(max(0.05, 0.15 + 1.2 * weight), 4),
            "scan": {
                "chain_count": max(1, module.chain_count),
                "max_chain_length_bits": module.max_chain_length_bits,
                "pattern_count": max(1, module.pattern_count),
                "requires_capture": True,
                "response_bits_per_pattern": module.max_chain_length_bits,
            },
            "bist": {"enabled": False},
            "power": {
                "shift_power_w": shift_power,
                "capture_power_w": capture_power,
                "access_power_w": access_power,
            },
            "thermal_region": f"thermal_{die_id}",
            "supported_recipes": ["S", "F", "H"],
            "required_resources": {
                "dwr_segments": dwr_by_die[die_id],
                "preferred_fpp_channel": "fpp_interposer" if len(die_ids) == 4 else "fpp_multitower",
            },
        }
        if bist_enabled:
            engine_id = f"bist_{object_id}"
            obj["bist"] = {
                "enabled": True,
                "engine_id": engine_id,
                "config_bits": 96,
                "local_cycles": max(50_000, module.pattern_count * module.max_chain_length_bits),
                "readout_bits": 128,
                "bist_clock_hz": 100_000_000,
            }
            obj["power"]["bist_power_w"] = round(0.35 + 0.95 * weight, 4)
            obj["supported_recipes"] = ["S", "F", "B", "H"]
            obj["required_resources"]["bist_engine"] = engine_id
        objects.append(obj)
    return objects


def _select_p22810_modules(modules: tuple[Itc02Module, ...]) -> tuple[Itc02Module, ...]:
    nonzero = [module for module in modules if module.level > 0 and module.pattern_count > 0]
    return tuple(sorted(nonzero, key=lambda module: module.total_chain_length_bits * module.pattern_count, reverse=True)[:12])


def _die(
    die_id: str,
    role: str,
    tower_id: str,
    layer_index: int,
    parent: str | None,
    x: int,
    y: int,
    z: int,
    width: int,
    height: int,
    thermal_resistance: float,
    thermal_capacitance: float,
    cooling_factor: float,
) -> dict[str, Any]:
    return {
        "die_id": die_id,
        "role": role,
        "tower_id": tower_id,
        "layer_index": layer_index,
        "access_parent_die": parent,
        "position_um": {"x": x, "y": y, "z": z},
        "size_um": {"width": width, "height": height},
        "thermal": {
            "region_id": f"thermal_{die_id}",
            "thermal_resistance_c_per_w": thermal_resistance,
            "thermal_capacitance_j_per_c": thermal_capacitance,
            "heat_sink_distance_rank": 1 + layer_index,
            "cooling_factor": cooling_factor,
        },
        "pdn": {
            "supply_voltage_v": 0.8,
            "self_resistance_ohm": round(0.030 + 0.006 * layer_index, 4),
            "shared_resistance_ohm": round(0.015 + 0.004 * layer_index, 4),
        },
    }


def _dwr(segment_id: str, die_id: str, bit_length: int) -> dict[str, Any]:
    return {
        "segment_id": segment_id,
        "die_id": die_id,
        "bit_length": bit_length,
        "supported_modes": ["EXTEST", "IF", "OF", "MISSION"],
        "serial_access": True,
        "fpp_access": True,
        "parallel_group": f"dwr_group_{die_id}",
        "mode_config_bits": 16,
    }


def _link(
    link_id: str,
    source_die: str,
    target_die: str,
    link_type: str,
    dwr_segments: list[str],
    route_resource: str,
    estimated_bits: int,
    power_w: float,
) -> dict[str, Any]:
    return {
        "link_id": link_id,
        "source_die": source_die,
        "target_die": target_die,
        "link_type": link_type,
        "test_mode": "DWR_EXTEST",
        "dwr_segments": dwr_segments,
        "route_resource": route_resource,
        "estimated_test_bits": estimated_bits,
        "power_w": power_w,
    }


def _thermal_edge(source: str, target: str, coupling_type: str, coupling_weight: float) -> dict[str, Any]:
    return {
        "source_region": source,
        "target_region": target,
        "coupling_type": coupling_type,
        "coupling_weight": coupling_weight,
        "avoid_concurrent_high_power": True,
    }


def _instrument(object_id: str, die_id: str, thermal_region: str) -> dict[str, Any]:
    return {
        "object_id": object_id,
        "object_type": "instrument",
        "die_id": die_id,
        "area_mm2": 0.05,
        "instrument": {
            "network_depth": 2,
            "address_bits": 16,
            "readout_bits": 32,
            "requires_readback": True,
        },
        "power": {"access_power_w": 0.04},
        "thermal_region": thermal_region,
        "supported_recipes": ["S"],
        "required_resources": {"instrument_network": f"instr_{die_id}"},
    }


def _parent_die(dies: list[dict[str, Any]], die_id: str) -> str:
    for die in dies:
        if die["die_id"] == die_id:
            return str(die["access_parent_die"])
    raise KeyError(die_id)


def write_json(payload: dict[str, Any], output_path: str | Path) -> None:
    Path(output_path).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
