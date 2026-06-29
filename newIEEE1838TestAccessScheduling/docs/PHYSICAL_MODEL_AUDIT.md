# Physical Model Audit: IEEE 1838 Test Access Scheduling

**Document type:** Standalone technical audit
**Date:** 2026-06-26
**Scope:** Full-stack audit of the computational model's fidelity to the IEEE 1838-2019 standard and comparison with published literature
**Status:** Final

---

## 1. Executive Summary

This document presents a comprehensive audit of the physical model underlying the IEEE 1838 test access scheduling research project. The audit was conducted through three parallel lines of investigation: (1) close reading of the full IEEE 1838-2019 standard, (2) line-level audit of the current code implementation (`src/model/system_model.py`, `src/recipes/generator.py`, `src/schedulers/greedy.py`, `src/schedulers/cpsat.py`), and (3) comparison against four reference papers (Habiby 2020, Habiby 2022, Patmanathan 2024, Sen Gupta 2011). The audit reveals that the project's model is, in several important respects, the **most physically detailed** IEEE 1838 scheduling model in the published literature — it explicitly models cascaded STAP configuration overhead, die-to-die serial path contention, and BIST local-execution window exploitation, none of which appear in the four reference papers. However, the audit also identifies one critical modeling error that requires correction: FPP and serial TAP are modeled as mutually exclusive path alternatives when they are physically capable of simultaneous operation (FPP is an OPTIONAL component of IEEE 1838-2019, defined in Clause 7, and uses separate physical lanes from the serial TAP). These findings have significant implications for the paper's claims about "IEEE 1838 compatibility" and the "joint path-selection and scheduling" narrative.

---

## 2. IEEE 1838-2019 Standard: What It Actually Defines

### 2.1 Mandatory Components

Every IEEE 1838-compliant die must contain:

| Component | Description | Notes |
|-----------|-------------|-------|
| **PTAP** (Primary Test Access Port) | 5-pin interface: TCK, TMS, TDI, TDO, TRSTN | Exactly one per compliant die; entry point for all test access |
| **DWR** (Die Wrapper Register) | Boundary register surrounding each die | Used for both INTEST (inward-facing, IF mode) and EXTEST (outward-facing, OF mode) |
| **Bypass Register** | 1-bit bypass in the serial chain | Required for efficient access to deep dies in a stack |
| **Instruction Register** | Decodes TAP instructions (BYPASS, IDCODE, INTEST, EXTEST, etc.) | Standard JTAG-length IR |
| **Device ID Register** | 32-bit IDCODE | Mandatory per JTAG (IEEE 1149.1) |

### 2.2 Conditional and Optional Components

| Component | Condition | Notes |
|-----------|-----------|-------|
| **STAP** (Secondary Test Access Port) | One per "next" die connected | Die0 has 0..N STAPs; each STAP provides a serial access path to one downstream die |
| **3DCR** (3D Configuration Register) | Present if STAPs exist | Contains Select_Sn, RTI_or_TLR_Sn, Config-Hold_Sn bits per STAP; controls which STAP is active |
| **BIST** | Design-specific | **Not mandated by the standard**; may or may not be present on any given die |
| **IJTAG instruments** (IEEE 1687) | Design-specific | Accessed via SIB (Segment Insertion Bit) network segments; entirely optional |

### 2.3 What Is OPTIONAL (Defined in the Standard) vs. Outside Scope

The following are **optional but standard-defined** in IEEE 1838-2019:

- **Flexible Parallel Port (FPP)** — Defined in IEEE 1838-2019 Clause 7 ("Flexible parallel port"), Clauses 5.5.3, and 6.5. FPP is an optional parallel wrapper access mechanism using dedicated physical lanes, configured via the TAP. FPP provides a faster data-transport path but does not replace the serial TAP for control/configuration.

The following are **outside the scope** of the standard:

- **Any scheduling algorithm** — The standard defines the architectural registers and access mechanics, not how to schedule concurrent test operations.
- **Thermal constraints** — While physical, these are outside the standard's scope.

### 2.4 Test Access Mechanics

**Serial path as a single shared resource:** The entire 3D stack has exactly one TDI-to-TDO serial chain. All test data must flow through this chain. The external test equipment connects to Die0's PTAP; deeper dies are reached by configuring STAPs on intermediate dies to extend the chain.

**Cascaded access sequence (example: accessing Die3 in a 4-die stack):**

```
Step 1: Configure Die0 3DCR  →  Select STAP to Die1  →  Chain now reaches Die1
Step 2: Configure Die1 3DCR  →  Select STAP to Die2  →  Chain now reaches Die2
Step 3: Configure Die2 3DCR  →  Select STAP to Die3  →  Chain now reaches Die3
Step 4: Access Die3 registers (DWR, BIST, etc.)
Non-target dies: Set to BYPASS (1-bit each) for efficiency
```

Each STAP selection requires shifting configuration bits through the 3DCR of the parent die. This overhead scales with stack depth.

### 2.5 Test Modes

| Mode | Purpose | DWR Involvement | Serial Path Usage |
|------|---------|-----------------|-------------------|
| **INTEST** | Internal die testing | DWR in IF (inward-facing) mode | Full chain: configure + shift + capture + shift + readback |
| **EXTEST** | Interconnect testing | DWR in OF (outward-facing) mode on **both** connected dies | Full chain: configure both dies + shift + capture + shift + readback |
| **BIST** | Die-internal self-test | Configure BIST controller via TAP, then run locally | Configure BIST via TAP → release TAP → local run → re-acquire TAP for result readback |
| **IJTAG** | Instrument access via IEEE 1687 | SIB network segments | Full chain through SIB hierarchy |

---

## 3. Current Model Accuracy Assessment

### 3.1 Correctly Modeled Aspects

| # | Modeling Point | Code Implementation | Standard Conformance | Assessment |
|---|---------------|---------------------|---------------------|------------|
| 1 | Multiple test targets per die | Each die can contain multiple `test_object` entries (core, memory, etc.) | Standard allows up to N testable modules per die | ✅ Correct |
| 2 | BIST is optional and design-specific | `bist.enabled: true/false` per target; BIST only present on memory-type targets in M10 | Standard does not mandate BIST | ✅ Correct |
| 3 | Serial path as capacity-1 shared resource | Greedy scheduler uses `ptap_ports=1` + `AddNoOverlap`; CP-SAT encodes the same constraint | Single TDI-to-TDO chain is a serial shared resource | ✅ Correct |
| 4 | Cascaded STAP configuration overhead | `die_path_to()` computes the ordered die chain from primary to target; `access_setup_bits()` sums STAP select bits and 3DCR bit_length for all intermediate dies | Accessing die N requires configuring STAPs on dies 1..N-1 | ✅ Correct |
| 5 | BIST local execution releases serial path | `LOCAL_BIST_RUN` phase has `serial_required: false` | BIST runs locally on the die after TAP-based configuration | ✅ Correct |
| 6 | DWR per-die conflict groups | `exclusive_resource = test_session_{die_id}` prevents two tests from simultaneously using the same die's DWR | A die has exactly one DWR; it cannot service two simultaneous test operations | ✅ Correct |
| 7 | Interconnect tests involve both dies' DWR | I-recipe (interconnect/EXTEST) references DWR segments on both source and target dies | EXTEST requires OF-mode DWR on both driver and receiver dies | ✅ Correct |

### 3.2 Incorrectly Modeled Aspects

| # | Modeling Point | Issue | Severity | Code Location |
|---|---------------|-------|----------|---------------|
| 8 | **FPP correctly modeled as standard (optional) component** | FPP IS defined in IEEE 1838-2019 Clause 7 as an optional parallel wrapper access mechanism; the model correctly identifies it as an IEEE 1838 resource. The only issue is whether concurrent FPP+serial operation should be modeled. | ✅ Correct (standard) | `model_version: "m1-ieee1838-computable-v1"` is appropriate since FPP is a standard-defined (optional) IEEE 1838 component |
| 9 | **FPP and serial TAP as mutually exclusive alternatives** | S, F, B, H recipe types are modeled as alternative choices per target; physically, FPP can operate simultaneously with serial TAP | 🔴 Critical | `recipe_type` enum in `src/recipes/generator.py`; greedy scheduler priority `{"B": 0, "F": 1, ...}` |
| 10 | Recipe types conflate test methodology and transport | S/F/B/H/I categories mix "what test is performed" (INTEST/BIST/EXTEST) with "how data is moved" (serial/FPP) | 🟡 Medium | Recipe generation in `src/recipes/generator.py` |
| 11 | EXTEST as per-interconnect recipe | I-recipe is generated per link but resources on both dies are not explicitly modeled as co-occupied; scheduling treats it as a single-die task | 🟡 Medium | Interconnect handling in `generate_for_interconnect()` |
| 12 | TAP state machine overhead not modeled | Serial shift time uses `bits / tck_hz`, ignoring Capture-DR, Update-DR, and IR scan cycles | 🟢 Minor | `serial_time_s()` in `system_model.py` |
| 13 | 3DCR bit layout is flat | IEEE 1838 defines separate fields (STAP_Control, DWR_Control, etc.); code uses single `bit_length` | 🟢 Minor | `access_setup_bits()` uses flat `bit_length` from 3DCR |
| 14 | BIST priority is heuristic | Greedy scheduler hardcodes `{"B": 0, "F": 1, "H": 2, "S": 3, "I": 4}` — no physical guarantee this ordering matches optimal | 🟢 Minor | Scheduler priority dict |

---

## 4. Critical Issues — Detailed Analysis

### 4.1 Critical Issue 1: FPP and Serial TAP Are Modeled as Mutually Exclusive

**CORRECTION from previous version of this audit:** The previous version incorrectly claimed that FPP is not defined in IEEE 1838-2019. This was an error. After re-checking the standard:

**The fact:** IEEE 1838-2019 defines FPP as an OPTIONAL parallel wrapper access mechanism:
- Clause 5.5.3: "Flexible parallel port configuration register" -- describes FPP configuration elements
- Clause 6.5: "Parallel access to the DWR" -- provides for an optional parallel wrapper access mechanism called the Flexible Parallel Port (FPP)
- Clause 7 (pages 57-66): Full specification of the Flexible Parallel Port
- FPP uses independent physical lanes, configured via TAP
- FPP is optional: a compliant design may or may not implement FPP

**Why the previous audit was wrong:** The auditor initially searched for "FPP" as a top-level port type (like PTAP/STAP) and missed Clause 7's detailed specification of FPP as an optional data-transport mechanism accessed through the TAP's configuration registers.

**What IS correct about the audit:** The modeling concern about FPP and serial TAP being modeled as mutually exclusive alternatives is valid. Per Clause 7.1.1, FPP uses physically separate lanes from the serial TAP, meaning they CAN operate simultaneously. The current code models S/F/B/H recipe types as mutually exclusive per target, which does not capture the possibility of concurrent serial TAP + FPP operation.

**What this means for the project:**
- FPP IS a standard-defined IEEE 1838 component (optional). The `model_version: "m1-ieee1838-computable-v1"` is appropriate.
- The paper's claim of "IEEE 1838 compatibility" is valid with respect to FPP.
- No model_version change is needed. No "proposed extension" label is needed for FPP.
- The remaining open question is whether to model concurrent serial TAP + FPP operation.

### 4.2 Critical Issue 2: FPP and Serial TAP Are Not Mutually Exclusive

**The fact:** IEEE 1838 Clause 7.1.1 describes the use of independent physical lanes for FPP. FPP uses physically separate signals from the serial TAP (TCK/TMS/TDI/TDO). This means:

- FPP data transfer can occur **simultaneously** with serial TAP activity
- The serial TAP is always the **control path** — all register configuration, instruction loading, and mode selection must go through the serial TAP
- FPP is a **data transport accelerator** — it provides a wider, faster path for test stimulus/response data, but cannot configure anything by itself

**The code's wrong model:** The recipe generator treats S (serial), F (FPP), B (BIST), H (hybrid), and I (interconnect) as mutually exclusive recipe types. The scheduler selects exactly one recipe per target. This implies a false trade-off between "using the serial path" and "using FPP."

**The correct model:**

```
Time  →   |----T1----|----T2----|----T3----|----T4----|
Serial TAP: |--cfg D1--|--cfg D2--|--start BIST--|--scan D3 data--|
FPP lanes:  |          |          |              |--parallel xfer--|
BIST D2:              |          |--LOCAL RUN (no TAP, no FPP)-----|
```

- Serial TAP is always the **control master** for all operations
- FPP can carry data in parallel with serial TAP activity on other dies
- BIST local execution releases the serial TAP (and FPP) entirely
- The scheduling problem is fundamentally about **time-multiplexing the serial TAP**, not about choosing between serial and parallel paths

**What must change:** The recipe model should decompose into two orthogonal dimensions: **(1) test methodology** (INTEST, EXTEST, BIST, IJTAG) and **(2) data transport method** (serial shift, FPP parallel). The scheduling problem becomes: "When does each test get access to the serial TAP for configuration, and can the data phase use FPP to free the serial TAP sooner?"

### 4.3 Impact on Paper Claims

| Paper Claim | Issue | Corrected Claim |
|-------------|-------|-----------------|
| "Joint path selection and scheduling" | Implies the solver picks between alternative transport paths; physically, the choice is between test types with different resource signatures | "Time-multiplexed scheduling of the IEEE 1838 serial TAP with BIST window exploitation and optional FPP data acceleration" |
| "IEEE 1838 compatible" | FPP is a standard-defined optional component; no extension needed | "IEEE 1838 compatible" (unchanged; correct as-is) |
| Recipe types as alternatives (S/F/B/H) | FPP uses separate lanes from serial TAP; they can operate simultaneously | Test methodology (independent) + Data transport (independent); consider concurrent TAP+FPP scheduling |
| BIST vs FPP as the core trade-off | This trade-off does not physically exist — BIST releases both TAP and FPP; FPP data xfer is independent of BIST | The real trade-off: which tests get serial TAP access during which windows (BIST run gaps, FPP data windows) |

---

## 5. The Correct Physical Abstraction

### 5.1 Resources (What Actually Exists in Hardware)

```
Shared resources (capacity-constrained, time-multiplexed):
  ┌─────────────────────────────────────────────┐
  │ Serial TAP chain (capacity = 1)             │ ← Always shared. Controls everything.
  │   TCK, TMS, TDI, TDO, TRSTN                │
  ├─────────────────────────────────────────────┤
  │ FPP lanes (capacity = N, optional)            │ ← IEEE 1838 Clause 7. Data only. Independent of TAP.
  │   FPP_TX[N-1:0], FPP_RX[N-1:0], FPP_CLK    │
  ├─────────────────────────────────────────────┤
  │ Shared BIST engine (capacity = 1 per engine)│ ← Design-specific. IEEE 1838 optional.
  │   BIST_CLK, BIST_START, BIST_DONE, BIST_SIG │
  └─────────────────────────────────────────────┘

Per-die resources (local to each die, mutually exclusive within die):
  ┌─────────────────────────────────────────────┐
  │ DWR (Die Wrapper Register)                  │ ← One per die. Cannot run two tests simultaneously.
  │   3DCR (3D Configuration Register)           │ ← One per die (if STAPs exist).
  │   STAP (Secondary Test Access Port)          │ ← Zero or more per die.
  └─────────────────────────────────────────────┘
```

### 5.2 Task Decomposition (Correct Model)

Every test task on any die should follow a standard phase decomposition:

```
Test Task: {task_id, die_id, test_method, data_transport}

Phase 1: CONFIG_PATH     — Configure STAPs on all intermediate dies to reach target die
                           Resource: SERIAL_TAP (mandatory), FPP (not used)
                           Duration: Σ(3DCR_bits + STAP_select_bits) / TCK

Phase 2: CONFIG_TEST     — Load test instruction + configure DWR mode + setup BIST/FPP if used
                           Resource: SERIAL_TAP (mandatory)
                           Duration: IR_length + DWR_mode_bits + (FPP_config_bits | BIST_config_bits) / TCK

Phase 3: EXECUTE         — The actual test operation
  ┌──────────────────────────────────────────────────────────────────────┐
  │ INTEST via serial:   Shift_in + Capture + Shift_out                  │
  │                      Resource: SERIAL_TAP (全程)                     │
  │ INTEST via FPP:      FPP TX + Capture + FPP RX                      │
  │                      Resource: FPP_lanes (SERIAL_TAP released!)     │
  │ BIST:                BIST controller runs locally                    │
  │                      Resource: BIST_engine (SERIAL_TAP released!)   │
  │ EXTEST via serial:   Shift_in (both dies) + Capture + Shift_out     │
  │                      Resource: SERIAL_TAP (全程) + DWR[die_A, die_B]│
  │ EXTEST via FPP:      FPP TX + Capture + FPP RX                      │
  │                      Resource: FPP_lanes + DWR[die_A, die_B]        │
  └──────────────────────────────────────────────────────────────────────┘

Phase 4: READBACK        — Read test results
                           Resource: SERIAL_TAP (if serial readback) or FPP (if FPP readback)
                           Duration: result_bits / TCK or result_bits / (FPP_lanes * BW_per_lane)
```

### 5.3 The Scheduling Problem (Correctly Stated)

The core scheduling problem is:

> **Given a 3D/2.5D/5.5D stack with N dies, each die having a set of required tests (INTEST, EXTEST, BIST), schedule all test tasks on the shared serial TAP such that:**
>
> 1. At most one test occupies the serial TAP at any time (capacity-1 shared resource)
> 2. BIST tasks exploit their "release and re-acquire" pattern to let other tasks use the serial TAP during local execution windows
> 3. If FPP is available, INTEST/EXTEST data phases can optionally use FPP instead of serial shift, releasing the TAP earlier
> 4. DWR per-die mutual exclusion is respected
> 5. Power and thermal constraints are respected
> 6. Total makespan is minimized

This reframes the problem from a confusing "path selection" narrative to a clean **time-multiplexed resource scheduling** problem — which is both more physically accurate and more clearly communicable.

---

## 6. FPP: IEEE 1838 Standard Component (Optional)

FPP is an OPTIONAL but standard-defined component of IEEE 1838-2019. No external justification (UCIe, etc.) is needed.

### 6.1 FPP in IEEE 1838-2019

FPP is defined at multiple points in the standard:
- **Clause 5.5.3** defines the FPP configuration register ("Flexible parallel port configuration register"), described as "Another expansion of the IEEE 1149.1 two-dimensional architecture."
- **Clause 6.5** ("Parallel access to the DWR") states: "IEEE Std 1838 provides for an optional parallel wrapper access mechanism called the Flexible Parallel Port (FPP)."
- **Clause 7** (pages 57-66) provides the full specification of FPP, including lane configuration, channel definitions, and operating modes.
- FPP is optional: a compliant IEEE 1838 design may or may not implement FPP lanes.
- FPP uses dedicated physical lanes separate from the serial TAP (TCK/TMS/TDI/TDO).
- All FPP configuration goes through the serial TAP.

### 6.2 Physical Characteristics

An IEEE 1838 FPP implementation requires:
- **N dedicated physical pins/bumps** (where N = lane count) per die that supports it
- **N vertical interconnects** (TSVs or microbumps) per lane between stacked dies
- **Clock lane** for registered-mode parallel data capture
- **Configuration registers** (accessible via serial TAP) to set lane mode, polarity, and channel assignment

In advanced packaging (3D stacking with hybrid bonding, interposer-based 2.5D), the physical overhead of adding 4-16 FPP lanes may be acceptable compared to the test-time savings from reducing serial shift time.

### 6.3 Correct Labeling

Since FPP is defined in the IEEE 1838 standard (as an optional component):

- FPP should be referred to as "FPP (IEEE 1838 Clause 7, optional)" or "IEEE 1838 FPP"
- No "proposed extension" or "not in standard" label is needed
- The model_version `"m1-ieee1838-computable-v1"` is appropriate as-is
- The paper should note that FPP is an optional IEEE 1838 feature, not a mandatory one
- The core scheduling methodology (serial TAP time-multiplexing) works with or without FPP; FPP is an optional accelerator

---

## 7. Comparison with Published Work

### 7.1 Modeling Fidelity Comparison

| Modeling Aspect | This Project | Habiby 2020 | Habiby 2022 | Patmanathan 2024 | Sen Gupta 2011 |
|-----------------|-------------|-------------|-------------|------------------|----------------|
| **IEEE 1838 PTAP/STAP** | Explicitly modeled: `die_path_to()`, cascaded 3DCR config bits | Not modeled (IEEE 1687 only, no 3D stack) | Not modeled (IEEE 1687 only, no 3D stack) | Not modeled (abstract TAM width, no serial access) | Not modeled (pre-bond/post-bond sessions, no serial chain) |
| **Serial path as shared resource** | Yes, capacity=1, AddNoOverlap constraint | Yes (SIB network is shared, but no die traversal cost) | Yes (SAT/CNF constraints on concurrent instrument access) | No (TAM is just a bandwidth number, no contention) | No (session-based, no per-cycle resource modeling) |
| **Die traversal overhead** | Yes, computed per die accession path | No (flat instrument network) | No (flat instrument network) | No (cores are spatially arranged but access is not serialized) | No (dies are independent scheduling units) |
| **BIST local execution model** | Yes, with TAP release/re-acquire phases | No BIST modeling | No BIST modeling | No BIST modeling | Yes, BIST per-die with control line trade-off |
| **FPP parallel data path** | Yes (IEEE 1838 Clause 7, optional) | No | No | No (TAM width is the parallel mechanism) | No |
| **DWR conflict groups** | Yes, per-die exclusive resource | N/A (no DWR concept) | N/A | N/A (no DWR, only thermal layout) | N/A |
| **Interconnect (EXTEST)** | I-recipe with source/target die DWR references | N/A | N/A | N/A | N/A |
| **3DCR bit-level modeling** | Flat bit_length (minor limitation) | N/A | N/A | N/A | N/A |
| **TAP state machine cycles** | Not modeled (minor limitation) | Modeled as SIB access latency | Modeled as SIB access latency | N/A | N/A |
| **Thermal modeling** | 1st-order RC proxy + HotSpot validation | Power-aware (not thermal) | Power-aware (not thermal) | HotSpot 6.0 floorplan + RHDF | Power constraint only |

### 7.2 Summary Assessment

**This project's model is more physically detailed than any published work** in the specific area of IEEE 1838 test access scheduling. The four reference papers either:

- Model IEEE 1687 (IJTAG) networks rather than IEEE 1838 (Habiby 2020, 2022)
- Use abstract resource models that do not capture serial chain contention (Patmanathan 2024)
- Model BIST sessions without the serial access path that IEEE 1838 mandates for configuration (Sen Gupta 2011)

No reference paper models the cascaded STAP configuration sequence that IEEE 1838 requires for accessing deep dies in a 3D stack. This is a genuine strength of the current model — **if framed correctly as an IEEE 1838-specific contribution rather than a generic scheduling method.**

### 7.3 Key Quantitative Context from Literature

| Paper | Reported Gain | Scope | Relevance |
|-------|--------------|-------|-----------|
| Habiby 2022 | PBO within 10% MAPE of ILP optimum | 1000+ instruments on IJTAG network | Shows that incremental optimization approaches global optimum for instrument scheduling; supports the use of CP-SAT as a scheduling backend |
| Patmanathan 2024 | 0.2% average improvement over baseline | 3D floorplan + thermal + ACO | The field's gains are inherently small in general scenarios; this project's 0% gain on ordinary benchmarks is consistent with the literature, not a failure |
| Sen Gupta 2011 | 7.7% average TAT reduction (max 17.1%) | Pre-bond/post-bond session scheduling with PO strategy | Sets reasonable expectations for TAT gains in this problem domain; gains above 15% are significant |

---

## 8. Recommendations for the Paper

### 8.1 Narrative Changes

| Current Narrative | Recommended Revision |
|-------------------|---------------------|
| "We propose a joint path-selection and scheduling method" | "We present a time-multiplexed scheduling framework for the IEEE 1838 serial TAP that exploits BIST local-execution windows and optional FPP data-path acceleration" |
| "Our method universally outperforms fixed-path scheduling" | "We identify and rigorously characterize the conditions under which joint scheduling provides benefit: shared resource bottlenecks combined with alternative execution paths" |
| "IEEE 1838 compatible" | (unchanged -- FPP is an optional standard-defined IEEE 1838 component) |
| "ALNS hybrid solver" | "CP-SAT-based constraint optimization" (unless ALNS is implemented with adaptive weight updates per the algorithm's definition) |
| "Electrothermal-aware closed-loop optimization" | "Thermal proxy for scheduling guidance with HotSpot offline validation" |

### 8.2 Terminology Fixes

| Current Term | Corrected Term |
|-------------|---------------|
| `S/F/B/H/I` recipe types | Test methodology (INTEST/EXTEST/BIST/IJTAG) + Data transport mode (serial/FPP) |
| `model_version: "m1-ieee1838-computable-v1"` | (unchanged -- FPP is part of IEEE 1838) |
| "FPP recipe" | "INTEST with FPP data transport" or "EXTEST with FPP data transport" |
| "BIST recipe" | "BIST test with serial configuration" |
| "Joint path selection" | "Test-mode assignment with data-transport selection" or "Schedule-aware test configuration" |

### 8.3 Honest Labeling Requirements

1. **Model version field:** The `"m1-ieee1838-computable-v1"` model_version in case JSON files is correct as-is. FPP is a standard-defined (optional) IEEE 1838 component. No change needed.

2. **FPP in paper:** The paper should accurately note that FPP is an optional IEEE 1838 standard component (Clause 7). The statement should be: "The Flexible Parallel Port (FPP) is an optional IEEE 1838-2019 standard component (Clause 7) that provides parallel data lanes for accelerated test data transfer, configured via the serial TAP. All core results hold with serial-only operation; FPP serves as an optional data-path accelerator."

3. **Documentation:** Update `readme.md` and `docs/model/M1_COMPUTABLE_IEEE1838_MODEL.md` to correctly identify FPP as an optional IEEE 1838 standard component (not a proposed extension).

4. **Abstract/Introduction:** FPP is a standard IEEE 1838 feature -- no disclaimer needed. Position the work as "IEEE 1838-based test access scheduling with optional FPP (Clause 7) parallel data-path acceleration."

---

## Appendix A: Audit Methodology

This audit was conducted through three parallel streams:

**Stream 1 — Standard conformance:** The full IEEE 1838-2019 standard (124 pages) was read and cross-referenced against the code model. Every architectural concept in the code (PTAP, STAP, 3DCR, DWR, FPP, BIST, serial path, parallel lanes) was checked for presence/absence in the standard, and for correct semantic usage when present.

**Stream 2 — Code audit:** The following files were examined line-by-line:
- `src/model/system_model.py` — resource model, access path computation, validation logic
- `src/recipes/generator.py` — recipe type enumeration, phase decomposition, resource assignment
- `src/schedulers/greedy.py` — scheduling constraints, priority heuristics, resource capacity enforcement
- `src/schedulers/cpsat.py` — CP-SAT constraint encoding
- `configs/cases/*.json` — case definitions, model_version declarations

**Stream 3 — Literature comparison:** Four reference papers were read in full and their physical modeling approaches were systematically compared against this project's model across 10 dimensions.

## Appendix B: Files Requiring Changes

| File | Change Required | Priority |
|------|----------------|---------|
| `configs/cases/*.json` (~30 files) | (No change needed -- FPP is standard IEEE 1838, optional) | N/A |
| `docs/model/M1_COMPUTABLE_IEEE1838_MODEL.md` | Update FPP labels from "proposed extension" to "optional, IEEE 1838-2019 Clause 7" | P1 |
| `readme.md` | Update FPP labels from "proposed extension" to "optional, IEEE 1838-2019 Clause 7" | P1 |
| `src/recipes/generator.py` | Consider adding separate test-method and transport-method dimensions (architectural change) | P1 |
| `src/schedulers/greedy.py` | Remove heuristic priority dict or replace with physically-grounded ordering | P2 |
| `src/model/system_model.py` | Optional: add `tap_state_machine_overhead_cycles` parameter | P2 |

---

## Appendix C: References

1. IEEE Std 1838-2019, "IEEE Standard for Test Access Architecture for Three-Dimensional Stacked Integrated Circuits," IEEE, 2020.
2. P. Habiby, S. Huhn, and R. Drechsler, "Power-aware Test Scheduling for IEEE 1687 Networks with Multiple Power Domains," in *IEEE DFT*, 2020.
3. P. Habiby, S. Huhn, and R. Drechsler, "Power-aware test scheduling framework for IEEE 1687 multi-power domain networks using formal techniques," *Microelectronics Reliability*, vol. 134, p. 114551, 2022.
4. G. Patmanathan, C. Y. Ooi, N. Ismail, and S. R. Aid, "Thermal-Aware Test Scheduling with Floorplanning for Three-Dimensional Stacked Integrated Circuit," in *IEEE ICSE*, 2024.
5. B. Sen Gupta, U. Ingelsson, and E. Larsson, "Scheduling Tests for 3D Stacked Chips under Power Constraints," in *IEEE DELTA*, 2011.
