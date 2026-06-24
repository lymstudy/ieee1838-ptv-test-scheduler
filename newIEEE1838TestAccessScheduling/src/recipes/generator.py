from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from src.model import SystemModel


@dataclass(frozen=True)
class RecipePhase:
    phase_name: str
    duration_s: float
    serial_required: bool = False
    fpp_lanes_required: int = 0
    fpp_channel: str = ""
    dwr_segments: tuple[str, ...] = ()
    route_resource: str = ""
    power_w: float = 0.0
    thermal_region: str = ""
    notes: str = ""


@dataclass(frozen=True)
class TestAccessRecipe:
    recipe_id: str
    target_id: str
    target_kind: str
    die_id: str
    recipe_type: str
    variant: str
    phases: str
    total_time_s: float
    access_time_s: float
    data_time_s: float
    local_execution_time_s: float
    readback_time_s: float
    peak_power_w: float
    access_power_w: float
    thermal_risk: float
    serial_access_required: bool
    fpp_lanes_required: int
    fpp_channel: str
    dwr_segments: str
    route_resource: str
    estimated_bits: int
    notes: str
    test_method: str
    access_mechanism: str
    test_endpoint: str
    bist_type: str
    phase_count: int
    serial_time_s: float
    fpp_time_s: float
    thermal_load: float
    max_fpp_lanes_required: int
    lane_occupancy: float
    phase_resources: str


class RecipeGenerator:
    def __init__(self, model: SystemModel):
        self.model = model

    def generate_all(self) -> list[TestAccessRecipe]:
        recipes: list[TestAccessRecipe] = []
        for obj in self.model.test_objects:
            recipes.extend(self.generate_for_test_object(obj))
        for link in self.model.interconnects:
            recipes.append(self.generate_for_interconnect(link))
        return sorted(recipes, key=lambda r: (r.target_kind, r.target_id, r.recipe_type, r.variant))

    def generate_for_test_object(self, obj: dict[str, Any]) -> list[TestAccessRecipe]:
        supported = set(obj.get("supported_recipes", []))
        recipes: list[TestAccessRecipe] = []
        if "S" in supported:
            recipes.append(self._serial_recipe(obj))
        if "F" in supported:
            recipes.extend(self._fpp_recipes(obj))
        if "B" in supported and obj.get("bist", {}).get("enabled", False):
            recipes.append(self._bist_recipe(obj))
        if "H" in supported:
            recipes.extend(self._hybrid_recipes(obj))
        return recipes

    def generate_for_interconnect(self, link: dict[str, Any]) -> TestAccessRecipe:
        source_die = str(link["source_die"])
        target_die = str(link["target_die"])
        die_id = self._deeper_die(source_die, target_die)
        dwr_segments = list(link.get("dwr_segments", []))
        payload_bits = int(link.get("estimated_test_bits", 0))
        setup_bits = self.model.access_setup_bits(die_id)
        mode_bits = self.model.dwr_mode_bits(dwr_segments)
        dwr_bits = self.model.dwr_payload_bits(dwr_segments)
        serial_bits = setup_bits + mode_bits + payload_bits * 2 + dwr_bits
        capture_time = float(self.model.timing.get("capture_time_s", 0.0))
        update_time = float(self.model.timing.get("mode_update_time_s", 0.0))
        access_time = self.model.serial_time_s(setup_bits + mode_bits)
        data_time = self.model.serial_time_s(payload_bits * 2 + dwr_bits)
        total_time = access_time + data_time + capture_time + update_time
        peak_power = float(link.get("power_w", 0.0))
        thermal_region = self.model.dies_by_id[die_id]["thermal"]["region_id"]
        risk = self._thermal_risk(die_id, thermal_region, peak_power, area_mm2=1.0)
        access_power = 0.0
        phase_list = [
            RecipePhase("CONFIG_ACCESS_PATH", self.model.serial_time_s(setup_bits), True, power_w=access_power, thermal_region=thermal_region),
            RecipePhase("CONFIG_DWR_MODE", self.model.serial_time_s(mode_bits) + update_time, True, dwr_segments=tuple(dwr_segments), power_w=access_power, thermal_region=thermal_region),
            RecipePhase("DWR_SHIFT_IN", self.model.serial_time_s(payload_bits), True, dwr_segments=tuple(dwr_segments), route_resource=str(link.get("route_resource", "")), power_w=peak_power, thermal_region=thermal_region),
            RecipePhase("DWR_CAPTURE", capture_time, False, dwr_segments=tuple(dwr_segments), route_resource=str(link.get("route_resource", "")), power_w=peak_power, thermal_region=thermal_region),
            RecipePhase("DWR_SHIFT_OUT", self.model.serial_time_s(payload_bits + dwr_bits), True, dwr_segments=tuple(dwr_segments), route_resource=str(link.get("route_resource", "")), power_w=peak_power, thermal_region=thermal_region),
        ]
        phase_summary = self._phase_summary(phase_list, die_id, thermal_region, peak_power, total_time)
        return TestAccessRecipe(
            recipe_id=f"I_{link['link_id']}_serial_extest",
            target_id=str(link["link_id"]),
            target_kind="interconnect",
            die_id=die_id,
            recipe_type="I",
            variant="serial_extest",
            phases=self._phase_names(phase_list),
            total_time_s=total_time,
            access_time_s=access_time,
            data_time_s=data_time,
            local_execution_time_s=0.0,
            readback_time_s=self.model.serial_time_s(payload_bits),
            peak_power_w=peak_power,
            access_power_w=0.0,
            thermal_risk=risk,
            serial_access_required=True,
            fpp_lanes_required=0,
            fpp_channel="",
            dwr_segments=";".join(dwr_segments),
            route_resource=str(link.get("route_resource", "")),
            estimated_bits=serial_bits,
            notes="DWR EXTEST interconnect recipe",
            test_method="EXTEST",
            access_mechanism="DWR_EXTEST",
            test_endpoint="interconnect_extest",
            bist_type="",
            **phase_summary,
        )

    def _serial_recipe(self, obj: dict[str, Any]) -> TestAccessRecipe:
        die_id = str(obj["die_id"])
        object_id = str(obj["object_id"])
        dwr_segments = self._required_dwr_segments(obj)
        setup_bits = self.model.access_setup_bits(die_id)
        mode_bits = self.model.dwr_mode_bits(dwr_segments)
        dwr_bits = self.model.dwr_payload_bits(dwr_segments)
        access_power = float(obj.get("power", {}).get("access_power_w", 0.0))
        thermal_region = str(obj.get("thermal_region", ""))

        if obj.get("object_type") == "instrument":
            instrument = obj.get("instrument", {})
            payload_bits = int(instrument.get("address_bits", 0)) + int(instrument.get("readout_bits", 0))
            access_bits = setup_bits + payload_bits
            access_time = self.model.serial_time_s(access_bits)
            total_time = access_time
            data_time = 0.0
            readback_time = self.model.serial_time_s(int(instrument.get("readout_bits", 0)))
            peak_power = access_power
            phase_list = [
                RecipePhase("CONFIG_ACCESS_PATH", self.model.serial_time_s(setup_bits), True, power_w=access_power, thermal_region=thermal_region),
                RecipePhase("ACCESS_INSTRUMENT", self.model.serial_time_s(int(instrument.get("address_bits", 0))), True, power_w=access_power, thermal_region=thermal_region),
                RecipePhase("READ_INSTRUMENT", readback_time, True, power_w=access_power, thermal_region=thermal_region),
            ]
            estimated_bits = access_bits
            notes = "serial instrument access"
            test_method = "INSTRUMENT_READ"
            access_mechanism = "PTAP_STAP_SERIAL"
            test_endpoint = "instrument_tdr"
        else:
            scan = obj.get("scan", {})
            stimulus_bits, response_bits = self._scan_bits(scan)
            capture_time = float(self.model.timing.get("capture_time_s", 0.0))
            update_time = float(self.model.timing.get("mode_update_time_s", 0.0))
            access_time = self.model.serial_time_s(setup_bits + mode_bits)
            data_time = self.model.serial_time_s(stimulus_bits + response_bits + dwr_bits)
            readback_time = self.model.serial_time_s(response_bits)
            total_time = access_time + data_time + capture_time + update_time
            peak_power = max(
                float(obj.get("power", {}).get("shift_power_w", 0.0)),
                float(obj.get("power", {}).get("capture_power_w", 0.0)),
            ) + access_power
            shift_power = float(obj.get("power", {}).get("shift_power_w", 0.0)) + access_power
            capture_power = float(obj.get("power", {}).get("capture_power_w", 0.0)) + access_power
            phase_list = [
                RecipePhase("CONFIG_ACCESS_PATH", self.model.serial_time_s(setup_bits), True, power_w=access_power, thermal_region=thermal_region),
                RecipePhase("CONFIG_SCAN_OR_DWR_MODE", self.model.serial_time_s(mode_bits) + update_time, True, dwr_segments=tuple(dwr_segments), power_w=access_power, thermal_region=thermal_region),
                RecipePhase("SERIAL_SHIFT_IN", self.model.serial_time_s(stimulus_bits), True, power_w=shift_power, thermal_region=thermal_region),
                RecipePhase("CAPTURE", capture_time, False, power_w=capture_power, thermal_region=thermal_region),
                RecipePhase("SERIAL_SHIFT_OUT", self.model.serial_time_s(response_bits + dwr_bits), True, dwr_segments=tuple(dwr_segments), power_w=shift_power, thermal_region=thermal_region),
            ]
            estimated_bits = setup_bits + mode_bits + stimulus_bits + response_bits + dwr_bits
            notes = "serial PTAP/STAP access to internal scan interface"
            test_method = "ATPG_SCAN"
            access_mechanism = "PTAP_STAP_SERIAL"
            test_endpoint = "internal_scan"

        risk = self._object_thermal_risk(obj, peak_power)
        phase_summary = self._phase_summary(phase_list, die_id, thermal_region, peak_power, total_time)
        return TestAccessRecipe(
            recipe_id=f"S_{object_id}_serial",
            target_id=object_id,
            target_kind=str(obj["object_type"]),
            die_id=die_id,
            recipe_type="S",
            variant="serial",
            phases=self._phase_names(phase_list),
            total_time_s=total_time,
            access_time_s=access_time,
            data_time_s=data_time,
            local_execution_time_s=0.0,
            readback_time_s=readback_time,
            peak_power_w=peak_power,
            access_power_w=access_power,
            thermal_risk=risk,
            serial_access_required=True,
            fpp_lanes_required=0,
            fpp_channel="",
            dwr_segments=";".join(dwr_segments),
            route_resource="",
            estimated_bits=estimated_bits,
            notes=notes,
            test_method=test_method,
            access_mechanism=access_mechanism,
            test_endpoint=test_endpoint,
            bist_type="",
            **phase_summary,
        )

    def _fpp_recipes(self, obj: dict[str, Any]) -> list[TestAccessRecipe]:
        die_id = str(obj["die_id"])
        dwr_segments = self._required_dwr_segments(obj)
        lane_options = self.model.fpp_lane_options(die_id, dwr_segments)
        channel = self._preferred_fpp_channel(obj)
        return [
            self._fpp_recipe(obj, lanes, channel)
            for lanes in lane_options
            if self._is_fpp_recipe_legal(obj, lanes, channel, dwr_segments)
        ]

    def _fpp_recipe(self, obj: dict[str, Any], lanes: int, channel: str) -> TestAccessRecipe:
        die_id = str(obj["die_id"])
        object_id = str(obj["object_id"])
        dwr_segments = self._required_dwr_segments(obj)
        scan = obj.get("scan", {})
        stimulus_bits, response_bits = self._scan_bits(scan)
        setup_bits = self.model.access_setup_bits(die_id)
        fpp_config_bits = self.model.fpp_config_bits(channel)
        mode_bits = self.model.dwr_mode_bits(dwr_segments)
        capture_time = float(self.model.timing.get("capture_time_s", 0.0))
        update_time = float(self.model.timing.get("mode_update_time_s", 0.0))
        access_time = self.model.serial_time_s(setup_bits + fpp_config_bits + mode_bits)
        bandwidth = self.model.fpp_bandwidth_bps(channel, lanes)
        data_time = (stimulus_bits + response_bits) / bandwidth
        total_time = access_time + data_time + capture_time + update_time
        access_power = float(obj.get("power", {}).get("access_power_w", 0.0))
        thermal_region = str(obj.get("thermal_region", ""))
        shift_power = float(obj.get("power", {}).get("shift_power_w", 0.0)) + 0.03 * lanes + access_power
        capture_power = float(obj.get("power", {}).get("capture_power_w", 0.0)) + access_power
        peak_power = max(
            float(obj.get("power", {}).get("shift_power_w", 0.0)) + 0.03 * lanes,
            float(obj.get("power", {}).get("capture_power_w", 0.0)),
        ) + access_power
        risk = self._object_thermal_risk(obj, peak_power)
        phase_list = [
            RecipePhase("CONFIG_ACCESS_PATH", self.model.serial_time_s(setup_bits), True, power_w=access_power, thermal_region=thermal_region),
            RecipePhase("CONFIG_FPP", self.model.serial_time_s(fpp_config_bits), True, fpp_channel=channel, power_w=access_power, thermal_region=thermal_region),
            RecipePhase("CONFIG_SCAN_OR_DWR_MODE", self.model.serial_time_s(mode_bits) + update_time, True, dwr_segments=tuple(dwr_segments), power_w=access_power, thermal_region=thermal_region),
            RecipePhase("FPP_SHIFT_IN", stimulus_bits / bandwidth, False, lanes, channel, tuple(dwr_segments), power_w=shift_power, thermal_region=thermal_region),
            RecipePhase("CAPTURE", capture_time, False, power_w=capture_power, thermal_region=thermal_region),
            RecipePhase("FPP_SHIFT_OUT", response_bits / bandwidth, False, lanes, channel, tuple(dwr_segments), power_w=shift_power, thermal_region=thermal_region),
        ]
        phase_summary = self._phase_summary(phase_list, die_id, thermal_region, peak_power, total_time)
        legality_note = self._fpp_legality_note(channel, lanes)
        return TestAccessRecipe(
            recipe_id=f"F_{object_id}_lane{lanes}",
            target_id=object_id,
            target_kind=str(obj["object_type"]),
            die_id=die_id,
            recipe_type="F",
            variant=f"lane{lanes}",
            phases=self._phase_names(phase_list),
            total_time_s=total_time,
            access_time_s=access_time,
            data_time_s=data_time,
            local_execution_time_s=0.0,
            readback_time_s=response_bits / bandwidth,
            peak_power_w=peak_power,
            access_power_w=access_power,
            thermal_risk=risk,
            serial_access_required=True,
            fpp_lanes_required=lanes,
            fpp_channel=channel,
            dwr_segments=";".join(dwr_segments),
            route_resource="",
            estimated_bits=setup_bits + fpp_config_bits + mode_bits + stimulus_bits + response_bits,
            notes="FPP optional parallel data transfer with serial configuration" + legality_note,
            test_method="ATPG_SCAN",
            access_mechanism="FPP_PARALLEL",
            test_endpoint="internal_scan",
            bist_type="",
            **phase_summary,
        )

    def _bist_recipe(self, obj: dict[str, Any]) -> TestAccessRecipe:
        die_id = str(obj["die_id"])
        object_id = str(obj["object_id"])
        bist = obj["bist"]
        setup_bits = self.model.access_setup_bits(die_id)
        config_bits = int(bist.get("config_bits", 0))
        readout_bits = int(bist.get("readout_bits", 0))
        bist_clock = float(bist.get("bist_clock_hz", self.model.timing["default_bist_clock_hz"]))
        access_time = self.model.serial_time_s(setup_bits + config_bits)
        local_time = int(bist.get("local_cycles", 0)) / bist_clock
        readback_setup_bits = setup_bits * 0.5
        readback_time = self.model.serial_time_s(readback_setup_bits + readout_bits)
        total_time = access_time + local_time + readback_time
        access_power = float(obj.get("power", {}).get("access_power_w", 0.0))
        peak_power = float(obj.get("power", {}).get("bist_power_w", 0.0)) + access_power
        risk = self._object_thermal_risk(obj, peak_power)
        thermal_region = str(obj.get("thermal_region", ""))
        bist_type = "MBIST" if obj.get("object_type") == "memory" else "LBIST"
        phase_list = [
            RecipePhase("CONFIG_BIST", access_time, True, power_w=access_power, thermal_region=thermal_region),
            RecipePhase("LOCAL_BIST_RUN", local_time, False, 0, power_w=peak_power, thermal_region=thermal_region, notes="external access resources released"),
            RecipePhase("READ_BIST_RESULT", readback_time, True, power_w=access_power, thermal_region=thermal_region),
        ]
        phase_summary = self._phase_summary(phase_list, die_id, thermal_region, peak_power, total_time)
        return TestAccessRecipe(
            recipe_id=f"B_{object_id}_local_bist",
            target_id=object_id,
            target_kind=str(obj["object_type"]),
            die_id=die_id,
            recipe_type="B",
            variant="local_bist",
            phases=self._phase_names(phase_list),
            total_time_s=total_time,
            access_time_s=access_time,
            data_time_s=0.0,
            local_execution_time_s=local_time,
            readback_time_s=readback_time,
            peak_power_w=peak_power,
            access_power_w=access_power,
            thermal_risk=risk,
            serial_access_required=True,
            fpp_lanes_required=0,
            fpp_channel="",
            dwr_segments=";".join(self._required_dwr_segments(obj)),
            route_resource="",
            estimated_bits=int(setup_bits + config_bits + readback_setup_bits + readout_bits),
            notes="local BIST releases external access resources during execution phase",
            test_method=bist_type,
            access_mechanism="LOCAL_BIST",
            test_endpoint="memory_bist" if bist_type == "MBIST" else "logic_bist",
            bist_type=bist_type,
            **phase_summary,
        )

    def _hybrid_recipes(self, obj: dict[str, Any]) -> list[TestAccessRecipe]:
        die_id = str(obj["die_id"])
        dwr_segments = self._required_dwr_segments(obj)
        lane_options = self.model.fpp_lane_options(die_id, dwr_segments)
        channel = self._preferred_fpp_channel(obj)
        return [
            self._hybrid_recipe(obj, lanes, channel)
            for lanes in lane_options
            if self._is_fpp_recipe_legal(obj, lanes, channel, dwr_segments)
        ]

    def _hybrid_recipe(self, obj: dict[str, Any], lanes: int, channel: str) -> TestAccessRecipe:
        die_id = str(obj["die_id"])
        object_id = str(obj["object_id"])
        dwr_segments = self._required_dwr_segments(obj)
        scan = obj.get("scan", {})
        stimulus_bits, response_bits = self._scan_bits(scan)
        setup_bits = self.model.access_setup_bits(die_id)
        fpp_config_bits = self.model.fpp_config_bits(channel)
        mode_bits = self.model.dwr_mode_bits(dwr_segments)
        status_bits = 64
        capture_time = float(self.model.timing.get("capture_time_s", 0.0))
        update_time = float(self.model.timing.get("mode_update_time_s", 0.0))
        access_time = self.model.serial_time_s(setup_bits + fpp_config_bits + mode_bits)
        bandwidth = self.model.fpp_bandwidth_bps(channel, lanes)
        data_time = (stimulus_bits + response_bits) / bandwidth
        readback_time = self.model.serial_time_s(status_bits)
        total_time = access_time + data_time + capture_time + update_time + readback_time
        access_power = float(obj.get("power", {}).get("access_power_w", 0.0))
        thermal_region = str(obj.get("thermal_region", ""))
        shift_power = float(obj.get("power", {}).get("shift_power_w", 0.0)) + 0.02 * lanes + access_power
        capture_power = float(obj.get("power", {}).get("capture_power_w", 0.0)) + access_power
        peak_power = max(
            float(obj.get("power", {}).get("shift_power_w", 0.0)) + 0.02 * lanes,
            float(obj.get("power", {}).get("capture_power_w", 0.0)),
        ) + access_power
        risk = self._object_thermal_risk(obj, peak_power)
        phase_list = [
            RecipePhase("CONFIG_ACCESS_PATH", self.model.serial_time_s(setup_bits), True, power_w=access_power, thermal_region=thermal_region),
            RecipePhase("CONFIG_FPP", self.model.serial_time_s(fpp_config_bits), True, fpp_channel=channel, power_w=access_power, thermal_region=thermal_region),
            RecipePhase("CONFIG_SCAN_OR_DWR_MODE", self.model.serial_time_s(mode_bits) + update_time, True, dwr_segments=tuple(dwr_segments), power_w=access_power, thermal_region=thermal_region),
            RecipePhase("FPP_SHIFT_IN", stimulus_bits / bandwidth, False, lanes, channel, tuple(dwr_segments), power_w=shift_power, thermal_region=thermal_region),
            RecipePhase("CAPTURE", capture_time, False, power_w=capture_power, thermal_region=thermal_region),
            RecipePhase("FPP_SHIFT_OUT", response_bits / bandwidth, False, lanes, channel, tuple(dwr_segments), power_w=shift_power, thermal_region=thermal_region),
            RecipePhase("SERIAL_STATUS_READBACK", readback_time, True, power_w=access_power, thermal_region=thermal_region),
        ]
        phase_summary = self._phase_summary(phase_list, die_id, thermal_region, peak_power, total_time)
        legality_note = self._fpp_legality_note(channel, lanes)
        return TestAccessRecipe(
            recipe_id=f"H_{object_id}_lane{lanes}",
            target_id=object_id,
            target_kind=str(obj["object_type"]),
            die_id=die_id,
            recipe_type="H",
            variant=f"lane{lanes}",
            phases=self._phase_names(phase_list),
            total_time_s=total_time,
            access_time_s=access_time,
            data_time_s=data_time,
            local_execution_time_s=0.0,
            readback_time_s=readback_time,
            peak_power_w=peak_power,
            access_power_w=access_power,
            thermal_risk=risk,
            serial_access_required=True,
            fpp_lanes_required=lanes,
            fpp_channel=channel,
            dwr_segments=";".join(dwr_segments),
            route_resource="",
            estimated_bits=setup_bits
            + fpp_config_bits
            + mode_bits
            + stimulus_bits
            + response_bits
            + status_bits,
            notes="serial configuration with FPP bulk transfer and short serial status/signature readback" + legality_note,
            test_method="ATPG_SCAN",
            access_mechanism="HYBRID",
            test_endpoint="internal_scan",
            bist_type="",
            **phase_summary,
        )

    def _scan_bits(self, scan: dict[str, Any]) -> tuple[int, int]:
        pattern_count = int(scan.get("pattern_count", 0))
        max_chain_length = int(scan.get("max_chain_length_bits", 0))
        response_bits = int(scan.get("response_bits_per_pattern", max_chain_length))
        return pattern_count * max_chain_length, pattern_count * response_bits

    def _required_dwr_segments(self, obj: dict[str, Any]) -> list[str]:
        return list(obj.get("required_resources", {}).get("dwr_segments", []))

    def _preferred_fpp_channel(self, obj: dict[str, Any]) -> str:
        channel = obj.get("required_resources", {}).get("preferred_fpp_channel")
        if channel:
            return str(channel)
        channels = self.model.access.get("fpp_channels", [])
        return str(channels[0]["channel_id"]) if channels else ""

    def _object_thermal_risk(self, obj: dict[str, Any], peak_power: float) -> float:
        area = float(obj.get("area_mm2", 1.0)) or 1.0
        return self._thermal_risk(str(obj["die_id"]), str(obj["thermal_region"]), peak_power, area)

    def _thermal_risk(self, die_id: str, thermal_region: str, peak_power: float, area_mm2: float) -> float:
        power_density = peak_power / max(area_mm2, 1e-12)
        adjacency = self.model.layer_conduction_factor(thermal_region)
        cooling = self.model.cooling_factor(die_id)
        return peak_power * power_density * adjacency / cooling

    def _deeper_die(self, first_die: str, second_die: str) -> str:
        dies = self.model.dies_by_id
        first_layer = int(dies[first_die].get("layer_index", 0))
        second_layer = int(dies[second_die].get("layer_index", 0))
        return first_die if first_layer >= second_layer else second_die

    def _is_fpp_recipe_legal(
        self,
        obj: dict[str, Any],
        lanes: int,
        channel: str,
        dwr_segments: list[str],
    ) -> bool:
        if not channel or lanes <= 0:
            return False
        channel_lanes = [
            lane for lane in self.model.access.get("fpp_lanes", [])
            if lane.get("channel_id") == channel
        ]
        if lanes > len(channel_lanes):
            return False
        channel_config = self.model.fpp_channels_by_id.get(channel)
        if channel_config and lanes > int(channel_config.get("max_lanes", len(channel_lanes))):
            return False

        p2s_lanes = [
            lane for lane in channel_lanes
            if lane.get("direction") in {"primary_to_secondary", "bidirectional"}
            and str(obj["die_id"]) in lane.get("connects", {}).get("dies", [])
        ]
        s2p_lanes = [
            lane for lane in channel_lanes
            if lane.get("direction") in {"secondary_to_primary", "bidirectional"}
            and str(obj["die_id"]) in lane.get("connects", {}).get("dies", [])
        ]
        if len(p2s_lanes) < lanes or len(s2p_lanes) < lanes:
            return False

        for segment in dwr_segments:
            if not any(segment in lane.get("connects", {}).get("dwr_segments", []) for lane in channel_lanes):
                return False
        return True

    def _fpp_legality_note(self, channel: str, lanes: int) -> str:
        channel_lanes = [
            lane for lane in self.model.access.get("fpp_lanes", [])
            if lane.get("channel_id") == channel
        ]
        needs_clock = any(lane.get("requires_clock_lane", False) for lane in channel_lanes[:lanes])
        has_clock = any(lane.get("is_clock_lane", False) for lane in channel_lanes)
        channel_has_clock = bool(self.model.fpp_channels_by_id.get(channel, {}).get("clock_lane_id"))
        if needs_clock and not (has_clock or channel_has_clock):
            return "; warning: clock lane availability is not explicitly modeled"
        return ""

    def _phase_summary(
        self,
        phases: list[RecipePhase],
        die_id: str,
        thermal_region: str,
        peak_power: float,
        total_time: float,
    ) -> dict[str, Any]:
        serial_time = sum(phase.duration_s for phase in phases if phase.serial_required)
        fpp_time = sum(phase.duration_s for phase in phases if phase.fpp_lanes_required > 0)
        lane_occupancy = sum(phase.duration_s * phase.fpp_lanes_required for phase in phases)
        max_fpp_lanes = max((phase.fpp_lanes_required for phase in phases), default=0)
        return {
            "phase_count": len(phases),
            "serial_time_s": serial_time,
            "fpp_time_s": fpp_time,
            "thermal_load": self._thermal_load(die_id, thermal_region, peak_power, total_time),
            "max_fpp_lanes_required": max_fpp_lanes,
            "lane_occupancy": lane_occupancy,
            "phase_resources": self._phase_resources_json(phases),
        }

    def _thermal_load(self, die_id: str, thermal_region: str, peak_power: float, total_time: float) -> float:
        return peak_power * total_time * self.model.layer_conduction_factor(thermal_region) / self.model.cooling_factor(die_id)

    def _phase_names(self, phases: list[RecipePhase]) -> str:
        return "|".join(phase.phase_name for phase in phases)

    def _phase_resources_json(self, phases: list[RecipePhase]) -> str:
        rows = []
        for phase in phases:
            row = asdict(phase)
            row["dwr_segments"] = list(phase.dwr_segments)
            rows.append(row)
        return json.dumps(rows, ensure_ascii=False, separators=(",", ":"))


def write_recipes_csv(recipes: list[TestAccessRecipe], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(asdict(recipes[0]).keys()) if recipes else [field.name for field in TestAccessRecipe.__dataclass_fields__.values()]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for recipe in recipes:
            writer.writerow(asdict(recipe))


def write_recipe_phases_csv(recipes: list[TestAccessRecipe], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "recipe_id",
        "target_id",
        "recipe_type",
        "phase_index",
        "phase_name",
        "duration_s",
        "serial_required",
        "fpp_lanes_required",
        "fpp_channel",
        "dwr_segments",
        "route_resource",
        "power_w",
        "thermal_region",
        "notes",
    ]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for recipe in recipes:
            phases = json.loads(recipe.phase_resources)
            for index, phase in enumerate(phases):
                writer.writerow(
                    {
                        "recipe_id": recipe.recipe_id,
                        "target_id": recipe.target_id,
                        "recipe_type": recipe.recipe_type,
                        "phase_index": index,
                        "phase_name": phase["phase_name"],
                        "duration_s": phase["duration_s"],
                        "serial_required": phase["serial_required"],
                        "fpp_lanes_required": phase["fpp_lanes_required"],
                        "fpp_channel": phase["fpp_channel"],
                        "dwr_segments": ";".join(phase["dwr_segments"]),
                        "route_resource": phase["route_resource"],
                        "power_w": phase["power_w"],
                        "thermal_region": phase["thermal_region"],
                        "notes": phase["notes"],
                    }
                )
