"""Data model for IEEE 1838 chiplet test scheduling.

All types are plain dataclasses.  No scheduling logic lives here.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ── Chiplet / Stack (topology) ──────────────────────────────────────────────

@dataclass
class Chiplet:
    """A single die within a chiplet stack."""
    chiplet_id: str
    stack_id: str
    layer_index: int           # 0 = closest to heat sink
    die_type: str              # "memory" | "logic" | "large_logic" | "io"
    # derived from ITC'02 module
    chain_count: int
    max_chain_length_bits: int
    total_chain_length_bits: int
    pattern_count: int
    # power
    shift_power_w: float
    capture_power_w: float
    access_power_w: float
    bist_power_w: float        # 0.0 if no BIST
    # FPP capability
    has_fpp: bool
    fpp_lanes: int             # 0 if !has_fpp
    # thermal
    thermal_resistance_c_per_w: float
    thermal_capacitance_j_per_c: float

    @property
    def total_test_bits(self) -> int:
        return self.total_chain_length_bits * max(self.pattern_count, 1)


@dataclass
class Stack:
    """A vertical stack of chiplets with shared thermal coupling."""
    stack_id: str
    topology: str              # "2.5D" | "3D" | "5.5D"
    chiplets: list[Chiplet]    # bottom→top (layer 0 first)


# ── Task / Phase ────────────────────────────────────────────────────────────

@dataclass
class TaskPhase:
    """One phase of a test task.

    MBIST:   CONFIG(needs_tap) → EXECUTE(needs_bist_engine, releases TAP)
             → READOUT(needs_tap)
    scan:    CONFIG(needs_tap) → SHIFT(needs_tap or FPP) → CAPTURE(needs_tap)
    LBIST:   same as MBIST
    INTEST:  CONFIG(needs_tap) → SHIFT(needs_tap or FPP)
    EXTEST:  CONFIG(needs_tap) → SHIFT(needs_tap or FPP)
    """
    phase_index: int
    phase_name: str            # CONFIG | SHIFT | CAPTURE | EXECUTE | READOUT
    duration_s: float
    power_w: float
    needs_tap: bool
    needs_fpp_lanes: int       # 0 = TAP-only
    needs_bist_engine: bool
    fpp_channel_id: str = ""   # which FPP channel (for multi-channel cases)


@dataclass
class Task:
    """A single test task to be scheduled."""
    task_id: str
    chiplet_id: str
    stack_id: str
    task_type: str             # MBIST | scan | LBIST | INTEST | EXTEST
    phases: list[TaskPhase]


# ── Case ────────────────────────────────────────────────────────────────────

@dataclass
class Case:
    """Complete test case: one topology, its chiplets, and their tasks."""
    case_id: str
    topology: str              # "2.5D" | "3D" | "5.5D"
    stacks: list[Stack]
    chiplets: list[Chiplet]
    tasks: list[Task]
    # global resource limits
    total_fpp_lanes: int
    max_power_w: float
    max_temperature_c: float
    ambient_temperature_c: float
    # timing
    ptap_tck_hz: float
    fpp_lane_bandwidth_bps: float
    bist_clock_hz: float = 100e6

    @property
    def cfg_bit_time_s(self) -> float:
        """Typical config register access time (64-bit control word)."""
        return 64.0 / self.ptap_tck_hz


# ── Schedule output ─────────────────────────────────────────────────────────

@dataclass
class ScheduledPhase:
    """A committed phase in the final schedule."""
    task_id: str
    chiplet_id: str
    stack_id: str
    task_type: str
    phase_index: int
    phase_name: str
    start_s: float
    end_s: float
    duration_s: float
    needs_tap: bool
    needs_fpp_lanes: int
    needs_bist_engine: bool
    power_w: float


@dataclass
class ScheduleResult:
    """Output of a scheduling run."""
    case_id: str
    method: str                # "greedy" | "pure_serial"
    phases: list[ScheduledPhase] = field(default_factory=list)
    makespan_s: float = 0.0
    peak_power_w: float = 0.0


# ── Helper ──────────────────────────────────────────────────────────────────

def phase_duration_s(bits: int, clock_hz: float) -> float:
    """Bits shifted at given clock rate."""
    if clock_hz <= 0:
        return 0.0
    return bits / clock_hz


def fpp_phase_duration_s(bits: int, bandwidth_bps: float) -> float:
    """Bits transferred over FPP at given bandwidth."""
    if bandwidth_bps <= 0:
        return float("inf")
    return bits / bandwidth_bps
