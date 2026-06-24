# M5 Schedule Refinement Report

- Case: 3d_stack_m1_example
- Backend: ortools
- Baseline M4 makespan: 0.005004640 s
- Refined M5 makespan: 0.003963920 s
- Improvement: 0.001040720 s (20.80%)
- Selected recipes: 8
- Scheduled phases: 42
- Peak scheduled power: 5.590000 W
- Peak FPP lanes used: 4
- CP-SAT status: OPTIMAL
- CP-SAT wall time: 0.878283 s

## Refinement Moves

| iteration | type | before_s | after_s | detail |
| ---: | --- | ---: | ---: | --- |
| 0 | cp_sat | 0.005004640 | 0.003963920 | OR-Tools CP-SAT status=OPTIMAL, wall_time_s=0.878 |

## Selected Recipes

| target_id | recipe_id | type | total_time_s | peak_power_w |
| --- | --- | --- | ---: | ---: |
| core_die0_logic | F_core_die0_logic_lane2 | F | 0.0015415199999999998 | 1.92 |
| core_die1_cpu | F_core_die1_cpu_lane2 | F | 0.00240712 | 2.24 |
| core_die3_accel | F_core_die3_accel_lane2 | F | 0.0034653600000000002 | 2.7600000000000002 |
| link_die0_die1 | I_link_die0_die1_serial_extest | I | 0.00017991999999999997 | 0.45 |
| link_die1_die2 | I_link_die1_die2_serial_extest | I | 0.00018248 | 0.5 |
| link_die2_die3 | I_link_die2_die3_serial_extest | I | 0.00018503999999999998 | 0.55 |
| mem_die2_sram | F_mem_die2_sram_lane2 | F | 0.0005204000000000001 | 1.7000000000000002 |
| sensor_die1_temp | S_sensor_die1_temp_serial | S | 4.16e-06 | 0.05 |
