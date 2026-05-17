"""Expand high-level test intents into execution phases."""

from __future__ import annotations

from src.access_path import AccessPath, AccessPathGenerator, StackAccessConfig
from src.layered.intent import (
    BISTIntent,
    BaseTestIntent,
    BypassIntent,
    DWRExTestIntent,
    InstrumentAccessIntent,
    InternalScanIntent,
)
from src.layered.phase import ExecutionPhase, LayeredTask


class LayeredTaskExpander:
    """Expand TestIntent objects into phase-level LayeredTask objects."""

    def __init__(
        self,
        config: StackAccessConfig,
        access_path_generator: AccessPathGenerator | None = None,
    ):
        self.config = config
        self.access_path_generator = access_path_generator or AccessPathGenerator(config)

    def expand(self, intent: BaseTestIntent) -> LayeredTask:
        """Dispatch an intent to its phase expander."""

        if isinstance(intent, BISTIntent):
            return self.expand_bist(intent)
        if isinstance(intent, InternalScanIntent):
            return self.expand_internal_scan(intent)
        if isinstance(intent, DWRExTestIntent):
            return self.expand_dwr_extest(intent)
        if isinstance(intent, InstrumentAccessIntent):
            return self.expand_instrument_access(intent)
        if isinstance(intent, BypassIntent):
            return self.expand_bypass(intent)
        raise TypeError(f"unsupported intent type: {type(intent).__name__}")

    def expand_bist(self, intent: BISTIntent) -> LayeredTask:
        """Expand BIST into access, trigger, local run, re-access, and readback."""

        target_die = self._require_target_die(intent)
        access_path = self.access_path_generator.generate_path_to_die(target_die)
        phases: list[ExecutionPhase] = []
        phases.append(
            self._access_phase(
                intent,
                access_path,
                suffix="config",
                description="Configure access path for BIST trigger.",
            )
        )
        phases.append(
            self._phase(
                intent,
                "TRIGGER_BIST",
                target_die,
                (target_die,),
                self._ptap_time(intent.trigger_bits),
                intent.trigger_power,
                ("PTAP_CONTROL_PATH", f"LOCAL_BIST_ENGINE:die{target_die}"),
                uses_ptap=True,
                dependencies=(phases[-1].phase_id,),
                description="Trigger local BIST start through the PTAP/STAP access path.",
            )
        )
        phases.append(
            self._phase(
                intent,
                "LOCAL_BIST_RUN",
                target_die,
                (target_die,),
                intent.local_run_time,
                intent.local_power,
                (f"LOCAL_BIST_ENGINE:die{target_die}", f"POWER_DOMAIN:die{target_die}"),
                is_local_execution=True,
                dependencies=(phases[-1].phase_id,),
                description=(
                    "Local BIST execution. This phase does not occupy PTAP, "
                    "so future schedulers may overlap it with other die access phases."
                ),
            )
        )
        phases.append(
            self._access_phase(
                intent,
                access_path,
                suffix="readback_access",
                dependencies=(phases[-1].phase_id,),
                description="Re-configure access path for BIST result readback.",
            )
        )
        phases.append(
            self._phase(
                intent,
                "READ_BIST_RESULT",
                target_die,
                (target_die,),
                self._ptap_time(intent.result_bits),
                intent.readback_power,
                ("PTAP_CONTROL_PATH", f"LOCAL_BIST_ENGINE:die{target_die}"),
                uses_ptap=True,
                requires_readback=True,
                dependencies=(phases[-1].phase_id,),
                description="Read BIST result bits through the PTAP/STAP access path.",
            )
        )
        return self._layered_task(intent, phases, "BIST split into access, trigger, local execution, re-access, and readback.")

    def expand_internal_scan(self, intent: InternalScanIntent) -> LayeredTask:
        """Expand internal scan into config, FPP shift, capture, shift-out, and readback."""

        target_die = self._require_target_die(intent)
        access_path = self.access_path_generator.generate_path_to_die(target_die)
        phases: list[ExecutionPhase] = [
            self._access_phase(
                intent,
                access_path,
                suffix="config",
                description="Configure target die access path for internal scan.",
            )
        ]
        fpp_lanes = intent.fpp_lanes if intent.requires_fpp else 0
        data_bits = intent.scan_chain_length * intent.pattern_count
        config_resources = ["PTAP_CONTROL_PATH"]
        if intent.requires_fpp:
            config_resources.extend(self._fpp_resources(fpp_lanes))
        phases.append(
            self._phase(
                intent,
                "CONFIG_SCAN_FPP",
                target_die,
                (target_die,),
                self._ptap_time(self.config.fpp_config_bits if intent.requires_fpp else 0),
                intent.shift_power,
                tuple(config_resources),
                fpp_lanes=fpp_lanes,
                uses_ptap=True,
                uses_fpp=intent.requires_fpp,
                dependencies=(phases[-1].phase_id,),
                description="Configure scan/FPP data path before scan shift.",
            )
        )
        phases.append(
            self._phase(
                intent,
                "FPP_SHIFT_IN",
                target_die,
                (target_die,),
                self._data_transfer_time(data_bits, fpp_lanes),
                intent.shift_power,
                tuple(self._fpp_resources(fpp_lanes)) if intent.requires_fpp else ("PTAP_CONTROL_PATH",),
                fpp_lanes=fpp_lanes,
                uses_ptap=not intent.requires_fpp,
                uses_fpp=intent.requires_fpp,
                dependencies=(phases[-1].phase_id,),
                description="Shift scan stimulus data into the target die.",
            )
        )
        phases.append(
            self._phase(
                intent,
                "SCAN_CAPTURE",
                target_die,
                (target_die,),
                self._ptap_time(max(1, intent.pattern_count)),
                intent.capture_power,
                (f"POWER_DOMAIN:die{target_die}", f"THERMAL_REGION:die{target_die}"),
                is_capture_phase=True,
                dependencies=(phases[-1].phase_id,),
                description="Capture scan response; this phase contributes high transient current risk.",
            )
        )
        phases.append(
            self._phase(
                intent,
                "FPP_SHIFT_OUT",
                target_die,
                (target_die,),
                self._data_transfer_time(data_bits, fpp_lanes),
                intent.shift_power,
                tuple(self._fpp_resources(fpp_lanes)) if intent.requires_fpp else ("PTAP_CONTROL_PATH",),
                fpp_lanes=fpp_lanes,
                uses_ptap=not intent.requires_fpp,
                uses_fpp=intent.requires_fpp,
                dependencies=(phases[-1].phase_id,),
                description="Shift scan response data out of the target die.",
            )
        )
        if intent.readback_bits > 0:
            phases.append(
                self._phase(
                    intent,
                    "READBACK",
                    target_die,
                    (target_die,),
                    self._ptap_time(intent.readback_bits),
                    intent.shift_power,
                    ("PTAP_CONTROL_PATH",),
                    uses_ptap=True,
                    requires_readback=True,
                    dependencies=(phases[-1].phase_id,),
                    description="Optional scan status or result readback.",
                )
            )
        return self._layered_task(intent, phases, "Internal scan split into config, FPP shift, capture, shift-out, and optional readback.")

    def expand_dwr_extest(self, intent: DWRExTestIntent) -> LayeredTask:
        """Expand DWR EXTEST into wrapper config, shift, capture, and shift-out."""

        target_die = max(intent.src_die, intent.dst_die)
        access_path = self.access_path_generator.generate_path_to_die(target_die)
        involved = (intent.src_die, intent.dst_die)
        dwr_segment = f"dwr_die{intent.src_die}_die{intent.dst_die}"
        dwr_bits = intent.dwr_bits * intent.pattern_count
        phases: list[ExecutionPhase] = [
            self._access_phase(
                intent,
                access_path,
                suffix="config",
                target_die=target_die,
                involved_dies=involved,
                description="Configure access path to adjacent source/destination DWR wrappers.",
            )
        ]
        phases.append(
            self._phase(
                intent,
                "CONFIG_DWR_MODE",
                target_die,
                involved,
                self._ptap_time(self.config.dwr_config_bits_per_die * len(involved)),
                intent.shift_power,
                ("PTAP_CONTROL_PATH", f"DWR_SEGMENT:{dwr_segment}"),
                dwr_segment=dwr_segment,
                uses_ptap=True,
                uses_dwr=True,
                dependencies=(phases[-1].phase_id,),
                description="Configure DWR EXTEST mode on adjacent wrappers.",
            )
        )
        phases.append(
            self._phase(
                intent,
                "DWR_SHIFT_IN",
                target_die,
                involved,
                self._ptap_time(dwr_bits),
                intent.shift_power,
                ("PTAP_CONTROL_PATH", f"DWR_SEGMENT:{dwr_segment}"),
                dwr_segment=dwr_segment,
                uses_ptap=True,
                uses_dwr=True,
                dependencies=(phases[-1].phase_id,),
                description="Shift DWR EXTEST stimulus bits into wrapper registers.",
            )
        )
        phases.append(
            self._phase(
                intent,
                "DWR_CAPTURE",
                target_die,
                involved,
                self._ptap_time(max(1, intent.pattern_count)),
                intent.capture_power,
                (f"DWR_SEGMENT:{dwr_segment}", f"POWER_DOMAIN:die{intent.src_die}", f"POWER_DOMAIN:die{intent.dst_die}"),
                dwr_segment=dwr_segment,
                uses_dwr=True,
                is_capture_phase=True,
                dependencies=(phases[-1].phase_id,),
                description="Capture die-to-die interconnect response through DWR EXTEST.",
            )
        )
        shift_out_bits = intent.readback_bits if intent.readback_bits > 0 else dwr_bits
        phases.append(
            self._phase(
                intent,
                "DWR_SHIFT_OUT",
                target_die,
                involved,
                self._ptap_time(shift_out_bits),
                intent.shift_power,
                ("PTAP_CONTROL_PATH", f"DWR_SEGMENT:{dwr_segment}"),
                dwr_segment=dwr_segment,
                uses_ptap=True,
                uses_dwr=True,
                requires_readback=True,
                dependencies=(phases[-1].phase_id,),
                description="Shift out DWR EXTEST response bits.",
            )
        )
        return self._layered_task(intent, phases, "DWR EXTEST split into wrapper config, shift, capture, and shift-out.")

    def expand_instrument_access(self, intent: InstrumentAccessIntent) -> LayeredTask:
        """Expand instrument access into path config, network access, and readback."""

        target_die = self._require_target_die(intent)
        access_path = self.access_path_generator.generate_path_to_die(target_die)
        phases: list[ExecutionPhase] = [
            self._access_phase(
                intent,
                access_path,
                suffix="config",
                description="Configure target die access path for instrument access.",
            )
        ]
        network_bits = max(1, intent.network_depth) * intent.register_bits
        readback_bits = intent.readback_bits if intent.readback_bits > 0 else 0
        phases.append(
            self._phase(
                intent,
                "ACCESS_INSTRUMENT",
                target_die,
                (target_die,),
                self._ptap_time(network_bits + readback_bits),
                intent.access_power,
                ("PTAP_CONTROL_PATH", f"INSTRUMENT_NETWORK:die{target_die}:{intent.instrument_id}"),
                uses_ptap=True,
                dependencies=(phases[-1].phase_id,),
                description=(
                    "Access instrument network. Later models may replace this with "
                    "SIB hierarchical or daisy-chain network timing."
                ),
            )
        )
        if intent.access_type.lower() == "read" or intent.readback_bits > 0:
            bits = intent.readback_bits if intent.readback_bits > 0 else intent.register_bits
            phases.append(
                self._phase(
                    intent,
                    "READBACK",
                    target_die,
                    (target_die,),
                    self._ptap_time(bits),
                    intent.access_power,
                    ("PTAP_CONTROL_PATH", f"INSTRUMENT_NETWORK:die{target_die}:{intent.instrument_id}"),
                    uses_ptap=True,
                    requires_readback=True,
                    dependencies=(phases[-1].phase_id,),
                    description="Optional instrument register readback/status phase.",
                )
            )
        return self._layered_task(intent, phases, "Instrument access split into path config, network access, and optional readback.")

    def expand_bypass(self, intent: BypassIntent) -> LayeredTask:
        """Expand a bypass intent into a BYPASS_CONFIG phase."""

        target_die = intent.target_die if intent.target_die is not None else intent.bypassed_die
        phases = [
            self._phase(
                intent,
                "BYPASS_CONFIG",
                target_die,
                (intent.bypassed_die,),
                self._ptap_time(intent.bypass_bits),
                intent.estimated_power,
                ("PTAP_CONTROL_PATH", f"BYPASS_PATH:die{intent.bypassed_die}"),
                uses_ptap=True,
                description="Configure abstract bypass bits for a non-target die.",
            )
        ]
        return self._layered_task(intent, phases, "Bypass intent expanded to a single bypass configuration phase.")

    def _access_phase(
        self,
        intent: BaseTestIntent,
        access_path: AccessPath,
        suffix: str,
        dependencies: tuple[str, ...] | None = None,
        target_die: int | None = None,
        involved_dies: tuple[int, ...] | None = None,
        description: str = "",
    ) -> ExecutionPhase:
        return self._phase(
            intent,
            "CONFIG_ACCESS_PATH",
            access_path.target_die if target_die is None else target_die,
            access_path.path_dies if involved_dies is None else involved_dies,
            access_path.estimated_access_time,
            intent.estimated_power,
            self._path_resources(access_path),
            uses_ptap=True,
            dependencies=dependencies if dependencies is not None else intent.dependencies,
            description=description,
            suffix=suffix,
        )

    def _phase(
        self,
        intent: BaseTestIntent,
        phase_type: str,
        target_die: int | None,
        involved_dies: tuple[int, ...],
        duration: float,
        power: float,
        occupied_resources: tuple[str, ...],
        *,
        fpp_lanes: int = 0,
        dwr_segment: str | None = None,
        uses_ptap: bool = False,
        uses_fpp: bool = False,
        uses_dwr: bool = False,
        is_local_execution: bool = False,
        is_capture_phase: bool = False,
        requires_readback: bool = False,
        dependencies: tuple[str, ...] = (),
        description: str = "",
        suffix: str | None = None,
    ) -> ExecutionPhase:
        phase_index = suffix or phase_type.lower()
        return ExecutionPhase(
            phase_id=f"{intent.intent_id}:{phase_index}",
            parent_intent_id=intent.intent_id,
            phase_type=phase_type,
            target_die=target_die,
            involved_dies=involved_dies,
            duration=duration,
            power=power,
            occupied_resources=occupied_resources,
            fpp_lanes=fpp_lanes,
            dwr_segment=dwr_segment,
            uses_ptap=uses_ptap,
            uses_fpp=uses_fpp,
            uses_dwr=uses_dwr,
            is_local_execution=is_local_execution,
            is_capture_phase=is_capture_phase,
            requires_readback=requires_readback,
            dependencies=dependencies,
            description=description,
        )

    @staticmethod
    def _layered_task(
        intent: BaseTestIntent,
        phases: list[ExecutionPhase],
        notes: str,
    ) -> LayeredTask:
        return LayeredTask(
            layered_task_id=f"layered_{intent.intent_id}",
            parent_intent=intent,
            phases=tuple(phases),
            notes=notes,
        )

    def _ptap_time(self, bits: int) -> float:
        return self.access_path_generator.estimate_ptap_shift_time(max(0, bits))

    def _data_transfer_time(self, bits: int, fpp_lanes: int) -> float:
        if fpp_lanes > 0:
            return self.access_path_generator.estimate_fpp_transfer_time(bits, fpp_lanes)
        return self._ptap_time(bits)

    @staticmethod
    def _path_resources(path: AccessPath) -> tuple[str, ...]:
        return tuple(
            f"{resource.resource_type}:{resource.resource_id}"
            for resource in path.occupied_resources
        )

    @staticmethod
    def _fpp_resources(fpp_lanes: int) -> list[str]:
        return [f"FPP_LANE:fpp_lane{lane_index}" for lane_index in range(fpp_lanes)]

    @staticmethod
    def _require_target_die(intent: BaseTestIntent) -> int:
        if intent.target_die is None:
            raise ValueError(f"{intent.intent_id} requires target_die")
        return intent.target_die
