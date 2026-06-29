# M12 Thermal Validation Report

This report uses the M7 first-order RC proxy and exports HotSpot-compatible inputs. It is not a HotSpot execution report.

- Summary rows: 24
- HotSpot export rows: 6

## Peak Temperature By Profile

| profile | method | rows | avg_peak_temp_c | max_peak_temp_c | avg_rise_c |
| --- | --- | ---: | ---: | ---: | ---: |
| nominal_proxy | fixed_fastest | 3 | 55.375658 | 71.135649 | 30.375658 |
| nominal_proxy | low_power | 3 | 64.356039 | 83.673369 | 39.356039 |
| nominal_proxy | thermal_min_risk | 3 | 64.356039 | 83.673369 | 39.356039 |
| nominal_proxy | m4_greedy | 3 | 55.375658 | 71.135649 | 30.375658 |
| stress_proxy | fixed_fastest | 3 | 76.287714 | 102.727558 | 51.287714 |
| stress_proxy | low_power | 3 | 98.908080 | 138.171494 | 73.908080 |
| stress_proxy | thermal_min_risk | 3 | 98.908080 | 138.171494 | 73.908080 |
| stress_proxy | m4_greedy | 3 | 76.287714 | 102.727558 | 51.287714 |

## Best Stress-Profile Method Per Case

| case | topology | best method | peak_temp_c | rise_c | makespan_s |
| --- | --- | --- | ---: | ---: | ---: |
| m10_medium_p22810_3d_stack | 3d_stack | fixed_fastest | 102.727558 | 77.727558 | 0.002277820 |
| m10_medium_p22810_5_5d_multi_tower | 5_5d_multi_tower | fixed_fastest | 82.237816 | 57.237816 | 0.002157836 |
| m10_small_d695_5_5d_multi_tower | 5_5d_multi_tower | fixed_fastest | 43.897768 | 18.897768 | 0.001259840 |

## HotSpot Input Export

| case | schedule | floorplan | ptrace | samples |
| --- | --- | --- | --- | ---: |
| m10_small_d695_5_5d_multi_tower | thermal_min_risk | `results/hotspot/m12/m10_small_d695_5_5d_multi_tower.flp` | `results/hotspot/m12/m10_small_d695_5_5d_multi_tower__thermal_min_risk.ptrace` | 134 |
| m10_small_d695_5_5d_multi_tower | m4_greedy | `results/hotspot/m12/m10_small_d695_5_5d_multi_tower.flp` | `results/hotspot/m12/m10_small_d695_5_5d_multi_tower__m4_greedy.ptrace` | 126 |
| m10_medium_p22810_3d_stack | thermal_min_risk | `results/hotspot/m12/m10_medium_p22810_3d_stack.flp` | `results/hotspot/m12/m10_medium_p22810_3d_stack__thermal_min_risk.ptrace` | 246 |
| m10_medium_p22810_3d_stack | m4_greedy | `results/hotspot/m12/m10_medium_p22810_3d_stack.flp` | `results/hotspot/m12/m10_medium_p22810_3d_stack__m4_greedy.ptrace` | 228 |
| m10_medium_p22810_5_5d_multi_tower | thermal_min_risk | `results/hotspot/m12/m10_medium_p22810_5_5d_multi_tower.flp` | `results/hotspot/m12/m10_medium_p22810_5_5d_multi_tower__thermal_min_risk.ptrace` | 245 |
| m10_medium_p22810_5_5d_multi_tower | m4_greedy | `results/hotspot/m12/m10_medium_p22810_5_5d_multi_tower.flp` | `results/hotspot/m12/m10_medium_p22810_5_5d_multi_tower__m4_greedy.ptrace` | 216 |

## Interpretation Notes

- `stress_proxy` is an intentionally amplified sensitivity profile, not measured silicon data.
- `.flp` and `.ptrace` files are generated HotSpot inputs only.
- Physical thermal claims require running HotSpot or another validated thermal simulator in M13/M12 follow-up.
