from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from src.model import SystemModel


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
        return TestAccessRecipe(
            recipe_id=f"I_{link['link_id']}_serial_extest",
            target_id=str(link["link_id"]),
            target_kind="interconnect",
            die_id=die_id,
            recipe_type="I",
            variant="serial_extest",
            phases="CONFIG_ACCESS_PATH|CONFIG_DWR_MODE|DWR_SHIFT_IN|DWR_CAPTURE|DWR_SHIFT_OUT",
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
        )

    def _serial_recipe(self, obj: dict[str, Any]) -> TestAccessRecipe:
        die_id = str(obj["die_id"])
        object_id = str(obj["object_id"])
        dwr_segments = self._required_dwr_segments(obj)
        setup_bits = self.model.access_setup_bits(die_id)
        mode_bits = self.model.dwr_mode_bits(dwr_segments)
        dwr_bits = self.model.dwr_payload_bits(dwr_segments)
        access_power = float(obj.get("power", {}).get("access_power_w", 0.0))

        if obj.get("object_type") == "instrument":
            instrument = obj.get("instrument", {})
            payload_bits = int(instrument.get("address_bits", 0)) + int(instrument.get("readout_bits", 0))
            access_bits = setup_bits + payload_bits
            access_time = self.model.serial_time_s(access_bits)
            total_time = access_time
            data_time = 0.0
            readback_time = self.model.serial_time_s(int(instrument.get("readout_bits", 0)))
            peak_power = access_power
            phases = "CONFIG_ACCESS_PATH|ACCESS_INSTRUMENT|READ_INSTRUMENT"
            estimated_bits = access_bits
            notes = "serial instrument access"
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
            phases = "CONFIG_ACCESS_PATH|CONFIG_DWR_MODE|SERIAL_SHIFT_IN|CAPTURE|SERIAL_SHIFT_OUT"
            estimated_bits = setup_bits + mode_bits + stimulus_bits + response_bits + dwr_bits
            notes = "serial PTAP/STAP/DWR access"

        risk = self._object_thermal_risk(obj, peak_power)
        return TestAccessRecipe(
            recipe_id=f"S_{object_id}_serial",
            target_id=object_id,
            target_kind=str(obj["object_type"]),
            die_id=die_id,
            recipe_type="S",
            variant="serial",
            phases=phases,
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
        )

    def _fpp_recipes(self, obj: dict[str, Any]) -> list[TestAccessRecipe]:
        die_id = str(obj["die_id"])
        dwr_segments = self._required_dwr_segments(obj)
        lane_options = self.model.fpp_lane_options(die_id, dwr_segments)
        channel = self._preferred_fpp_channel(obj)
        return [self._fpp_recipe(obj, lanes, channel) for lanes in lane_options]

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
        peak_power = max(
            float(obj.get("power", {}).get("shift_power_w", 0.0)) + 0.03 * lanes,
            float(obj.get("power", {}).get("capture_power_w", 0.0)),
        ) + access_power
        risk = self._object_thermal_risk(obj, peak_power)
        return TestAccessRecipe(
            recipe_id=f"F_{object_id}_lane{lanes}",
            target_id=object_id,
            target_kind=str(obj["object_type"]),
            die_id=die_id,
            recipe_type="F",
            variant=f"lane{lanes}",
            phases="CONFIG_ACCESS_PATH|CONFIG_FPP|FPP_SHIFT_IN|CAPTURE|FPP_SHIFT_OUT",
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
            notes="FPP data transfer with serial configuration",
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
        readback_time = self.model.serial_time_s(setup_bits + readout_bits)
        total_time = access_time + local_time + readback_time
        access_power = float(obj.get("power", {}).get("access_power_w", 0.0))
        peak_power = float(obj.get("power", {}).get("bist_power_w", 0.0)) + access_power
        risk = self._object_thermal_risk(obj, peak_power)
        return TestAccessRecipe(
            recipe_id=f"B_{object_id}_local_bist",
            target_id=object_id,
            target_kind=str(obj["object_type"]),
            die_id=die_id,
            recipe_type="B",
            variant="local_bist",
            phases="CONFIG_BIST|LOCAL_BIST_RUN|READ_BIST_RESULT",
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
            estimated_bits=setup_bits * 2 + config_bits + readout_bits,
            notes="local BIST releases PTAP during execution phase",
        )

    def _hybrid_recipes(self, obj: dict[str, Any]) -> list[TestAccessRecipe]:
        die_id = str(obj["die_id"])
        dwr_segments = self._required_dwr_segments(obj)
        lane_options = self.model.fpp_lane_options(die_id, dwr_segments)
        channel = self._preferred_fpp_channel(obj)
        return [self._hybrid_recipe(obj, lanes, channel) for lanes in lane_options]

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
        peak_power = max(
            float(obj.get("power", {}).get("shift_power_w", 0.0)) + 0.02 * lanes,
            float(obj.get("power", {}).get("capture_power_w", 0.0)),
        ) + access_power
        risk = self._object_thermal_risk(obj, peak_power)
        return TestAccessRecipe(
            recipe_id=f"H_{object_id}_lane{lanes}",
            target_id=object_id,
            target_kind=str(obj["object_type"]),
            die_id=die_id,
            recipe_type="H",
            variant=f"lane{lanes}",
            phases="CONFIG_ACCESS_PATH|CONFIG_FPP|CONFIG_DWR_MODE|FPP_SHIFT_IN|CAPTURE|FPP_SHIFT_OUT|SERIAL_STATUS_READBACK",
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
            notes="serial configuration with FPP bulk transfer and short serial status readback",
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
        adjacency = self.model.adjacency_factor(thermal_region)
        cooling = self.model.cooling_factor(die_id)
        return peak_power * power_density * adjacency / cooling

    def _deeper_die(self, first_die: str, second_die: str) -> str:
        dies = self.model.dies_by_id
        first_layer = int(dies[first_die].get("layer_index", 0))
        second_layer = int(dies[second_die].get("layer_index", 0))
        return first_die if first_layer >= second_layer else second_die


def write_recipes_csv(recipes: list[TestAccessRecipe], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(asdict(recipes[0]).keys()) if recipes else [field.name for field in TestAccessRecipe.__dataclass_fields__.values()]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for recipe in recipes:
            writer.writerow(asdict(recipe))
