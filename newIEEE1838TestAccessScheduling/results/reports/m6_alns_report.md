# M6 ALNS Schedule Report

- Case: 3d_stack_m1_example
- Repair backend: ortools
- Seed: 1838
- Iterations: 20
- Initial makespan: 0.003963920 s
- Best makespan: 0.003963920 s
- Improvement: 0.000000000 s (0.00%)
- Accepted moves: 20
- Improving moves: 0
- Peak scheduled power: 5.040000 W
- Peak FPP lanes used: 4

## Convergence

| iteration | operator | candidate_s | incumbent_s | best_s | accepted | improved |
| ---: | --- | ---: | ---: | ---: | --- | --- |
| 1 | critical_path | 0.003963920 | 0.003963920 | 0.003963920 | True | False |
| 2 | resource_congestion | 0.003963920 | 0.003963920 | 0.003963920 | True | False |
| 3 | thermal_hotspot | 0.003963920 | 0.003963920 | 0.003963920 | True | False |
| 4 | random | 0.003963920 | 0.003963920 | 0.003963920 | True | False |
| 5 | critical_path | 0.003963920 | 0.003963920 | 0.003963920 | True | False |
| 6 | resource_congestion | 0.003963920 | 0.003963920 | 0.003963920 | True | False |
| 7 | thermal_hotspot | 0.003963920 | 0.003963920 | 0.003963920 | True | False |
| 8 | random | 0.003963920 | 0.003963920 | 0.003963920 | True | False |
| 9 | critical_path | 0.003963920 | 0.003963920 | 0.003963920 | True | False |
| 10 | resource_congestion | 0.003963920 | 0.003963920 | 0.003963920 | True | False |
| 11 | thermal_hotspot | 0.003963920 | 0.003963920 | 0.003963920 | True | False |
| 12 | random | 0.003963920 | 0.003963920 | 0.003963920 | True | False |
| 13 | critical_path | 0.003963920 | 0.003963920 | 0.003963920 | True | False |
| 14 | resource_congestion | 0.003963920 | 0.003963920 | 0.003963920 | True | False |
| 15 | thermal_hotspot | 0.003963920 | 0.003963920 | 0.003963920 | True | False |
| 16 | random | 0.003963920 | 0.003963920 | 0.003963920 | True | False |
| 17 | critical_path | 0.003963920 | 0.003963920 | 0.003963920 | True | False |
| 18 | resource_congestion | 0.003963920 | 0.003963920 | 0.003963920 | True | False |
| 19 | thermal_hotspot | 0.003963920 | 0.003963920 | 0.003963920 | True | False |
| 20 | random | 0.003963920 | 0.003963920 | 0.003963920 | True | False |

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
