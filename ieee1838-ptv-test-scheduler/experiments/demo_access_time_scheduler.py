"""Demonstrate B3.1 ExecutionPhase-level access-time-aware scheduling."""

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
    AccessTimeAwareScheduler,
    BISTIntent,
    DWRExTestIntent,
    ExecutionPhase,
    InstrumentAccessIntent,
    InternalScanIntent,
    LayeredTask,
    LayeredTaskExpander,
    ScheduledPhase,
)


DEFAULT_RESULT_DIR = ROOT / "results" / "access_time_scheduler"


def prepare_output_dir(output_dir: Path | str) -> Path:
    """Create and return the output directory, raising a clear error on failure."""

    path = Path(output_dir)
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RuntimeError(f"failed to create output directory '{path}': {exc}") from exc
    return path


def create_demo_config() -> StackAccessConfig:
    """Create a deterministic 4-die access-time scheduler demo configuration."""

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
    """Create a small mixed workload for phase-level scheduling."""

    return [
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


def expand_demo_phases(config: StackAccessConfig) -> list[ExecutionPhase]:
    """Expand demo intents into a flat phase list."""

    expander = LayeredTaskExpander(config, AccessPathGenerator(config))
    tasks: list[LayeredTask] = [expander.expand(intent) for intent in create_demo_intents()]
    return [phase for task in tasks for phase in task.phases]


def resource_summary(phase: ExecutionPhase) -> str:
    """Return a compact resource summary for one phase."""

    resources: list[str] = []
    if phase.uses_ptap:
        resources.append("PTAP")
    if phase.uses_fpp:
        resources.append(f"FPP[{phase.fpp_lanes or 1}]")
    if phase.uses_dwr:
        resources.append(f"DWR:{phase.dwr_segment or 'GLOBAL'}")
    if phase.is_capture_phase:
        resources.append("CAPTURE")
    if phase.is_local_execution:
        resources.append("LOCAL")
    return ",".join(resources) if resources else "-"


def schedule_row(item: ScheduledPhase) -> dict[str, str | int | float | bool | None]:
    """Convert one scheduled phase into a CSV row."""

    phase = item.phase
    return {
        "phase_id": phase.phase_id,
        "parent_intent_id": phase.parent_intent_id,
        "phase_type": phase.phase_type,
        "start_time": item.start_time,
        "end_time": item.end_time,
        "duration": phase.duration,
        "target_die": phase.target_die,
        "uses_ptap": phase.uses_ptap,
        "uses_fpp": phase.uses_fpp,
        "fpp_lanes": phase.fpp_lanes,
        "uses_dwr": phase.uses_dwr,
        "dwr_segment": phase.dwr_segment or "",
        "is_capture_phase": phase.is_capture_phase,
        "is_local_execution": phase.is_local_execution,
        "dependencies": "|".join(phase.dependencies),
        "resources": resource_summary(phase),
        "description": phase.description,
    }


def write_csv(path: Path, rows: list[dict[str, str | int | float | bool | None]]) -> None:
    """Write scheduled phase rows to CSV."""

    if not rows:
        raise ValueError("cannot write empty access-time schedule")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, scheduled_phases: list[ScheduledPhase], total_time: float) -> None:
    """Write a short Markdown summary for the phase-level schedule."""

    lines = [
        "# Access-Time-Aware Phase Schedule",
        "",
        "This B3.1 demo schedules ExecutionPhase objects produced by the B2 layered expander.",
        "It is a first phase-level scheduler prototype, not predictive PTV scheduling and not a full IEEE 1838 implementation.",
        "",
        f"- total_time_s: {total_time:.9g}",
        f"- scheduled_phase_count: {len(scheduled_phases)}",
        "",
        "| start_s | end_s | phase_id | phase_type | resources |",
        "| ---: | ---: | --- | --- | --- |",
    ]
    for item in scheduled_phases:
        lines.append(
            "| "
            f"{item.start_time:.9g} | "
            f"{item.end_time:.9g} | "
            f"{item.phase.phase_id} | "
            f"{item.phase.phase_type} | "
            f"{resource_summary(item.phase)} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_schedule_table(scheduled_phases: list[ScheduledPhase]) -> None:
    """Print a compact phase schedule table."""

    print(f"{'start_s':>12} {'end_s':>12} {'phase_type':<22} {'phase_id':<42} resources")
    for item in scheduled_phases:
        print(
            f"{item.start_time:12.9g} "
            f"{item.end_time:12.9g} "
            f"{item.phase.phase_type:<22} "
            f"{item.phase.phase_id:<42} "
            f"{resource_summary(item.phase)}"
        )


def run(output_dir: Path | str = DEFAULT_RESULT_DIR) -> dict[str, Path]:
    """Run the access-time-aware scheduler demo and write summaries."""

    result_dir = prepare_output_dir(output_dir)
    config = create_demo_config()
    phases = expand_demo_phases(config)
    scheduler = AccessTimeAwareScheduler(total_fpp_lanes=config.fpp_lane_count)
    result = scheduler.schedule(phases)

    csv_path = result_dir / "phase_schedule.csv"
    markdown_path = result_dir / "phase_schedule.md"
    write_csv(csv_path, [schedule_row(item) for item in result.scheduled_phases])
    write_markdown(markdown_path, result.scheduled_phases, result.total_time)
    print_schedule_table(result.scheduled_phases)

    return {
        "phase_schedule_csv": csv_path,
        "phase_schedule_md": markdown_path,
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
