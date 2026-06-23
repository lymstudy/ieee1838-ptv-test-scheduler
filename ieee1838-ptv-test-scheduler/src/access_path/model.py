"""Data models for abstract IEEE 1838-compatible access paths.

These models describe B1 access-path estimation objects. They are not a
bit-accurate implementation of the IEEE 1838 standard.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class StackAccessConfig:
    """Configuration knobs used by the MVP access-path timing estimator."""

    die_count: int
    first_die_id: int = 0
    tck_frequency_hz: float = 50_000_000.0
    ptap_instruction_bits: int = 8
    stap_select_bits_per_die: int = 4
    three_dcr_bits_per_die: int = 8
    dwr_config_bits_per_die: int = 16
    bypass_bits_per_die: int = 1
    fpp_config_bits: int = 16
    fpp_lane_count: int = 2
    fpp_bandwidth_bits_per_s: float = 1_000_000_000.0
    default_readback_bits: int = 32

    def __post_init__(self) -> None:
        """Validate basic timing and stack dimensions."""

        if self.die_count <= 0:
            raise ValueError("die_count must be positive")
        if not 0 <= self.first_die_id < self.die_count:
            raise ValueError("first_die_id must be within the stack")
        if self.tck_frequency_hz <= 0:
            raise ValueError("tck_frequency_hz must be positive")
        if self.fpp_bandwidth_bits_per_s <= 0:
            raise ValueError("fpp_bandwidth_bits_per_s must be positive")
        if self.fpp_lane_count < 0:
            raise ValueError("fpp_lane_count cannot be negative")


@dataclass(frozen=True)
class AccessResource:
    """A resource occupied by an access path or operation."""

    resource_type: str
    resource_id: str
    die_id: int | None
    exclusive: bool
    description: str = ""


@dataclass(frozen=True)
class AccessOperation:
    """An access-level operation with bit length, time, and resources."""

    op_id: str
    op_type: str
    target_die: int
    involved_dies: tuple[int, ...]
    bit_length: int
    estimated_time: float
    occupied_resources: tuple[AccessResource, ...] = field(default_factory=tuple)
    description: str = ""


@dataclass(frozen=True)
class AccessPath:
    """Generated abstract path to a target die or data path."""

    path_id: str
    target_die: int
    path_dies: tuple[int, ...]
    selected_staps: tuple[int, ...]
    bypassed_dies: tuple[int, ...]
    required_3dcr_bits: int
    required_dwr_segments: tuple[str, ...]
    required_fpp_lanes: int
    access_bit_length: int
    estimated_access_time: float
    operations: tuple[AccessOperation, ...] = field(default_factory=tuple)
    occupied_resources: tuple[AccessResource, ...] = field(default_factory=tuple)
    notes: str = ""
