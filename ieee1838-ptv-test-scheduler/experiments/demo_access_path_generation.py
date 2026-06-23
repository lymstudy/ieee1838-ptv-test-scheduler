"""Demonstrate B1 AccessPath generation and timing estimates."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.access_path import AccessPath, AccessPathGenerator, StackAccessConfig


DEFAULT_RESULT_DIR = ROOT / "results" / "access_path"


def prepare_output_dir(output_dir: Path | str) -> Path:
    """Create and return the output directory, raising a clear error on failure."""

    path = Path(output_dir)
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RuntimeError(f"failed to create output directory '{path}': {exc}") from exc
    return path


def create_demo_config() -> StackAccessConfig:
    """Create a deterministic 4-die access-path demo configuration."""

    return StackAccessConfig(
        die_count=4,
        first_die_id=0,
        tck_frequency_hz=50_000_000.0,
        ptap_instruction_bits=8,
        stap_select_bits_per_die=4,
        three_dcr_bits_per_die=8,
        dwr_config_bits_per_die=16,
        bypass_bits_per_die=1,
        fpp_config_bits=16,
        fpp_lane_count=2,
        fpp_bandwidth_bits_per_s=1_000_000_000.0,
        default_readback_bits=32,
    )


def path_to_row(path: AccessPath) -> dict[str, str | int | float]:
    """Convert an AccessPath into a CSV row."""

    return {
        "path_id": path.path_id,
        "target_die": path.target_die,
        "path_dies": "|".join(str(die_id) for die_id in path.path_dies),
        "selected_staps": "|".join(str(die_id) for die_id in path.selected_staps),
        "required_3dcr_bits": path.required_3dcr_bits,
        "access_bit_length": path.access_bit_length,
        "estimated_access_time": path.estimated_access_time,
        "operation_count": len(path.operations),
        "occupied_resource_count": len(path.occupied_resources),
        "notes": path.notes,
    }


def write_csv(path: Path, rows: list[dict[str, str | int | float]]) -> None:
    """Write access-path summary rows."""

    if not rows:
        raise ValueError("cannot write empty access path summary")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, paths: list[AccessPath]) -> None:
    """Write a short Markdown summary for the generated paths."""

    basic_paths = [item for item in paths if item.path_id.startswith("basic")]
    lines = [
        "# Access Path Summary",
        "",
        "This B1 demo uses an abstract IEEE 1838-compatible access-path estimator.",
        "It is not a bit-accurate implementation of the IEEE 1838 standard.",
        "",
        "## Observations",
        "",
        "- Deeper die access overhead increases because more STAP/3DCR path configuration bits are required.",
        "- DWR access adds wrapper configuration, shift, and readback overhead.",
        "- FPP data path reduces bulk data transfer time but still requires PTAP/STAP/FPP configuration.",
        "",
        "## Generated Paths",
        "",
        "| path_id | target_die | path_dies | estimated_access_time_s | operations |",
        "| --- | ---: | --- | ---: | ---: |",
    ]
    for access_path in paths:
        lines.append(
            "| "
            f"{access_path.path_id} | "
            f"{access_path.target_die} | "
            f"{'->'.join(str(die_id) for die_id in access_path.path_dies)} | "
            f"{access_path.estimated_access_time:.9g} | "
            f"{len(access_path.operations)} |"
        )
    if basic_paths:
        lines.extend(
            [
                "",
                "## Basic Path Depth Check",
                "",
                f"- die0 estimated access time: {basic_paths[0].estimated_access_time:.9g} s",
                f"- die3 estimated access time: {basic_paths[-1].estimated_access_time:.9g} s",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(output_dir: Path | str = DEFAULT_RESULT_DIR) -> dict[str, Path]:
    """Generate the access-path demo outputs."""

    result_dir = prepare_output_dir(output_dir)
    generator = AccessPathGenerator(create_demo_config())
    paths = [generator.generate_path_to_die(die_id) for die_id in range(4)]
    paths.append(generator.generate_dwr_access_path(target_die=3, dwr_bits=512))
    paths.append(generator.generate_fpp_data_path(target_die=3, data_bits=8192, lanes=2))

    csv_path = result_dir / "access_path_summary.csv"
    markdown_path = result_dir / "access_path_summary.md"
    write_csv(csv_path, [path_to_row(path) for path in paths])
    write_markdown(markdown_path, paths)

    return {
        "access_path_summary_csv": csv_path,
        "access_path_summary_md": markdown_path,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_RESULT_DIR,
        help=f"directory for demo outputs (default: {DEFAULT_RESULT_DIR})",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Run the demo from the command line."""

    args = parse_args(argv)
    outputs = run(args.output_dir)
    for output_path in outputs.values():
        print(output_path)


if __name__ == "__main__":
    main()
