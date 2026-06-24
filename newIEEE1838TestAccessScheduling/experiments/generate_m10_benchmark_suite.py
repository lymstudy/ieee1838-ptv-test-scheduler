from __future__ import annotations

import argparse
import csv
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.generate_m9_cases import (
    _case,
    _die,
    _dwr,
    _instrument,
    _link,
    _objects_from_modules,
    _thermal_edge,
    write_json,
)
from src.model import Itc02Module, Itc02Soc, load_system_model, parse_soc_file


@dataclass(frozen=True)
class BenchmarkSpec:
    soc_name: str
    scale: str
    module_count: int
    die_count: int


DEFAULT_SPECS = (
    BenchmarkSpec("d695", "small", 10, 4),
    BenchmarkSpec("p22810", "medium", 16, 6),
    BenchmarkSpec("p34392", "large", 20, 8),
    BenchmarkSpec("p93791", "xlarge", 24, 12),
)

TOPOLOGIES = ("3d_stack", "2_5d_interposer", "5_5d_multi_tower")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate M10 ITC'02-derived benchmark suite cases.")
    parser.add_argument("--itc02-dir", default="docs/data/itc02_benchmarks", help="Directory containing ITC'02 .soc files.")
    parser.add_argument("--case-dir", default="configs/cases/m10", help="Output directory for M10 case JSONs.")
    parser.add_argument(
        "--manifest-output",
        default="data/derived/m10_benchmark_suite_manifest.csv",
        help="Output CSV manifest path.",
    )
    parser.add_argument("--max-fpp-lanes", type=int, default=16, help="Generated maximum FPP lanes per case.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = generate_suite(
        itc02_dir=Path(args.itc02_dir),
        case_dir=Path(args.case_dir),
        manifest_output=Path(args.manifest_output),
        max_fpp_lanes=args.max_fpp_lanes,
    )
    print(f"generated_cases={len(rows)}")
    print(f"manifest_output={args.manifest_output}")


def generate_suite(
    itc02_dir: Path,
    case_dir: Path,
    manifest_output: Path,
    max_fpp_lanes: int = 16,
    specs: tuple[BenchmarkSpec, ...] = DEFAULT_SPECS,
    topologies: tuple[str, ...] = TOPOLOGIES,
) -> list[dict[str, Any]]:
    case_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for spec in specs:
        soc = parse_soc_file(itc02_dir / f"{spec.soc_name}.soc")
        modules = select_modules(soc, spec.module_count)
        for topology in topologies:
            payload = build_m10_case(soc, spec, modules, topology, max_fpp_lanes=max_fpp_lanes)
            output_path = case_dir / f"{payload['case_id']}.json"
            write_json(payload, output_path)
            load_system_model(output_path)
            rows.append(_manifest_row(payload, modules, output_path))
    write_manifest(rows, manifest_output)
    return rows


def build_m10_case(
    soc: Itc02Soc,
    spec: BenchmarkSpec,
    modules: tuple[Itc02Module, ...],
    topology_type: str,
    max_fpp_lanes: int = 16,
) -> dict[str, Any]:
    if topology_type not in TOPOLOGIES:
        raise ValueError(f"unsupported M10 topology: {topology_type}")

    fpp_channel_id = {
        "3d_stack": "fpp_3d_stack",
        "2_5d_interposer": "fpp_interposer",
        "5_5d_multi_tower": "fpp_multitower",
    }[topology_type]
    fpp_bandwidth_bps = 32_000_000_000 if topology_type == "2_5d_interposer" else 4_000_000_000

    topology = _topology(topology_type, spec.die_count)
    dwr_segments = [_dwr(f"dwr_die{i}", f"die{i}", 256 + 16 * (i % 8)) for i in range(spec.die_count)]
    die_ids = [die["die_id"] for die in topology["dies"]]
    objects = _objects_from_modules(
        modules,
        die_ids=die_ids,
        dwr_by_die={die_id: [f"dwr_{die_id}"] for die_id in die_ids},
        prefix=soc.soc_name,
        bist_every=max(3, min(6, len(modules) // 3 or 3)),
    )
    for obj in objects:
        obj["required_resources"]["preferred_fpp_channel"] = fpp_channel_id

    case_id = f"m10_{spec.scale}_{soc.soc_name}_{topology_type}"
    payload = _case(
        case_id=case_id,
        description=(
            f"M10 {spec.scale} {topology_type} benchmark case derived from ITC'02 {soc.soc_name}. "
            "Topology, IEEE 1838 control widths, power split, and thermal RC parameters are model assumptions."
        ),
        topology_type=topology_type,
        tower_count=topology["tower_count"],
        dies=topology["dies"],
        dwr_segments=dwr_segments,
        fpp_channel_id=fpp_channel_id,
        fpp_bandwidth_bps=fpp_bandwidth_bps,
        fpp_lanes=max_fpp_lanes,
        test_objects=objects + [_instrument(f"sensor_{case_id}", die_ids[-1], f"thermal_{die_ids[-1]}")],
        interconnects=topology["interconnects"],
        thermal_adjacency=topology["thermal_adjacency"],
        provenance_notes=[
            f"ITC'02 {soc.soc_name}.soc provides selected module I/O, scan-chain lengths, and pattern counts.",
            "UCIe/Open3DBench public values motivate link/topology abstractions but do not define IEEE 1838 FPP internals.",
            "IEEE 1838 bit widths, DWR lengths, per-phase power, and thermal proxy parameters are model assumptions.",
        ],
    )
    payload["benchmark_source"] = {
        "milestone": "M10",
        "source": "ITC02_SOC",
        "soc_name": soc.soc_name,
        "scale": spec.scale,
        "selected_module_count": len(modules),
        "selected_module_ids": [module.module_id for module in modules],
    }
    return payload


def select_modules(soc: Itc02Soc, module_count: int) -> tuple[Itc02Module, ...]:
    candidates = [module for module in soc.leaf_modules if module.pattern_count > 0]
    if not candidates:
        raise ValueError(f"{soc.soc_name} has no test-bearing modules")
    ranked = sorted(
        candidates,
        key=lambda module: (module.total_chain_length_bits * module.pattern_count, module.pattern_count, module.module_id),
        reverse=True,
    )
    return tuple(ranked[: min(module_count, len(ranked))])


def write_manifest(rows: list[dict[str, Any]], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "case_id",
        "source_soc",
        "scale",
        "topology_type",
        "die_count",
        "tower_count",
        "selected_module_count",
        "target_count",
        "total_scan_bits",
        "total_patterns",
        "case_path",
    ]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _manifest_row(payload: dict[str, Any], modules: tuple[Itc02Module, ...], output_path: Path) -> dict[str, Any]:
    source = payload["benchmark_source"]
    return {
        "case_id": payload["case_id"],
        "source_soc": source["soc_name"],
        "scale": source["scale"],
        "topology_type": payload["package"]["topology_type"],
        "die_count": payload["package"]["die_count"],
        "tower_count": payload["package"]["tower_count"],
        "selected_module_count": len(modules),
        "target_count": len(payload["test_objects"]) + len(payload["interconnects"]),
        "total_scan_bits": sum(module.total_chain_length_bits for module in modules),
        "total_patterns": sum(module.pattern_count for module in modules),
        "case_path": output_path.as_posix(),
    }


def _topology(topology_type: str, die_count: int) -> dict[str, Any]:
    if topology_type == "3d_stack":
        return _stack_topology(die_count)
    if topology_type == "2_5d_interposer":
        return _interposer_topology(die_count)
    if topology_type == "5_5d_multi_tower":
        even_count = die_count if die_count % 2 == 0 else die_count + 1
        return _multi_tower_topology(even_count)
    raise ValueError(topology_type)


def _stack_topology(die_count: int) -> dict[str, Any]:
    dies = [
        _die(
            f"die{i}",
            "primary" if i == 0 else "secondary",
            "tower0",
            i,
            None if i == 0 else f"die{i - 1}",
            0,
            0,
            45 * i,
            900,
            900,
            0.55 + 0.035 * i,
            0.16,
            max(0.55, 0.95 - 0.035 * i),
        )
        for i in range(die_count)
    ]
    interconnects = [
        _link(
            f"link_die{i}_die{i + 1}",
            f"die{i}",
            f"die{i + 1}",
            "hybrid_bond",
            [f"dwr_die{i}", f"dwr_die{i + 1}"],
            f"hbt_die{i}_die{i + 1}",
            8192 + 1024 * i,
            0.25 + 0.02 * i,
        )
        for i in range(die_count - 1)
    ]
    thermal = [
        _thermal_edge(f"thermal_die{i}", f"thermal_die{i + 1}", "vertical", min(0.90, 0.62 + 0.02 * i))
        for i in range(die_count - 1)
    ]
    return {"tower_count": 1, "dies": dies, "interconnects": interconnects, "thermal_adjacency": thermal}


def _interposer_topology(die_count: int) -> dict[str, Any]:
    columns = max(2, math.ceil(math.sqrt(die_count)))
    dies = []
    for i in range(die_count):
        row, column = divmod(i, columns)
        width = 850 + 50 * (i % 3)
        height = 850 + 40 * (i % 4)
        dies.append(
            _die(
                f"die{i}",
                "primary" if i == 0 else "secondary",
                "interposer0",
                0,
                None if i == 0 else "die0",
                column * 1300,
                row * 1300,
                0,
                width,
                height,
                0.50 + 0.02 * (i % 4),
                0.16,
                0.82,
            )
        )
    interconnects = [
        _link(
            f"link_die0_die{i}",
            "die0",
            f"die{i}",
            "interposer_ucie_like",
            ["dwr_die0", f"dwr_die{i}"],
            f"ucie_adv_die0_die{i}",
            8192 + 512 * i,
            0.22 + 0.01 * i,
        )
        for i in range(1, die_count)
    ]
    thermal = [
        _thermal_edge(f"thermal_die{i}", f"thermal_die{i + 1}", "horizontal", 0.28 + 0.01 * (i % 4))
        for i in range(die_count - 1)
    ]
    return {"tower_count": 1, "dies": dies, "interconnects": interconnects, "thermal_adjacency": thermal}


def _multi_tower_topology(die_count: int) -> dict[str, Any]:
    tower_count = die_count // 2
    dies = []
    for tower in range(tower_count):
        x = (tower % 4) * 1400
        y = (tower // 4) * 1400
        bottom = 2 * tower
        top = bottom + 1
        dies.append(
            _die(
                f"die{bottom}",
                "primary" if bottom == 0 else "secondary",
                f"tower{tower}",
                0,
                None if bottom == 0 else "die0",
                x,
                y,
                0,
                850,
                850,
                0.55,
                0.16,
                0.84,
            )
        )
        dies.append(
            _die(
                f"die{top}",
                "secondary",
                f"tower{tower}",
                1,
                f"die{bottom}",
                x,
                y,
                45,
                800,
                800,
                0.72 + 0.01 * (tower % 3),
                0.15,
                0.94,
            )
        )

    interconnects = []
    thermal = []
    for tower in range(tower_count):
        bottom = 2 * tower
        top = bottom + 1
        interconnects.append(
            _link(
                f"link_tower{tower}_vertical",
                f"die{bottom}",
                f"die{top}",
                "hybrid_bond",
                [f"dwr_die{bottom}", f"dwr_die{top}"],
                f"hbt_tower{tower}",
                8192,
                0.32,
            )
        )
        thermal.append(_thermal_edge(f"thermal_die{bottom}", f"thermal_die{top}", "vertical", 0.72))

    for tower in range(tower_count - 1):
        left = 2 * tower
        right = 2 * (tower + 1)
        interconnects.append(
            _link(
                f"link_tower{tower}_tower{tower + 1}",
                f"die{left}",
                f"die{right}",
                "interposer_ucie_like",
                [f"dwr_die{left}", f"dwr_die{right}"],
                f"ucie_tower{tower}_tower{tower + 1}",
                12288,
                0.38,
            )
        )
        thermal.append(_thermal_edge(f"thermal_die{left}", f"thermal_die{right}", "horizontal", 0.32))
        thermal.append(_thermal_edge(f"thermal_die{left + 1}", f"thermal_die{right + 1}", "horizontal", 0.24))

    return {
        "tower_count": tower_count,
        "dies": dies,
        "interconnects": interconnects,
        "thermal_adjacency": thermal,
    }


if __name__ == "__main__":
    main()
