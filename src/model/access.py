"""IEEE 1838-style access resource model objects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class DwrSegment:
    """A Die Wrapper Register segment associated with one die."""

    die_id: int
    name: str
    length_bits: int

    def __post_init__(self) -> None:
        if self.die_id < 0:
            raise ValueError("die_id must be non-negative")
        if not self.name:
            raise ValueError("DWR segment name must be non-empty")
        if self.length_bits <= 0:
            raise ValueError("DWR segment length_bits must be positive")


@dataclass(frozen=True)
class FppConfig:
    """Optional Flexible Parallel Port lane configuration."""

    enabled: bool
    lanes: int
    lane_width_bits: int

    def __post_init__(self) -> None:
        if self.lanes < 0:
            raise ValueError("FPP lanes must be non-negative")
        if self.lane_width_bits <= 0:
            raise ValueError("FPP lane_width_bits must be positive")
        if not self.enabled and self.lanes != 0:
            raise ValueError("disabled FPP must use zero lanes")

    @property
    def total_width_bits(self) -> int:
        """Return total active FPP width in bits."""

        if not self.enabled:
            return 0
        return self.lanes * self.lane_width_bits


@dataclass(frozen=True)
class AccessConfig:
    """PTAP, STAP, DWR, and optional FPP access resources."""

    ptap_width_bits: int
    stap_count: int
    dwr_segments: tuple[DwrSegment, ...]
    fpp: FppConfig

    def __post_init__(self) -> None:
        if self.ptap_width_bits <= 0:
            raise ValueError("ptap_width_bits must be positive")
        if self.stap_count <= 0:
            raise ValueError("stap_count must be positive")
        die_ids = [segment.die_id for segment in self.dwr_segments]
        if len(die_ids) != len(set(die_ids)):
            raise ValueError("only one DWR segment per die is supported in the scaffold")

    @classmethod
    def from_config(cls, data: dict) -> "AccessConfig":
        """Build access resources from a config mapping."""

        fpp_enabled = bool(data.get("fpp_enabled", False))
        fpp_lanes = int(data.get("fpp_lanes", 0))
        fpp = FppConfig(
            enabled=fpp_enabled,
            lanes=fpp_lanes if fpp_enabled else 0,
            lane_width_bits=int(data.get("fpp_lane_width_bits", 1)),
        )
        return cls(
            ptap_width_bits=int(data["ptap_width_bits"]),
            stap_count=int(data["stap_count"]),
            dwr_segments=build_dwr_segments(data.get("dwr_segments", ())),
            fpp=fpp,
        )

    def dwr_for_die(self, die_id: int) -> DwrSegment:
        """Return the DWR segment associated with a die id."""

        for segment in self.dwr_segments:
            if segment.die_id == die_id:
                return segment
        raise KeyError(f"no DWR segment for die id: {die_id}")


def build_dwr_segments(entries: Iterable[dict]) -> tuple[DwrSegment, ...]:
    """Build DWR segments from iterable config entries."""

    return tuple(DwrSegment(**entry) for entry in entries)
