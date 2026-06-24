from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


class ModelValidationError(ValueError):
    """Raised when an M1 system model is internally inconsistent."""


def _require_positive(value: float, field_name: str) -> None:
    if value <= 0:
        raise ModelValidationError(f"{field_name} must be positive, got {value!r}")


def _require_non_negative(value: float, field_name: str) -> None:
    if value < 0:
        raise ModelValidationError(f"{field_name} must be non-negative, got {value!r}")


@dataclass(frozen=True)
class SystemModel:
    raw: dict[str, Any]
    source_path: Path | None = None

    @property
    def case_id(self) -> str:
        return str(self.raw["case_id"])

    @property
    def timing(self) -> dict[str, Any]:
        return self.raw["timing"]

    @property
    def resource_limits(self) -> dict[str, Any]:
        return self.raw["resource_limits"]

    @property
    def access(self) -> dict[str, Any]:
        return self.raw["ieee1838_access"]

    @property
    def dies(self) -> list[dict[str, Any]]:
        return self.raw["dies"]

    @property
    def test_objects(self) -> list[dict[str, Any]]:
        return self.raw["test_objects"]

    @property
    def interconnects(self) -> list[dict[str, Any]]:
        return self.raw["interconnects"]

    @property
    def primary_die_id(self) -> str:
        return str(self.raw["package"]["primary_entry_die"])

    @property
    def ptap_tck_hz(self) -> float:
        return float(self.access["ptap"].get("tck_hz", self.timing["ptap_tck_hz"]))

    @property
    def dies_by_id(self) -> dict[str, dict[str, Any]]:
        return {str(die["die_id"]): die for die in self.dies}

    @property
    def staps_by_die(self) -> dict[str, dict[str, Any]]:
        return {str(stap["die_id"]): stap for stap in self.access.get("staps", [])}

    @property
    def dwr_segments_by_id(self) -> dict[str, dict[str, Any]]:
        return {
            str(segment["segment_id"]): segment
            for segment in self.access.get("dwr_segments", [])
        }

    @property
    def three_dcrs_by_die(self) -> dict[str, dict[str, Any]]:
        return {str(reg["die_id"]): reg for reg in self.access.get("three_dcrs", [])}

    @property
    def fpp_channels_by_id(self) -> dict[str, dict[str, Any]]:
        return {
            str(channel["channel_id"]): channel
            for channel in self.access.get("fpp_channels", [])
        }

    @property
    def thermal_regions_by_id(self) -> dict[str, dict[str, Any]]:
        return {
            str(region["region_id"]): region
            for region in self.raw["resource_groups"].get("thermal_regions", [])
        }

    def validate(self) -> None:
        required_top_level = [
            "model_version",
            "case_id",
            "units",
            "package",
            "timing",
            "resource_limits",
            "dies",
            "ieee1838_access",
            "test_objects",
            "interconnects",
            "resource_groups",
            "thermal_adjacency",
        ]
        for key in required_top_level:
            if key not in self.raw:
                raise ModelValidationError(f"missing top-level field: {key}")

        dies_by_id = self.dies_by_id
        if len(dies_by_id) != len(self.dies):
            raise ModelValidationError("die_id values must be unique")

        primary_die = dies_by_id.get(self.primary_die_id)
        if not primary_die:
            raise ModelValidationError("primary_entry_die must reference an existing die")
        if primary_die.get("role") != "primary":
            raise ModelValidationError("primary_entry_die must reference a primary die")

        expected_die_count = int(self.raw["package"]["die_count"])
        if expected_die_count != len(self.dies):
            raise ModelValidationError(
                f"package.die_count={expected_die_count} does not match dies length={len(self.dies)}"
            )

        self._validate_die_paths(dies_by_id)
        self._validate_access_references(dies_by_id)
        self._validate_test_objects(dies_by_id)
        self._validate_interconnects(dies_by_id)
        self._validate_thermal_regions()
        self._validate_numeric_fields()

    def die_path_to(self, die_id: str) -> list[str]:
        dies_by_id = self.dies_by_id
        if die_id not in dies_by_id:
            raise KeyError(f"unknown die_id: {die_id}")

        path: list[str] = []
        current: str | None = die_id
        seen: set[str] = set()
        while current is not None:
            if current in seen:
                raise ModelValidationError(f"cycle in die access path at {current}")
            seen.add(current)
            path.append(current)
            current = dies_by_id[current].get("access_parent_die")

        path.reverse()
        if path[0] != self.primary_die_id:
            raise ModelValidationError(
                f"die {die_id} path does not start at primary die {self.primary_die_id}"
            )
        return path

    def access_setup_bits(self, die_id: str, include_target_3dcr: bool = True) -> int:
        ptap = self.access["ptap"]
        bits = int(ptap.get("control_bits_per_access", 0))
        path = self.die_path_to(die_id)

        for path_die in path[1:]:
            stap = self.staps_by_die.get(path_die)
            if not stap:
                raise ModelValidationError(f"missing STAP for secondary die {path_die}")
            bits += int(stap.get("select_bits", 0))

        dcr_path = path if include_target_3dcr else path[:-1]
        for path_die in dcr_path:
            reg = self.three_dcrs_by_die.get(path_die)
            if reg:
                bits += int(reg.get("bit_length", 0))
        return bits

    def serial_time_s(self, bits: float) -> float:
        return float(bits) / self.ptap_tck_hz

    def fpp_lane_options(self, die_id: str, dwr_segments: Iterable[str] = ()) -> list[int]:
        required_segments = set(dwr_segments)
        lane_count = 0
        for lane in self.access.get("fpp_lanes", []):
            connects = lane.get("connects", {})
            if die_id not in set(connects.get("dies", [])):
                continue
            if required_segments:
                lane_segments = set(connects.get("dwr_segments", []))
                if not (required_segments & lane_segments):
                    continue
            lane_count += 1

        if lane_count <= 0:
            return []

        capped = min(lane_count, int(self.resource_limits.get("total_fpp_lanes", lane_count)))
        candidates = [1, min(2, capped), capped]
        return sorted(set(candidates))

    def fpp_bandwidth_bps(self, channel_id: str | None, lanes: int) -> float:
        _require_positive(lanes, "lanes")
        lane_bandwidths = []
        for lane in self.access.get("fpp_lanes", []):
            if channel_id and lane.get("channel_id") != channel_id:
                continue
            lane_bandwidths.append(float(lane["bandwidth_bps"]))

        if not lane_bandwidths:
            lane_bandwidths.append(float(self.timing["default_fpp_lane_bandwidth_bps"]))
        return min(lane_bandwidths) * lanes

    def fpp_config_bits(self, channel_id: str | None) -> int:
        if not channel_id:
            return 0
        channel = self.fpp_channels_by_id.get(channel_id)
        if not channel:
            raise ModelValidationError(f"unknown FPP channel: {channel_id}")
        return int(channel.get("config_bits", 0))

    def dwr_mode_bits(self, segment_ids: Iterable[str]) -> int:
        return sum(
            int(self.dwr_segments_by_id[segment_id].get("mode_config_bits", 0))
            for segment_id in segment_ids
        )

    def dwr_payload_bits(self, segment_ids: Iterable[str]) -> int:
        return sum(
            int(self.dwr_segments_by_id[segment_id].get("bit_length", 0))
            for segment_id in segment_ids
        )

    def adjacency_factor(self, thermal_region: str) -> float:
        factor = 1.0
        for edge in self.raw.get("thermal_adjacency", []):
            if edge.get("source_region") == thermal_region or edge.get("target_region") == thermal_region:
                factor += float(edge.get("coupling_weight", 0.0))
        return factor

    def layer_conduction_factor(self, thermal_region: str) -> float:
        thermal_model = self.raw.get("thermal_model", {})
        self_weight = float(thermal_model.get("self_heating_weight", 1.0))
        vertical_weight = float(thermal_model.get("vertical_coupling_weight", 0.35))
        distance_decay = float(thermal_model.get("layer_distance_decay", 0.5))

        region_to_die = {
            str(die.get("thermal", {}).get("region_id")): die
            for die in self.dies
        }
        target_die = region_to_die.get(thermal_region)
        if not target_die:
            return self_weight

        target_layer = int(target_die.get("layer_index", 0))
        factor = self_weight
        for edge in self.raw.get("thermal_adjacency", []):
            if edge.get("coupling_type") != "vertical":
                continue
            if thermal_region == edge.get("source_region"):
                other_region = str(edge.get("target_region"))
            elif thermal_region == edge.get("target_region"):
                other_region = str(edge.get("source_region"))
            else:
                continue

            other_die = region_to_die.get(other_region)
            if not other_die:
                continue
            layer_distance = abs(target_layer - int(other_die.get("layer_index", target_layer)))
            if layer_distance <= 0:
                layer_distance = 1
            coupling = float(edge.get("coupling_weight", 0.0))
            factor += vertical_weight * coupling * (distance_decay ** (layer_distance - 1))
        return factor

    def cooling_factor(self, die_id: str) -> float:
        die = self.dies_by_id[die_id]
        return float(die.get("thermal", {}).get("cooling_factor", 1.0)) or 1.0

    def _validate_die_paths(self, dies_by_id: dict[str, dict[str, Any]]) -> None:
        for die_id, die in dies_by_id.items():
            parent = die.get("access_parent_die")
            if die_id == self.primary_die_id:
                if parent is not None:
                    raise ModelValidationError("primary die access_parent_die must be null")
            elif parent not in dies_by_id:
                raise ModelValidationError(f"die {die_id} has unknown access_parent_die {parent!r}")
            self.die_path_to(die_id)

    def _validate_access_references(self, dies_by_id: dict[str, dict[str, Any]]) -> None:
        access = self.access
        if access["ptap"]["die_id"] not in dies_by_id:
            raise ModelValidationError("PTAP die_id must reference an existing die")

        for stap in access.get("staps", []):
            if stap["die_id"] not in dies_by_id:
                raise ModelValidationError(f"STAP {stap['stap_id']} references unknown die")
            if stap["parent_die"] not in dies_by_id:
                raise ModelValidationError(f"STAP {stap['stap_id']} references unknown parent die")

        for reg in access.get("three_dcrs", []):
            if reg["die_id"] not in dies_by_id:
                raise ModelValidationError(f"3DCR {reg['register_id']} references unknown die")

        for segment in access.get("dwr_segments", []):
            if segment["die_id"] not in dies_by_id:
                raise ModelValidationError(f"DWR segment {segment['segment_id']} references unknown die")

        segment_ids = set(self.dwr_segments_by_id)
        channel_ids = set(self.fpp_channels_by_id)
        for lane in access.get("fpp_lanes", []):
            if lane["channel_id"] not in channel_ids:
                raise ModelValidationError(f"FPP lane {lane['lane_id']} references unknown channel")
            connects = lane.get("connects", {})
            for die_id in connects.get("dies", []):
                if die_id not in dies_by_id:
                    raise ModelValidationError(f"FPP lane {lane['lane_id']} references unknown die")
            for segment_id in connects.get("dwr_segments", []):
                if segment_id not in segment_ids:
                    raise ModelValidationError(
                        f"FPP lane {lane['lane_id']} references unknown DWR segment"
                    )

    def _validate_test_objects(self, dies_by_id: dict[str, dict[str, Any]]) -> None:
        segment_ids = set(self.dwr_segments_by_id)
        for obj in self.test_objects:
            if obj["die_id"] not in dies_by_id:
                raise ModelValidationError(f"test object {obj['object_id']} references unknown die")
            for segment_id in obj.get("required_resources", {}).get("dwr_segments", []):
                if segment_id not in segment_ids:
                    raise ModelValidationError(
                        f"test object {obj['object_id']} references unknown DWR segment"
                    )

    def _validate_interconnects(self, dies_by_id: dict[str, dict[str, Any]]) -> None:
        segment_ids = set(self.dwr_segments_by_id)
        for link in self.interconnects:
            if link["source_die"] not in dies_by_id or link["target_die"] not in dies_by_id:
                raise ModelValidationError(f"interconnect {link['link_id']} references unknown die")
            for segment_id in link.get("dwr_segments", []):
                if segment_id not in segment_ids:
                    raise ModelValidationError(
                        f"interconnect {link['link_id']} references unknown DWR segment"
                    )

    def _validate_thermal_regions(self) -> None:
        region_ids = set(self.thermal_regions_by_id)
        for obj in self.test_objects:
            region = obj.get("thermal_region")
            if region not in region_ids:
                raise ModelValidationError(f"test object {obj['object_id']} has unknown thermal region")

        for edge in self.raw.get("thermal_adjacency", []):
            if edge["source_region"] not in region_ids or edge["target_region"] not in region_ids:
                raise ModelValidationError("thermal_adjacency references unknown thermal region")

    def _validate_numeric_fields(self) -> None:
        _require_positive(self.ptap_tck_hz, "ptap.tck_hz")
        _require_positive(float(self.timing["default_fpp_lane_bandwidth_bps"]), "default FPP bandwidth")
        _require_positive(float(self.timing["default_bist_clock_hz"]), "default BIST clock")
        _require_non_negative(float(self.timing.get("capture_time_s", 0.0)), "capture_time_s")
        _require_non_negative(float(self.timing.get("mode_update_time_s", 0.0)), "mode_update_time_s")
        thermal_model = self.raw.get("thermal_model", {})
        _require_non_negative(float(thermal_model.get("self_heating_weight", 1.0)), "self_heating_weight")
        _require_non_negative(float(thermal_model.get("vertical_coupling_weight", 0.35)), "vertical_coupling_weight")
        _require_non_negative(float(thermal_model.get("layer_distance_decay", 0.5)), "layer_distance_decay")

        for die in self.dies:
            size = die.get("size_um", {})
            _require_positive(float(size.get("width", 0)), f"{die['die_id']}.size.width")
            _require_positive(float(size.get("height", 0)), f"{die['die_id']}.size.height")
            _require_positive(self.cooling_factor(str(die["die_id"])), f"{die['die_id']}.cooling_factor")

        for lane in self.access.get("fpp_lanes", []):
            _require_positive(float(lane["bandwidth_bps"]), f"{lane['lane_id']}.bandwidth_bps")


def load_system_model(path: str | Path) -> SystemModel:
    source = Path(path)
    with source.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    model = SystemModel(raw=raw, source_path=source)
    model.validate()
    return model
