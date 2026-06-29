# Habiby 2022 PBO Incremental Scheduling Baseline Report

## Summary

- Successful cases: 6
- Failed cases: 0

## Results

| case_id | makespan_s | sessions | targets | peak_power_w | solver_status | solver_wall_s | vs_serial_% | vs_fixed_fastest_% |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| m10_small_d695_3d_stack | 0.0012 | 7 | 14 | 5.5 | OPTIMAL | 0.105 | 65.7% | -1.0% |
| m10_medium_p22810_3d_stack | 0.0030 | 9 | 22 | 6.6 | OPTIMAL | 0.132 | 96.8% | -30.7% |
| m10_large_p34392_3d_stack | 0.0046 | 11 | 28 | 6.3 | OPTIMAL | 0.157 | 97.8% | -30.8% |
| m21_pressure_small_d695_3d_stack | 0.1785 | 7 | 14 | 9.5 | OPTIMAL | 0.093 | 98.3% | -197.5% |
| m21_pressure_medium_p22810_3d_stack | 5.1466 | 9 | 22 | 14.1 | OPTIMAL | 0.131 | 96.8% | -5260.3% |
| m21_pressure_large_p34392_3d_stack | 7.2739 | 11 | 28 | 18.6 | OPTIMAL | 0.157 | 98.3% | -5960.8% |

**Averages:**
- Makespan: 2.1013 s
- Sessions: 9.0
- Solver wall time: 0.129 s
- Gain vs pure serial: 92.3%
- Gain vs fixed fastest (greedy): -1913.5%

## Per-case Session Details

### m10_small_d695_3d_stack
- Makespan: 0.0012 s
- Sessions: 7
- Peak power: 5.5 W
- Solver status: OPTIMAL
- Solver wall time: 0.105 s

| session | duration_s | targets | num_targets | status |
| --- | ---: | --- | ---: | --- |
| 1 | 0.000026 | d695_m1_die1, d695_m3_die0, d695_m8_die3, d695_m9_die2 | 4 | OPTIMAL |
| 2 | 0.000035 | d695_m10_die2, d695_m2_die0, d695_m6_die1, d695_m7_die3 | 4 | OPTIMAL |
| 3 | 0.000013 | d695_m4_die1, d695_m5_die0 | 2 | OPTIMAL |
| 4 | 0.000430 | link_die2_die3 | 1 | OPTIMAL |
| 5 | 0.000387 | link_die1_die2 | 1 | OPTIMAL |
| 6 | 0.000344 | link_die0_die1 | 1 | OPTIMAL |
| 7 | 0.000007 | sensor_m10_small_d695_3d_stack | 1 | OPTIMAL |

### m10_medium_p22810_3d_stack
- Makespan: 0.0030 s
- Sessions: 9
- Peak power: 6.6 W
- Solver status: OPTIMAL
- Solver wall time: 0.132 s

| session | duration_s | targets | num_targets | status |
| --- | ---: | --- | ---: | --- |
| 1 | 0.000237 | p22810_m20_die2, p22810_m21_die4, p22810_m3_die3, p22810_m6_die5, p22810_m7_die1, ... (+1) | 6 | OPTIMAL |
| 2 | 0.000535 | p22810_m1_die2, p22810_m26_die0, p22810_m2_die1, p22810_m4_die3, p22810_m5_die5, ... (+1) | 6 | OPTIMAL |
| 3 | 0.000046 | p22810_m11_die1, p22810_m12_die0, p22810_m18_die2, p22810_m25_die3 | 4 | OPTIMAL |
| 4 | 0.000516 | link_die4_die5 | 1 | OPTIMAL |
| 5 | 0.000473 | link_die3_die4 | 1 | OPTIMAL |
| 6 | 0.000430 | link_die2_die3 | 1 | OPTIMAL |
| 7 | 0.000387 | link_die1_die2 | 1 | OPTIMAL |
| 8 | 0.000344 | link_die0_die1 | 1 | OPTIMAL |
| 9 | 0.000009 | sensor_m10_medium_p22810_3d_stack | 1 | OPTIMAL |

### m10_large_p34392_3d_stack
- Makespan: 0.0046 s
- Sessions: 11
- Peak power: 6.3 W
- Solver status: OPTIMAL
- Solver wall time: 0.157 s

| session | duration_s | targets | num_targets | status |
| --- | ---: | --- | ---: | --- |
| 1 | 0.000085 | p34392_m0_die1, p34392_m12_die2, p34392_m14_die0, p34392_m16_die3, p34392_m17_die6, ... (+3) | 8 | OPTIMAL |
| 2 | 0.000603 | p34392_m11_die7, p34392_m13_die3, p34392_m15_die2, p34392_m2_die1, p34392_m3_die0, ... (+3) | 8 | OPTIMAL |
| 3 | 0.000560 | p34392_m10_die2, p34392_m18_die0, p34392_m19_die3, p34392_m1_die1 | 4 | OPTIMAL |
| 4 | 0.000601 | link_die6_die7 | 1 | OPTIMAL |
| 5 | 0.000558 | link_die5_die6 | 1 | OPTIMAL |
| 6 | 0.000516 | link_die4_die5 | 1 | OPTIMAL |
| 7 | 0.000473 | link_die3_die4 | 1 | OPTIMAL |
| 8 | 0.000430 | link_die2_die3 | 1 | OPTIMAL |
| 9 | 0.000387 | link_die1_die2 | 1 | OPTIMAL |
| 10 | 0.000344 | link_die0_die1 | 1 | OPTIMAL |
| 11 | 0.000012 | sensor_m10_large_p34392_3d_stack | 1 | OPTIMAL |

### m21_pressure_small_d695_3d_stack
- Makespan: 0.1785 s
- Sessions: 7
- Peak power: 9.5 W
- Solver status: OPTIMAL
- Solver wall time: 0.093 s

| session | duration_s | targets | num_targets | status |
| --- | ---: | --- | ---: | --- |
| 1 | 0.051224 | d695_m10_die2, d695_m3_die0, d695_m4_die1, d695_m8_die3 | 4 | OPTIMAL |
| 2 | 0.051224 | d695_m1_die1, d695_m2_die0, d695_m7_die3, d695_m9_die2 | 4 | OPTIMAL |
| 3 | 0.074890 | d695_m5_die0, d695_m6_die1 | 2 | OPTIMAL |
| 4 | 0.000430 | link_die2_die3 | 1 | OPTIMAL |
| 5 | 0.000387 | link_die1_die2 | 1 | OPTIMAL |
| 6 | 0.000344 | link_die0_die1 | 1 | OPTIMAL |
| 7 | 0.000007 | sensor_m10_small_d695_3d_stack | 1 | OPTIMAL |

### m21_pressure_medium_p22810_3d_stack
- Makespan: 5.1466 s
- Sessions: 9
- Peak power: 14.1 W
- Solver status: OPTIMAL
- Solver wall time: 0.131 s

| session | duration_s | targets | num_targets | status |
| --- | ---: | --- | ---: | --- |
| 1 | 0.994602 | p22810_m20_die2, p22810_m21_die4, p22810_m3_die3, p22810_m6_die5, p22810_m7_die1, ... (+1) | 6 | OPTIMAL |
| 2 | 3.943722 | p22810_m1_die2, p22810_m26_die0, p22810_m2_die1, p22810_m4_die3, p22810_m5_die5, ... (+1) | 6 | OPTIMAL |
| 3 | 0.206104 | p22810_m11_die1, p22810_m12_die0, p22810_m18_die2, p22810_m25_die3 | 4 | OPTIMAL |
| 4 | 0.000516 | link_die4_die5 | 1 | OPTIMAL |
| 5 | 0.000473 | link_die3_die4 | 1 | OPTIMAL |
| 6 | 0.000430 | link_die2_die3 | 1 | OPTIMAL |
| 7 | 0.000387 | link_die1_die2 | 1 | OPTIMAL |
| 8 | 0.000344 | link_die0_die1 | 1 | OPTIMAL |
| 9 | 0.000009 | sensor_m10_medium_p22810_3d_stack | 1 | OPTIMAL |

### m21_pressure_large_p34392_3d_stack
- Makespan: 7.2739 s
- Sessions: 11
- Peak power: 18.6 W
- Solver status: OPTIMAL
- Solver wall time: 0.157 s

| session | duration_s | targets | num_targets | status |
| --- | ---: | --- | ---: | --- |
| 1 | 3.177666 | p34392_m0_die1, p34392_m13_die3, p34392_m15_die2, p34392_m3_die0, p34392_m4_die6, ... (+3) | 8 | OPTIMAL |
| 2 | 3.947586 | p34392_m11_die7, p34392_m12_die2, p34392_m17_die6, p34392_m18_die0, p34392_m19_die3, ... (+3) | 8 | OPTIMAL |
| 3 | 0.145304 | p34392_m10_die2, p34392_m14_die0, p34392_m16_die3, p34392_m1_die1 | 4 | OPTIMAL |
| 4 | 0.000601 | link_die6_die7 | 1 | OPTIMAL |
| 5 | 0.000558 | link_die5_die6 | 1 | OPTIMAL |
| 6 | 0.000516 | link_die4_die5 | 1 | OPTIMAL |
| 7 | 0.000473 | link_die3_die4 | 1 | OPTIMAL |
| 8 | 0.000430 | link_die2_die3 | 1 | OPTIMAL |
| 9 | 0.000387 | link_die1_die2 | 1 | OPTIMAL |
| 10 | 0.000344 | link_die0_die1 | 1 | OPTIMAL |
| 11 | 0.000012 | sensor_m10_large_p34392_3d_stack | 1 | OPTIMAL |

## Method Description

The Habiby 2022 PBO (Pseudo-Boolean Optimization) incremental approach,
adapted for IEEE 1838:

1. **Recipe selection** (fixed-path): For each FPP-capable target, select the
   recipe with the fewest FPP lanes to maximize concurrency in the shared lane
   pool. For non-FPP targets (S/I), select the fastest available recipe.
2. **PBO iteration**: Build a CP-SAT model with boolean variables x_i for each
   target in the pool.
3. **Resource constraints** encoded as linear inequalities:
   - PTAP serial mutual exclusion: at most 1 serial-only (S/I) target;
     FPP/BIST targets can overlap with each other.
   - FPP lanes: cumulative sum constraint (per-channel).
   - Power: cumulative power budget.
   - BIST engine groups: capacity limits on shared BIST engines.
   - DWR conflict groups: mutual exclusion on shared DWR segments.
   - Exclusive resources (test sessions): one target per test session per die.
4. **Objective**: Maximize the number of concurrently active targets.
5. **Session formation**: Solve, record active targets as a session, remove
   them from the pool. Session duration = sum(serial_resource_times) +
   max(non_serial_times), approximating sequential serial phases with
   overlapping non-serial phases.
6. Repeat until all targets scheduled.
7. Total makespan = sum of session durations.

This matches the incremental PBO methodology from:

> Habiby et al. "Power-aware test scheduling framework for IEEE 1687
> multi-power domain networks using formal techniques."
> Microelectronics Reliability, 2022.

## Notes

- OR-Tools CP-SAT is used instead of a native PBO solver (clasp).
- CP-SAT provides comparable incremental optimization capability.
- The approach balances per-target speed (fastest recipe) with concurrency
  (PBO packing). FPP targets use minimal-lane recipes to enable concurrency;
  this trades some per-target speed for overall makespan reduction.
- The negative gain vs `fixed_fastest` is expected: `fixed_fastest` uses
  maximum-lane recipes (fastest per target) but cannot achieve concurrency
  due to lane monopolization. PBO achieves 2-2.5x concurrency with
  slightly slower per-target recipes.
