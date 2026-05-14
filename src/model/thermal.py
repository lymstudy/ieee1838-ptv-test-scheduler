"""Discrete RC-style thermal model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ThermalConfig:
    """Parameters for a first-order RC thermal approximation."""

    ambient_temp_c: float
    thermal_resistance_c_per_w: float
    thermal_capacitance_j_per_c: float
    max_temp_c: float

    def __post_init__(self) -> None:
        if self.thermal_resistance_c_per_w <= 0:
            raise ValueError("thermal_resistance_c_per_w must be positive")
        if self.thermal_capacitance_j_per_c <= 0:
            raise ValueError("thermal_capacitance_j_per_c must be positive")
        if self.max_temp_c <= self.ambient_temp_c:
            raise ValueError("max_temp_c must exceed ambient_temp_c")

    @classmethod
    def from_config(cls, data: dict) -> "ThermalConfig":
        """Build thermal parameters from a config mapping."""

        return cls(**data)


@dataclass(frozen=True)
class TemperatureState:
    """Per-die temperatures in degrees Celsius."""

    by_die_id: dict[int, float]

    def peak_temp_c(self) -> float:
        """Return the peak temperature across all dies."""

        if not self.by_die_id:
            raise ValueError("temperature state must not be empty")
        return max(self.by_die_id.values())


class RCThermalModel:
    """A simple per-die first-order RC temperature update."""

    def __init__(self, config: ThermalConfig) -> None:
        self.config = config

    def step(
        self,
        state: TemperatureState,
        power_by_die_w: dict[int, float],
        time_step_s: float,
    ) -> TemperatureState:
        """Advance temperatures by one time step using explicit Euler update."""

        if time_step_s <= 0:
            raise ValueError("time_step_s must be positive")

        next_temps: dict[int, float] = {}
        resistance = self.config.thermal_resistance_c_per_w
        capacitance = self.config.thermal_capacitance_j_per_c
        ambient = self.config.ambient_temp_c

        for die_id, temp_c in state.by_die_id.items():
            power_w = power_by_die_w.get(die_id, 0.0)
            if power_w < 0:
                raise ValueError("die power must be non-negative")
            cooling_w = (temp_c - ambient) / resistance
            delta_c = (power_w - cooling_w) * time_step_s / capacitance
            next_temps[die_id] = temp_c + delta_c

        return TemperatureState(next_temps)

    def violates_limit(self, state: TemperatureState) -> bool:
        """Return true when the state exceeds the configured thermal limit."""

        return state.peak_temp_c() > self.config.max_temp_c
