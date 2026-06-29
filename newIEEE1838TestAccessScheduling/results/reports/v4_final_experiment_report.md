# V4 Final Experiment Report

## Overview

- **Cases:** 3 (v4_4die_2_5d_interposer, v4_4die_3d_stack, v4_small_3d_stack)
- **Conditions:** 5 (bist_fpp, bist_fpp_thermal, bist_only, fpp_only, serial_baseline)
- **Methods:** 2 (m4_greedy, m5_cpsat)
- **Total runs:** 30
- **Successful:** 30
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
| v4_small_3d_stack | serial_baseline | m4_greedy | ok | 228434 | 1.000 | 0.000 | 0.000 | 0 | 47.4 | 0 | I+IJTAG+S | 6/6 |
| v4_small_3d_stack | bist_only | m5_cpsat | ok | 228442 | 1.000 | 0.000 | 0.429 | 2 | 50.2 | 0 | B+I+IJTAG+S | 8/8 |
| v4_small_3d_stack | bist_only | m4_greedy | ok | 230203 | 0.992 | 0.000 | 0.429 | 2 | 48.2 | 0 | B+I+IJTAG+S | 8/8 |
| v4_small_3d_stack | fpp_only | m5_cpsat | ok | 128426 | 1.000 | 0.002 | 0.000 | 0 | 49.8 | 0 | F+I+IJTAG+S | 6/6 |
| v4_small_3d_stack | fpp_only | m4_greedy | ok | 128430 | 1.000 | 0.002 | 0.000 | 0 | 54.1 | 0 | F+I+IJTAG+S | 6/6 |
| v4_small_3d_stack | bist_fpp | m5_cpsat | ok | 128439 | 1.000 | 0.002 | 0.429 | 2 | 54.5 | 0 | B+F+I+IJTAG+S | 8/8 |
| v4_small_3d_stack | bist_fpp | m4_greedy | ok | 130199 | 0.986 | 0.002 | 0.429 | 2 | 54.1 | 0 | B+F+I+IJTAG+S | 8/8 |
| v4_small_3d_stack | bist_fpp_thermal | m5_cpsat | ok | 128439 | 1.000 | 0.002 | 0.429 | 2 | 54.5 | 0 | B+F+I+IJTAG+S | 8/8 |
| v4_small_3d_stack | bist_fpp_thermal | m4_greedy | ok | 130199 | 0.986 | 0.002 | 0.429 | 2 | 54.1 | 0 | B+F+I+IJTAG+S | 8/8 |
| v4_4die_3d_stack | serial_baseline | m5_cpsat | ok | 3729304 | 1.000 | 0.000 | 0.000 | 0 | 57.0 | 0 | I+IJTAG+S | 10/10 |
| v4_4die_3d_stack | serial_baseline | m4_greedy | ok | 3729313 | 1.000 | 0.000 | 0.000 | 0 | 59.8 | 0 | I+IJTAG+S | 10/10 |
| v4_4die_3d_stack | bist_only | m5_cpsat | ok | 3729321 | 1.000 | 0.000 | 0.455 | 2 | 58.3 | 0 | B+I+IJTAG+S | 12/12 |
| v4_4die_3d_stack | bist_only | m4_greedy | ok | 3734403 | 0.999 | 0.000 | 0.454 | 2 | 84.6 | 0 | B+I+IJTAG+S | 12/12 |
| v4_4die_3d_stack | fpp_only | m5_cpsat | ok | 1159287 | 1.000 | 0.003 | 0.000 | 0 | 75.9 | 0 | F+I+IJTAG+S | 10/10 |
| v4_4die_3d_stack | fpp_only | m4_greedy | ok | 1159292 | 1.000 | 0.003 | 0.000 | 0 | 85.3 | 1 | F+I+IJTAG+S | 10/10 |
| v4_4die_3d_stack | bist_fpp | m5_cpsat | ok | 1159303 | 1.000 | 0.003 | 0.000 | 1 | 101.6 | 3 | B+F+I+IJTAG+S | 12/12 |
| v4_4die_3d_stack | bist_fpp | m4_greedy | ok | 1165631 | 0.995 | 0.003 | 0.454 | 2 | 116.1 | 4 | B+F+I+IJTAG+S | 12/12 |
| v4_4die_3d_stack | bist_fpp_thermal | m5_cpsat | ok | 1159303 | 1.000 | 0.003 | 0.000 | 1 | 80.7 | 0 | B+F+I+IJTAG+S | 12/12 |
| v4_4die_3d_stack | bist_fpp_thermal | m4_greedy | ok | 1165631 | 0.995 | 0.003 | 0.454 | 2 | 116.1 | 4 | B+F+I+IJTAG+S | 12/12 |
| v4_4die_2_5d_interposer | serial_baseline | m5_cpsat | ok | 4230349 | 1.000 | 0.000 | 0.000 | 0 | 43.0 | 0 | I+IJTAG+S | 11/11 |
| v4_4die_2_5d_interposer | serial_baseline | m4_greedy | ok | 4230359 | 1.000 | 0.000 | 0.000 | 0 | 47.1 | 0 | I+IJTAG+S | 11/11 |
| v4_4die_2_5d_interposer | bist_only | m5_cpsat | ok | 4230375 | 1.000 | 0.000 | 0.324 | 2 | 43.0 | 0 | B+I+IJTAG+S | 14/14 |
| v4_4die_2_5d_interposer | bist_only | m4_greedy | ok | 4236117 | 0.999 | 0.000 | 0.919 | 3 | 47.1 | 0 | B+I+IJTAG+S | 14/14 |
| v4_4die_2_5d_interposer | fpp_only | m5_cpsat | ok | 1278329 | 1.000 | 0.001 | 0.000 | 0 | 50.5 | 0 | F+I+IJTAG+S | 11/11 |
| v4_4die_2_5d_interposer | fpp_only | m4_greedy | ok | 1278525 | 1.000 | 0.001 | 0.000 | 0 | 51.9 | 0 | F+I+IJTAG+S | 11/11 |
| v4_4die_2_5d_interposer | bist_fpp | m5_cpsat | ok | 1278355 | 1.000 | 0.001 | 0.394 | 3 | 51.7 | 0 | B+F+I+IJTAG+S | 14/14 |
| v4_4die_2_5d_interposer | bist_fpp | m4_greedy | ok | 1284720 | 0.995 | 0.001 | 0.919 | 3 | 51.9 | 0 | B+F+I+IJTAG+S | 14/14 |
| v4_4die_2_5d_interposer | bist_fpp_thermal | m5_cpsat | ok | 1278355 | 1.000 | 0.001 | 0.394 | 3 | 51.7 | 0 | B+F+I+IJTAG+S | 14/14 |
| v4_4die_2_5d_interposer | bist_fpp_thermal | m4_greedy | ok | 1284720 | 0.995 | 0.001 | 0.919 | 3 | 51.9 | 0 | B+F+I+IJTAG+S | 14/14 |

## Figure 1 & 2: Makespan Comparison and Speedup vs Serial Baseline

### v4_4die_2_5d_interposer
Serial baseline makespan: 4230349 us

| Condition | Method | Makespan (us) | Speedup vs Serial | TAP Util | FPP Util | BIST Overlap | max_BIST |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| bist_fpp | m4_greedy | 1284720 | 3.29x | 0.995 | 0.001 | 0.919 | 3 |
| bist_fpp | m5_cpsat | 1278355 | 3.31x | 1.000 | 0.001 | 0.394 | 3 |
| bist_fpp_thermal | m4_greedy | 1284720 | 3.29x | 0.995 | 0.001 | 0.919 | 3 |
| bist_fpp_thermal | m5_cpsat | 1278355 | 3.31x | 1.000 | 0.001 | 0.394 | 3 |
| bist_only | m4_greedy | 4236117 | 1.00x | 0.999 | 0.000 | 0.919 | 3 |
| bist_only | m5_cpsat | 4230375 | 1.00x | 1.000 | 0.000 | 0.324 | 2 |
| fpp_only | m4_greedy | 1278525 | 3.31x | 1.000 | 0.001 | 0.000 | 0 |
| fpp_only | m5_cpsat | 1278329 | 3.31x | 1.000 | 0.001 | 0.000 | 0 |
| serial_baseline | m4_greedy | 4230359 | 1.00x | 1.000 | 0.000 | 0.000 | 0 |
| serial_baseline | m5_cpsat | 4230349 | 1.00x | 1.000 | 0.000 | 0.000 | 0 |

### v4_4die_3d_stack
Serial baseline makespan: 3729304 us

| Condition | Method | Makespan (us) | Speedup vs Serial | TAP Util | FPP Util | BIST Overlap | max_BIST |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| bist_fpp | m4_greedy | 1165631 | 3.20x | 0.995 | 0.003 | 0.454 | 2 |
| bist_fpp | m5_cpsat | 1159303 | 3.22x | 1.000 | 0.003 | 0.000 | 1 |
| bist_fpp_thermal | m4_greedy | 1165631 | 3.20x | 0.995 | 0.003 | 0.454 | 2 |
| bist_fpp_thermal | m5_cpsat | 1159303 | 3.22x | 1.000 | 0.003 | 0.000 | 1 |
| bist_only | m4_greedy | 3734403 | 1.00x | 0.999 | 0.000 | 0.454 | 2 |
| bist_only | m5_cpsat | 3729321 | 1.00x | 1.000 | 0.000 | 0.455 | 2 |
| fpp_only | m4_greedy | 1159292 | 3.22x | 1.000 | 0.003 | 0.000 | 0 |
| fpp_only | m5_cpsat | 1159287 | 3.22x | 1.000 | 0.003 | 0.000 | 0 |
| serial_baseline | m4_greedy | 3729313 | 1.00x | 1.000 | 0.000 | 0.000 | 0 |
| serial_baseline | m5_cpsat | 3729304 | 1.00x | 1.000 | 0.000 | 0.000 | 0 |

### v4_small_3d_stack
Serial baseline makespan: 228429 us

| Condition | Method | Makespan (us) | Speedup vs Serial | TAP Util | FPP Util | BIST Overlap | max_BIST |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| bist_fpp | m4_greedy | 130199 | 1.75x | 0.986 | 0.002 | 0.429 | 2 |
| bist_fpp | m5_cpsat | 128439 | 1.78x | 1.000 | 0.002 | 0.429 | 2 |
| bist_fpp_thermal | m4_greedy | 130199 | 1.75x | 0.986 | 0.002 | 0.429 | 2 |
| bist_fpp_thermal | m5_cpsat | 128439 | 1.78x | 1.000 | 0.002 | 0.429 | 2 |
| bist_only | m4_greedy | 230203 | 0.99x | 0.992 | 0.000 | 0.429 | 2 |
| bist_only | m5_cpsat | 228442 | 1.00x | 1.000 | 0.000 | 0.429 | 2 |
| fpp_only | m4_greedy | 128430 | 1.78x | 1.000 | 0.002 | 0.000 | 0 |
| fpp_only | m5_cpsat | 128426 | 1.78x | 1.000 | 0.002 | 0.000 | 0 |
| serial_baseline | m4_greedy | 228434 | 1.00x | 1.000 | 0.000 | 0.000 | 0 |
| serial_baseline | m5_cpsat | 228429 | 1.00x | 1.000 | 0.000 | 0.000 | 0 |

## Figure 3: TAP (Serial) Utilization

| case_id | condition | method | serial_busy_ratio |
| --- | --- | --- | ---: |
| v4_4die_2_5d_interposer | fpp_only | m5_cpsat | 1.0000 |
| v4_4die_2_5d_interposer | bist_fpp | m5_cpsat | 1.0000 |
| v4_4die_2_5d_interposer | bist_fpp_thermal | m5_cpsat | 1.0000 |
| v4_small_3d_stack | bist_only | m5_cpsat | 1.0000 |
| v4_small_3d_stack | fpp_only | m5_cpsat | 1.0000 |
| v4_small_3d_stack | bist_fpp | m5_cpsat | 1.0000 |
| v4_small_3d_stack | bist_fpp_thermal | m5_cpsat | 1.0000 |
| v4_4die_3d_stack | bist_fpp_thermal | m5_cpsat | 1.0000 |
| v4_small_3d_stack | serial_baseline | m5_cpsat | 1.0000 |
| v4_4die_3d_stack | bist_fpp | m5_cpsat | 1.0000 |
| v4_4die_3d_stack | serial_baseline | m5_cpsat | 1.0000 |
| v4_4die_3d_stack | bist_only | m5_cpsat | 1.0000 |
| v4_4die_3d_stack | fpp_only | m5_cpsat | 1.0000 |
| v4_4die_2_5d_interposer | serial_baseline | m5_cpsat | 1.0000 |
| v4_4die_2_5d_interposer | bist_only | m5_cpsat | 1.0000 |
| v4_4die_2_5d_interposer | serial_baseline | m4_greedy | 1.0000 |
| v4_4die_3d_stack | serial_baseline | m4_greedy | 1.0000 |
| v4_4die_3d_stack | fpp_only | m4_greedy | 1.0000 |
| v4_small_3d_stack | serial_baseline | m4_greedy | 1.0000 |
| v4_small_3d_stack | fpp_only | m4_greedy | 1.0000 |
| v4_4die_2_5d_interposer | fpp_only | m4_greedy | 0.9998 |
| v4_4die_2_5d_interposer | bist_only | m4_greedy | 0.9986 |
| v4_4die_3d_stack | bist_only | m4_greedy | 0.9986 |
| v4_4die_2_5d_interposer | bist_fpp | m4_greedy | 0.9950 |
| v4_4die_2_5d_interposer | bist_fpp_thermal | m4_greedy | 0.9950 |
| v4_4die_3d_stack | bist_fpp | m4_greedy | 0.9946 |
| v4_4die_3d_stack | bist_fpp_thermal | m4_greedy | 0.9946 |
| v4_small_3d_stack | bist_only | m4_greedy | 0.9923 |
| v4_small_3d_stack | bist_fpp | m4_greedy | 0.9865 |
| v4_small_3d_stack | bist_fpp_thermal | m4_greedy | 0.9865 |

## Figure 4: FPP Utilization

| case_id | condition | method | fpp_utilization |
| --- | --- | --- | ---: |
| v4_4die_3d_stack | fpp_only | m5_cpsat | 0.0035 |
| v4_4die_3d_stack | fpp_only | m4_greedy | 0.0035 |
| v4_4die_3d_stack | bist_fpp | m5_cpsat | 0.0035 |
| v4_4die_3d_stack | bist_fpp_thermal | m5_cpsat | 0.0035 |
| v4_4die_3d_stack | bist_fpp | m4_greedy | 0.0034 |
| v4_4die_3d_stack | bist_fpp_thermal | m4_greedy | 0.0034 |
| v4_small_3d_stack | fpp_only | m5_cpsat | 0.0024 |
| v4_small_3d_stack | fpp_only | m4_greedy | 0.0024 |
| v4_small_3d_stack | bist_fpp | m5_cpsat | 0.0024 |
| v4_small_3d_stack | bist_fpp_thermal | m5_cpsat | 0.0024 |
| v4_small_3d_stack | bist_fpp | m4_greedy | 0.0024 |
| v4_small_3d_stack | bist_fpp_thermal | m4_greedy | 0.0024 |
| v4_4die_2_5d_interposer | fpp_only | m5_cpsat | 0.0014 |
| v4_4die_2_5d_interposer | bist_fpp | m5_cpsat | 0.0014 |
| v4_4die_2_5d_interposer | bist_fpp_thermal | m5_cpsat | 0.0014 |
| v4_4die_2_5d_interposer | fpp_only | m4_greedy | 0.0014 |
| v4_4die_2_5d_interposer | bist_fpp | m4_greedy | 0.0014 |
| v4_4die_2_5d_interposer | bist_fpp_thermal | m4_greedy | 0.0014 |
| v4_small_3d_stack | serial_baseline | m5_cpsat | 0.0000 |
| v4_small_3d_stack | serial_baseline | m4_greedy | 0.0000 |
| v4_small_3d_stack | bist_only | m5_cpsat | 0.0000 |
| v4_small_3d_stack | bist_only | m4_greedy | 0.0000 |
| v4_4die_3d_stack | serial_baseline | m5_cpsat | 0.0000 |
| v4_4die_3d_stack | serial_baseline | m4_greedy | 0.0000 |
| v4_4die_3d_stack | bist_only | m5_cpsat | 0.0000 |
| v4_4die_3d_stack | bist_only | m4_greedy | 0.0000 |
| v4_4die_2_5d_interposer | serial_baseline | m5_cpsat | 0.0000 |
| v4_4die_2_5d_interposer | serial_baseline | m4_greedy | 0.0000 |
| v4_4die_2_5d_interposer | bist_only | m5_cpsat | 0.0000 |
| v4_4die_2_5d_interposer | bist_only | m4_greedy | 0.0000 |

## Figure 5: BIST Overlap Ratio

| case_id | condition | method | bist_overlap_ratio | max_concurrent_bist |
| --- | --- | --- | ---: | ---: |
| v4_4die_2_5d_interposer | bist_only | m4_greedy | 0.9189 | 3 |
| v4_4die_2_5d_interposer | bist_fpp | m4_greedy | 0.9189 | 3 |
| v4_4die_2_5d_interposer | bist_fpp_thermal | m4_greedy | 0.9189 | 3 |
| v4_4die_3d_stack | bist_only | m5_cpsat | 0.4545 | 2 |
| v4_4die_3d_stack | bist_only | m4_greedy | 0.4542 | 2 |
| v4_4die_3d_stack | bist_fpp | m4_greedy | 0.4542 | 2 |
| v4_4die_3d_stack | bist_fpp_thermal | m4_greedy | 0.4542 | 2 |
| v4_small_3d_stack | bist_only | m5_cpsat | 0.4286 | 2 |
| v4_small_3d_stack | bist_fpp | m5_cpsat | 0.4286 | 2 |
| v4_small_3d_stack | bist_fpp_thermal | m5_cpsat | 0.4286 | 2 |
| v4_small_3d_stack | bist_only | m4_greedy | 0.4286 | 2 |
| v4_small_3d_stack | bist_fpp | m4_greedy | 0.4286 | 2 |
| v4_small_3d_stack | bist_fpp_thermal | m4_greedy | 0.4286 | 2 |
| v4_4die_2_5d_interposer | bist_fpp_thermal | m5_cpsat | 0.3941 | 3 |
| v4_4die_2_5d_interposer | bist_fpp | m5_cpsat | 0.3936 | 3 |
| v4_4die_2_5d_interposer | bist_only | m5_cpsat | 0.3243 | 2 |
| v4_small_3d_stack | serial_baseline | m5_cpsat | 0.0000 | 0 |
| v4_small_3d_stack | serial_baseline | m4_greedy | 0.0000 | 0 |
| v4_small_3d_stack | fpp_only | m5_cpsat | 0.0000 | 0 |
| v4_small_3d_stack | fpp_only | m4_greedy | 0.0000 | 0 |
| v4_4die_3d_stack | serial_baseline | m5_cpsat | 0.0000 | 0 |
| v4_4die_3d_stack | serial_baseline | m4_greedy | 0.0000 | 0 |
| v4_4die_3d_stack | fpp_only | m5_cpsat | 0.0000 | 0 |
| v4_4die_3d_stack | fpp_only | m4_greedy | 0.0000 | 0 |
| v4_4die_3d_stack | bist_fpp | m5_cpsat | 0.0000 | 1 |
| v4_4die_3d_stack | bist_fpp_thermal | m5_cpsat | 0.0000 | 1 |
| v4_4die_2_5d_interposer | serial_baseline | m5_cpsat | 0.0000 | 0 |
| v4_4die_2_5d_interposer | serial_baseline | m4_greedy | 0.0000 | 0 |
| v4_4die_2_5d_interposer | fpp_only | m5_cpsat | 0.0000 | 0 |
| v4_4die_2_5d_interposer | fpp_only | m4_greedy | 0.0000 | 0 |

## Figure 6: Max Concurrent BIST

| case_id | condition | method | max_concurrent_bist | bist_engine_count |
| --- | --- | --- | ---: | ---: |
| v4_4die_2_5d_interposer | bist_only | m4_greedy | 3 | 3 |
| v4_4die_2_5d_interposer | bist_fpp | m5_cpsat | 3 | 3 |
| v4_4die_2_5d_interposer | bist_fpp | m4_greedy | 3 | 3 |
| v4_4die_2_5d_interposer | bist_fpp_thermal | m5_cpsat | 3 | 3 |
| v4_4die_2_5d_interposer | bist_fpp_thermal | m4_greedy | 3 | 3 |
| v4_small_3d_stack | bist_only | m5_cpsat | 2 | 2 |
| v4_small_3d_stack | bist_only | m4_greedy | 2 | 2 |
| v4_small_3d_stack | bist_fpp | m5_cpsat | 2 | 2 |
| v4_small_3d_stack | bist_fpp | m4_greedy | 2 | 2 |
| v4_small_3d_stack | bist_fpp_thermal | m5_cpsat | 2 | 2 |
| v4_small_3d_stack | bist_fpp_thermal | m4_greedy | 2 | 2 |
| v4_4die_3d_stack | bist_only | m5_cpsat | 2 | 2 |
| v4_4die_3d_stack | bist_only | m4_greedy | 2 | 2 |
| v4_4die_3d_stack | bist_fpp | m4_greedy | 2 | 2 |
| v4_4die_3d_stack | bist_fpp_thermal | m4_greedy | 2 | 2 |
| v4_4die_2_5d_interposer | bist_only | m5_cpsat | 2 | 3 |
| v4_4die_3d_stack | bist_fpp | m5_cpsat | 1 | 2 |
| v4_4die_3d_stack | bist_fpp_thermal | m5_cpsat | 1 | 2 |
| v4_small_3d_stack | serial_baseline | m5_cpsat | 0 | 0 |
| v4_small_3d_stack | serial_baseline | m4_greedy | 0 | 0 |
| v4_small_3d_stack | fpp_only | m5_cpsat | 0 | 0 |
| v4_small_3d_stack | fpp_only | m4_greedy | 0 | 0 |
| v4_4die_3d_stack | serial_baseline | m5_cpsat | 0 | 0 |
| v4_4die_3d_stack | serial_baseline | m4_greedy | 0 | 0 |
| v4_4die_3d_stack | fpp_only | m5_cpsat | 0 | 0 |
| v4_4die_3d_stack | fpp_only | m4_greedy | 0 | 0 |
| v4_4die_2_5d_interposer | serial_baseline | m5_cpsat | 0 | 0 |
| v4_4die_2_5d_interposer | serial_baseline | m4_greedy | 0 | 0 |
| v4_4die_2_5d_interposer | fpp_only | m5_cpsat | 0 | 0 |
| v4_4die_2_5d_interposer | fpp_only | m4_greedy | 0 | 0 |

## Figure 7: Thermal Analysis (bist_fpp_thermal condition)

| case_id | method | peak_T_C | thermal_violations |
| --- | --- | ---: | ---: |
| v4_small_3d_stack | m5_cpsat | 54.54 | 0 |
| v4_small_3d_stack | m4_greedy | 54.10 | 0 |
| v4_4die_3d_stack | m5_cpsat | 80.73 | 0 |
| v4_4die_3d_stack | m4_greedy | 116.09 | 4 |
| v4_4die_2_5d_interposer | m5_cpsat | 51.66 | 0 |
| v4_4die_2_5d_interposer | m4_greedy | 51.93 | 0 |

## Figure 8: Scaling Analysis (Makespan vs Die Count / Topology)

| case_id | topology | die_count | condition | method | makespan_us |
| --- | --- | ---: | --- | --- | ---: |
| v4_small_3d_stack | 3d_stack | 3 | bist_fpp | m5_cpsat | 128439 |
| v4_small_3d_stack | 3d_stack | 3 | bist_fpp_thermal | m5_cpsat | 128439 |
| v4_small_3d_stack | 3d_stack | 3 | bist_only | m5_cpsat | 228442 |
| v4_small_3d_stack | 3d_stack | 3 | fpp_only | m5_cpsat | 128426 |
| v4_small_3d_stack | 3d_stack | 3 | serial_baseline | m5_cpsat | 228429 |
| v4_4die_2_5d_interposer | 2_5d_interposer | 4 | bist_fpp | m5_cpsat | 1278355 |
| v4_4die_2_5d_interposer | 2_5d_interposer | 4 | bist_fpp_thermal | m5_cpsat | 1278355 |
| v4_4die_2_5d_interposer | 2_5d_interposer | 4 | bist_only | m5_cpsat | 4230375 |
| v4_4die_2_5d_interposer | 2_5d_interposer | 4 | fpp_only | m5_cpsat | 1278329 |
| v4_4die_2_5d_interposer | 2_5d_interposer | 4 | serial_baseline | m5_cpsat | 4230349 |
| v4_4die_3d_stack | 3d_stack | 4 | bist_fpp | m5_cpsat | 1159303 |
| v4_4die_3d_stack | 3d_stack | 4 | bist_fpp_thermal | m5_cpsat | 1159303 |
| v4_4die_3d_stack | 3d_stack | 4 | bist_only | m5_cpsat | 3729321 |
| v4_4die_3d_stack | 3d_stack | 4 | fpp_only | m5_cpsat | 1159287 |
| v4_4die_3d_stack | 3d_stack | 4 | serial_baseline | m5_cpsat | 3729304 |

## Figure 9: CP-SAT vs Greedy Comparison

| case_id | condition | CP-SAT makespan_us | Greedy makespan_us | CP-SAT/Greedy ratio |
| --- | --- | ---: | ---: | ---: |
| v4_4die_2_5d_interposer | bist_fpp | 1278355 | 1284720 | 0.995 |
| v4_4die_2_5d_interposer | bist_fpp_thermal | 1278355 | 1284720 | 0.995 |
| v4_4die_2_5d_interposer | bist_only | 4230375 | 4236117 | 0.999 |
| v4_4die_2_5d_interposer | fpp_only | 1278329 | 1278525 | 1.000 |
| v4_4die_2_5d_interposer | serial_baseline | 4230349 | 4230359 | 1.000 |
| v4_4die_3d_stack | bist_fpp | 1159303 | 1165631 | 0.995 |
| v4_4die_3d_stack | bist_fpp_thermal | 1159303 | 1165631 | 0.995 |
| v4_4die_3d_stack | bist_only | 3729321 | 3734403 | 0.999 |
| v4_4die_3d_stack | fpp_only | 1159287 | 1159292 | 1.000 |
| v4_4die_3d_stack | serial_baseline | 3729304 | 3729313 | 1.000 |
| v4_small_3d_stack | bist_fpp | 128439 | 130199 | 0.986 |
| v4_small_3d_stack | bist_fpp_thermal | 128439 | 130199 | 0.986 |
| v4_small_3d_stack | bist_only | 228442 | 230203 | 0.992 |
| v4_small_3d_stack | fpp_only | 128426 | 128430 | 1.000 |
| v4_small_3d_stack | serial_baseline | 228429 | 228434 | 1.000 |

## Figure 10: Gantt Charts

Schedule CSVs saved to `results/schedules/v4_final/` for representative case+condition combos.

Key schedule files for the best-condition scenario:

| File | Description |
| --- | --- |
| `v4_4die_2_5d_interposer__bist_fpp__cpsat.csv` | Schedule CSV |
| `v4_4die_2_5d_interposer__bist_fpp__greedy.csv` | Schedule CSV |
| `v4_4die_2_5d_interposer__bist_fpp_thermal__cpsat.csv` | Schedule CSV |
| `v4_4die_2_5d_interposer__bist_fpp_thermal__greedy.csv` | Schedule CSV |
| `v4_4die_2_5d_interposer__bist_only__cpsat.csv` | Schedule CSV |
| `v4_4die_2_5d_interposer__bist_only__greedy.csv` | Schedule CSV |
| `v4_4die_2_5d_interposer__fpp_only__cpsat.csv` | Schedule CSV |
| `v4_4die_2_5d_interposer__fpp_only__greedy.csv` | Schedule CSV |
| `v4_4die_2_5d_interposer__serial_baseline__cpsat.csv` | Schedule CSV |
| `v4_4die_2_5d_interposer__serial_baseline__greedy.csv` | Schedule CSV |
| `v4_4die_3d_stack__bist_fpp__cpsat.csv` | Schedule CSV |
| `v4_4die_3d_stack__bist_fpp__greedy.csv` | Schedule CSV |
| `v4_4die_3d_stack__bist_fpp_thermal__cpsat.csv` | Schedule CSV |
| `v4_4die_3d_stack__bist_fpp_thermal__greedy.csv` | Schedule CSV |
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

### v4_small_3d_stack / bist_only / m4_greedy
  Total BIST phases: 2
  - mem0_die0 on die0: 3us -> 2003us (2000us)
  - mem1_die1 on die1: 8us -> 1508us (1500us)

  - mem0_die0 vs mem1_die1: overlap=1500us OVERLAP

### v4_small_3d_stack / bist_fpp / m5_cpsat
  Total BIST phases: 2
  - mem0_die0 on die0: 100022us -> 102022us (2000us)
  - mem1_die1 on die1: 100027us -> 101527us (1500us)

  - mem0_die0 vs mem1_die1: overlap=1500us OVERLAP

### v4_small_3d_stack / bist_fpp / m4_greedy
  Total BIST phases: 2
  - mem0_die0 on die0: 3us -> 2003us (2000us)
  - mem1_die1 on die1: 8us -> 1508us (1500us)

  - mem0_die0 vs mem1_die1: overlap=1500us OVERLAP

### v4_small_3d_stack / bist_fpp_thermal / m5_cpsat
  Total BIST phases: 2
  - mem0_die0 on die0: 100022us -> 102022us (2000us)
  - mem1_die1 on die1: 100027us -> 101527us (1500us)

  - mem0_die0 vs mem1_die1: overlap=1500us OVERLAP

### v4_small_3d_stack / bist_fpp_thermal / m4_greedy
  Total BIST phases: 2
  - mem0_die0 on die0: 3us -> 2003us (2000us)
  - mem1_die1 on die1: 8us -> 1508us (1500us)

  - mem0_die0 vs mem1_die1: overlap=1500us OVERLAP

### v4_4die_3d_stack / bist_only / m5_cpsat
  Total BIST phases: 2
  - mem0_die0 on die0: 3533058us -> 3539058us (6000us)
  - mem1_die1 on die1: 3533063us -> 3538063us (5000us)

  - mem0_die0 vs mem1_die1: overlap=5000us OVERLAP

### v4_4die_3d_stack / bist_only / m4_greedy
  Total BIST phases: 2
  - mem1_die1 on die1: 5us -> 5005us (5000us)
  - mem0_die0 on die0: 9us -> 6009us (6000us)

  - mem1_die1 vs mem0_die0: overlap=4996us OVERLAP

### v4_4die_3d_stack / bist_fpp / m5_cpsat
  Total BIST phases: 2
  - mem1_die1 on die1: 963040us -> 968040us (5000us)
  - mem0_die0 on die0: 968045us -> 974045us (6000us)

  - mem1_die1 vs mem0_die0: overlap=0us no overlap

### v4_4die_3d_stack / bist_fpp / m4_greedy
  Total BIST phases: 2
  - mem1_die1 on die1: 5us -> 5005us (5000us)
  - mem0_die0 on die0: 9us -> 6009us (6000us)

  - mem1_die1 vs mem0_die0: overlap=4996us OVERLAP

### v4_4die_3d_stack / bist_fpp_thermal / m5_cpsat
  Total BIST phases: 2
  - mem1_die1 on die1: 267us -> 5267us (5000us)
  - mem0_die0 on die0: 17840us -> 23840us (6000us)

  - mem1_die1 vs mem0_die0: overlap=0us no overlap

### v4_4die_3d_stack / bist_fpp_thermal / m4_greedy
  Total BIST phases: 2
  - mem1_die1 on die1: 5us -> 5005us (5000us)
  - mem0_die0 on die0: 9us -> 6009us (6000us)

  - mem1_die1 vs mem0_die0: overlap=4996us OVERLAP

### v4_4die_2_5d_interposer / bist_only / m5_cpsat
  Total BIST phases: 3
  - mem1_die1 on die1: 5us -> 5505us (5500us)
  - mem0_die0 on die0: 3990066us -> 3997066us (7000us)
  - mem2_die2 on die2: 3990071us -> 3996071us (6000us)

  - mem1_die1 vs mem0_die0: overlap=0us no overlap
  - mem1_die1 vs mem2_die2: overlap=0us no overlap
  - mem0_die0 vs mem2_die2: overlap=6000us OVERLAP

### v4_4die_2_5d_interposer / bist_only / m4_greedy
  Total BIST phases: 3
  - mem0_die0 on die0: 4us -> 7004us (7000us)
  - mem2_die2 on die2: 9us -> 6009us (6000us)
  - mem1_die1 on die1: 14us -> 5514us (5500us)

  - mem0_die0 vs mem2_die2: overlap=6000us OVERLAP
  - mem0_die0 vs mem1_die1: overlap=5500us OVERLAP
  - mem2_die2 vs mem1_die1: overlap=5500us OVERLAP

### v4_4die_2_5d_interposer / bist_fpp / m5_cpsat
  Total BIST phases: 3
  - mem1_die1 on die1: 1038031us -> 1043531us (5500us)
  - mem2_die2 on die2: 1042043us -> 1048043us (6000us)
  - mem0_die0 on die0: 1042891us -> 1049891us (7000us)

  - mem1_die1 vs mem2_die2: overlap=1488us OVERLAP
  - mem1_die1 vs mem0_die0: overlap=641us OVERLAP
  - mem2_die2 vs mem0_die0: overlap=5153us OVERLAP

### v4_4die_2_5d_interposer / bist_fpp / m4_greedy
  Total BIST phases: 3
  - mem0_die0 on die0: 4us -> 7004us (7000us)
  - mem2_die2 on die2: 9us -> 6009us (6000us)
  - mem1_die1 on die1: 14us -> 5514us (5500us)

  - mem0_die0 vs mem2_die2: overlap=6000us OVERLAP
  - mem0_die0 vs mem1_die1: overlap=5500us OVERLAP
  - mem2_die2 vs mem1_die1: overlap=5500us OVERLAP

### v4_4die_2_5d_interposer / bist_fpp_thermal / m5_cpsat
  Total BIST phases: 3
  - mem1_die1 on die1: 1038037us -> 1043537us (5500us)
  - mem2_die2 on die2: 1042043us -> 1048043us (6000us)
  - mem0_die0 on die0: 1042891us -> 1049891us (7000us)

  - mem1_die1 vs mem2_die2: overlap=1493us OVERLAP
  - mem1_die1 vs mem0_die0: overlap=646us OVERLAP
  - mem2_die2 vs mem0_die0: overlap=5153us OVERLAP

### v4_4die_2_5d_interposer / bist_fpp_thermal / m4_greedy
  Total BIST phases: 3
  - mem0_die0 on die0: 4us -> 7004us (7000us)
  - mem2_die2 on die2: 9us -> 6009us (6000us)
  - mem1_die1 on die1: 14us -> 5514us (5500us)

  - mem0_die0 vs mem2_die2: overlap=6000us OVERLAP
  - mem0_die0 vs mem1_die1: overlap=5500us OVERLAP
  - mem2_die2 vs mem1_die1: overlap=5500us OVERLAP

## Notes

- **Two transport resources**: TAP (serial, capacity=1, all dies) and FPP (parallel, optional, some dies).
- **Task types**: INTEST, EXTEST, BIST, IJTAG -- all mandatory.
- **BIST model**: Per-die BIST engines (capacity=1 each). BIST releases TAP during local execution, enabling overlap.
- **FPP model**: Standard IEEE 1838-2019 Clause 7 FPP lanes for parallel data transport.
- **Thermal model**: First-order RC proxy with die-to-die vertical coupling and heat sink distance factors.
- **CP-SAT time limit**: 30s per solve.
- **10 figures** regenerable from this experiment data and schedule CSVs.
