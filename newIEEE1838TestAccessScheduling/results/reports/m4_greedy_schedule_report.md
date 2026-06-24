# M4 Greedy Schedule Report

- Case: 3d_stack_m1_example
- Selected recipes: 8
- Scheduled phases: 42
- Makespan: 0.005004640 s
- Peak scheduled power: 3.270000 W
- Peak FPP lanes used: 4
- Serial busy time: 0.000575000 s
- FPP lane-time: 0.015808000 lane*s

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

## Gantt Preview

```text
0.000000000-0.000003200 | #                                                            | core_die1_cpu:CONFIG_ACCESS_PATH
0.000003200-0.000004480 | #                                                            | core_die1_cpu:CONFIG_FPP
0.000004480-0.000006120 | #                                                            | core_die1_cpu:CONFIG_SCAN_OR_DWR_MODE
0.000006120-0.000008040 | #                                                            | core_die0_logic:CONFIG_ACCESS_PATH
0.000006120-0.001206120 | ##############                                               | core_die1_cpu:FPP_SHIFT_IN
0.000008040-0.000009320 | #                                                            | core_die0_logic:CONFIG_FPP
0.000009320-0.000010640 | #                                                            | core_die0_logic:CONFIG_SCAN_OR_DWR_MODE
0.000010640-0.000778640 | #########                                                    | core_die0_logic:FPP_SHIFT_IN
0.000010640-0.000016400 | #                                                            | core_die3_accel:CONFIG_ACCESS_PATH
0.000016400-0.000017680 | #                                                            | core_die3_accel:CONFIG_FPP
0.000017680-0.000019000 | #                                                            | core_die3_accel:CONFIG_SCAN_OR_DWR_MODE
0.000019000-0.000023480 | #                                                            | mem_die2_sram:CONFIG_ACCESS_PATH
0.000023480-0.000024760 | #                                                            | mem_die2_sram:CONFIG_FPP
0.000024760-0.000026400 | #                                                            | mem_die2_sram:CONFIG_SCAN_OR_DWR_MODE
0.000026400-0.000030880 | #                                                            | link_die1_die2:CONFIG_ACCESS_PATH
0.000030880-0.000034080 | #                                                            | link_die0_die1:CONFIG_ACCESS_PATH
0.000034080-0.000039840 | #                                                            | link_die2_die3:CONFIG_ACCESS_PATH
0.000039840-0.000041480 | #                                                            | link_die2_die3:CONFIG_DWR_MODE
0.000041480-0.000123400 | #                                                            | link_die2_die3:DWR_SHIFT_IN
0.000123400-0.000124400 |  #                                                           | link_die2_die3:DWR_CAPTURE
0.000124400-0.000219120 |  #                                                           | link_die2_die3:DWR_SHIFT_OUT
0.000219120-0.000222320 |   #                                                          | sensor_die1_temp:CONFIG_ACCESS_PATH
0.000222320-0.000222640 |   #                                                          | sensor_die1_temp:ACCESS_INSTRUMENT
0.000222640-0.000223280 |   #                                                          | sensor_die1_temp:READ_INSTRUMENT
0.000778640-0.000779640 |          #                                                   | core_die0_logic:CAPTURE
0.000779640-0.001547640 |          #########                                           | core_die0_logic:FPP_SHIFT_OUT
0.001206120-0.001207120 |               #                                              | core_die1_cpu:CAPTURE
0.001207120-0.002407120 |               ##############                                 | core_die1_cpu:FPP_SHIFT_OUT
0.001547640-0.003275640 |                   ####################                       | core_die3_accel:FPP_SHIFT_IN
0.002407120-0.002408760 |                             #                                | link_die0_die1:CONFIG_DWR_MODE
0.002407120-0.002663120 |                             ###                              | mem_die2_sram:FPP_SHIFT_IN
0.002408760-0.002490680 |                             #                                | link_die0_die1:DWR_SHIFT_IN
0.002490680-0.002491680 |                              #                               | link_die0_die1:DWR_CAPTURE
0.002491680-0.002583840 |                              #                               | link_die0_die1:DWR_SHIFT_OUT
0.002663120-0.002664120 |                                #                             | mem_die2_sram:CAPTURE
0.002664120-0.002920120 |                                ###                           | mem_die2_sram:FPP_SHIFT_OUT
0.002920120-0.002921760 |                                    #                         | link_die1_die2:CONFIG_DWR_MODE
0.002921760-0.003003680 |                                    #                         | link_die1_die2:DWR_SHIFT_IN
0.003003680-0.003004680 |                                     #                        | link_die1_die2:DWR_CAPTURE
0.003004680-0.003098120 |                                     #                        | link_die1_die2:DWR_SHIFT_OUT
0.003275640-0.003276640 |                                        #                     | core_die3_accel:CAPTURE
0.003276640-0.005004640 |                                        ####################  | core_die3_accel:FPP_SHIFT_OUT
```
