# M7 Thermal Proxy Report

This report uses a first-order RC thermal proxy. It is not a HotSpot replacement.

## Schedule Summary

| schedule | makespan_s | peak_temp_c | peak_region | over_limit_s | violations |
| --- | ---: | ---: | --- | ---: | ---: |
| m4_greedy | 0.005004640 | 25.028299 | thermal_die3 | 0.000000000 | 0 |
| m5_cpsat | 0.003963920 | 25.028282 | thermal_die3 | 0.000000000 | 0 |
| m6_alns | 0.003963920 | 25.028282 | thermal_die3 | 0.000000000 | 0 |

- Lowest proxy peak temperature: `m5_cpsat` at 25.028282 C.

## Hotspots

| schedule | region | die | peak_temp_c | peak_time_s | limit_c |
| --- | --- | --- | ---: | ---: | ---: |
| m4_greedy | thermal_die3 | die3 | 25.028299 | 0.005004640 | 85.00 |
| m4_greedy | thermal_die1 | die1 | 25.019724 | 0.003098120 | 85.00 |
| m4_greedy | thermal_die2 | die2 | 25.014942 | 0.005004640 | 85.00 |
| m4_greedy | thermal_die0 | die0 | 25.012783 | 0.002583840 | 85.00 |
| m5_cpsat | thermal_die3 | die3 | 25.028282 | 0.003962282 | 85.00 |
| m5_cpsat | thermal_die1 | die1 | 25.019752 | 0.003963920 | 85.00 |
| m5_cpsat | thermal_die2 | die2 | 25.014990 | 0.003963920 | 85.00 |
| m5_cpsat | thermal_die0 | die0 | 25.012709 | 0.003963920 | 85.00 |
| m6_alns | thermal_die3 | die3 | 25.028282 | 0.003961000 | 85.00 |
| m6_alns | thermal_die1 | die1 | 25.019752 | 0.003963920 | 85.00 |
| m6_alns | thermal_die2 | die2 | 25.014990 | 0.003963920 | 85.00 |
| m6_alns | thermal_die0 | die0 | 25.012709 | 0.003963920 | 85.00 |
