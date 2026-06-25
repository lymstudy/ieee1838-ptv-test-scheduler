# M12 Thermal Validation Report

This report uses the M7 first-order RC proxy and exports HotSpot-compatible inputs. It is not a HotSpot execution report.

- Summary rows: 30
- HotSpot export rows: 6

## Peak Temperature By Profile

| profile | method | rows | avg_peak_temp_c | max_peak_temp_c | avg_rise_c |
| --- | --- | ---: | ---: | ---: | ---: |
| nominal_proxy | fixed_fastest | 3 | 25.001482 | 25.001621 | 0.001482 |
| nominal_proxy | low_power | 3 | 25.006741 | 25.008395 | 0.006741 |
| nominal_proxy | thermal_min_risk | 3 | 25.006741 | 25.008395 | 0.006741 |
| nominal_proxy | m4_greedy | 3 | 25.001482 | 25.001621 | 0.001482 |
| nominal_proxy | m5_cpsat | 3 | 25.001848 | 25.002593 | 0.001848 |
| stress_proxy | fixed_fastest | 3 | 25.109100 | 25.117535 | 0.109100 |
| stress_proxy | low_power | 3 | 25.430873 | 25.566668 | 0.430873 |
| stress_proxy | thermal_min_risk | 3 | 25.430873 | 25.566668 | 0.430873 |
| stress_proxy | m4_greedy | 3 | 25.109100 | 25.117535 | 0.109100 |
| stress_proxy | m5_cpsat | 3 | 25.128671 | 25.167561 | 0.128671 |

## Best Stress-Profile Method Per Case

| case | topology | best method | peak_temp_c | rise_c | makespan_s |
| --- | --- | --- | ---: | ---: | ---: |
| m10_medium_p22810_3d_stack | 3d_stack | fixed_fastest | 25.117535 | 0.117535 | 0.002277820 |
| m10_medium_p22810_5_5d_multi_tower | 5_5d_multi_tower | fixed_fastest | 25.117490 | 0.117490 | 0.002157836 |
| m10_small_d695_5_5d_multi_tower | 5_5d_multi_tower | fixed_fastest | 25.092276 | 0.092276 | 0.001259840 |

## HotSpot Input Export

| case | schedule | floorplan | ptrace | samples |
| --- | --- | --- | --- | ---: |
| m10_small_d695_5_5d_multi_tower | thermal_min_risk | `results/hotspot/m12/m10_small_d695_5_5d_multi_tower.flp` | `results/hotspot/m12/m10_small_d695_5_5d_multi_tower__thermal_min_risk.ptrace` | 134 |
| m10_small_d695_5_5d_multi_tower | m4_greedy | `results/hotspot/m12/m10_small_d695_5_5d_multi_tower.flp` | `results/hotspot/m12/m10_small_d695_5_5d_multi_tower__m4_greedy.ptrace` | 126 |
| m10_medium_p22810_3d_stack | thermal_min_risk | `results/hotspot/m12/m10_medium_p22810_3d_stack.flp` | `results/hotspot/m12/m10_medium_p22810_3d_stack__thermal_min_risk.ptrace` | 246 |
| m10_medium_p22810_3d_stack | m4_greedy | `results/hotspot/m12/m10_medium_p22810_3d_stack.flp` | `results/hotspot/m12/m10_medium_p22810_3d_stack__m4_greedy.ptrace` | 228 |
| m10_medium_p22810_5_5d_multi_tower | thermal_min_risk | `results/hotspot/m12/m10_medium_p22810_5_5d_multi_tower.flp` | `results/hotspot/m12/m10_medium_p22810_5_5d_multi_tower__thermal_min_risk.ptrace` | 244 |
| m10_medium_p22810_5_5d_multi_tower | m4_greedy | `results/hotspot/m12/m10_medium_p22810_5_5d_multi_tower.flp` | `results/hotspot/m12/m10_medium_p22810_5_5d_multi_tower__m4_greedy.ptrace` | 216 |

## Interpretation Notes

- `stress_proxy` is an intentionally amplified sensitivity profile, not measured silicon data.
- `.flp` and `.ptrace` files are generated HotSpot inputs only.
- Physical thermal claims require running HotSpot or another validated thermal simulator in M13/M12 follow-up.
