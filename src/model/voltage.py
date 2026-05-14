"""Equivalent PDN resistance and IR drop model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VoltageConfig:
    """Parameters for a simple IR-drop approximation."""

    nominal_voltage_v: float
    pdn_resistance_ohm: float
    max_ir_drop_v: float

    def __post_init__(self) -> None:
        if self.nominal_voltage_v <= 0:
            raise ValueError("nominal_voltage_v must be positive")
        if self.pdn_resistance_ohm < 0:
            raise ValueError("pdn_resistance_ohm must be non-negative")
        if self.max_ir_drop_v < 0:
            raise ValueError("max_ir_drop_v must be non-negative")

    @classmethod
    def from_config(cls, data: dict) -> "VoltageConfig":
        """Build voltage parameters from a config mapping."""

        return cls(**data)


@dataclass(frozen=True)
class VoltageState:
    """IR-drop state in volts."""

    ir_drop_by_die_v: dict[int, float]

    def peak_ir_drop_v(self) -> float:
        """Return the peak IR drop across all dies."""

        if not self.ir_drop_by_die_v:
            raise ValueError("voltage state must not be empty")
        return max(self.ir_drop_by_die_v.values())


class EquivalentPdnModel:
    """Estimate IR drop from die power and equivalent PDN resistance."""

    def __init__(self, config: VoltageConfig) -> None:
        self.config = config

    def estimate(self, power_by_die_w: dict[int, float]) -> VoltageState:
        """Estimate per-die IR drop from power values."""

        drops: dict[int, float] = {}
        for die_id, power_w in power_by_die_w.items():
            if power_w < 0:
                raise ValueError("die power must be non-negative")
            current_a = power_w / self.config.nominal_voltage_v
            drops[die_id] = current_a * self.config.pdn_resistance_ohm
        return VoltageState(drops)

    def violates_limit(self, state: VoltageState) -> bool:
        """Return true when the state exceeds the configured IR-drop limit."""

        return state.peak_ir_drop_v() > self.config.max_ir_drop_v
