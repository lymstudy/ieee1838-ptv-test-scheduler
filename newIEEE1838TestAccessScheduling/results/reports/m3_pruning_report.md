# M3 Pareto Pruning Report

- Recipes before pruning: 26
- Recipes after pruning: 17
- Recipes removed: 9
- Dominance metrics: total_time_s, peak_power_w, thermal_risk, thermal_load, serial_time_s, max_fpp_lanes_required, lane_occupancy

| target_id | before | after | removed | removed recipes |
| --- | ---: | ---: | ---: | --- |
| core_die0_logic | 5 | 3 | 2 | H_core_die0_logic_lane1;H_core_die0_logic_lane2 |
| core_die1_cpu | 5 | 3 | 2 | H_core_die1_cpu_lane1;H_core_die1_cpu_lane2 |
| core_die3_accel | 6 | 3 | 3 | H_core_die3_accel_lane1;H_core_die3_accel_lane2;S_core_die3_accel_serial |
| link_die0_die1 | 1 | 1 | 0 |  |
| link_die1_die2 | 1 | 1 | 0 |  |
| link_die2_die3 | 1 | 1 | 0 |  |
| mem_die2_sram | 6 | 4 | 2 | H_mem_die2_sram_lane1;H_mem_die2_sram_lane2 |
| sensor_die1_temp | 1 | 1 | 0 |  |

## Dominance Notes

### core_die0_logic
- H_core_die0_logic_lane1 dominated by F_core_die0_logic_lane1 (better=total_time_s,thermal_load,serial_time_s; equal_or_tied=peak_power_w,thermal_risk,max_fpp_lanes_required,lane_occupancy)
- H_core_die0_logic_lane2 dominated by F_core_die0_logic_lane2 (better=total_time_s,thermal_load,serial_time_s; equal_or_tied=peak_power_w,thermal_risk,max_fpp_lanes_required,lane_occupancy)

### core_die1_cpu
- H_core_die1_cpu_lane1 dominated by F_core_die1_cpu_lane1 (better=total_time_s,thermal_load,serial_time_s; equal_or_tied=peak_power_w,thermal_risk,max_fpp_lanes_required,lane_occupancy)
- H_core_die1_cpu_lane2 dominated by F_core_die1_cpu_lane2 (better=total_time_s,thermal_load,serial_time_s; equal_or_tied=peak_power_w,thermal_risk,max_fpp_lanes_required,lane_occupancy)

### core_die3_accel
- H_core_die3_accel_lane1 dominated by F_core_die3_accel_lane1 (better=total_time_s,thermal_load,serial_time_s; equal_or_tied=peak_power_w,thermal_risk,max_fpp_lanes_required,lane_occupancy)
- H_core_die3_accel_lane2 dominated by F_core_die3_accel_lane2 (better=total_time_s,thermal_load,serial_time_s; equal_or_tied=peak_power_w,thermal_risk,max_fpp_lanes_required,lane_occupancy)
- S_core_die3_accel_serial dominated by B_core_die3_accel_local_bist (better=total_time_s,peak_power_w,thermal_risk,thermal_load,serial_time_s; equal_or_tied=max_fpp_lanes_required,lane_occupancy)

### mem_die2_sram
- H_mem_die2_sram_lane1 dominated by F_mem_die2_sram_lane1 (better=total_time_s,thermal_load,serial_time_s; equal_or_tied=peak_power_w,thermal_risk,max_fpp_lanes_required,lane_occupancy)
- H_mem_die2_sram_lane2 dominated by F_mem_die2_sram_lane2 (better=total_time_s,thermal_load,serial_time_s; equal_or_tied=peak_power_w,thermal_risk,max_fpp_lanes_required,lane_occupancy)
