"""ITC'02 parser + chiplet test case generator.

Parses ITC'02 SOC files, classifies modules into chiplet die types,
builds stacks for 2.5D/3D/5.5D topologies, generates test tasks,
and assembles a complete Case ready for scheduling.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from model import (
    Case,
    Chiplet,
    Stack,
    Task,
    TaskPhase,
    fpp_phase_duration_s,
    phase_duration_s,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Part A: ITC'02 Parser
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Itc02Test:
    """A single test record from an ITC'02 SOC file."""
    test_id: int
    scan_use: int
    tam_use: int
    patterns: int


@dataclass
class Itc02Module:
    """A module (core) parsed from an ITC'02 SOC file."""
    module_id: int
    level: int
    inputs: int
    outputs: int
    bidirs: int
    scan_chains: tuple[int, ...]
    tests: tuple[Itc02Test, ...]

    @property
    def pattern_count(self) -> int:
        return sum(t.patterns for t in self.tests)

    @property
    def chain_count(self) -> int:
        return len(self.scan_chains)

    @property
    def max_chain_length_bits(self) -> int:
        return max(self.scan_chains) if self.scan_chains else 0

    @property
    def total_chain_length_bits(self) -> int:
        return sum(self.scan_chains)


@dataclass
class Itc02Soc:
    """Parsed ITC'02 SOC file."""
    soc_name: str
    total_modules: int
    modules: tuple[Itc02Module, ...]

    @property
    def leaf_modules(self) -> list[Itc02Module]:
        """Modules that have at least one test (i.e., leaf cores)."""
        return [m for m in self.modules if m.tests]


def parse_soc_file(path: str) -> Itc02Soc:
    """Parse an ITC'02 SOC-format file and return an Itc02Soc."""
    text = Path(path).read_text()

    soc_name = ""
    total_modules = 0

    # Extract header (search across full text since fields are on different lines)
    name_match = re.search(r"SocName\s+(\S+)", text)
    if name_match:
        soc_name = name_match.group(1)

    tm_match = re.search(r"TotalModules\s+(\d+)", text)
    if tm_match:
        total_modules = int(tm_match.group(1))

    lines = text.splitlines()

    # First pass: parse module header lines to build module objects
    modules: dict[int, dict] = {}

    for line in lines:
        m = re.match(
            r"Module\s+(\d+)\s+Level\s+(\d+)\s+"
            r"Inputs\s+(\d+)\s+Outputs\s+(\d+)\s+"
            r"Bidirs\s+(\d+)\s+ScanChains\s+(\d+)\s*:\s*(.*)",
            line,
        )
        if m:
            mid = int(m.group(1))
            level = int(m.group(2))
            inputs = int(m.group(3))
            outputs = int(m.group(4))
            bidirs = int(m.group(5))
            n_chains = int(m.group(6))
            rest = m.group(7).strip()

            chains: tuple[int, ...] = ()
            if rest:
                chains = tuple(int(x) for x in rest.split())

            modules[mid] = {
                "module_id": mid,
                "level": level,
                "inputs": inputs,
                "outputs": outputs,
                "bidirs": bidirs,
                "scan_chains": chains,
                "tests": [],
            }

    # Second pass: parse test lines
    for line in lines:
        m = re.match(
            r"Module\s+(\d+)\s+Test\s+(\d+)\s+"
            r"ScanUse\s+(\d+)\s+TamUse\s+(\d+)\s+"
            r"Patterns\s+(\d+)",
            line,
        )
        if m:
            mid = int(m.group(1))
            test_id = int(m.group(2))
            scan_use = int(m.group(3))
            tam_use = int(m.group(4))
            patterns = int(m.group(5))
            if mid in modules:
                modules[mid]["tests"].append(
                    Itc02Test(test_id=test_id, scan_use=scan_use,
                              tam_use=tam_use, patterns=patterns)
                )

    # Build sorted list
    module_list: list[Itc02Module] = []
    for mid in sorted(modules.keys()):
        d = modules[mid]
        module_list.append(Itc02Module(
            module_id=d["module_id"],
            level=d["level"],
            inputs=d["inputs"],
            outputs=d["outputs"],
            bidirs=d["bidirs"],
            scan_chains=d["scan_chains"],
            tests=tuple(d["tests"]),
        ))

    return Itc02Soc(
        soc_name=soc_name,
        total_modules=total_modules,
        modules=tuple(module_list),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Part B: Module Classification
# ═══════════════════════════════════════════════════════════════════════════════

def classify_modules(soc: Itc02Soc, chiplet_count: int) -> list[dict]:
    """Classify ITC'02 leaf modules into chiplet die types.

    Takes the top `chiplet_count` leaf modules ranked by
    total_test_bits = total_chain_length_bits * pattern_count.

    Classification rules:
      - chain_count >= 16 and total_chain_length_bits > 500000 -> "large_logic"
      - chain_count > 0                                        -> "logic"
      - chain_count == 0 and pattern_count > 0                 -> "memory"
      - else                                                   -> "io"
    """
    leaves = soc.leaf_modules

    # Score each leaf by test volume.
    # For chain-based modules: total_chain_length_bits * pattern_count.
    # For memory modules (no chains, pattern-heavy): use patterns * 1000 as a proxy,
    # since BIST cycle count scales with patterns for combinational test.
    scored: list[tuple[int, Itc02Module]] = []
    for m in leaves:
        if m.chain_count > 0:
            total_bits = m.total_chain_length_bits * max(m.pattern_count, 1)
        else:
            # Memory / combinational: rank by pattern count (proxy for BIST effort)
            total_bits = m.pattern_count * 1000
        scored.append((total_bits, m))

    # Sort descending by test volume, take top N
    scored.sort(key=lambda x: x[0], reverse=True)
    selected = scored[:chiplet_count]

    result: list[dict] = []
    for _, m in selected:
        if m.chain_count >= 16 and m.total_chain_length_bits > 500_000:
            die_type = "large_logic"
        elif m.chain_count > 0:
            die_type = "logic"
        elif m.pattern_count > 0:
            die_type = "memory"
        else:
            die_type = "io"

        result.append({
            "module_id": m.module_id,
            "die_type": die_type,
            "chain_count": m.chain_count,
            "max_chain_length_bits": m.max_chain_length_bits,
            "total_chain_length_bits": m.total_chain_length_bits,
            "pattern_count": m.pattern_count,
            "inputs": m.inputs,
            "outputs": m.outputs,
            "bidirs": m.bidirs,
        })

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Part C: Stack Builder
# ═══════════════════════════════════════════════════════════════════════════════

def build_stacks(
    chiplets: list[Chiplet],
    topology: str,
    thermal_r_lo: float = 3.0,
    thermal_r_hi: float = 6.0,
) -> list[Stack]:
    """Organize chiplets into stacks based on topology.

    2.5D: single stack, all chiplets at layer 0 (side-by-side on interposer)
    3D:   single stack, layers 0..N-1 (vertical stack)
    5.5D: N/2 towers, each with 2 chiplets (layers 0,1 per tower)
          If N is odd, the last tower has 1 chiplet.

    thermal_r_lo/hi: C/W range. Bottom layer (closest to heat sink) gets lo;
                     upper layers get proportionally higher values.
    """
    if topology == "2.5D":
        # All chiplets in one stack at layer 0
        for c in chiplets:
            c.stack_id = "stack_0"
            c.layer_index = 0
            c.thermal_resistance_c_per_w = thermal_r_lo
        stack = Stack(
            stack_id="stack_0",
            topology=topology,
            chiplets=list(chiplets),
        )
        return [stack]

    elif topology == "3D":
        # Single stack, layers 0..N-1
        n = len(chiplets)
        for i, c in enumerate(chiplets):
            c.stack_id = "stack_0"
            c.layer_index = i
            frac = i / max(n - 1, 1)
            c.thermal_resistance_c_per_w = thermal_r_lo + (thermal_r_hi - thermal_r_lo) * frac
        stack = Stack(
            stack_id="stack_0",
            topology=topology,
            chiplets=list(chiplets),
        )
        return [stack]

    elif topology == "5.5D":
        # N/2 towers, 2 chiplets each (layers 0, 1)
        n = len(chiplets)
        num_towers = (n + 1) // 2  # ceil division for odd N
        stacks: list[Stack] = []
        idx = 0
        for tower_id in range(num_towers):
            tower_chiplets: list[Chiplet] = []
            layer = 0
            while layer < 2 and idx < n:
                c = chiplets[idx]
                c.stack_id = f"stack_{tower_id}"
                c.layer_index = layer
                frac = layer / 1.0  # layer is 0 or 1
                c.thermal_resistance_c_per_w = thermal_r_lo + (thermal_r_hi - thermal_r_lo) * frac * 0.5
                tower_chiplets.append(c)
                idx += 1
                layer += 1
            stacks.append(Stack(
                stack_id=f"stack_{tower_id}",
                topology=topology,
                chiplets=tower_chiplets,
            ))
        return stacks

    else:
        raise ValueError(f"Unknown topology: {topology}")


# ═══════════════════════════════════════════════════════════════════════════════
# Part D: Task Generator
# ═══════════════════════════════════════════════════════════════════════════════

def generate_tasks(
    chiplets: list[Chiplet],
    stacks: list[Stack],
    cfg: dict,
) -> list[Task]:
    """Generate test tasks for all chiplets.

    Per chiplet:
      - memory:      MBIST + INTEST
      - logic:       scan + INTEST
      - large_logic: LBIST + scan + INTEST
      - io:          INTEST only

    Also generates EXTEST tasks between adjacent chiplet pairs.
    """
    tasks: list[Task] = []
    ptap_tck = cfg["ptap_tck_hz"]
    fpp_bw = cfg["fpp_lane_bandwidth_bps"]
    bist_clk = cfg["bist_clock_hz"]
    cfg_bit_time = 64.0 / ptap_tck

    # Build quick lookup: chiplet_id -> chiplet
    cmap: dict[str, Chiplet] = {c.chiplet_id: c for c in chiplets}

    for c in chiplets:
        base_id = c.chiplet_id

        if c.die_type == "memory":
            # MBIST task
            tasks.append(_make_bist(
                c, base_id, "MBIST",
                cfg_bit_time, ptap_tck, fpp_bw, bist_clk, c.pattern_count, 2000,
            ))
            # INTEST task
            tasks.append(_make_intest(
                c, base_id, cfg_bit_time, ptap_tck, fpp_bw,
            ))

        elif c.die_type == "logic":
            # scan task
            tasks.append(_make_scan(
                c, base_id, cfg_bit_time, ptap_tck, fpp_bw,
            ))
            # INTEST task
            tasks.append(_make_intest(
                c, base_id, cfg_bit_time, ptap_tck, fpp_bw,
            ))

        elif c.die_type == "large_logic":
            # LBIST task
            tasks.append(_make_bist(
                c, base_id, "LBIST",
                cfg_bit_time, ptap_tck, fpp_bw, bist_clk, c.pattern_count, 80,
            ))
            # scan task
            tasks.append(_make_scan(
                c, base_id, cfg_bit_time, ptap_tck, fpp_bw,
            ))
            # INTEST task
            tasks.append(_make_intest(
                c, base_id, cfg_bit_time, ptap_tck, fpp_bw,
            ))

        elif c.die_type == "io":
            # INTEST only
            tasks.append(_make_intest(
                c, base_id, cfg_bit_time, ptap_tck, fpp_bw,
            ))

    # EXTEST tasks: between adjacent chiplet pairs
    for stack in stacks:
        st_chiplets = list(stack.chiplets)
        # Adjacent layers within same stack
        for i in range(len(st_chiplets)):
            for j in range(i + 1, len(st_chiplets)):
                a, b = st_chiplets[i], st_chiplets[j]
                if a.layer_index != b.layer_index and abs(a.layer_index - b.layer_index) == 1:
                    tasks.append(_make_extest(
                        a, b, cfg_bit_time, ptap_tck, fpp_bw, cmap,
                    ))

    # 5.5D: EXTEST between same-layer chiplets in different towers
    if cfg.get("topology") == "5.5D" and len(stacks) > 1:
        for layer_idx in range(2):
            layer_chiplets = [
                c for s in stacks
                for c in s.chiplets
                if c.layer_index == layer_idx
            ]
            for i in range(len(layer_chiplets)):
                for j in range(i + 1, len(layer_chiplets)):
                    tasks.append(_make_extest(
                        layer_chiplets[i], layer_chiplets[j],
                        cfg_bit_time, ptap_tck, fpp_bw, cmap,
                    ))

    return tasks


def _make_bist(
    c: Chiplet,
    base_id: str,
    task_type: str,
    cfg_bit_time: float,
    ptap_tck: float,
    fpp_bw: float,
    bist_clk: float,
    pattern_count: int,
    cycles_multiplier: int,
) -> Task:
    """Build MBIST or LBIST task (3 phases: CONFIG, EXECUTE, READOUT).

    For memory (MBIST): bist_cycles = pattern_count * cycles_multiplier
    For large_logic (LBIST): bist_cycles = total_chain_length_bits * cycles_multiplier
    """
    if c.die_type == "memory":
        # Memory BIST cycles scale with pattern count, not chain length
        bist_cycles = pattern_count * cycles_multiplier
    else:
        bist_cycles = c.total_chain_length_bits * cycles_multiplier

    phases = [
        TaskPhase(
            phase_index=0, phase_name="CONFIG",
            duration_s=cfg_bit_time,
            power_w=c.access_power_w,
            needs_tap=True, needs_fpp_lanes=0, needs_bist_engine=False,
        ),
        TaskPhase(
            phase_index=1, phase_name="EXECUTE",
            duration_s=bist_cycles / bist_clk if bist_clk > 0 else 0.0,
            power_w=c.bist_power_w,
            needs_tap=False, needs_fpp_lanes=0, needs_bist_engine=True,
        ),
        TaskPhase(
            phase_index=2, phase_name="READOUT",
            duration_s=128.0 / ptap_tck if ptap_tck > 0 else 0.0,
            power_w=c.access_power_w,
            needs_tap=True, needs_fpp_lanes=0, needs_bist_engine=False,
        ),
    ]
    return Task(
        task_id=f"{base_id}_{task_type}",
        chiplet_id=c.chiplet_id,
        stack_id=c.stack_id,
        task_type=task_type,
        phases=phases,
    )


def _make_scan(
    c: Chiplet,
    base_id: str,
    cfg_bit_time: float,
    ptap_tck: float,
    fpp_bw: float,
) -> Task:
    """Build scan task (4 phases: CONFIG, SHIFT_IN, CAPTURE, SHIFT_OUT).

    Scan chains: stimulus shift-in → capture → response shift-out.
    Shift data split 50/50 between in and out.
    """
    total_bits = c.total_chain_length_bits * max(c.pattern_count, 1)
    half_bits = total_bits / 2.0

    if c.has_fpp and c.fpp_lanes > 0:
        half_duration = fpp_phase_duration_s(half_bits, fpp_bw)
        shift_fpp_lanes = c.fpp_lanes
    else:
        half_duration = phase_duration_s(half_bits, ptap_tck)
        shift_fpp_lanes = 0

    phases = [
        TaskPhase(
            phase_index=0, phase_name="CONFIG",
            duration_s=cfg_bit_time,
            power_w=c.access_power_w,
            needs_tap=True, needs_fpp_lanes=0, needs_bist_engine=False,
        ),
        TaskPhase(
            phase_index=1, phase_name="SHIFT_IN",
            duration_s=half_duration,
            power_w=c.shift_power_w,
            needs_tap=(shift_fpp_lanes == 0),
            needs_fpp_lanes=shift_fpp_lanes,
            needs_bist_engine=False,
        ),
        TaskPhase(
            phase_index=2, phase_name="CAPTURE",
            duration_s=1e-6,
            power_w=c.capture_power_w,
            needs_tap=True, needs_fpp_lanes=0, needs_bist_engine=False,
        ),
        TaskPhase(
            phase_index=3, phase_name="SHIFT_OUT",
            duration_s=half_duration,
            power_w=c.shift_power_w,
            needs_tap=(shift_fpp_lanes == 0),
            needs_fpp_lanes=shift_fpp_lanes,
            needs_bist_engine=False,
        ),
    ]
    return Task(
        task_id=f"{base_id}_scan",
        chiplet_id=c.chiplet_id,
        stack_id=c.stack_id,
        task_type="scan",
        phases=phases,
    )


def _make_intest(
    c: Chiplet,
    base_id: str,
    cfg_bit_time: float,
    ptap_tck: float,
    fpp_bw: float,
) -> Task:
    """Build INTEST task (3 phases: CONFIG, SHIFT_IN, SHIFT_OUT).

    INTEST uses a smaller data volume (DWR boundary test).
    Estimate: (inputs + outputs + bidirs) * 32 bits * pattern_count, minimum 1000 bits.
    Data split 50/50 between stimulus and response.
    """
    boundary_bits = (c.inputs + c.outputs + c.bidirs) * 32
    # Use a reduced pattern count for boundary test (min 4 patterns)
    intest_patterns = max(c.pattern_count // 10, 4)
    total_bits = boundary_bits * intest_patterns
    total_bits = max(total_bits, 1000)
    half_bits = total_bits / 2.0

    if c.has_fpp and c.fpp_lanes > 0:
        half_duration = fpp_phase_duration_s(half_bits, fpp_bw)
        shift_fpp_lanes = c.fpp_lanes
    else:
        half_duration = phase_duration_s(half_bits, ptap_tck)
        shift_fpp_lanes = 0

    phases = [
        TaskPhase(
            phase_index=0, phase_name="CONFIG",
            duration_s=cfg_bit_time,
            power_w=c.access_power_w,
            needs_tap=True, needs_fpp_lanes=0, needs_bist_engine=False,
        ),
        TaskPhase(
            phase_index=1, phase_name="SHIFT_IN",
            duration_s=half_duration,
            power_w=0.5,  # Low power for boundary test
            needs_tap=(shift_fpp_lanes == 0),
            needs_fpp_lanes=shift_fpp_lanes,
            needs_bist_engine=False,
        ),
        TaskPhase(
            phase_index=2, phase_name="SHIFT_OUT",
            duration_s=half_duration,
            power_w=0.5,
            needs_tap=(shift_fpp_lanes == 0),
            needs_fpp_lanes=shift_fpp_lanes,
            needs_bist_engine=False,
        ),
    ]
    return Task(
        task_id=f"{base_id}_INTEST",
        chiplet_id=c.chiplet_id,
        stack_id=c.stack_id,
        task_type="INTEST",
        phases=phases,
    )


def _make_extest(
    a: Chiplet,
    b: Chiplet,
    cfg_bit_time: float,
    ptap_tck: float,
    fpp_bw: float,
    cmap: dict[str, Chiplet],
) -> Task:
    """Build EXTEST task between two chiplets (3 phases: CONFIG, SHIFT_IN, SHIFT_OUT).

    EXTEST tests inter-die connections. Data volume ~ min boundary of the two.
    Data split 50/50 in/out.
    """
    boundary_a = (a.inputs + a.outputs + a.bidirs) * 32
    boundary_b = (b.inputs + b.outputs + b.bidirs) * 32
    total_bits = min(boundary_a, boundary_b) * 10  # 10 patterns for interconnect
    total_bits = max(total_bits, 500)
    half_bits = total_bits / 2.0

    # Use the first chiplet's FPP/TAP resources
    shift_fpp_lanes = 0
    use_fpp = a.has_fpp and a.fpp_lanes > 0
    if use_fpp:
        half_duration = fpp_phase_duration_s(half_bits, fpp_bw)
        shift_fpp_lanes = a.fpp_lanes
    else:
        half_duration = phase_duration_s(half_bits, ptap_tck)

    task_id = f"{a.chiplet_id}_{b.chiplet_id}_EXTEST"

    phases = [
        TaskPhase(
            phase_index=0, phase_name="CONFIG",
            duration_s=cfg_bit_time,
            power_w=a.access_power_w,
            needs_tap=True, needs_fpp_lanes=0, needs_bist_engine=False,
        ),
        TaskPhase(
            phase_index=1, phase_name="SHIFT_IN",
            duration_s=half_duration,
            power_w=0.5,
            needs_tap=(shift_fpp_lanes == 0),
            needs_fpp_lanes=shift_fpp_lanes,
            needs_bist_engine=False,
        ),
        TaskPhase(
            phase_index=2, phase_name="SHIFT_OUT",
            duration_s=half_duration,
            power_w=0.5,
            needs_tap=(shift_fpp_lanes == 0),
            needs_fpp_lanes=shift_fpp_lanes,
            needs_bist_engine=False,
        ),
    ]
    return Task(
        task_id=task_id,
        chiplet_id=a.chiplet_id,  # primary chiplet
        stack_id=a.stack_id,
        task_type="EXTEST",
        phases=phases,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Part E: FPP Assignment
# ═══════════════════════════════════════════════════════════════════════════════

def assign_fpp(
    chiplets: list[Chiplet],
    total_fpp_lanes: int,
    fpp_probability: float,
    seed: str,
) -> None:
    """Deterministic FPP assignment, prioritizing largest test-volume chiplets.

    Chiplets are sorted by total_test_bits descending so the biggest
    scan-heavy dies get FPP lanes first.  Lane count is proportional
    to chain_count (more chains → more lanes to exploit parallelism).
    Total assigned lanes never exceeds total_fpp_lanes.
    All chiplets with chain_count > 0 get FPP (fpp_probability ignored
    for them — only combinational chiplets may be skipped).

    Mutates chiplets in place.
    """
    ordered = sorted(chiplets, key=lambda c: c.total_test_bits, reverse=True)
    assigned = 0

    for c in ordered:
        if assigned >= total_fpp_lanes:
            c.has_fpp = False
            c.fpp_lanes = 0
            continue

        # Combinational chiplets (chain_count=0): only assign if hash passes
        if c.chain_count == 0:
            h = abs(hash(seed + c.chiplet_id)) % 100
            if h >= int(fpp_probability * 100):
                c.has_fpp = False
                c.fpp_lanes = 0
                continue

        # Lane count: proportional to chain_count, min 1, max 4
        if c.chain_count >= 16:
            lanes = min(4, total_fpp_lanes - assigned)
        elif c.chain_count >= 8:
            lanes = min(2, total_fpp_lanes - assigned)
        else:
            lanes = min(1, total_fpp_lanes - assigned)

        c.has_fpp = True
        c.fpp_lanes = lanes
        assigned += lanes


# ═══════════════════════════════════════════════════════════════════════════════
# Part F: Main Entry Point
# ═══════════════════════════════════════════════════════════════════════════════

def generate_case(config_path: str) -> Case:
    """Load config JSON, parse SOC, generate complete Case.

    1. Read config JSON
    2. Parse SOC file from data/ directory (relative to config dir)
    3. Classify modules, select top chiplet_count
    4. Create Chiplet objects with power/thermal params
    5. Assign FPP
    6. Build stacks
    7. Generate tasks
    8. Return Case
    """
    config_path = Path(config_path)
    cfg = json.loads(config_path.read_text())

    # Resolve SOC file path relative to TESTSCHEDULE/ directory
    config_dir = config_path.parent
    project_dir = config_dir.parent  # TESTSCHEDULE/
    data_dir = project_dir / "data"
    soc_path = data_dir / cfg["soc_file"]

    # Parse SOC
    soc = parse_soc_file(str(soc_path))

    # Classify modules
    classified = classify_modules(soc, cfg["chiplet_count"])

    # Create Chiplet objects
    chiplets: list[Chiplet] = []
    for i, cls in enumerate(classified):
        chain_count = cls["chain_count"]

        # Power estimation — per-die values tuned so power budget binds meaningfully
        shift_power_w = max(chain_count * 0.35, 1.2)
        capture_power_w = shift_power_w * 0.9
        access_power_w = 0.8
        bist_power_w = shift_power_w * 0.6 if cls["die_type"] in ("memory", "large_logic") else 0.0

        # Thermal params — use low end of range initially, stack builder updates for layer
        tr_lo, tr_hi = cfg.get("thermal_resistance_range", [3.0, 6.0])
        tc_lo, tc_hi = cfg.get("thermal_capacitance_range", [0.005, 0.015])
        thermal_r = tr_lo
        thermal_c = (tc_lo + tc_hi) / 2

        chiplet = Chiplet(
            chiplet_id=f"die_{i}",
            stack_id="",  # assigned by build_stacks
            layer_index=0,  # assigned by build_stacks
            die_type=cls["die_type"],
            chain_count=chain_count,
            max_chain_length_bits=cls["max_chain_length_bits"],
            total_chain_length_bits=cls["total_chain_length_bits"],
            pattern_count=cls["pattern_count"],
            shift_power_w=shift_power_w,
            capture_power_w=capture_power_w,
            access_power_w=access_power_w,
            bist_power_w=bist_power_w,
            has_fpp=False,
            fpp_lanes=0,
            thermal_resistance_c_per_w=thermal_r,
            thermal_capacitance_j_per_c=thermal_c,
        )

        # Store ITC'02 attributes needed by task generator
        chiplet.inputs = cls["inputs"]
        chiplet.outputs = cls["outputs"]
        chiplet.bidirs = cls["bidirs"]

        chiplets.append(chiplet)

    # Assign FPP
    assign_fpp(
        chiplets,
        cfg["total_fpp_lanes"],
        cfg["fpp_probability"],
        cfg["case_id"],
    )

    # Build stacks (mutates chiplet stack_id / layer_index / thermal R)
    topology = cfg["topology"]
    tr_lo, tr_hi = cfg.get("thermal_resistance_range", [3.0, 6.0])
    stacks = build_stacks(chiplets, topology, tr_lo, tr_hi)

    # Generate tasks
    tasks = generate_tasks(chiplets, stacks, cfg)

    return Case(
        case_id=cfg["case_id"],
        topology=topology,
        stacks=stacks,
        chiplets=chiplets,
        tasks=tasks,
        total_fpp_lanes=cfg["total_fpp_lanes"],
        max_power_w=cfg["max_power_w"],
        max_temperature_c=cfg["max_temperature_c"],
        ambient_temperature_c=cfg["ambient_temperature_c"],
        ptap_tck_hz=cfg["ptap_tck_hz"],
        fpp_lane_bandwidth_bps=cfg["fpp_lane_bandwidth_bps"],
        bist_clock_hz=cfg.get("bist_clock_hz", 100e6),
    )
