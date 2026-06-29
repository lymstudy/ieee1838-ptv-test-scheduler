# V4 Core Experiment Report

- Case: `v4_core_4die_task`
- Description: Section 0.4 task-multiplexed scheduling with mandatory tasks
- Total conditions: 4
- Total runs: 8

## Conditions

| Condition | Scheduler | Status | Makespan (s) | Tasks Scheduled | BIST Overlap | TAP Util | FPP Util | Peak Power (W) | Peak Temp (C) |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Pure Serial (no BIST, no FPP) | greedy | ok | 0.101922720 | 10/10 | 0.0000 | 0.9999 | 0.0000 | 2.7600 | 56.91 |
| Pure Serial (no BIST, no FPP) | cpsat | ok | 0.101912720 | 10/10 | 0.0000 | 1.0000 | 0.0000 | 4.1200 | 56.64 |
| BIST Parallel (per-die engines, no FPP) | greedy | ok | 0.105568960 | 12/12 | 0.2874 | 0.9655 | 0.0000 | 3.1300 | 69.63 |
| BIST Parallel (per-die engines, no FPP) | cpsat | ok | 0.101930640 | 12/12 | 0.0000 | 1.0000 | 0.0000 | 3.6000 | 64.64 |
| BIST+FPP (per-die engines, 8 FPP lanes) | greedy | ok | 0.005539560 | 12/12 | 0.4444 | 0.1090 | 0.0286 | 6.4600 | 119.02 |
| BIST+FPP (per-die engines, 8 FPP lanes) | cpsat | ok | 0.005532160 | 12/12 | 0.4444 | 0.1092 | 0.0286 | 6.7600 | 96.24 |
| BIST+FPP+Thermal (all mechanisms, thermal monitoring) | greedy | ok | 0.005539560 | 12/12 | 0.4444 | 0.1090 | 0.0286 | 6.4600 | 119.02 |
| BIST+FPP+Thermal (all mechanisms, thermal monitoring) | cpsat | ok | 0.005532160 | 12/12 | 0.4444 | 0.1092 | 0.0286 | 6.2900 | 96.31 |

## Speedup vs Pure Serial

| Condition | Scheduler | Makespan (s) | Speedup vs Pure Serial |
| --- | --- | ---: | ---: |
| Pure Serial (no BIST, no FPP) | greedy | 0.101922720 | 1.00x |
| Pure Serial (no BIST, no FPP) | cpsat | 0.101912720 | 1.00x |
| BIST Parallel (per-die engines, no FPP) | greedy | 0.105568960 | 0.97x |
| BIST Parallel (per-die engines, no FPP) | cpsat | 0.101930640 | 1.00x |
| BIST+FPP (per-die engines, 8 FPP lanes) | greedy | 0.005539560 | 18.40x |
| BIST+FPP (per-die engines, 8 FPP lanes) | cpsat | 0.005532160 | 18.42x |
| BIST+FPP+Thermal (all mechanisms, thermal monitoring) | greedy | 0.005539560 | 18.40x |
| BIST+FPP+Thermal (all mechanisms, thermal monitoring) | cpsat | 0.005532160 | 18.42x |

## BIST Overlap Analysis

| Condition | Scheduler | BIST Tasks | Overlap Ratio |
| --- | --- | ---: | ---: |
| Pure Serial (no BIST, no FPP) | greedy | 0 | 0.0000 |
| Pure Serial (no BIST, no FPP) | cpsat | 0 | 0.0000 |
| BIST Parallel (per-die engines, no FPP) | greedy | 2 | 0.2874 |
| BIST Parallel (per-die engines, no FPP) | cpsat | 2 | 0.0000 |
| BIST+FPP (per-die engines, 8 FPP lanes) | greedy | 2 | 0.4444 |
| BIST+FPP (per-die engines, 8 FPP lanes) | cpsat | 2 | 0.4444 |
| BIST+FPP+Thermal (all mechanisms, thermal monitoring) | greedy | 2 | 0.4444 |
| BIST+FPP+Thermal (all mechanisms, thermal monitoring) | cpsat | 2 | 0.4444 |

## Notes

- All tasks are mandatory (unlike pre-v4 where recipes were alternatives per target).
- Task mode: AddExactlyOne constraint per task_id (one variant per task).
- BIST engines are per-die (capacity=1 each), so BIST on die0 and die1 can overlap.
- TAP is released during LOCAL_BIST_RUN, enabling parallel BIST execution.
- FPP data offload uses standard-defined FPP lanes (IEEE 1838-2019 Clause 7).
- Thermal evaluation uses first-order RC proxy model.
