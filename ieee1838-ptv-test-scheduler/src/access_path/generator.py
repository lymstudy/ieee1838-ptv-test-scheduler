"""Access path generator and timing estimator for B1."""

from __future__ import annotations

from dataclasses import replace

from src.access_path.model import (
    AccessOperation,
    AccessPath,
    AccessResource,
    StackAccessConfig,
)


class AccessPathGenerator:
    """Generate abstract IEEE 1838-compatible access paths.

    The generator estimates access overheads from configurable bit counts and
    bandwidths. It is intentionally abstract and not bit-accurate standard
    behavior.
    """

    def __init__(self, config: StackAccessConfig):
        self.config = config

    def estimate_ptap_shift_time(self, bits: int) -> float:
        """Estimate serial PTAP/STAP/DWR shift time in seconds."""

        if bits < 0:
            raise ValueError("bits cannot be negative")
        return bits / self.config.tck_frequency_hz

    def estimate_fpp_transfer_time(self, bits: int, lanes: int | None = None) -> float:
        """Estimate FPP bulk transfer time in seconds."""

        if bits < 0:
            raise ValueError("bits cannot be negative")
        active_lanes = self.config.fpp_lane_count if lanes is None else lanes
        if active_lanes <= 0:
            raise ValueError("lanes must be positive")
        if self.config.fpp_lane_count > 0 and active_lanes > self.config.fpp_lane_count:
            raise ValueError("requested lanes exceed configured FPP lane count")
        effective_bandwidth = self.config.fpp_bandwidth_bits_per_s * active_lanes
        return bits / effective_bandwidth

    def generate_path_to_die(self, target_die: int) -> AccessPath:
        """Generate a basic PTAP/STAP/3DCR access path to a target die."""

        self._validate_target_die(target_die)
        path_dies = self._path_dies_to(target_die)
        selected_staps = tuple(die for die in path_dies if die != self.config.first_die_id)
        bypassed_dies: tuple[int, ...] = ()
        required_3dcr_bits = len(path_dies) * self.config.three_dcr_bits_per_die
        stap_select_bits = len(selected_staps) * self.config.stap_select_bits_per_die
        bypass_bits = len(bypassed_dies) * self.config.bypass_bits_per_die

        operations: list[AccessOperation] = []
        occupied_resources = self._base_resources(path_dies)

        select_bits = self.config.ptap_instruction_bits
        operations.append(
            AccessOperation(
                op_id=f"select_path_die{target_die}",
                op_type="SELECT_DIE_PATH",
                target_die=target_die,
                involved_dies=path_dies,
                bit_length=select_bits,
                estimated_time=self.estimate_ptap_shift_time(select_bits),
                occupied_resources=(self._ptap_resource(),),
                description="Select stack-level path through the PTAP control path.",
            )
        )

        operations.append(
            AccessOperation(
                op_id=f"config_3dcr_die{target_die}",
                op_type="CONFIG_3DCR",
                target_die=target_die,
                involved_dies=path_dies,
                bit_length=required_3dcr_bits,
                estimated_time=self.estimate_ptap_shift_time(required_3dcr_bits),
                occupied_resources=tuple(
                    self._three_dcr_resource(die_id) for die_id in path_dies
                ),
                description="Configure abstract 3DCR select/bypass state along the path.",
            )
        )

        if stap_select_bits:
            operations.append(
                AccessOperation(
                    op_id=f"open_stap_die{target_die}",
                    op_type="OPEN_STAP",
                    target_die=target_die,
                    involved_dies=selected_staps,
                    bit_length=stap_select_bits,
                    estimated_time=self.estimate_ptap_shift_time(stap_select_bits),
                    occupied_resources=tuple(
                        self._stap_resource(die_id) for die_id in selected_staps
                    ),
                    description="Open STAP path segments needed to reach the target die.",
                )
            )

        access_bit_length = select_bits + required_3dcr_bits + stap_select_bits + bypass_bits
        estimated_access_time = sum(operation.estimated_time for operation in operations)
        return AccessPath(
            path_id=f"basic_die{target_die}",
            target_die=target_die,
            path_dies=path_dies,
            selected_staps=selected_staps,
            bypassed_dies=bypassed_dies,
            required_3dcr_bits=required_3dcr_bits,
            required_dwr_segments=(),
            required_fpp_lanes=0,
            access_bit_length=access_bit_length,
            estimated_access_time=estimated_access_time,
            operations=tuple(operations),
            occupied_resources=occupied_resources,
            notes="Basic PTAP/STAP/3DCR access path estimate.",
        )

    def generate_dwr_access_path(self, target_die: int, dwr_bits: int) -> AccessPath:
        """Generate a DWR access path including mode config, shift, and readback."""

        if dwr_bits <= 0:
            raise ValueError("dwr_bits must be positive")
        base_path = self.generate_path_to_die(target_die)
        dwr_segment = f"dwr_die{target_die}"
        dwr_resource = AccessResource(
            resource_type="DWR_SEGMENT",
            resource_id=dwr_segment,
            die_id=target_die,
            exclusive=True,
            description="Die Wrapper Register segment occupied by this access.",
        )
        config_bits = self.config.dwr_config_bits_per_die
        readback_bits = self.config.default_readback_bits
        extra_operations = (
            AccessOperation(
                op_id=f"config_dwr_die{target_die}",
                op_type="CONFIG_DWR_MODE",
                target_die=target_die,
                involved_dies=(target_die,),
                bit_length=config_bits,
                estimated_time=self.estimate_ptap_shift_time(config_bits),
                occupied_resources=(self._ptap_resource(), dwr_resource),
                description="Configure DWR mode for the target die.",
            ),
            AccessOperation(
                op_id=f"shift_dwr_die{target_die}",
                op_type="PTAP_SHIFT",
                target_die=target_die,
                involved_dies=(target_die,),
                bit_length=dwr_bits,
                estimated_time=self.estimate_ptap_shift_time(dwr_bits),
                occupied_resources=(self._ptap_resource(), dwr_resource),
                description="Shift DWR payload through the serial access path.",
            ),
            AccessOperation(
                op_id=f"readback_dwr_die{target_die}",
                op_type="READBACK",
                target_die=target_die,
                involved_dies=(target_die,),
                bit_length=readback_bits,
                estimated_time=self.estimate_ptap_shift_time(readback_bits),
                occupied_resources=(self._ptap_resource(), dwr_resource),
                description="Read back DWR response bits.",
            ),
        )
        operations = base_path.operations + extra_operations
        occupied_resources = self._dedupe_resources(base_path.occupied_resources + (dwr_resource,))
        return replace(
            base_path,
            path_id=f"dwr_die{target_die}_{dwr_bits}b",
            required_dwr_segments=(dwr_segment,),
            access_bit_length=base_path.access_bit_length + config_bits + dwr_bits + readback_bits,
            estimated_access_time=sum(operation.estimated_time for operation in operations),
            operations=operations,
            occupied_resources=occupied_resources,
            notes="DWR access adds wrapper mode configuration, serial shift, and readback overhead.",
        )

    def generate_fpp_data_path(
        self,
        target_die: int,
        data_bits: int,
        lanes: int | None = None,
    ) -> AccessPath:
        """Generate an FPP data path with PTAP/STAP setup overhead."""

        if data_bits <= 0:
            raise ValueError("data_bits must be positive")
        active_lanes = self.config.fpp_lane_count if lanes is None else lanes
        self.estimate_fpp_transfer_time(data_bits, active_lanes)

        base_path = self.generate_path_to_die(target_die)
        fpp_resources = tuple(self._fpp_lane_resource(index) for index in range(active_lanes))
        config_bits = self.config.fpp_config_bits
        fpp_transfer_time = self.estimate_fpp_transfer_time(data_bits, active_lanes)
        extra_operations = (
            AccessOperation(
                op_id=f"config_fpp_die{target_die}",
                op_type="CONFIG_FPP",
                target_die=target_die,
                involved_dies=base_path.path_dies,
                bit_length=config_bits,
                estimated_time=self.estimate_ptap_shift_time(config_bits),
                occupied_resources=(self._ptap_resource(),) + fpp_resources,
                description="Configure optional FPP data transport after PTAP/STAP setup.",
            ),
            AccessOperation(
                op_id=f"fpp_transfer_die{target_die}",
                op_type="FPP_TRANSFER",
                target_die=target_die,
                involved_dies=(target_die,),
                bit_length=data_bits,
                estimated_time=fpp_transfer_time,
                occupied_resources=fpp_resources,
                description="Transfer bulk test data over optional FPP lanes.",
            ),
        )
        operations = base_path.operations + extra_operations
        occupied_resources = self._dedupe_resources(base_path.occupied_resources + fpp_resources)
        return replace(
            base_path,
            path_id=f"fpp_die{target_die}_{data_bits}b_{active_lanes}lanes",
            required_fpp_lanes=active_lanes,
            access_bit_length=base_path.access_bit_length + config_bits + data_bits,
            estimated_access_time=sum(operation.estimated_time for operation in operations),
            operations=operations,
            occupied_resources=occupied_resources,
            notes=(
                "FPP is a data transport resource, not a universal control path; "
                "PTAP/STAP/FPP configuration overhead is still included."
            ),
        )

    def _validate_target_die(self, target_die: int) -> None:
        if not 0 <= target_die < self.config.die_count:
            raise ValueError(
                f"target_die must be in [0, {self.config.die_count - 1}], got {target_die}"
            )

    def _path_dies_to(self, target_die: int) -> tuple[int, ...]:
        first_die = self.config.first_die_id
        step = 1 if target_die >= first_die else -1
        return tuple(range(first_die, target_die + step, step))

    def _base_resources(self, path_dies: tuple[int, ...]) -> tuple[AccessResource, ...]:
        resources: list[AccessResource] = [self._ptap_resource()]
        resources.extend(self._stap_resource(die_id) for die_id in path_dies)
        resources.extend(self._three_dcr_resource(die_id) for die_id in path_dies)
        return self._dedupe_resources(tuple(resources))

    def _ptap_resource(self) -> AccessResource:
        return AccessResource(
            resource_type="PTAP_CONTROL_PATH",
            resource_id="ptap_control_path",
            die_id=self.config.first_die_id,
            exclusive=True,
            description="Primary stack-level test access control path.",
        )

    @staticmethod
    def _stap_resource(die_id: int) -> AccessResource:
        return AccessResource(
            resource_type="STAP_PATH",
            resource_id=f"stap_path_die{die_id}",
            die_id=die_id,
            exclusive=True,
            description="STAP path segment for a die in the access path.",
        )

    @staticmethod
    def _three_dcr_resource(die_id: int) -> AccessResource:
        return AccessResource(
            resource_type="THREE_DCR_CONFIG",
            resource_id=f"three_dcr_die{die_id}",
            die_id=die_id,
            exclusive=True,
            description="Abstract 3DCR configuration state for one die.",
        )

    @staticmethod
    def _fpp_lane_resource(lane_index: int) -> AccessResource:
        return AccessResource(
            resource_type="FPP_LANE",
            resource_id=f"fpp_lane{lane_index}",
            die_id=None,
            exclusive=False,
            description="Optional FPP lane used for bulk data transfer.",
        )

    @staticmethod
    def _dedupe_resources(resources: tuple[AccessResource, ...]) -> tuple[AccessResource, ...]:
        seen: set[tuple[str, str]] = set()
        deduped: list[AccessResource] = []
        for resource in resources:
            key = (resource.resource_type, resource.resource_id)
            if key not in seen:
                seen.add(key)
                deduped.append(resource)
        return tuple(deduped)
