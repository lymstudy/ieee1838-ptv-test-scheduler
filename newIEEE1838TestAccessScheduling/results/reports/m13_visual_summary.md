# M13 Visualization Summary

M13 converts existing M10/M11/M12b outputs into a small fixed set of publication-oriented figures.
It does not rerun scheduling or HotSpot.

## Figure Index

| figure | path | purpose |
| --- | --- | --- |
| `m13_m10_speedup_nominal_lane8` | `results/figures/m13/m13_m10_speedup_nominal_lane8.png` | Uses m4_greedy rows at power_profile=nominal and lane_count=8. |
| `m13_m11_algorithm_makespan` | `results/figures/m13/m13_m11_algorithm_makespan.png` | Averages successful rows across M11 representative cases; lower is better. |
| `m13_m12b_proxy_hotspot_peak_comparison` | `results/figures/m13/m13_m12b_proxy_hotspot_peak_comparison.png` | Two-panel plot avoids implying direct numeric equivalence between proxy and HotSpot temperatures. |
| `m13_hotspot_trace_heatmap_medium_3d_m4_greedy` | `results/figures/m13/m13_hotspot_trace_heatmap_medium_3d_m4_greedy.png` | Uses the representative medium 3D m4_greedy HotSpot .ttrace output. |
| `m13_representative_m4_greedy_gantt` | `results/figures/m13/m13_representative_m4_greedy_gantt.png` | Plots scan/capture phases from the existing representative schedule CSV. |

## Interpretation Notes

- M10 and M11 figures support algorithm and scale comparison.
- M12b figures support representative offline HotSpot validation.
- Proxy and HotSpot values should be discussed as trend validation, not as numerically identical models.
- The HotSpot heatmap is block-level and simplified; it is not industrial thermal signoff.
