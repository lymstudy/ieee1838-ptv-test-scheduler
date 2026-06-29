# CORRECTED PHYSICAL MODEL SPECIFICATION

**Status:** Specification (not yet implemented in code)
**Version:** 1.0
**Based on:** IEEE 1838-2019 standard audit + existing M1-M5/M22 code model analysis

---

## Table of Contents

1. [Why This Spec Exists](#1-why-this-spec-exists)
2. [The Correct Physical Abstraction](#2-the-correct-physical-abstraction)
3. [New Core Model: TestTask](#3-new-core-model-testtask)
4. [Design Decisions](#4-design-decisions)
5. [Resource Model](#5-resource-model)
6. [Scheduling Problem Statement (Corrected)](#6-scheduling-problem-statement-corrected)
7. [Migration Path](#7-migration-path)
8. [Paper Impact](#8-paper-impact)
9. [New Experiments Required](#9-new-experiments-required)
10. [Validation Checklist](#10-validation-checklist)

---

## 1. Why This Spec Exists

### 1.1 The Physics Error

The current "recipe" model treats five recipe types (S, F, B, H, I) as **mutually exclusive alternatives**. The greedy scheduler (M4) and CP-SAT scheduler (M5) both enforce the constraint "each target picks exactly one recipe" (`AddExactlyOne`).

This is physically wrong because:

1. **FPP and serial TAP are physically independent, not alternatives.** IEEE 1838 defines a serial TAP chain (TCK/TMS/TDI/TDO). FPP lanes (IEEE 1838 Clause 7, optional) use physically separate wires. They can operate simultaneously. The only shared resource across the entire stack is the single serial TAP chain.

2. **BIST is a different test type, not an alternative data path.** BIST executes locally on the die and releases the serial TAP during its local-execution phase. A die that has both scan chains and BIST engines needs both tested.

3. **The labels confuse test type with transport mechanism:**
   - `S` = INTEST via serial scan (combines test type + transport)
   - `F` = INTEST via FPP lanes (combines test type + transport)
   - `B` = BIST local test (different test type entirely)
   - `H` = BIST + FPP hybrid (combines two test types + transport)
   - `I` = EXTEST interconnect test (different test type entirely)

   A target does not "choose between S, F, B, H" -- the target has a set of **required test operations** (INTEST for scan, BIST for memories, EXTEST for interconnects), and each operation can use one or more **transport options** (serial shift, FPP parallel).

### 1.2 What the Code Already Gets Right

Even with the recipe abstraction error, many lower-level resource checks are correct:

| Aspect | Implementation | Correctness |
|--------|---------------|-------------|
| Single serial bottleneck | `ptap_ports=1`, `serial_required` on TAP-using phases | Correct |
| BIST releases TAP | `LOCAL_BIST_RUN` phase has `serial_required: false` | Correct |
| Phase precedence | Intra-recipe phase ordering enforced | Correct |
| DWR conflict groups | Shared DWR segments gated by capacity | Correct |
| FPP lane capacity | `AddCumulative` on lane count | Correct |
| Exclusive test sessions | `exclusive_resource` prevents co-execution on same die | Correct |
| Die-path hierarchy | `die_path_to()` computes cascaded STAP configuration cost | Correct |
| Access setup bits | PTAP control + STAP select + 3DCR register chain | Correct |

The error is in the **top-level abstraction** of recipes as alternatives, not in the low-level resource checks.

---

## 2. The Correct Physical Abstraction

### 2.1 The Serial TAP is the Single Shared Bottleneck

```
                PTAP (Die0, primary entry)
                  |
          ┌───────┴───────┐
          |  TDI → TDO    |  ← One serial chain for the ENTIRE stack
          └───────┬───────┘
                  |
           STAP (Die1)
          ┌───┴───┐
          |  TDI  |
          └───┬───┘
              |
           STAP (Die2)
          ┌───┴───┐
          |  TDI  |
          └───────┘

         Only one "shift" operation can be active on this chain at any instant.
         Configuration (3DCR writes) MUST go through this chain.
         Data transfer CAN go through this chain (serial shift) OR through FPP (if available).
```

### 2.2 Test Types (per die)

Each die supports a set of test operations defined by its hardware:

| Test Type | What it tests | Hardware required | IEEE 1838 mode |
|-----------|---------------|-------------------|----------------|
| **INTEST** | Internal die scan logic (cores, scan chains) | DWR inward-facing (IF) mode + internal scan access | INTEST instruction |
| **EXTEST** | Die-to-die interconnect (TSVs, microbumps) | DWR outward-facing (OF) mode on BOTH dies | EXTEST instruction |
| **BIST** | Internal memory/logic (built-in self-test) | BIST engine on die (design-specific, optional) | BIST instruction (optional) |
| **IJTAG** | Embedded instruments (IEEE 1687 network) | IEEE 1687 SIB network + instrument TDRs | IEEE 1687 via 1838 |

Each test type is **an independent test task**. A die may have multiple test tasks of different types (e.g., both INTEST for its scan chains AND BIST for its memories AND EXTEST for its interconnects).

### 2.3 Transport Options for Data Phase

For test types that require stimulus/response data transfer (INTEST, EXTEST):

| Transport | Mechanism | Occupies TAP during data phase? | Standard? |
|-----------|-----------|-------------------------------|-----------|
| **Serial shift** | Data shifted through PTAP/STAP chain | YES -- occupies the serial chain | IEEE 1838 standard |
| **FPP parallel** | Data through parallel FPP lanes | NO -- TAP released for other uses | IEEE 1838 Clause 7 (optional) |
| **Local (BIST)** | On-die test execution | NO -- TAP fully released | IEEE 1838 standard (design-specific) |

### 2.4 Test Task Life Cycle (all test types share this shape)

Every test task goes through four phases:

```
Phase 1: CONFIG_PATH    SHARED   Use serial TAP to reach target die
                                (PTAP + STAP selects + 3DCR writes)
                                Resource: occupies serial TAP

Phase 2: CONFIG_TEST    SHARED   Use serial TAP to set up the test
                                (load test instruction, configure DWR mode, start BIST)
                                Resource: occupies serial TAP

Phase 3: EXECUTE        VARIES   The actual test operation
                                INTEST serial:  shift data through TAP (occupies TAP)
                                INTEST FPP:     transfer data via FPP (releases TAP)
                                BIST:           local execution (releases TAP AND FPP)
                                EXTEST serial:  shift data through TAP (occupies TAP, uses both dies' DWR)

Phase 4: READ_RESULT     SHARED   Use serial TAP to read back test results
                                Resource: occupies serial TAP
```

The **key scheduling insight**: While one die's BIST is running locally (Phase 3), the TAP is FREE to configure and test another die. This is the fundamental source of parallelism in IEEE 1838 test scheduling -- time-multiplexing the serial TAP.

FPP extends this by also freeing the TAP during the INTEST/EXTEST data phase, creating additional scheduling opportunities.

---

## 3. New Core Model: TestTask

### 3.1 TestTask Definition

```python
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple


class TestType(str, Enum):
    """The test operation to perform. Defined by hardware, not by transport choice."""
    INTEST = "INTEST"       # Internal die test via DWR inward-facing mode
    EXTEST = "EXTEST"       # Interconnect test via DWR outward-facing mode
    BIST = "BIST"           # Built-in self-test (local execution)
    IJTAG = "IJTAG"         # IEEE 1687 instrument access


class Transport(str, Enum):
    """The data-transport mechanism for Phase 3 execute."""
    SERIAL = "serial"       # Data through PTAP/STAP serial chain
    FPP = "fpp"             # Data through FPP parallel lanes (IEEE 1838 Clause 7, optional)
    LOCAL = "local"         # Local on-die execution (BIST only, no external transport)


@dataclass(frozen=True)
class TestTask:
    """A single test operation on a target testable unit.

    Each TestTask represents ONE test type that must be performed
    on ONE targetable unit. A die may have multiple TestTasks of
    different types (e.g., both INTEST AND BIST for different units).

    The task is NOT a "recipe alternative" -- it is a mandatory
    scheduling unit. Transport choice (serial vs FPP) may create
    multiple CompilationVariants per task, but the task itself
    is not optional.
    """

    # ── Identity ──────────────────────────────────────────
    task_id: str                   # e.g., "die0_core0_intest"
    target_id: str                 # which testable unit (matches M1 test_objects.object_id)
    die_id: str                    # which die this target resides on
    test_type: TestType            # what kind of test this is

    # ── Phase timing (computed from physical parameters) ──
    config_path_bits: int          # TAP bits to configure the serial path to this die
                                   # (PTAP control + STAP select chain + 3DCR writes on path)
    config_test_bits: int          # TAP bits to set up the test itself
                                   # (DWR mode config + BIST config + instruction load)
    execute_serial_bits: int       # TAP bits if execute were done via serial
                                   # (stimulus + response for INTEST/EXTEST)
                                   # (0 for BIST -- local execution has no serial bits)
    execute_bist_cycles: int       # BIST clock cycles for local execution (0 for non-BIST)
    read_result_bits: int          # TAP bits to read back test results
                                   # (response bits for serial scan, pass/fail for BIST)

    # ── Computed timing ───────────────────────────────────
    config_path_time_s: float      # = config_path_bits / tck_hz
    config_test_time_s: float      # = config_test_bits / tck_hz
    execute_serial_time_s: float   # = execute_serial_bits / tck_hz
    execute_bist_time_s: float     # = execute_bist_cycles / bist_clock_hz
    read_result_time_s: float      # = read_result_bits / tck_hz

    # ── Resource consumption ──────────────────────────────
    power_w: float                 # peak power during execute phase
    access_power_w: float          # power during TAP configuration/read phases
    affected_dies: List[str]       # which dies' DWR resources are needed
                                   # INTEST: [target die]
                                   # EXTEST: [source_die, target_die]
                                   # BIST: [target die]
    dwr_segments: List[str]        # DWR segment IDs required
    thermal_region: str            # thermal region of the target
    bist_engine_group: str         # BIST engine group ID (empty for non-BIST)
    test_session_group: str        # exclusive test session group

    # ── FPP-related ───────────────────────────────────────
    fpp_capable: bool = False      # does this task have FPP lane connectivity?
    fpp_lanes_available: int = 0   # number of FPP lanes that can reach this target
    fpp_channel: str = ""          # which FPP channel connects to this target
    fpp_bandwidth_bps: float = 0.0 # aggregate FPP bandwidth for this target


@dataclass(frozen=True)
class CompilationVariant:
    """A specific execution plan for a TestTask.

    One TestTask may have multiple CompilationVariants that differ
    only in their transport choice for Phase 3. The task identity
    and test type are fixed; the variant only changes the resource
    footprint during execution.
    """

    task_id: str                   # references TestTask.task_id
    variant_id: str                # e.g., "die0_core0_intest_serial", "die0_core0_intest_fpp_4lane"
    transport: Transport           # "serial" | "fpp" | "local"

    # ── Phase breakdown with transport-specific timing ────
    # All variants share the same Phase 1,2,4 (TAP config/read)
    # Variants differ only in Phase 3 timing and resource occupancy

    phase_1_time_s: float          # CONFIG_PATH = always config_path_time_s (TAP occupied)
    phase_2_time_s: float          # CONFIG_TEST = always config_test_time_s (TAP occupied)
    phase_3_time_s: float          # EXECUTE = transport-dependent
    phase_4_time_s: float          # READ_RESULT = always read_result_time_s (TAP occupied)
    total_time_s: float            # sum of all phases

    # ── Resource signature per phase ──────────────────────
    # Phase 1: TAP=busy, FPP=free
    # Phase 2: TAP=busy, FPP=free
    # Phase 3: TAP = busy if transport=SERIAL else free
    #          FPP = busy if transport=FPP else free
    #          DWR = busy if test_type in {INTEST, EXTEST}
    #          BIST_engine = busy if test_type=BIST
    # Phase 4: TAP=busy, FPP=free

    fpp_lanes_used: int = 0        # FPP lanes occupied during Phase 3 (0 for serial/local)
    fpp_channel: str = ""          # FPP channel used (empty for serial/local)

    # other resource fields inherited from TestTask
    peak_power_w: float = 0.0
    thermal_region: str = ""
    dwr_segments: List[str] = ()
    affected_dies: List[str] = ()
    bist_engine_group: str = ""
    test_session_group: str = ""
```

### 3.2 How TestTask Replaces the Old Recipe Model

**Old model (recipe per target, mutually exclusive):**
```
Target "die0_core0":
  ├── S recipe: full serial INTEST,   total_time=1.2s
  ├── F recipe: FPP INTEST,           total_time=0.8s
  ├── B recipe: BIST,                 total_time=0.5s
  └── H recipe: BIST+check via FPP,   total_time=0.6s

Scheduler picks exactly ONE recipe per target.
```

**New model (task per test type, transport-choice creates variants):**
```
Target "die0_core0" -- required tests (2 independent tasks):
  Task 1: INTEST (scan test for internal logic -- REQUIRED)
    ├── Variant serial:  TAP-only, Phase3 occupies TAP, total=1.2s
    └── Variant fpp_4lane: FPP data, Phase3 releases TAP, total=0.8s

  Task 2: BIST (memory BIST -- REQUIRED)
    └── Variant local: Phase3 releases TAP, total=0.5s

Target "die0_memory0" -- required tests:
  Task 3: INTEST (scan test -- OPTIONAL if BIST covers it, depends on design)
    ...
  Task 4: BIST (MBIST -- REQUIRED)
    └── Variant local: Phase3 releases TAP, total=1.0s

Interconnect "die0_die1":
  Task 5: EXTEST (interconnect test -- REQUIRED, involves both dies)
    ├── Variant serial: Phase3 occupies TAP, uses DWR on die0 AND die1, total=0.3s
    └── Variant fpp_2lane: ...

Total mandatory tasks: 5 (if INTEST is mandatory for all scan targets).
Scheduler MUST schedule ALL tasks, choosing one variant per task.
```

### 3.3 Task Generation Rules

For each `test_object` in the `SystemModel` (M1 input):

| object_type | test_types generated | Rule |
|-------------|---------------------|------|
| `core` with scan | 1 INTEST task | Always required if scan data exists |
| `core` with BIST | 1 BIST task | Only if `bist.enabled = true` |
| `core` with both | 1 INTEST task + 1 BIST task | Both are independent mandatory tasks |
| `memory` with BIST | 1 BIST task | Only if `bist.enabled = true` |
| `memory` with scan AND BIST | 1 INTEST task + 1 BIST task | Both mandatory |
| `memory` with scan only | 1 INTEST task | Mandatory |
| `instrument` | 1 IJTAG task | Always required |

For each `interconnect` in the `SystemModel`:

| link | test_types generated | Rule |
|------|---------------------|------|
| any interconnect | 1 EXTEST task | Always required (involves both dies) |

Transport variants per task:

| Test Type | Transport Variants Generated | Condition |
|-----------|------------------------------|-----------|
| INTEST | `serial` | Always generated |
| INTEST | `fpp_{N}lane` (N in lane_options) | If FPP lanes reach this die |
| BIST | `local` | Always (only variant) |
| EXTEST | `serial` | Always generated |
| EXTEST | `fpp_{N}lane` | If FPP lanes reach the deeper die |
| IJTAG | `serial` | Always (only variant) |

---

## 4. Design Decisions

### 4.1 Decision A: BIST tasks are independent tasks, not "alternatives to scan"

**Rationale:** In real 3D-IC designs, a die may have both scan chains (for ATPG coverage of logic) and BIST engines (for memories or logic LBIST). These are complementary test strategies, not alternatives. The BIST engine tests the memory array; ATPG scan tests the surrounding logic and scan chains.

**Modeling implication:**
- BIST tasks and INTEST tasks are both created for a target that supports both.
- Each gets its own CompilationVariant(s).
- The scheduler schedules both independently.
- BIST's value in the scheduling problem is: Phase 3 is `Transport.LOCAL`, which **releases the serial TAP**, creating windows where other tasks can use the TAP.

**What changes from old model:**
- Old: `B` recipe was a mutually exclusive alternative to `S`/`F`/`H`
- New: BIST task co-exists with INTEST task; scheduler runs both
- The "BIST benefit" is now correctly measured as: total makespan with BIST tasks that release TAP during execution vs. a hypothetical scenario where all tasks use serial-only transport

### 4.2 Decision B: FPP is an optional IEEE 1838 standard component

**Rationale:** FPP IS defined in IEEE 1838-2019:
- Clause 5.5.3: "Flexible parallel port configuration register"
- Clause 6.5: "Parallel access to the DWR" -- optional parallel wrapper access mechanism called FPP
- Clause 7 (pages 57-66): Full specification of the Flexible Parallel Port
- FPP uses independent physical lanes, configured via TAP

**Modeling implication:**
- FPP is labeled as "IEEE 1838 Clause 7 (optional)" throughout the code and documentation
- All FPP-related fields have `fpp_` prefix to clearly distinguish from serial TAP resources
- The core scheduling mechanism (time-multiplexing the serial TAP) works without FPP
- FPP adds an additional optimization dimension: it frees the TAP during INTEST/EXTEST data phases

**What changes from old model:**
- Old: FPP was treated as a peer transport alongside serial, as if both were standard
- New: FPP is correctly identified as a standard-defined optional accelerator. Claims about scheduling gains are first made WITHOUT FPP (TAP time-multiplexing alone), then FPP is layered on as an optional feature that provides additional gains

### 4.3 Decision C: EXTEST is a cross-die task

**Rationale:** IEEE 1838 EXTEST requires DWR on both the driving die (output cells apply stimulus) and receiving die (input cells capture response). The old model treated I recipes as just another recipe type targeting a single die -- this is physically incomplete.

**Modeling implication:**
- EXTEST task has `affected_dies = [source_die, target_die]`
- EXTEST task consumes DWR segments on BOTH dies
- The transport variant (serial vs FPP) determines whether the serial TAP is occupied during data transfer
- EXTEST tasks involving the same die-pair but different interconnect links are independent tasks

**What changes from old model:**
- Old: I recipe assigned to one die (the "deeper" die)
- New: EXTEST task explicitly occupies two dies' resources

### 4.4 Decision D: Scheduling problem is "schedule all tasks" not "pick one per target"

**Old problem statement:**
> Select one recipe per target and schedule them

**New problem statement:**
> Schedule ALL test tasks (each die may have multiple tasks of different types) by
> time-multiplexing the serial TAP, exploiting BIST local-execution windows where the
> TAP is released, and optionally accelerating data transfer via FPP lanes (proposed
> extension). For each task, select one transport variant (serial, FPP, or local)
> that minimizes total makespan while respecting all resource constraints.

This means the scheduler now has TWO decisions per task:
1. **Variant choice**: Which transport variant (serial vs FPP N-lane vs local)?
2. **Timing**: When does each phase start?

The greedy scheduler's current `AddExactlyOne(per target)` constraint becomes:
- `AddExactlyOne(per task)` for variant selection
- Plus explicit modeling that multiple tasks can target the same die/unit

---

## 5. Resource Model

### 5.1 Shared Resources (capacity-limited)

| Resource | Capacity | Occupied By | When Released |
|----------|----------|-------------|---------------|
| **Serial TAP** | 1 (single chain) | Any phase with TAP activity (config, serial shift, readback) | Between phases; during BIST Phase 3; during FPP Phase 3 |
| **FPP lanes (per channel)** | `channel.max_lanes` | Phases using `transport=FPP` | Between phases; during non-FPP phases |
| **BIST engine (per group)** | `group.capacity` | Phase 3 of BIST tasks | Between BIST tasks |
| **DWR segment (per conflict group)** | `group.capacity` | Phases using DWR (INTEST, EXTEST) | Between phases |
| **Total power** | `max_total_power_w` | All active phases | Instantaneous (sum of active phase powers) |
| **Capture concurrency** | `max_concurrent_capture` | Capture phases | Instantaneous |
| **Test session (per die)** | 1 (exclusive) | Any test using that die's hardware | Between tests |

### 5.2 Resource Signature per Phase (table)

This table defines what each Phase 3 (EXECUTE) looks like for each combination of test type and transport:

| Test Type + Transport | TAP occupied? | FPP occupied? | DWR occupied? | BIST engine? | Affected dies |
|-----------------------|---------------|---------------|---------------|-------------|---------------|
| INTEST + serial | **YES** | NO | YES (target die) | NO | [target_die] |
| INTEST + FPP | NO | YES (N lanes) | YES (target die) | NO | [target_die] |
| EXTEST + serial | **YES** | NO | YES (both dies) | NO | [source_die, target_die] |
| EXTEST + FPP | NO | YES (N lanes) | YES (both dies) | NO | [source_die, target_die] |
| BIST + local | NO | NO | NO | YES (group) | [target_die] |
| IJTAG + serial | **YES** | NO | NO | NO | [target_die] |

Note: Phase 1 and Phase 4 ALWAYS occupy the TAP, regardless of transport. Phase 2 ALWAYS occupies the TAP. This means even an FPP-accelerated task still needs TAP access before and after its data phase.

### 5.3 TAP Time-Multiplexing -- The Core Mechanism

The fundamental scheduling mechanism is:

```
Time →
TAP:    |===Task1 P1===|===Task1 P2===|            |===Task1 P4===|===Task2 P1===|===Task2 P2===|===Task2 P3(TAP)===|...
               (Task1 is BIST; releases TAP during P3)
               TAP:    |===Task1 P1===|===Task1 P2===|
BIST:                            |============= Task1 P3 (local exec) ======================|
TAP:                                              |=== Task2 P1 ===|=== Task2 P2 ===|=== Task2 P3 (if serial) ===|...
```

Without BIST: TAP is 100% occupied end-to-end. Tasks serialize completely.
With BIST: TAP is freed during BIST local execution, allowing other tasks to use TAP.
With FPP: TAP is additionally freed during INTEST/EXTEST data phases.

---

## 6. Scheduling Problem Statement (Corrected)

### 6.1 Input

- **System model** (M1): dies, topology, test resources, resource limits
- **Set of mandatory TestTasks** (replaces recipe generation):
  - Generated from `test_objects` and `interconnects` in the system model
  - Each task has one or more `CompilationVariant`s (differing only in transport)
- **Resource capacities** from M1 `resource_limits`

### 6.2 Decisions

For each TestTask `t`:
1. Select exactly one `CompilationVariant` `v(t)` from `t.variants`
2. Assign start time `s(t, phase_i)` for each of the 4 phases (or fewer for simple tasks)

### 6.3 Constraints

1. **Phase precedence:** `s(t, phase_i) + duration(t, phase_i) <= s(t, phase_{i+1})`
2. **Serial TAP mutex:** At any instant, at most 1 phase with TAP occupied
3. **FPP lane capacity:** At any instant, sum(FPP lanes used) <= channel capacity
4. **BIST engine capacity:** At any instant, at most `group.capacity` BIST Phase-3 phases active in same `bist_engine_group`
5. **DWR conflict:** At any instant, at most `group.capacity` tasks using DWR segments in same conflict group
6. **Power limit:** At any instant, sum(active phase powers) <= `max_total_power_w`
7. **Capture concurrency:** At any instant, at most `max_concurrent_capture` capture phases active
8. **Test session exclusivity:** Per die, at most 1 task using that die's test session at any instant
9. **All tasks must be scheduled:** No task is optional.

### 6.4 Objective

Minimize **makespan**: `max(s(t, phase_last) + duration(t, phase_last))` over all tasks `t`.

Secondary objectives (in order):
- Minimize peak power
- Minimize thermal load on hottest region

### 6.5 Key Differences from Old Problem Statement

| Aspect | Old | New |
|--------|-----|-----|
| Unit of scheduling | Recipe (mutually exclusive per target) | TestTask (mandatory; each target may have multiple) |
| Choice per unit | Pick 1 recipe from {S,F,B,H,I} | Pick 1 transport variant per task |
| Number of scheduling units | = number of targets | >= number of targets (more if dual BIST+scan) |
| TAP modeling | `serial_required: true` on phases; mutex via capacity=1 | Same underlying check, but applied to per-phase TAP occupancy |
| BIST role | An "alternative recipe" | A mandatory task that happens to release TAP during execution |
| FPP role | An "alternative recipe" | A transport variant that releases TAP but occupies FPP lanes |
| EXTEST | A "recipe for interconnect target" | A task involving two dies' DWR resources |

---

## 7. Migration Path

### 7.1 What Stays the Same

| Component | Status | Notes |
|-----------|--------|-------|
| `SystemModel` (M1) | **Keep as-is** | The system model correctly describes dies, resources, access paths. The error is in recipe generation, not in the system description. |
| `system_model.py` | **Keep as-is** | All access-path computation (`die_path_to`, `access_setup_bits`, `fpp_lane_options`, etc.) remains valid. |
| `resource_limits` in JSON configs | **Keep as-is** | Capacity limits are physically correct. |
| `resource_groups` in JSON configs | **Keep as-is** | DWR conflict groups, BIST engine groups, thermal regions are correct. |
| Die topology (`dies`, `interconnects`, `staps`, `ptap`) | **Keep as-is** | Physical topology encoding is correct. |
| Phase-level constraint checks in greedy scheduler | **Keep the mechanisms** | `_resources_fit()`, `_dwr_groups_fit()`, `_bist_engine_groups_fit()`, `_exclusive_resources_fit()` all implement correct low-level physics. The wrapper that invokes them changes. |
| CP-SAT encoding of resources | **Keep the mechanisms** | The `AddNoOverlap`/`AddCumulative` constraint encodings are correct. The "exactly one per target" constraint changes to "exactly one variant per task (and all tasks must be scheduled)." |
| Pareto pruning (M3) | **Reframe** | Instead of pruning recipes across types, prune variants within each task. Same concept, different granularity. |
| M10 benchmark suite | **Keep source cases** | The 12 ITC'02-derived source cases and 3 topology types remain valid inputs. What changes is the task generation logic from those inputs, not the inputs themselves. |
| M11 algorithm study | **Keep structure** | Comparison framework (serial, fixed-fastest, greedy, CP-SAT, ALNS) remains. Results will change because the scheduling problem itself has changed. |
| M12 thermal validation | **Keep** | HotSpot integration is independent of recipe vs. task model. |
| M22 mechanism ablation | **Keep the conclusion, reframe the mechanism** | The 25.84% gain finding stays. The mechanism is reframed as "time-multiplexing the TAP via BIST release windows" rather than "joint path selection." |

### 7.2 What Changes

| Component | Change | Effort |
|-----------|--------|--------|
| `src/recipes/generator.py` | **Rewrite** as `src/tasks/generator.py` | Medium (3-5 days) |
| `src/recipes/__init__.py` | Rename to `src/tasks/` | Low |
| `TestAccessRecipe` dataclass | **Replace** with `TestTask` + `CompilationVariant` | Medium |
| `RecipePhase` dataclass | **Keep** but generated from task+variant instead of recipe | Low |
| `generate_m2_recipes.py` | **Rewrite** as `generate_tasks.py` | Low (1 day) |
| Greedy scheduler `greedy.py` | **Modify**: change grouping from `target_id` to `task_id`, change "pick one recipe per target" to "schedule all tasks, one variant each" | Medium (2-3 days) |
| CP-SAT scheduler (M5) | **Modify**: change `AddExactlyOne(per target)` to `AddExactlyOne(per task)` + add constraint that all tasks have at least one variant selected | Medium (2-3 days) |
| ALNS scheduler (M6) | **Modify** or **deprecate** (if ALNS is being downgraded per PAPER_REVISION_PLAN anyway) | Medium |
| M3 pareto pruner | **Modify**: prune variants within each task instead of recipes across types | Low (1 day) |
| CSV output schemas | **New fields**: `task_id`, `test_type`, `transport`, `affected_dies` | Low |
| CP-SAT encoding | **Modify**: per-task variant choice instead of per-target recipe choice | Medium (2 days) |
| All experiment runners (M4-M22) | **Modify**: input is task table not recipe table | Low per runner (1-2 days total) |

### 7.3 What Experiments Remain Valid (and how to reframe them)

| Experiment | Remains Valid? | Reframing Required |
|------------|---------------|-------------------|
| **M10 benchmark sweep** | YES -- same source cases, same topology, same coverage goal | Change from "recipe type sweep" to "transport-variant sweep"; recompute results |
| **M22 mechanism ablation** | YES -- same ablation conditions, same 192-row structure | Reframe from "BIST vs FPP path selection" to "BIST TAP-release windows + FPP TAP-offload windows combine" |
| **M11 algorithm study** | YES -- same comparison structure | Recomputed with task-model results |
| **M17 innovation support** | YES but needs recomputation | Reframe innovation claim as described in section 8 |
| **M18 pressure study** | Partially -- methodology still applies | Reframe pressure model to target TAP contention, not recipe-type choice |
| **M21 pressure suite** | Partially | Recompute on task-model results |
| **M12 thermal** | YES -- unchanged | No reframing needed |
| **M9 scenario expansion** | YES -- source data unchanged | No reframing needed |

### 7.4 Migration Order (Recommended)

1. **Phase 1 (model):** Create `TestTask` and `CompilationVariant` dataclasses. Write `src/tasks/generator.py` that reads M1 model and produces tasks+variants. Verify output matches expected task counts.
2. **Phase 2 (scheduler):** Modify greedy scheduler to work with tasks instead of recipes. Ensure all resource constraints still pass. Verify on a small 2-die case.
3. **Phase 3 (CP-SAT):** Update CP-SAT encoding for task-level variant selection. Verify produces same or better makespan than greedy.
4. **Phase 4 (experiments):** Rerun key experiments (M10 sweep, M22 ablation) with new model. Compare makespan values to old model.
5. **Phase 5 (docs + paper):** Update all model documentation. Rewrite paper narrative per PAPER_REVISION_PLAN section 2.

---

## 8. Paper Impact

### 8.1 New Core Claim

**Old claim:**
> "Joint path selection and scheduling reduces test time compared to fixed-path approaches"

**New claim:**
> "TAP time-multiplexed scheduling exploits BIST local-execution windows and optional FPP data-transport offloading to reduce total test time, under the constraint that the single serial TAP chain must be shared across all test configuration phases."

### 8.2 Innovation Reframing

| Innovation | Old Framing | New Framing |
|------------|-------------|-------------|
| Recipe abstraction | "S/F/B/H recipes as alternatives" | "TestTask+CompilationVariant: tasks are mandatory, variants differ in transport" |
| Joint scheduling | "Picking recipes and scheduling them" | "Scheduling all tasks by time-multiplexing the serial TAP" |
| BIST role | "One of several recipe options" | "BIST creates TAP-free windows during local execution -- the core scheduling opportunity" |
| FPP role | "An alternative data path (F recipe)" | "FPP offloads data-phase traffic from TAP, creating additional scheduling headroom" |
| Mechanism (M22) | "BIST vs FPP path selection" | "Time-multiplexing the TAP: BIST releases it (local execution), FPP offloads it (parallel data) -- two mechanisms that combine" |
| Thermal awareness | "Electro-thermal co-optimization" | Unchanged, but benefit is clearer because tasks have finer-grained phase structures |

### 8.3 M22 Reframing

The M22 finding (25.84% average gain in shared-BIST-with-parallel-escape scenario) is reframed:

**Old interpretation:** "Joint recipe selection works when you can choose BIST instead of FPP."
**New interpretation:** "When BIST tasks release the TAP during local execution (creating scheduling windows), and FPP variants offload the data phase from the TAP (freeing it further), the scheduler can interleave work across dies to reduce makespan. Neither mechanism alone is sufficient: without alternative data transport (FPP), the data phases still serialize on TAP; without BIST, there are no TAP-release windows to exploit."

### 8.4 Impact on Existing 7 Figures

| Figure | Status | Adjustment |
|--------|--------|------------|
| Fig 1 (concept) | New draw | Show TAP time-multiplexing timeline, not recipe alternatives |
| Fig 2 (benchmark coverage) | Minor update | Update bubble sizes based on task counts (higher than recipe counts) |
| Fig 3 (box plot) | Minor update | Re-plot from recomputed M22 data; same 4-way structure, slightly different gain values possible |
| Fig 4 (gradient) | Needs new data | Re-run pressure sweep with task model |
| Fig 5 (Gantt) | Redraw | Now shows tasks stacked, with TAP occupancy as a timeline row |
| Fig 6 (resource occupancy) | Minor update | Same concept, recomputed from task model schedules |
| Fig 7 (topology) | Minor update | Recompute from task model; relative ordering likely unchanged |
| Fig 8 (recipe mix) | **Repurposed** | Now shows "transport choice mix" (serial vs FPP vs local variants selected), not "recipe type mix." The visual structure (stacked bars) remains. |
| Fig 9 (literature baseline) | Needs new data | Recompute baselines on task model |
| Fig 10 (framework) | Minor update | Update pipeline blocks: "Task Generation" replaces "Recipe Generation" |

---

## 9. New Experiments Required

### 9.1 Immediate (needed with migration)

1. **Task-generation validation:** Verify that the task generator produces the correct number of tasks per die, correct variant counts, and correct phase timing from the same M1 input files.
2. **Baseline recomparison:** Run greedy + CP-SAT on the task model with the M10 source cases. Report makespan differences vs. old recipe model. (Expected: makespan will be HIGHER because more mandatory tasks, but the relative gains from BIST TAP-release scheduling should be clearer.)
3. **M22 re-execution:** Rerun the 4 ablation conditions on the task model. Verify the core finding (shared_bist_with_parallel_escape > 0% gain; others at 0%) still holds.

### 9.2 New Experiments Enabled by Corrected Model

1. **TAP utilization timeline:** Measure "serial TAP busy time / makespan" ratio. This metric was not meaningful in the old model because it was conflated with recipe-type choice. In the new model, it directly measures scheduling efficiency.
2. **BIST-window utilization:** What fraction of BIST execution time overlaps with TAP activity on other dies? This measures how well the scheduler exploits BIST TAP-release windows.
3. **Transport-mix sensitivity:** How does the serial/FPP/local variant mix change as FPP lane count varies? This replaces the old "recipe type mix" analysis with a physically meaningful alternative.

---

## 10. Validation Checklist

Before claiming correctness of the new model, verify:

- [ ] **Serial TAP mutex check is really about TAP occupancy, not recipe type.**
  Every phase with `transport != LOCAL` that does TAP I/O (`serial_required: true`) goes through the capacity-1 TAP resource. BIST Phase 3 has `serial_required: false` (already correct in old model).

- [ ] **BIST tasks release TAP during Phase 3.**
  Verified by: BIST Phase 3 has no `serial_required`, and the scheduler allows another task's TAP Phase to overlap with it.

- [ ] **FPP variants release TAP during Phase 3.**
  Verified by: FPP-execute Phase 3 has `serial_required: false` and occupies `fpp_lanes_required > 0`. A different task can use TAP during this phase.

- [ ] **All phases 1, 2, 4 always occupy TAP (even for FPP variants).**
  Verified by: `config_path_time_s`, `config_test_time_s`, and `read_result_time_s` phases all have `serial_required: true`. This is the key physical constraint -- FPP accelerates data only, not configuration.

- [ ] **EXTEST tasks occupy DWR on both dies.**
  Verified by: `affected_dies` contains both source and target. DWR conflict checks consider both dies' segments.

- [ ] **Multiple tasks on the same die are correctly handled.**
  Verified by: test session exclusivity (`test_session_group`) gates concurrent access to the same die's hardware, even if two tasks target the same die.

- [ ] **Variant selection is per-task, not per-target.**
  Verified by: scheduler selects exactly one variant for each TestTask (not one recipe per target). Multiple tasks for the same target (e.g., INTEST + BIST for `die0_core0`) each get their own variant selection.

---

## Appendix A: Comparison -- Old vs New Scheduling Problem

### Old (current code)
```
Input: Pareto recipe set from M3
 Units: targets (cores, memories, interconnects)
 Per target: pick 1 recipe from candidate set {S, F, B, H, I}
 Output: makespan, per-target recipe choice
```

### New (this spec)
```
Input: TestTask set generated from M1
 Units: TestTasks (may be multiple per target)
 Per task: pick 1 CompilationVariant from {serial, fpp_Nlane, local}
 Output: makespan, per-task variant choice, resource utilization timeline
```

### Example: 2-die stack with 3 targets

Old model:
```
Targets: die0_core0, die0_mem0, die1_core0
Recipes:
  die0_core0: S, F(1lane), F(4lane)  → scheduler picks 1
  die0_mem0:  S, B                    → scheduler picks 1
  die1_core0: S, F(1lane)             → scheduler picks 1
Total scheduling units: 3
```

New model:
```
Tasks:
  die0_core0_INTEST:  serial, fpp_1lane, fpp_4lane    → scheduler picks 1 variant
  die0_mem0_INTEST:   serial                            → scheduler picks serial
  die0_mem0_BIST:     local                             → scheduler picks local
  die1_core0_INTEST:  serial, fpp_1lane                 → scheduler picks 1 variant
Total scheduling units: 4 (more tasks, same physical targets)
```

---

## Appendix B: FPP Justification Language

Use this language in papers and documentation when mentioning FPP:

> "The Flexible Parallel Port (FPP) is an optional IEEE 1838-2019 standard component
> (Clause 7). FPP provides dedicated parallel lanes for test data transfer between dies,
> physically separate from the serial TAP control chain (TCK/TMS/TDI/TDO). FPP lanes
> are configured via the serial TAP and provide an accelerated data path while the TAP
> handles low-bandwidth control operations."

Key constraints to acknowledge:
1. FPP IS defined in IEEE 1838-2019 (Clauses 5.5.3, 6.5, 7) -- it is an optional standard component, not an extension
2. FPP lanes are optional -- the core scheduling mechanism (TAP time-multiplexing via BIST) works without FPP
3. FPP requires additional die-to-die physical wires -- increases interconnect cost
4. FPP does not replace the serial TAP for configuration -- Phases 1, 2, and 4 still need TAP

---

## Appendix C: Relationship to Existing Code Files

| File | Relationship |
|------|-------------|
| `src/model/system_model.py` | **Unchanged** -- reads M1 JSON, provides access-path computation |
| `src/recipes/generator.py` | **To be rewritten** as `src/tasks/generator.py` |
| `src/recipes/__init__.py` | **To be renamed** to `src/tasks/` |
| `src/schedulers/greedy.py` | **To be modified** -- task-level grouping, per-task variant selection |
| `src/schedulers/cp_sat.py` | **To be modified** -- per-task `AddExactlyOne`, all-tasks-scheduled constraint |
| `src/pareto/pruner.py` | **To be modified** -- prune variants within each task instead of recipes |
| `configs/cases/*.json` | **Unchanged** -- M1 system model is physically correct |
| `experiments/generate_m2_recipes.py` | **To be rewritten** as task generation |
| `experiments/run_m4_greedy_scheduler.py` | **To be modified** -- input is task table |
| `experiments/run_m5_refinement_scheduler.py` | **To be modified** -- input is task table |
| `experiments/run_m22_mechanism_ablation.py` | **To be modified** -- task model generation, re-execute |
| All other experiment runners | **To be modified** -- consume task output instead of recipe output |
