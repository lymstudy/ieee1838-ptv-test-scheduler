"""Pipeline entry point for IEEE 1838 test access scheduling.

Wires together benchmark case generation, greedy scheduling,
pure-serial baseline scheduling, thermal simulation, and
visualisation outputs.

Usage
-----
    cd TESTSCHEDULE
    python main.py
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

from model import Case, ScheduleResult
from benchmark import generate_case
from scheduler import greedy_schedule, pure_serial_schedule, StackThermalSimulator
from visualize import (
    configure_matplotlib,
    plot_power_time,
    plot_temperature_time,
    plot_gantt,
    plot_comparison,
    write_schedule_csv,
)

# ═══════════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════════

CONFIGS_DIR = Path(__file__).resolve().parent / "configs"
RESULTS_DIR = Path(__file__).resolve().parent / "results"
SECTION_WIDTH = 72


def _header(text: str) -> None:
    """Print a section header."""
    print()
    print("=" * SECTION_WIDTH)
    print(f"  {text}")
    print("=" * SECTION_WIDTH)


def _subheader(text: str) -> None:
    """Print a sub-section header."""
    print(f"\n{'─' * SECTION_WIDTH}")
    print(f"  {text}")
    print(f"{'─' * SECTION_WIDTH}")


# ═══════════════════════════════════════════════════════════════════════════════
# Single-case runner
# ═══════════════════════════════════════════════════════════════════════════════

def run_case(config_path: str, results_dir: str) -> dict | None:
    """Run a single case end-to-end: generate, schedule, save outputs.

    Parameters
    ----------
    config_path : str
        Path to a JSON case-configuration file.
    results_dir : str
        Directory in which to write output files.

    Returns
    -------
    dict or None
        ``{'case_label': str, 'greedy': ScheduleResult, 'serial': ScheduleResult,
           'thermal_traces': dict, 'case': Case, 'topology': str,
           'n_chiplets': int, 'n_tasks': int}``
        or ``None`` if the case could not be run.
    """
    config_path = Path(config_path)
    results_dir = Path(results_dir)

    try:
        # ── 1. Generate case ────────────────────────────────────────────
        case = generate_case(str(config_path))

        n_chiplets = len(case.chiplets)
        n_tasks = len(case.tasks)
        case_label = case.case_id

        print(f"\n  Case:   {case_label}")
        print(f"  Topo:   {case.topology}  |  Chiplets: {n_chiplets}  |  Tasks: {n_tasks}")

        # ── 2. Greedy schedule (with thermal traces) ────────────────────
        greedy_result, thermal_traces = greedy_schedule(case)
        print(f"  Greedy makespan: {greedy_result.makespan_s * 1e6:,.2f} μs"
              f"  |  peak power: {greedy_result.peak_power_w:.2f} W")

        # ── 3. Pure serial schedule ─────────────────────────────────────
        serial_result, _ = pure_serial_schedule(case)
        speedup = serial_result.makespan_s / greedy_result.makespan_s if greedy_result.makespan_s > 0 else float("inf")
        print(f"  Serial makespan: {serial_result.makespan_s * 1e6:,.2f} μs"
              f"  |  speedup: {speedup:.1f}x")

        # ── 4. Write schedule CSV ───────────────────────────────────────
        csv_path = results_dir / f"{case_label}_greedy_schedule.csv"
        write_schedule_csv(greedy_result, str(csv_path))
        print(f"  Saved: {csv_path.name}")

        # ── 5. Power-time plot ──────────────────────────────────────────
        pt_path = results_dir / f"{case_label}_greedy_power.png"
        plot_power_time(greedy_result, str(pt_path), case.max_power_w)
        print(f"  Saved: {pt_path.name}")

        # ── 6. Temperature-time plot ────────────────────────────────────
        if thermal_traces:
            tt_path = results_dir / f"{case_label}_greedy_temperature.png"
            plot_temperature_time(
                thermal_traces,
                case_label,
                case.max_temperature_c,
                str(tt_path),
            )
            print(f"  Saved: {tt_path.name}")
        else:
            print("  (no thermal traces — skipping T-t plot)")

        # ── 7. Gantt chart ──────────────────────────────────────────────
        gantt_path = results_dir / f"{case_label}_greedy_gantt.png"
        plot_gantt(greedy_result, str(gantt_path))
        print(f"  Saved: {gantt_path.name}")

        return {
            "case_label": case_label,
            "greedy": greedy_result,
            "serial": serial_result,
            "thermal_traces": thermal_traces,
            "case": case,
            "topology": case.topology,
            "n_chiplets": n_chiplets,
            "n_tasks": n_tasks,
        }

    except Exception:
        print(f"\n  ERROR running case {config_path.name}:", file=sys.stderr)
        traceback.print_exc()
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# Summary table
# ═══════════════════════════════════════════════════════════════════════════════

def _print_summary_table(results: list[dict]) -> None:
    """Print a markdown-format summary table of all cases."""
    _header("Summary")

    header_fmt = (
        "| {case:<30s} | {topo:<8s} | {chiplets:>8s} | {tasks:>5s} | "
        "{greedy:>13s} | {serial:>13s} | {speedup:>7s} |"
    )
    sep = (
        "|" + "-" * 32 + "|" + "-" * 10 + "|" + "-" * 10 + "|" + "-" * 7 + "|"
        + "-" * 15 + "|" + "-" * 15 + "|" + "-" * 9 + "|"
    )

    print()
    print(header_fmt.format(
        case="Case", topo="Topology", chiplets="Chiplets",
        tasks="Tasks", greedy="Greedy (μs)", serial="Serial (μs)",
        speedup="Speedup",
    ))
    print(sep)

    for r in results:
        g_us = r["greedy"].makespan_s * 1e6
        s_us = r["serial"].makespan_s * 1e6
        sp = s_us / g_us if g_us > 0 else float("inf")
        print(header_fmt.format(
            case=r["case_label"][:30],
            topo=r["topology"],
            chiplets=str(r["n_chiplets"]),
            tasks=str(r["n_tasks"]),
            greedy=f"{g_us:,.2f}",
            serial=f"{s_us:,.2f}",
            speedup=f"{sp:.1f}x",
        ))

    print()


# ═══════════════════════════════════════════════════════════════════════════════
# Main pipeline
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    """Run the complete scheduling pipeline.

    1. Find all config JSONs in ``configs/`` directory.
    2. For each config:
       a. Generate Case via ``benchmark.generate_case()``.
       b. Print case summary (case_id, topology, N chiplets, N tasks).
       c. Run ``greedy_schedule(case)`` — also get thermal traces.
       d. Run ``pure_serial_schedule(case)``.
       e. Print comparison: greedy makespan, serial makespan, speedup.
       f. Save schedule CSV for greedy result to ``results/``.
       g. Generate P-t plot for greedy result → ``results/``.
       h. Generate T-t plot for greedy thermal traces → ``results/``.
       i. Generate Gantt chart for greedy result → ``results/``.
    3. Generate cross-case comparison bar chart → ``results/``.
    4. Print final summary table.
    """
    # ── Setup ──────────────────────────────────────────────────────────
    configure_matplotlib()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # ── Discover configs ───────────────────────────────────────────────
    config_files = sorted(CONFIGS_DIR.glob("*.json"))
    if not config_files:
        print(f"No JSON config files found in {CONFIGS_DIR}", file=sys.stderr)
        sys.exit(1)

    _header("IEEE 1838 Test Access Scheduling Pipeline")
    print(f"\n  Config dir : {CONFIGS_DIR}")
    print(f"  Results dir: {RESULTS_DIR}")
    print(f"  Configs found: {len(config_files)}")

    # ── Run each case ──────────────────────────────────────────────────
    success_results: list[dict] = []  # for comparison + summary

    for i, config_path in enumerate(config_files, start=1):
        _subheader(f"[{i}/{len(config_files)}] {config_path.name}")

        result = run_case(str(config_path), str(RESULTS_DIR))
        if result is not None:
            success_results.append(result)

    # ── Cross-case comparison chart ────────────────────────────────────
    if len(success_results) >= 2:
        _header("Cross-Case Comparison")

        comparison_data: list[tuple[str, ScheduleResult, ScheduleResult]] = [
            (r["case_label"], r["greedy"], r["serial"])
            for r in success_results
        ]
        comp_path = RESULTS_DIR / "comparison_speedup.png"
        plot_comparison(comparison_data, str(comp_path))
        print(f"\n  Saved: {comp_path.name}")

    elif len(success_results) == 1:
        print("\n  Only one case succeeded — skipping comparison chart.")

    # ── Summary table ──────────────────────────────────────────────────
    if success_results:
        _print_summary_table(success_results)

    # ── Done ───────────────────────────────────────────────────────────
    n_failed = len(config_files) - len(success_results)
    print(f"  Successful: {len(success_results)}  |  Failed: {n_failed}")
    print(f"\n{' Done. Results in '}{RESULTS_DIR}{' '}")
    print()


# ═══════════════════════════════════════════════════════════════════════════════
# Direct invocation
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    main()
