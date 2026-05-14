"""3D die stack model objects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Die:
    """A die in a 3D stack."""

    id: int
    name: str
    layer_index: int
    area_mm2: float
    initial_temp_c: float
    nominal_power_w: float

    def __post_init__(self) -> None:
        if self.id < 0:
            raise ValueError("die id must be non-negative")
        if self.layer_index < 0:
            raise ValueError("layer_index must be non-negative")
        if self.area_mm2 <= 0:
            raise ValueError("area_mm2 must be positive")
        if self.nominal_power_w < 0:
            raise ValueError("nominal_power_w must be non-negative")


@dataclass(frozen=True)
class DieStack:
    """An ordered collection of dies in a vertical stack."""

    dies: tuple[Die, ...]

    def __post_init__(self) -> None:
        if not self.dies:
            raise ValueError("die stack must contain at least one die")
        ids = [die.id for die in self.dies]
        if len(ids) != len(set(ids)):
            raise ValueError("die ids must be unique")
        layers = [die.layer_index for die in self.dies]
        if len(layers) != len(set(layers)):
            raise ValueError("die layer indices must be unique")

    @classmethod
    def from_config(cls, data: dict) -> "DieStack":
        """Build a die stack from a config mapping."""

        dies = tuple(Die(**item) for item in data["dies"])
        return cls(tuple(sorted(dies, key=lambda die: die.layer_index)))

    def get_die(self, die_id: int) -> Die:
        """Return a die by id."""

        for die in self.dies:
            if die.id == die_id:
                return die
        raise KeyError(f"unknown die id: {die_id}")

    def die_ids(self) -> tuple[int, ...]:
        """Return die identifiers in stack order."""

        return tuple(die.id for die in self.dies)

    def total_nominal_power_w(self) -> float:
        """Return total nominal stack power in watts."""

        return sum(die.nominal_power_w for die in self.dies)


def build_stack(die_entries: Iterable[dict]) -> DieStack:
    """Build a die stack from iterable die config entries."""

    return DieStack(tuple(sorted((Die(**entry) for entry in die_entries), key=lambda die: die.layer_index)))
