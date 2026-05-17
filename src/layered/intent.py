"""High-level test intent data models for B2 layered expansion."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, kw_only=True)
class BaseTestIntent:
    """High-level description of what should be tested."""

    intent_id: str
    intent_type: str = field(default="base", init=False)
    target_die: int | None = None
    target_core: str | None = None
    module_name: str | None = None
    estimated_power: float = 0.0
    dependencies: tuple[str, ...] = field(default_factory=tuple)
    notes: str = ""


@dataclass(frozen=True, kw_only=True)
class InternalScanIntent(BaseTestIntent):
    """Intent for internal scan shift/capture/readback on one die."""

    intent_type: str = field(default="internal_scan", init=False)
    scan_chain_length: int
    pattern_count: int = 1
    requires_fpp: bool = True
    fpp_lanes: int = 1
    shift_power: float = 0.0
    capture_power: float = 0.0
    readback_bits: int = 0


@dataclass(frozen=True, kw_only=True)
class BISTIntent(BaseTestIntent):
    """Intent for local BIST trigger, execution, and result readback."""

    intent_type: str = field(default="bist", init=False)
    bist_id: str
    local_run_time: float
    trigger_bits: int
    result_bits: int
    trigger_power: float = 0.0
    local_power: float = 0.0
    readback_power: float = 0.0


@dataclass(frozen=True, kw_only=True)
class DWRExTestIntent(BaseTestIntent):
    """Intent for Die Wrapper Register EXTEST between adjacent dies."""

    intent_type: str = field(default="dwr_extest", init=False)
    src_die: int
    dst_die: int
    dwr_bits: int
    pattern_count: int = 1
    shift_power: float = 0.0
    capture_power: float = 0.0
    readback_bits: int = 0


@dataclass(frozen=True, kw_only=True)
class InstrumentAccessIntent(BaseTestIntent):
    """Intent for abstract instrument register read or write access."""

    intent_type: str = field(default="instrument_access", init=False)
    instrument_id: str
    access_type: str
    network_depth: int
    register_bits: int
    access_power: float = 0.0
    readback_bits: int = 0


@dataclass(frozen=True, kw_only=True)
class BypassIntent(BaseTestIntent):
    """Intent for configuring a die bypass path."""

    intent_type: str = field(default="bypass", init=False)
    bypassed_die: int
    bypass_bits: int
