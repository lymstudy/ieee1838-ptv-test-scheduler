# V4 Final Experiment Report

## Overview

- **Cases:** 1 (v4_small_3d_stack)
- **Conditions:** 5 (bist_fpp, bist_fpp_thermal, bist_only, fpp_only, serial_baseline)
- **Methods:** 1 (m5_cpsat)
- **Total runs:** 5
- **Successful:** 5
- **Failed:** 0

## Conditions

- **serial_baseline**: Worst case: BIST disabled, no FPP. All tasks use serial TAP exclusively.
- **bist_only**: Per-die BIST engines fire and release TAP. Pure IEEE 1838 BIST model.
- **fpp_only**: BIST disabled, FPP offloads INTEST data from TAP.
- **bist_fpp**: Both BIST (per-die engines) and FPP parallel data offload combined.
- **bist_fpp_thermal**: Full model: all mechanisms active with per-die thermal constraints (85C limit).

## Full Results Table

| case_id | condition | method | status | makespan_us | TAP_util | FPP_util | BIST_overlap | max_BIST | peak_T_C | viol | recipe_types | tasks |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| v4_small_3d_stack | serial_baseline | m5_cpsat | ok | 228429 | 1.000 | 0.000 | 0.000 | 0 | 44.9 | 0 | I+IJTAG+S | 6/6 |
| v4_small_3d_stack | bist_only | m5_cpsat | ok | 228442 | 1.000 | 0.000 | 0.429 | 2 | 50.2 | 0 | B+I+IJTAG+S | 8/8 |
| v4_small_3d_stack | fpp_only | m5_cpsat | ok | 128426 | 1.000 | 0.002 | 0.000 | 0 | 49.8 | 0 | F+I+IJTAG+S | 6/6 |
| v4_small_3d_stack | bist_fpp | m5_cpsat | ok | 128439 | 1.000 | 0.002 | 0.429 | 2 | 54.5 | 0 | B+F+I+IJTAG+S | 8/8 |
| v4_small_3d_stack | bist_fpp_thermal | m5_cpsat | ok | 128439 | 1.000 | 0.002 | 0.429 | 2 | 54.5 | 0 | B+F+I+IJTAG+S | 8/8 |

## Figure 1 & 2: Makespan Comparison and Speedup vs Serial Baseline

### v4_small_3d_stack
Serial baseline makespan: 228429 us

| Condition | Method | Makespan (us) | Speedup vs Serial | TAP Util | FPP Util | BIST Overlap | max_BIST |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| bist_fpp | m5_cpsat | 128439 | 1.78x | 1.000 | 0.002 | 0.429 | 2 |
| bist_fpp_thermal | m5_cpsat | 128439 | 1.78x | 1.000 | 0.002 | 0.429 | 2 |
| bist_only | m5_cpsat | 228442 | 1.00x | 1.000 | 0.000 | 0.429 | 2 |
| fpp_only | m5_cpsat | 128426 | 1.78x | 1.000 | 0.002 | 0.000 | 0 |
| serial_baseline | m5_cpsat | 228429 | 1.00x | 1.000 | 0.000 | 0.000 | 0 |

## Figure 3: TAP (Serial) Utilization

| case_id | condition | method | serial_busy_ratio |
| --- | --- | --- | ---: |
| v4_small_3d_stack | bist_only | m5_cpsat | 1.0000 |
| v4_small_3d_stack | fpp_only | m5_cpsat | 1.0000 |
| v4_small_3d_stack | bist_fpp | m5_cpsat | 1.0000 |
| v4_small_3d_stack | bist_fpp_thermal | m5_cpsat | 1.0000 |
| v4_small_3d_stack | serial_baseline | m5_cpsat | 1.0000 |

## Figure 4: FPP Utilization

| case_id | condition | method | fpp_utilization |
| --- | --- | --- | ---: |
| v4_small_3d_stack | fpp_only | m5_cpsat | 0.0024 |
| v4_small_3d_stack | bist_fpp | m5_cpsat | 0.0024 |
| v4_small_3d_stack | bist_fpp_thermal | m5_cpsat | 0.0024 |
| v4_small_3d_stack | serial_baseline | m5_cpsat | 0.0000 |
| v4_small_3d_stack | bist_only | m5_cpsat | 0.0000 |

## Figure 5: BIST Overlap Ratio

| case_id | condition | method | bist_overlap_ratio | max_concurrent_bist |
| --- | --- | --- | ---: | ---: |
| v4_small_3d_stack | bist_only | m5_cpsat | 0.4286 | 2 |
| v4_small_3d_stack | bist_fpp | m5_cpsat | 0.4286 | 2 |
| v4_small_3d_stack | bist_fpp_thermal | m5_cpsat | 0.4286 | 2 |
| v4_small_3d_stack | serial_baseline | m5_cpsat | 0.0000 | 0 |
| v4_small_3d_stack | fpp_only | m5_cpsat | 0.0000 | 0 |

## Figure 6: Max Concurrent BIST

| case_id | condition | method | max_concurrent_bist | bist_engine_count |
| --- | --- | --- | ---: | ---: |
| v4_small_3d_stack | bist_only | m5_cpsat | 2 | 2 |
| v4_small_3d_stack | bist_fpp | m5_cpsat | 2 | 2 |
| v4_small_3d_stack | bist_fpp_thermal | m5_cpsat | 2 | 2 |
| v4_small_3d_stack | serial_baseline | m5_cpsat | 0 | 0 |
| v4_small_3d_stack | fpp_only | m5_cpsat | 0 | 0 |

## Figure 7: Thermal Analysis (bist_fpp_thermal condition)

| case_id | method | peak_T_C | thermal_violations |
| --- | --- | ---: | ---: |
| v4_small_3d_stack | m5_cpsat | 54.54 | 0 |

## Figure 8: Scaling Analysis (Makespan vs Die Count / Topology)

| case_id | topology | die_count | condition | method | makespan_us |
| --- | --- | ---: | --- | --- | ---: |
| v4_small_3d_stack | 3d_stack | 3 | bist_fpp | m5_cpsat | 128439 |
| v4_small_3d_stack | 3d_stack | 3 | bist_fpp_thermal | m5_cpsat | 128439 |
| v4_small_3d_stack | 3d_stack | 3 | bist_only | m5_cpsat | 228442 |
| v4_small_3d_stack | 3d_stack | 3 | fpp_only | m5_cpsat | 128426 |
| v4_small_3d_stack | 3d_stack | 3 | serial_baseline | m5_cpsat | 228429 |

## Figure 9: CP-SAT vs Greedy Comparison

| case_id | condition | CP-SAT makespan_us | Greedy makespan_us | CP-SAT/Greedy ratio |
| --- | --- | ---: | ---: | ---: |

## Figure 10: Gantt Charts

Schedule CSVs saved to `results/schedules/v4_final/` for representative case+condition combos.

Key schedule files for the best-condition scenario:

| File | Description |
| --- | --- |
| `v4_4die_3d_stack__bist_only__cpsat.csv` | Schedule CSV |
| `v4_4die_3d_stack__bist_only__greedy.csv` | Schedule CSV |
| `v4_4die_3d_stack__fpp_only__cpsat.csv` | Schedule CSV |
| `v4_4die_3d_stack__fpp_only__greedy.csv` | Schedule CSV |
| `v4_4die_3d_stack__serial_baseline__cpsat.csv` | Schedule CSV |
| `v4_4die_3d_stack__serial_baseline__greedy.csv` | Schedule CSV |
| `v4_small_3d_stack__bist_fpp__cpsat.csv` | Schedule CSV |
| `v4_small_3d_stack__bist_fpp__greedy.csv` | Schedule CSV |
| `v4_small_3d_stack__bist_fpp_thermal__cpsat.csv` | Schedule CSV |
| `v4_small_3d_stack__bist_fpp_thermal__greedy.csv` | Schedule CSV |
| `v4_small_3d_stack__bist_only__cpsat.csv` | Schedule CSV |
| `v4_small_3d_stack__bist_only__greedy.csv` | Schedule CSV |
| `v4_small_3d_stack__fpp_only__cpsat.csv` | Schedule CSV |
| `v4_small_3d_stack__fpp_only__greedy.csv` | Schedule CSV |
| `v4_small_3d_stack__serial_baseline__cpsat.csv` | Schedule CSV |
| `v4_small_3d_stack__serial_baseline__greedy.csv` | Schedule CSV |

## BIST Overlap Verification

### v4_small_3d_stack / bist_only / m5_cpsat
  Total BIST phases: 2
  - mem0_die0 on die0: 200025us -> 202025us (2000us)
  - mem1_die1 on die1: 200030us -> 201530us (1500us)

  - mem0_die0 vs mem1_die1: overlap=1500us OVERLAP

### v4_small_3d_stack / bist_fpp / m5_cpsat
  Total BIST phases: 2
  - mem0_die0 on die0: 100022us -> 102022us (2000us)
  - mem1_die1 on die1: 100027us -> 101527us (1500us)

  - mem0_die0 vs mem1_die1: overlap=1500us OVERLAP

### v4_small_3d_stack / bist_fpp_thermal / m5_cpsat
  Total BIST phases: 2
  - mem0_die0 on die0: 100022us -> 102022us (2000us)
  - mem1_die1 on die1: 100027us -> 101527us (1500us)

  - mem0_die0 vs mem1_die1: overlap=1500us OVERLAP

## Notes

- **Two transport resources**: TAP (serial, capacity=1, all dies) and FPP (parallel, optional, some dies).
- **Task types**: INTEST, EXTEST, BIST, IJTAG -- all mandatory.
- **BIST model**: Per-die BIST engines (capacity=1 each). BIST releases TAP during local execution, enabling overlap.
- **FPP model**: Standard IEEE 1838-2019 Clause 7 FPP lanes for parallel data transport.
- **Thermal model**: First-order RC proxy with die-to-die vertical coupling and heat sink distance factors.
- **CP-SAT time limit**: 30s per solve.
- **10 figures** regenerable from this experiment data and schedule CSVs.
