"""Test Access Task & Recipe generator for IEEE 1838-compatible systems.

This module provides TWO generation APIs:

  NEW (physically correct) -- TaskGenerator
  -----------------------------------------
  Each test OBJECT generates independent TestTask objects (one per test
  type that physically exists). Each TestTask has CompilationVariant(s)
  that differ only in Phase 3 transport (serial, FPP, local).

  OLD (deprecated, backward-compat) -- RecipeGenerator
  ----------------------------------------------------
  Treats recipe types S/F/B/H/I as mutually exclusive alternatives per
  target.  Kept working so existing schedulers and experiment runners
  are not broken by this refactor.

Note: FPP (Flexible Parallel Port) is an OPTIONAL but standard-defined
component of IEEE 1838-2019 (Clauses 5.5.3, 6.5, Clause 7). Recipes of
type F and H use FPP as a standard-defined parallel data-transport
mechanism, always in combination with standard PTAP/STAP serial
configuration. FPP is treated as an optional accelerator, not a
replacement for TAP control.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from src.model import SystemModel


# ---------------------------------------------------------------------------
#  NEW dataclasses  (physically correct model)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TestTask:
    """A single mandatory test operation on a target.

    A target may require multiple TestTasks of different test types
    (e.g. both INTEST for scan chains AND BIST for memories).
    TestTask is NOT a recipe alternative -- each is a mandatory
    scheduling unit.
    """
    task_id: str               # e.g. "die0_core0_INTEST"
    target_id: str              # test object / interconnect id
    die_id: str                 # die this target resides on
    test_type: str              # "INTEST" | "EXTEST" | "BIST" | "IJTAG"

    # Phase timing (computed from physical parameters)
    config_path_bits: int       # TAP bits to configure serial path to this die
    config_test_bits: int       # TAP bits to set up the test itself
    execute_bits_or_cycles: int # scan bits for INTEST/EXTEST, BIST cycles for BIST
    read_result_bits: int       # TAP bits to read back test results

    # Default transport (how Phase 3 data moves without FPP)
    default_transport: str = ""  # "serial" | "fpp" | "local"

    # Additional metadata for compilation
    _raw_obj: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @property
    def is_scan_based(self) -> bool:
        return self.test_type in {"INTEST", "EXTEST"}


@dataclass(frozen=True)
class CompilationVariant:
    """A specific execution plan for a TestTask.

    One TestTask may have multiple CompilationVariants that differ
    only in their transport choice for Phase 3.  The variant changes
    the resource footprint during execution -- the task identity and
    test type are fixed.

    Compatible with existing schedulers: every CompilationVariant
    exposes the same fields that greedy.py / cpsat.py read from
    RecipeRow dicts (total_time_s, peak_power_w, fpp_lanes_required,
    phase_resources, serial_time_s, fpp_time_s, etc.).
    """
    variant_id: str              # e.g. "die0_core0_INTEST_serial"
    task_id: str                 # references TestTask.task_id

    # Replicated identity fields (backward-compat with RecipeRow)
    target_id: str = ""
    target_kind: str = ""
    die_id: str = ""
    recipe_type: str = ""        # maps to old recipe_type for compat
    variant: str = ""

    transport: str = "serial"    # "serial" | "fpp" | "local"

    # Phase-level details (compatible with existing ScheduledPhase)
    phases: list[str] = field(default_factory=list)   # "|".join of phase names
    phase_resources: str = "[]"  # JSON list of phase dicts

    # Timing fields (compatible with greedy / cpsat / pruning consumers)
    total_time_s: float = 0.0
    access_time_s: float = 0.0
    data_time_s: float = 0.0
    local_execution_time_s: float = 0.0
    readback_time_s: float = 0.0
    serial_time_s: float = 0.0
    fpp_time_s: float = 0.0

    # Resource fields
    peak_power_w: float = 0.0
    access_power_w: float = 0.0
    thermal_risk: float = 0.0
    thermal_load: float = 0.0
    serial_access_required: bool = True
    fpp_lanes_required: int = 0
    max_fpp_lanes_required: int = 0
    lane_occupancy: float = 0.0
    fpp_channel: str = ""
    dwr_segments: str = ""          # ";"-joined
    route_resource: str = ""
    exclusive_resource: str = ""

    # Metadata
    estimated_bits: int = 0
    notes: str = ""
    test_method: str = ""
    access_mechanism: str = ""
    test_endpoint: str = ""
    bist_type: str = ""
    phase_count: int = 0

    # NEW fields (not in old RecipeRow)
    uses_tap_during_execute: bool = True  # True for serial, False for FPP/BIST
    fpp_lanes_needed: int = 0
    bist_engine_needed: str = ""          # non-empty for BIST tasks
    test_session_group: str = ""

    def to_recipe_row(self) -> dict[str, object]:
        """Convert to a dict that looks like an old RecipeRow for backward compat.

        Existing schedulers (greedy.py, cpsat.py) access dict fields
        like row["total_time_s"], row["peak_power_w"], etc.  This
        returns a flat dict with all the keys they expect, so they
        work without modification.
        """
        return {
            "recipe_id": self.variant_id,
            "task_id": self.task_id,
            "target_id": self.target_id,
            "target_kind": self.target_kind,
            "die_id": self.die_id,
            "recipe_type": self.recipe_type,
            "variant": self.variant or self.transport,
            "phases": self.phases if isinstance(self.phases, str) else "|".join(self.phases),
            "total_time_s": self.total_time_s,
            "access_time_s": self.access_time_s,
            "data_time_s": self.data_time_s,
            "local_execution_time_s": self.local_execution_time_s,
            "readback_time_s": self.readback_time_s,
            "serial_time_s": self.serial_time_s,
            "fpp_time_s": self.fpp_time_s,
            "peak_power_w": self.peak_power_w,
            "access_power_w": self.access_power_w,
            "thermal_risk": self.thermal_risk,
            "thermal_load": self.thermal_load,
            "serial_access_required": self.serial_access_required,
            "fpp_lanes_required": self.fpp_lanes_required,
            "max_fpp_lanes_required": self.max_fpp_lanes_required,
            "lane_occupancy": self.lane_occupancy,
            "fpp_channel": self.fpp_channel,
            "dwr_segments": self.dwr_segments,
            "route_resource": self.route_resource,
            "estimated_bits": self.estimated_bits,
            "notes": self.notes,
            "test_method": self.test_method,
            "access_mechanism": self.access_mechanism,
            "test_endpoint": self.test_endpoint,
            "bist_type": self.bist_type,
            "phase_count": self.phase_count,
            "phase_resources": self.phase_resources,
            "serial_resource_time_s": self._compute_serial_resource_time(),
        }

    def _compute_serial_resource_time(self) -> float:
        if not self.serial_access_required:
            return 0.0
        rc = self.recipe_type
        if rc in {"S", "I"}:
            return self.access_time_s + self.data_time_s
        if rc in {"B", "H"}:
            return self.access_time_s + self.readback_time_s
        return self.access_time_s


# Backward-compat helpers ---------------------------------------------------

def rows_from_variants(variants: list[CompilationVariant]) -> list[dict[str, object]]:
    """Convert CompilationVariants to row dicts compatible with existing schedulers."""
    return [v.to_recipe_row() for v in variants]


# ---------------------------------------------------------------------------
#  OLD dataclasses  (unchanged, deprecated)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RecipePhase:
    phase_name: str
    duration_s: float
    serial_required: bool = False
    fpp_lanes_required: int = 0
    fpp_channel: str = ""
    dwr_segments: tuple[str, ...] = ()
    route_resource: str = ""
    exclusive_resource: str = ""
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


# ---------------------------------------------------------------------------
#  NEW TaskGenerator  (physically correct model)
# ---------------------------------------------------------------------------

class TaskGenerator:
    """Generate TestTasks + CompilationVariants from a SystemModel.

    This is the physically correct generator: each test object produces
    independent TestTask objects, one per test type.  Each TestTask
    gets CompilationVariants that differ only in Phase 3 transport.
    """

    def __init__(self, model: SystemModel):
        self.model = model

    # -- Tasks -----------------------------------------------------------

    def generate_tasks(self) -> list[TestTask]:
        """Generate all mandatory test tasks for the entire stack."""
        tasks: list[TestTask] = []
        for obj in self.model.test_objects:
            tasks.extend(self._tasks_for_test_object(obj))
        for link in self.model.interconnects:
            tasks.append(self._extest_task(link))
        return sorted(tasks, key=lambda t: (t.die_id, t.test_type, t.target_id))

    def _tasks_for_test_object(self, obj: dict[str, Any]) -> list[TestTask]:
        object_type = str(obj.get("object_type", "core"))
        bist_enabled = obj.get("bist", {}).get("enabled", False)
        tasks: list[TestTask] = []

        # Determine if this object has scan chains
        scan = obj.get("scan", {})
        has_scan_chains = bool(scan) and (int(scan.get("max_chain_length_bits", 0)) > 0
                                          or int(scan.get("pattern_count", 0)) > 0)

        if object_type == "instrument":
            tasks.append(self._ijtag_task(obj))
        else:
            # INTEST task (for any object with scan chains)
            if has_scan_chains:
                tasks.append(self._intest_task(obj))
            # BIST task (if hardware exists)
            if bist_enabled:
                tasks.append(self._bist_task(obj))
            # If core has no scan and no BIST, still create an INTEST stub
            # for the logic to be tested at least minimally
            if not tasks and object_type == "core":
                tasks.append(self._intest_task(obj, force_empty_scan=True))
        return tasks

    def _die_id(self, obj: dict[str, Any]) -> str:
        return str(obj["die_id"])

    def _target_id(self, obj: dict[str, Any]) -> str:
        return str(obj["object_id"])

    def _task_id(self, obj: dict[str, Any], test_type: str) -> str:
        return f"{self._die_id(obj)}_{self._target_id(obj)}_{test_type}"

    # -- INTEST ----------------------------------------------------------

    def _intest_task(self, obj: dict[str, Any], force_empty_scan: bool = False) -> TestTask:
        die_id = self._die_id(obj)
        target_id = self._target_id(obj)
        dwr_segments = self._required_dwr_segments(obj)
        setup_bits = self.model.access_setup_bits(die_id)
        mode_bits = self.model.dwr_mode_bits(dwr_segments)
        dwr_bits = self.model.dwr_payload_bits(dwr_segments)

        if force_empty_scan:
            stimulus_bits = 0
            response_bits = 0
        else:
            scan = obj.get("scan", {})
            stimulus_bits, response_bits = self._scan_bits(scan)

        # INTEST must deliver stimulus + capture + shift out response
        execute_bits_or_cycles = stimulus_bits + response_bits + dwr_bits
        read_result_bits = response_bits

        return TestTask(
            task_id=self._task_id(obj, "INTEST"),
            target_id=target_id,
            die_id=die_id,
            test_type="INTEST",
            config_path_bits=setup_bits,
            config_test_bits=mode_bits,
            execute_bits_or_cycles=execute_bits_or_cycles,
            read_result_bits=read_result_bits,
            default_transport="serial",
            _raw_obj=dict(obj),
        )

    # -- BIST ------------------------------------------------------------

    def _bist_task(self, obj: dict[str, Any]) -> TestTask:
        die_id = self._die_id(obj)
        target_id = self._target_id(obj)
        bist = obj["bist"]
        setup_bits = self.model.access_setup_bits(die_id)
        config_bits = int(bist.get("config_bits", 0))
        readout_bits = int(bist.get("readout_bits", 0))
        bist_cycles = int(bist.get("local_cycles", 0))

        return TestTask(
            task_id=self._task_id(obj, "BIST"),
            target_id=target_id,
            die_id=die_id,
            test_type="BIST",
            config_path_bits=setup_bits,
            config_test_bits=config_bits,
            execute_bits_or_cycles=bist_cycles,
            read_result_bits=readout_bits,
            default_transport="local",
            _raw_obj=dict(obj),
        )

    # -- IJTAG -----------------------------------------------------------

    def _ijtag_task(self, obj: dict[str, Any]) -> TestTask:
        die_id = self._die_id(obj)
        target_id = self._target_id(obj)
        instrument = obj.get("instrument", {})
        setup_bits = self.model.access_setup_bits(die_id)
        address_bits = int(instrument.get("address_bits", 0))
        readout_bits = int(instrument.get("readout_bits", 0))

        return TestTask(
            task_id=self._task_id(obj, "IJTAG"),
            target_id=target_id,
            die_id=die_id,
            test_type="IJTAG",
            config_path_bits=setup_bits,
            config_test_bits=address_bits,
            execute_bits_or_cycles=0,
            read_result_bits=readout_bits,
            default_transport="serial",
            _raw_obj=dict(obj),
        )

    # -- EXTEST ----------------------------------------------------------

    def _extest_task(self, link: dict[str, Any]) -> TestTask:
        source_die = str(link["source_die"])
        target_die = str(link["target_die"])
        die_id = self._deeper_die(source_die, target_die)
        dwr_segments = list(link.get("dwr_segments", []))
        setup_bits = self.model.access_setup_bits(die_id)
        mode_bits = self.model.dwr_mode_bits(dwr_segments)
        dwr_bits = self.model.dwr_payload_bits(dwr_segments)
        payload_bits = int(link.get("estimated_test_bits", 0))

        execute_bits = payload_bits * 2 + dwr_bits

        return TestTask(
            task_id=f"{die_id}_{link['link_id']}_EXTEST",
            target_id=str(link["link_id"]),
            die_id=die_id,
            test_type="EXTEST",
            config_path_bits=setup_bits,
            config_test_bits=mode_bits,
            execute_bits_or_cycles=execute_bits,
            read_result_bits=payload_bits,
            default_transport="serial",
            _raw_obj={"link": dict(link), "source_die": source_die, "target_die": target_die},
        )

    # -- Variants --------------------------------------------------------

    def compile_variants(self, task: TestTask) -> list[CompilationVariant]:
        """Generate transport variants for a task.

        INTEST   → serial, fpp_{N}lane (if FPP lanes available)
        BIST     → local (only variant)
        EXTEST   → serial, fpp_extest (if FPP lanes available)
        IJTAG    → serial (only variant)
        """
        if task.test_type == "BIST":
            return [self._bist_variant(task)]
        if task.test_type == "IJTAG":
            return [self._ijtag_variant(task)]
        if task.test_type == "INTEST":
            return self._intest_variants(task)
        if task.test_type == "EXTEST":
            return self._extest_variants(task)
        return []

    def generate_all_variants(self) -> list[CompilationVariant]:
        """Generate all CompilationVariants for all tasks."""
        variants: list[CompilationVariant] = []
        for task in self.generate_tasks():
            variants.extend(self.compile_variants(task))
        return variants

    def _bist_variant(self, task: TestTask) -> CompilationVariant:
        obj = task._raw_obj
        die_id = task.die_id
        target_id = task.target_id
        bist = obj.get("bist", {})
        bist_clock = float(bist.get("bist_clock_hz", self.model.timing["default_bist_clock_hz"]))
        setup_bits = task.config_path_bits
        config_bits = task.config_test_bits
        readout_bits = task.read_result_bits
        bist_cycles = task.execute_bits_or_cycles

        access_time = self.model.serial_time_s(setup_bits + config_bits)
        local_time = bist_cycles / bist_clock
        readback_setup_bits = int(setup_bits * 0.5)
        readback_time = self.model.serial_time_s(readback_setup_bits + readout_bits)
        total_time = access_time + local_time + readback_time

        access_power = float(obj.get("power", {}).get("access_power_w", 0.0))
        peak_power = float(obj.get("power", {}).get("bist_power_w", 0.0)) + access_power
        dwr_segments = self._required_dwr_segments(obj)
        thermal_region = str(obj.get("thermal_region", ""))
        test_session = self._test_session_resource(obj)
        bist_type_label = "MBIST" if obj.get("object_type") == "memory" else "LBIST"

        phases_raw = json.dumps([
            {"phase_name": "CONFIG_BIST", "duration_s": access_time, "serial_required": True,
             "fpp_lanes_required": 0, "fpp_channel": "", "dwr_segments": dwr_segments,
             "route_resource": "", "exclusive_resource": "", "power_w": access_power,
             "thermal_region": thermal_region, "notes": ""},
            {"phase_name": "LOCAL_BIST_RUN", "duration_s": local_time, "serial_required": False,
             "fpp_lanes_required": 0, "fpp_channel": "", "dwr_segments": dwr_segments,
             "route_resource": "", "exclusive_resource": test_session, "power_w": peak_power,
             "thermal_region": thermal_region,
             "notes": "external TAP resources released; local test session remains occupied"},
            {"phase_name": "READ_BIST_RESULT", "duration_s": readback_time, "serial_required": True,
             "fpp_lanes_required": 0, "fpp_channel": "", "dwr_segments": dwr_segments,
             "route_resource": "", "exclusive_resource": "", "power_w": access_power,
             "thermal_region": thermal_region, "notes": ""},
        ], ensure_ascii=False, separators=(",", ":"))

        risk = self._object_thermal_risk(obj, peak_power)
        serial_time = access_time + readback_time
        phase_count_val = 3

        return CompilationVariant(
            variant_id=f"B_{target_id}_local_bist",
            task_id=task.task_id,
            target_id=target_id,
            target_kind=str(obj.get("object_type", "")),
            die_id=die_id,
            recipe_type="B",
            variant="local_bist",
            transport="local",
            phases="CONFIG_BIST|LOCAL_BIST_RUN|READ_BIST_RESULT",
            phase_resources=phases_raw,
            total_time_s=total_time,
            access_time_s=access_time,
            data_time_s=0.0,
            local_execution_time_s=local_time,
            readback_time_s=readback_time,
            serial_time_s=serial_time,
            fpp_time_s=0.0,
            peak_power_w=peak_power,
            access_power_w=access_power,
            thermal_risk=risk,
            thermal_load=peak_power * total_time
            * self.model.layer_conduction_factor(thermal_region)
            / self.model.cooling_factor(die_id),
            serial_access_required=True,
            fpp_lanes_required=0,
            max_fpp_lanes_required=0,
            lane_occupancy=0.0,
            fpp_channel="",
            dwr_segments=";".join(dwr_segments),
            route_resource="",
            estimated_bits=int(setup_bits + config_bits + readback_setup_bits + readout_bits),
            notes="local BIST releases external access resources during execution phase",
            test_method=bist_type_label,
            access_mechanism="LOCAL_BIST",
            test_endpoint="memory_bist" if bist_type_label == "MBIST" else "logic_bist",
            bist_type=bist_type_label,
            phase_count=phase_count_val,
            uses_tap_during_execute=False,
            fpp_lanes_needed=0,
            bist_engine_needed=test_session,
            test_session_group=test_session,
        )

    def _ijtag_variant(self, task: TestTask) -> CompilationVariant:
        obj = task._raw_obj
        die_id = task.die_id
        target_id = task.target_id
        instrument = obj.get("instrument", {})
        setup_bits = task.config_path_bits
        address_bits = task.config_test_bits
        readout_bits = task.read_result_bits

        access_power = float(obj.get("power", {}).get("access_power_w", 0.0))
        thermal_region = str(obj.get("thermal_region", ""))
        dwr_segments = self._required_dwr_segments(obj)

        access_time = self.model.serial_time_s(setup_bits + address_bits)
        readback_time = self.model.serial_time_s(readout_bits)
        total_time = access_time + readback_time
        peak_power = access_power

        phases_raw = json.dumps([
            {"phase_name": "CONFIG_ACCESS_PATH", "duration_s": self.model.serial_time_s(setup_bits),
             "serial_required": True, "fpp_lanes_required": 0, "fpp_channel": "",
             "dwr_segments": dwr_segments, "route_resource": "", "exclusive_resource": "",
             "power_w": access_power, "thermal_region": thermal_region, "notes": ""},
            {"phase_name": "ACCESS_INSTRUMENT", "duration_s": self.model.serial_time_s(address_bits),
             "serial_required": True, "fpp_lanes_required": 0, "fpp_channel": "",
             "dwr_segments": dwr_segments, "route_resource": "", "exclusive_resource": "",
             "power_w": access_power, "thermal_region": thermal_region, "notes": ""},
            {"phase_name": "READ_INSTRUMENT", "duration_s": readback_time,
             "serial_required": True, "fpp_lanes_required": 0, "fpp_channel": "",
             "dwr_segments": dwr_segments, "route_resource": "", "exclusive_resource": "",
             "power_w": access_power, "thermal_region": thermal_region, "notes": ""},
        ], ensure_ascii=False, separators=(",", ":"))

        risk = self._object_thermal_risk(obj, peak_power)
        serial_time = access_time + readback_time
        phase_count_val = 3

        return CompilationVariant(
            variant_id=f"IJTAG_{target_id}_serial",
            task_id=task.task_id,
            target_id=target_id,
            target_kind=str(obj.get("object_type", "")),
            die_id=die_id,
            recipe_type="IJTAG",
            variant="serial",
            transport="serial",
            phases="CONFIG_ACCESS_PATH|ACCESS_INSTRUMENT|READ_INSTRUMENT",
            phase_resources=phases_raw,
            total_time_s=total_time,
            access_time_s=access_time,
            data_time_s=0.0,
            local_execution_time_s=0.0,
            readback_time_s=readback_time,
            serial_time_s=serial_time,
            fpp_time_s=0.0,
            peak_power_w=peak_power,
            access_power_w=access_power,
            thermal_risk=risk,
            thermal_load=peak_power * total_time
            * self.model.layer_conduction_factor(thermal_region)
            / self.model.cooling_factor(die_id),
            serial_access_required=True,
            fpp_lanes_required=0,
            max_fpp_lanes_required=0,
            lane_occupancy=0.0,
            fpp_channel="",
            dwr_segments=";".join(dwr_segments),
            route_resource="",
            estimated_bits=int(setup_bits + address_bits),
            notes="serial instrument access",
            test_method="INSTRUMENT_READ",
            access_mechanism="PTAP_STAP_SERIAL",
            test_endpoint="instrument_tdr",
            bist_type="",
            phase_count=phase_count_val,
            uses_tap_during_execute=True,
            fpp_lanes_needed=0,
            bist_engine_needed="",
            test_session_group="",
        )

    def _intest_variants(self, task: TestTask) -> list[CompilationVariant]:
        obj = task._raw_obj
        die_id = task.die_id
        target_id = task.target_id
        dwr_segments = self._required_dwr_segments(obj)
        scan = obj.get("scan", {})
        stimulus_bits, response_bits = self._scan_bits(scan)
        setup_bits = task.config_path_bits
        mode_bits = task.config_test_bits
        capture_time = float(self.model.timing.get("capture_time_s", 0.0))
        update_time = float(self.model.timing.get("mode_update_time_s", 0.0))
        access_power = float(obj.get("power", {}).get("access_power_w", 0.0))
        thermal_region = str(obj.get("thermal_region", ""))
        test_session = self._test_session_resource(obj)
        dwr_bits = self.model.dwr_payload_bits(dwr_segments)

        variants: list[CompilationVariant] = []

        # -- serial variant (always available) --
        access_time = self.model.serial_time_s(setup_bits + mode_bits)
        data_time = self.model.serial_time_s(stimulus_bits + response_bits + dwr_bits)
        readback_time = self.model.serial_time_s(response_bits)
        total_time = access_time + data_time + capture_time + update_time

        shift_power = float(obj.get("power", {}).get("shift_power_w", 0.0)) + access_power
        capture_power = float(obj.get("power", {}).get("capture_power_w", 0.0)) + access_power
        peak_power = max(
            float(obj.get("power", {}).get("shift_power_w", 0.0)),
            float(obj.get("power", {}).get("capture_power_w", 0.0)),
        ) + access_power

        phases_raw = json.dumps([
            {"phase_name": "CONFIG_ACCESS_PATH",
             "duration_s": self.model.serial_time_s(setup_bits),
             "serial_required": True, "fpp_lanes_required": 0, "fpp_channel": "",
             "dwr_segments": dwr_segments, "route_resource": "", "exclusive_resource": "",
             "power_w": access_power, "thermal_region": thermal_region, "notes": ""},
            {"phase_name": "CONFIG_SCAN_OR_DWR_MODE",
             "duration_s": self.model.serial_time_s(mode_bits) + update_time,
             "serial_required": True, "fpp_lanes_required": 0, "fpp_channel": "",
             "dwr_segments": dwr_segments, "route_resource": "", "exclusive_resource": "",
             "power_w": access_power, "thermal_region": thermal_region, "notes": ""},
            {"phase_name": "SERIAL_SHIFT_IN",
             "duration_s": self.model.serial_time_s(stimulus_bits),
             "serial_required": True, "fpp_lanes_required": 0, "fpp_channel": "",
             "dwr_segments": dwr_segments, "route_resource": "", "exclusive_resource": test_session,
             "power_w": shift_power, "thermal_region": thermal_region, "notes": ""},
            {"phase_name": "CAPTURE",
             "duration_s": capture_time,
             "serial_required": False, "fpp_lanes_required": 0, "fpp_channel": "",
             "dwr_segments": dwr_segments, "route_resource": "", "exclusive_resource": test_session,
             "power_w": capture_power, "thermal_region": thermal_region, "notes": ""},
            {"phase_name": "SERIAL_SHIFT_OUT",
             "duration_s": self.model.serial_time_s(response_bits + dwr_bits),
             "serial_required": True, "fpp_lanes_required": 0, "fpp_channel": "",
             "dwr_segments": dwr_segments, "route_resource": "", "exclusive_resource": test_session,
             "power_w": shift_power, "thermal_region": thermal_region, "notes": ""},
        ], ensure_ascii=False, separators=(",", ":"))

        risk = self._object_thermal_risk(obj, peak_power)
        serial_time = access_time + data_time
        phase_count_val = 5
        estimated_bits = setup_bits + mode_bits + stimulus_bits + response_bits + dwr_bits

        variants.append(CompilationVariant(
            variant_id=f"S_{target_id}_serial",
            task_id=task.task_id,
            target_id=target_id,
            target_kind=str(obj.get("object_type", "")),
            die_id=die_id,
            recipe_type="S",
            variant="serial",
            transport="serial",
            phases="CONFIG_ACCESS_PATH|CONFIG_SCAN_OR_DWR_MODE|SERIAL_SHIFT_IN|CAPTURE|SERIAL_SHIFT_OUT",
            phase_resources=phases_raw,
            total_time_s=total_time,
            access_time_s=access_time,
            data_time_s=data_time,
            local_execution_time_s=0.0,
            readback_time_s=readback_time,
            serial_time_s=serial_time,
            fpp_time_s=0.0,
            peak_power_w=peak_power,
            access_power_w=access_power,
            thermal_risk=risk,
            thermal_load=peak_power * total_time
            * self.model.layer_conduction_factor(thermal_region)
            / self.model.cooling_factor(die_id),
            serial_access_required=True,
            fpp_lanes_required=0,
            max_fpp_lanes_required=0,
            lane_occupancy=0.0,
            fpp_channel="",
            dwr_segments=";".join(dwr_segments),
            route_resource="",
            estimated_bits=estimated_bits,
            notes="serial PTAP/STAP access to internal scan interface",
            test_method="ATPG_SCAN",
            access_mechanism="PTAP_STAP_SERIAL",
            test_endpoint="internal_scan",
            bist_type="",
            phase_count=phase_count_val,
            uses_tap_during_execute=True,
            fpp_lanes_needed=0,
            bist_engine_needed="",
            test_session_group=test_session,
        ))

        # -- FPP variants (one per lane option) --
        lane_options = self.model.fpp_lane_options(die_id, dwr_segments)
        channel = self._preferred_fpp_channel(obj if isinstance(obj, dict) else {})
        for lanes in lane_options:
            if not self._is_fpp_recipe_legal(obj if isinstance(obj, dict) else {}, lanes, channel, dwr_segments):
                continue

            fpp_config_bits = self.model.fpp_config_bits(channel)
            bandwidth = self.model.fpp_bandwidth_bps(channel, lanes)
            total_fpp_config_bits = fpp_config_bits
            access_time_fp = self.model.serial_time_s(setup_bits + total_fpp_config_bits + mode_bits)
            data_time_fp = (stimulus_bits + response_bits) / bandwidth
            total_time_fp = access_time_fp + data_time_fp + capture_time + update_time

            shift_power_fp = float(obj.get("power", {}).get("shift_power_w", 0.0)) + 0.03 * lanes + access_power
            capture_power_fp = float(obj.get("power", {}).get("capture_power_w", 0.0)) + access_power
            peak_power_fp = max(
                float(obj.get("power", {}).get("shift_power_w", 0.0)) + 0.03 * lanes,
                float(obj.get("power", {}).get("capture_power_w", 0.0)),
            ) + access_power
            risk_fp = self._object_thermal_risk(obj, peak_power_fp)

            phases_raw_fp = json.dumps([
                {"phase_name": "CONFIG_ACCESS_PATH",
                 "duration_s": self.model.serial_time_s(setup_bits),
                 "serial_required": True, "fpp_lanes_required": 0, "fpp_channel": "",
                 "dwr_segments": dwr_segments, "route_resource": "", "exclusive_resource": "",
                 "power_w": access_power, "thermal_region": thermal_region, "notes": ""},
                {"phase_name": "CONFIG_FPP",
                 "duration_s": self.model.serial_time_s(fpp_config_bits),
                 "serial_required": True, "fpp_lanes_required": 0, "fpp_channel": channel,
                 "dwr_segments": dwr_segments, "route_resource": "", "exclusive_resource": "",
                 "power_w": access_power, "thermal_region": thermal_region, "notes": ""},
                {"phase_name": "CONFIG_SCAN_OR_DWR_MODE",
                 "duration_s": self.model.serial_time_s(mode_bits) + update_time,
                 "serial_required": True, "fpp_lanes_required": 0, "fpp_channel": "",
                 "dwr_segments": dwr_segments, "route_resource": "", "exclusive_resource": "",
                 "power_w": access_power, "thermal_region": thermal_region, "notes": ""},
                {"phase_name": "FPP_SHIFT_IN",
                 "duration_s": stimulus_bits / bandwidth,
                 "serial_required": False, "fpp_lanes_required": lanes, "fpp_channel": channel,
                 "dwr_segments": dwr_segments, "route_resource": "", "exclusive_resource": test_session,
                 "power_w": shift_power_fp, "thermal_region": thermal_region, "notes": ""},
                {"phase_name": "CAPTURE",
                 "duration_s": capture_time,
                 "serial_required": False, "fpp_lanes_required": 0, "fpp_channel": "",
                 "dwr_segments": dwr_segments, "route_resource": "", "exclusive_resource": test_session,
                 "power_w": capture_power_fp, "thermal_region": thermal_region, "notes": ""},
                {"phase_name": "FPP_SHIFT_OUT",
                 "duration_s": response_bits / bandwidth,
                 "serial_required": False, "fpp_lanes_required": lanes, "fpp_channel": channel,
                 "dwr_segments": dwr_segments, "route_resource": "", "exclusive_resource": test_session,
                 "power_w": shift_power_fp, "thermal_region": thermal_region, "notes": ""},
            ], ensure_ascii=False, separators=(",", ":"))

            legality_note = self._fpp_legality_note(channel, lanes)
            serial_time_fp = self.model.serial_time_s(setup_bits + fpp_config_bits + mode_bits)
            fpp_time_fp = data_time_fp
            est_bits_fp = setup_bits + fpp_config_bits + mode_bits + stimulus_bits + response_bits

            variants.append(CompilationVariant(
                variant_id=f"F_{target_id}_lane{lanes}",
                task_id=task.task_id,
                target_id=target_id,
                target_kind=str(obj.get("object_type", "")),
                die_id=die_id,
                recipe_type="F",
                variant=f"lane{lanes}",
                transport="fpp",
                phases="CONFIG_ACCESS_PATH|CONFIG_FPP|CONFIG_SCAN_OR_DWR_MODE|FPP_SHIFT_IN|CAPTURE|FPP_SHIFT_OUT",
                phase_resources=phases_raw_fp,
                total_time_s=total_time_fp,
                access_time_s=access_time_fp,
                data_time_s=data_time_fp,
                local_execution_time_s=0.0,
                readback_time_s=response_bits / bandwidth,
                serial_time_s=serial_time_fp,
                fpp_time_s=fpp_time_fp,
                peak_power_w=peak_power_fp,
                access_power_w=access_power,
                thermal_risk=risk_fp,
                thermal_load=peak_power_fp * total_time_fp
                * self.model.layer_conduction_factor(thermal_region)
                / self.model.cooling_factor(die_id),
                serial_access_required=True,
                fpp_lanes_required=lanes,
                max_fpp_lanes_required=lanes,
                lane_occupancy=data_time_fp * lanes,
                fpp_channel=channel,
                dwr_segments=";".join(dwr_segments),
                route_resource="",
                estimated_bits=est_bits_fp,
                notes="FPP (IEEE 1838-2019 Clause 7, optional) parallel data transfer with serial configuration" + legality_note,
                test_method="ATPG_SCAN",
                access_mechanism="FPP_PARALLEL",
                test_endpoint="internal_scan",
                bist_type="",
                phase_count=6,
                uses_tap_during_execute=False,
                fpp_lanes_needed=lanes,
                bist_engine_needed="",
                test_session_group=test_session,
            ))

        return variants

    def _extest_variants(self, task: TestTask) -> list[CompilationVariant]:
        raw = task._raw_obj
        link = raw["link"]
        source_die = raw["source_die"]
        target_die = raw["target_die"]
        die_id = task.die_id
        dwr_segments = list(link.get("dwr_segments", []))
        payload_bits = int(link.get("estimated_test_bits", 0))
        setup_bits = task.config_path_bits
        mode_bits = task.config_test_bits
        dwr_bits = self.model.dwr_payload_bits(dwr_segments)
        capture_time = float(self.model.timing.get("capture_time_s", 0.0))
        update_time = float(self.model.timing.get("mode_update_time_s", 0.0))
        peak_power = float(link.get("power_w", 0.0))
        thermal_region = self.model.dies_by_id[die_id]["thermal"]["region_id"]
        route_resource = str(link.get("route_resource", ""))
        test_session = f"interconnect_session_{route_resource or link['link_id']}"
        access_power = 0.0

        variants: list[CompilationVariant] = []

        # -- serial variant --
        access_time = self.model.serial_time_s(setup_bits + mode_bits)
        data_time = self.model.serial_time_s(payload_bits * 2 + dwr_bits)
        readback_time = self.model.serial_time_s(payload_bits)
        total_time = access_time + data_time + capture_time + update_time

        phases_raw = json.dumps([
            {"phase_name": "CONFIG_ACCESS_PATH",
             "duration_s": self.model.serial_time_s(setup_bits),
             "serial_required": True, "fpp_lanes_required": 0, "fpp_channel": "",
             "dwr_segments": dwr_segments, "route_resource": "", "exclusive_resource": "",
             "power_w": access_power, "thermal_region": thermal_region, "notes": ""},
            {"phase_name": "CONFIG_DWR_MODE",
             "duration_s": self.model.serial_time_s(mode_bits) + update_time,
             "serial_required": True, "fpp_lanes_required": 0, "fpp_channel": "",
             "dwr_segments": dwr_segments, "route_resource": "", "exclusive_resource": "",
             "power_w": access_power, "thermal_region": thermal_region, "notes": ""},
            {"phase_name": "DWR_SHIFT_IN",
             "duration_s": self.model.serial_time_s(payload_bits),
             "serial_required": True, "fpp_lanes_required": 0, "fpp_channel": "",
             "dwr_segments": dwr_segments, "route_resource": route_resource,
             "exclusive_resource": test_session, "power_w": peak_power,
             "thermal_region": thermal_region, "notes": ""},
            {"phase_name": "DWR_CAPTURE",
             "duration_s": capture_time,
             "serial_required": False, "fpp_lanes_required": 0, "fpp_channel": "",
             "dwr_segments": dwr_segments, "route_resource": route_resource,
             "exclusive_resource": test_session, "power_w": peak_power,
             "thermal_region": thermal_region, "notes": ""},
            {"phase_name": "DWR_SHIFT_OUT",
             "duration_s": self.model.serial_time_s(payload_bits + dwr_bits),
             "serial_required": True, "fpp_lanes_required": 0, "fpp_channel": "",
             "dwr_segments": dwr_segments, "route_resource": route_resource,
             "exclusive_resource": test_session, "power_w": peak_power,
             "thermal_region": thermal_region, "notes": ""},
        ], ensure_ascii=False, separators=(",", ":"))

        risk = self._thermal_risk(die_id, thermal_region, peak_power, area_mm2=1.0)
        serial_time = access_time + data_time
        phase_count_val = 5
        estimated_bits = setup_bits + mode_bits + payload_bits * 2 + dwr_bits

        variants.append(CompilationVariant(
            variant_id=f"I_{link['link_id']}_serial_extest",
            task_id=task.task_id,
            target_id=str(link["link_id"]),
            target_kind="interconnect",
            die_id=die_id,
            recipe_type="I",
            variant="serial_extest",
            transport="serial",
            phases="CONFIG_ACCESS_PATH|CONFIG_DWR_MODE|DWR_SHIFT_IN|DWR_CAPTURE|DWR_SHIFT_OUT",
            phase_resources=phases_raw,
            total_time_s=total_time,
            access_time_s=access_time,
            data_time_s=data_time,
            local_execution_time_s=0.0,
            readback_time_s=readback_time,
            serial_time_s=serial_time,
            fpp_time_s=0.0,
            peak_power_w=peak_power,
            access_power_w=access_power,
            thermal_risk=risk,
            thermal_load=peak_power * total_time
            * self.model.layer_conduction_factor(thermal_region)
            / self.model.cooling_factor(die_id),
            serial_access_required=True,
            fpp_lanes_required=0,
            max_fpp_lanes_required=0,
            lane_occupancy=0.0,
            fpp_channel="",
            dwr_segments=";".join(dwr_segments),
            route_resource=route_resource,
            estimated_bits=estimated_bits,
            notes="DWR EXTEST interconnect recipe",
            test_method="EXTEST",
            access_mechanism="DWR_EXTEST",
            test_endpoint="interconnect_extest",
            bist_type="",
            phase_count=phase_count_val,
            uses_tap_during_execute=True,
            fpp_lanes_needed=0,
            bist_engine_needed="",
            test_session_group=test_session,
        ))

        return variants

    # -- Helpers (mirrors RecipeGenerator) --------------------------------

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

    def _test_session_resource(self, obj: dict[str, Any]) -> str:
        resource = obj.get("required_resources", {}).get("test_session_group")
        if resource:
            return str(resource)
        return f"test_session_{obj['die_id']}"

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
        self, obj: dict[str, Any], lanes: int, channel: str, dwr_segments: list[str]
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
            and str(obj.get("die_id", "")) in lane.get("connects", {}).get("dies", [])
        ]
        s2p_lanes = [
            lane for lane in channel_lanes
            if lane.get("direction") in {"secondary_to_primary", "bidirectional"}
            and str(obj.get("die_id", "")) in lane.get("connects", {}).get("dies", [])
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
        route_resource = str(link.get("route_resource", ""))
        test_session = f"interconnect_session_{route_resource or link['link_id']}"
        phase_list = [
            RecipePhase("CONFIG_ACCESS_PATH", self.model.serial_time_s(setup_bits), True, power_w=access_power, thermal_region=thermal_region),
            RecipePhase("CONFIG_DWR_MODE", self.model.serial_time_s(mode_bits) + update_time, True, dwr_segments=tuple(dwr_segments), power_w=access_power, thermal_region=thermal_region),
            RecipePhase("DWR_SHIFT_IN", self.model.serial_time_s(payload_bits), True, dwr_segments=tuple(dwr_segments), route_resource=route_resource, exclusive_resource=test_session, power_w=peak_power, thermal_region=thermal_region),
            RecipePhase("DWR_CAPTURE", capture_time, False, dwr_segments=tuple(dwr_segments), route_resource=route_resource, exclusive_resource=test_session, power_w=peak_power, thermal_region=thermal_region),
            RecipePhase("DWR_SHIFT_OUT", self.model.serial_time_s(payload_bits + dwr_bits), True, dwr_segments=tuple(dwr_segments), route_resource=route_resource, exclusive_resource=test_session, power_w=peak_power, thermal_region=thermal_region),
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
            route_resource=route_resource,
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
        test_session = self._test_session_resource(obj)

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
                RecipePhase("SERIAL_SHIFT_IN", self.model.serial_time_s(stimulus_bits), True, exclusive_resource=test_session, power_w=shift_power, thermal_region=thermal_region),
                RecipePhase("CAPTURE", capture_time, False, exclusive_resource=test_session, power_w=capture_power, thermal_region=thermal_region),
                RecipePhase("SERIAL_SHIFT_OUT", self.model.serial_time_s(response_bits + dwr_bits), True, dwr_segments=tuple(dwr_segments), exclusive_resource=test_session, power_w=shift_power, thermal_region=thermal_region),
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
        test_session = self._test_session_resource(obj)
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
            RecipePhase("FPP_SHIFT_IN", stimulus_bits / bandwidth, False, lanes, channel, tuple(dwr_segments), exclusive_resource=test_session, power_w=shift_power, thermal_region=thermal_region),
            RecipePhase("CAPTURE", capture_time, False, exclusive_resource=test_session, power_w=capture_power, thermal_region=thermal_region),
            RecipePhase("FPP_SHIFT_OUT", response_bits / bandwidth, False, lanes, channel, tuple(dwr_segments), exclusive_resource=test_session, power_w=shift_power, thermal_region=thermal_region),
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
            notes="FPP (IEEE 1838-2019 Clause 7, optional) parallel data transfer with serial configuration" + legality_note,
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
        test_session = self._test_session_resource(obj)
        bist_type = "MBIST" if obj.get("object_type") == "memory" else "LBIST"
        phase_list = [
            RecipePhase("CONFIG_BIST", access_time, True, power_w=access_power, thermal_region=thermal_region),
            RecipePhase("LOCAL_BIST_RUN", local_time, False, 0, exclusive_resource=test_session, power_w=peak_power, thermal_region=thermal_region, notes="external TAP resources released; local test session remains occupied"),
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
        test_session = self._test_session_resource(obj)
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
            RecipePhase("FPP_SHIFT_IN", stimulus_bits / bandwidth, False, lanes, channel, tuple(dwr_segments), exclusive_resource=test_session, power_w=shift_power, thermal_region=thermal_region),
            RecipePhase("CAPTURE", capture_time, False, exclusive_resource=test_session, power_w=capture_power, thermal_region=thermal_region),
            RecipePhase("FPP_SHIFT_OUT", response_bits / bandwidth, False, lanes, channel, tuple(dwr_segments), exclusive_resource=test_session, power_w=shift_power, thermal_region=thermal_region),
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
            notes="serial configuration + FPP (IEEE 1838-2019 Clause 7, optional) bulk transfer + short serial status/signature readback" + legality_note,
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

    def _test_session_resource(self, obj: dict[str, Any]) -> str:
        resource = obj.get("required_resources", {}).get("test_session_group")
        if resource:
            return str(resource)
        return f"test_session_{obj['die_id']}"

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
        "exclusive_resource",
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
                        "exclusive_resource": phase.get("exclusive_resource", ""),
                        "power_w": phase["power_w"],
                        "thermal_region": phase["thermal_region"],
                        "notes": phase["notes"],
                    }
                )
