"""Demonstrate B2 TestIntent to ExecutionPhase expansion."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.access_path import AccessPathGenerator, StackAccessConfig
from src.layered import (
    BISTIntent,
    DWRExTestIntent,
    InstrumentAccessIntent,
    InternalScanIntent,
    LayeredTask,
    LayeredTaskExpander,
)


DEFAULT_RESULT_DIR = ROOT / "results" / "layered_expansion"


def prepare_output_dir(output_dir: Path | str) -> Path:
    """Create and return the output directory, raising a clear error on failure."""

    path = Path(output_dir)
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RuntimeError(f"failed to create output directory '{path}': {exc}") from exc
    return path


def create_demo_config() -> StackAccessConfig:
    """Create a deterministic 4-die stack access config."""

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


def create_demo_intents() -> list:
    """Create representative high-level test intents."""

    return [
        InternalScanIntent(
            intent_id="scan_die3",
            target_die=3,
            target_core="scan_core",
            module_name="die3_scan",
            estimated_power=0.2,
            scan_chain_length=2048,
            pattern_count=4,
            requires_fpp=True,
            fpp_lanes=2,
            shift_power=0.7,
            capture_power=0.95,
            readback_bits=32,
        ),
        BISTIntent(
            intent_id="bist_die2",
            target_die=2,
            target_core="bist_engine",
            module_name="die2_logic",
            estimated_power=0.15,
            bist_id="bist0",
            local_run_time=0.0025,
            trigger_bits=16,
            result_bits=64,
            trigger_power=0.25,
            local_power=0.8,
            readback_power=0.2,
        ),
        DWRExTestIntent(
            intent_id="dwr_extest_die1_die2",
            src_die=1,
            dst_die=2,
            module_name="die1_die2_link",
            estimated_power=0.2,
            dwr_bits=512,
            pattern_count=2,
            shift_power=0.55,
            capture_power=0.9,
            readback_bits=512,
        ),
        InstrumentAccessIntent(
            intent_id="instrument_die0",
            target_die=0,
            module_name="die0_status",
            estimated_power=0.1,
            instrument_id="temp_monitor",
            access_type="read",
            network_depth=3,
            register_bits=32,
            access_power=0.18,
            readback_bits=32,
        ),
    ]


def layered_task_row(task: LayeredTask) -> dict[str, str | int | float | bool | None]:
    """Convert a LayeredTask to a CSV row."""

    phases = task.phases
    return {
        "layered_task_id": task.layered_task_id,
        "parent_intent_id": task.parent_intent.intent_id,
        "intent_type": task.parent_intent.intent_type,
        "target_die": task.parent_intent.target_die,
        "phase_count": len(phases),
        "total_estimated_time": task.total_estimated_time,
        "contains_local_execution": any(phase.is_local_execution for phase in phases),
        "contains_capture_phase": any(phase.is_capture_phase for phase in phases),
        "contains_fpp_phase": any(phase.uses_fpp for phase in phases),
        "contains_dwr_phase": any(phase.uses_dwr for phase in phases),
    }


def execution_phase_row(task: LayeredTask, phase) -> dict[str, str | int | float | bool | None]:
    """Convert an ExecutionPhase to a CSV row."""

    return {
        "phase_id": phase.phase_id,
        "parent_intent_id": phase.parent_intent_id,
        "phase_type": phase.phase_type,
        "target_die": phase.target_die,
        "involved_dies": "|".join(str(die_id) for die_id in phase.involved_dies),
        "duration": phase.duration,
        "power": phase.power,
        "uses_ptap": phase.uses_ptap,
        "uses_fpp": phase.uses_fpp,
        "uses_dwr": phase.uses_dwr,
        "is_local_execution": phase.is_local_execution,
        "is_capture_phase": phase.is_capture_phase,
        "requires_readback": phase.requires_readback,
        "dependencies": "|".join(phase.dependencies),
        "description": phase.description,
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    """Write dictionaries to CSV."""

    if not rows:
        raise ValueError("cannot write empty CSV")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, tasks: list[LayeredTask]) -> None:
    """Write a short Markdown summary of the layered expansion."""

    lines = [
        "# Layered Task Expansion Summary",
        "",
        "This B2 demo expands high-level TestIntent objects into ExecutionPhase sequences.",
        "It is not a complete IEEE 1838 behavior implementation and is not connected to the A0 scheduler.",
        "",
        "## Key Semantics",
        "",
        "- BIST is split into access, trigger, local run, re-access, and readback.",
        "- LOCAL_BIST_RUN does not occupy PTAP, so future schedulers can overlap it with other die access phases.",
        "- Scan is split into config, FPP shift-in, capture, FPP shift-out, and optional readback.",
        "- DWR EXTEST is split into wrapper config, DWR shift-in, capture, and shift-out.",
        "- Instrument access can later be expanded to SIB hierarchical or daisy-chain network timing.",
        "",
        "## Layered Tasks",
        "",
        "| layered_task_id | intent_type | phase_count | total_estimated_time_s |",
        "| --- | --- | ---: | ---: |",
    ]
    for task in tasks:
        lines.append(
            "| "
            f"{task.layered_task_id} | "
            f"{task.parent_intent.intent_type} | "
            f"{len(task.phases)} | "
            f"{task.total_estimated_time:.9g} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(output_dir: Path | str = DEFAULT_RESULT_DIR) -> dict[str, Path]:
    """Run the layered task expansion demo and write summaries."""

    result_dir = prepare_output_dir(output_dir)
    config = create_demo_config()
    expander = LayeredTaskExpander(config, AccessPathGenerator(config))
    tasks = [expander.expand(intent) for intent in create_demo_intents()]

    layered_task_summary = result_dir / "layered_task_summary.csv"
    execution_phase_summary = result_dir / "execution_phase_summary.csv"
    markdown_summary = result_dir / "layered_task_summary.md"

    write_csv(layered_task_summary, [layered_task_row(task) for task in tasks])
    write_csv(
        execution_phase_summary,
        [execution_phase_row(task, phase) for task in tasks for phase in task.phases],
    )
    write_markdown(markdown_summary, tasks)

    return {
        "layered_task_summary": layered_task_summary,
        "execution_phase_summary": execution_phase_summary,
        "layered_task_summary_md": markdown_summary,
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
