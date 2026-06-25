# M14 Experiment Chapter Draft

## 1. Experimental Setup

The evaluation uses the computable IEEE 1838 model and generated Test Access Recipes from the previous stages.
The M10 benchmark suite contains 12 cases, 4 ITC'02-derived workloads (d695, p22810, p34392, p93791), 4 scale levels (small, medium, large, xlarge), and 3 package topologies (2_5d_interposer, 3d_stack, 5_5d_multi_tower).
The M10 sweep produced 216 schedule rows, of which 216 were successful.

The algorithm comparison in M11 evaluates baseline and proposed schedulers on representative small and medium cases.
It contains 6 cases, 8 methods, and 45 successful rows out of 48.

Thermal validation is split into two levels: a fast thermal proxy for broad sweeps and an offline HotSpot check for a representative subset.
M12b contains 6 successful HotSpot executions across 3 representative cases.

## 2. Benchmark Scale and Topology Coverage

M10 is used to show that the recipe generation and greedy scheduler scale across package organizations rather than only one hand-written stack.
For the nominal 8-lane setting, M4 greedy averages 35.67x speedup over pure serial with mean normalized makespan 0.1026.

| topology | M4 rows | avg normalized makespan | avg speedup |
| --- | ---: | ---: | ---: |
| 2_5d_interposer | 36 | 0.1009 | 37.01 |
| 3d_stack | 36 | 0.1050 | 31.30 |
| 5_5d_multi_tower | 36 | 0.1033 | 35.92 |

The best M4 row in each scale level is:

| scale | case | lanes | power profile | normalized makespan | speedup |
| --- | --- | ---: | --- | ---: | ---: |
| small | m10_small_d695_2_5d_interposer | 2 | tight | 0.3361 | 2.97 |
| medium | m10_medium_p22810_2_5d_interposer | 8 | tight | 0.0228 | 43.94 |
| large | m10_large_p34392_5_5d_multi_tower | 16 | tight | 0.0145 | 69.16 |
| xlarge | m10_xlarge_p93791_5_5d_multi_tower | 16 | tight | 0.0273 | 36.62 |

## 3. Algorithm Comparison

M11 separates path-selection effects from scheduler effects by comparing serial, fixed-path, TAM-like, power-aware, M4, M5, and M6 variants.
The CP-SAT rows are feasible schedules under the modeled constraints; they should not be described as globally optimal unless the solver status proves optimality.

| method | family | successful rows | avg normalized makespan | avg speedup |
| --- | --- | ---: | ---: | ---: |
| pure_serial | baseline | 6 | 1.0000 | 1.00 |
| fixed_fastest | baseline | 6 | 0.1819 | 22.80 |
| tam_like | baseline | 6 | 0.1819 | 22.80 |
| low_power | baseline | 6 | 0.1929 | 20.47 |
| m4_all_recipes | ablation | 6 | 0.1819 | 22.80 |
| m4_greedy | proposed | 6 | 0.1819 | 22.80 |
| m5_cpsat | proposed | 6 | 0.1814 | 22.86 |
| m6_alns | proposed | 3 | 0.3394 | 2.95 |

M11 skipped or bounded rows are reported explicitly:

| case | method | status | reason |
| --- | --- | --- | --- |
| m10_medium_p22810_3d_stack | m6_alns | skipped | target_count=22 exceeds max_alns_targets=16 |
| m10_medium_p22810_2_5d_interposer | m6_alns | skipped | target_count=22 exceeds max_alns_targets=16 |
| m10_medium_p22810_5_5d_multi_tower | m6_alns | skipped | target_count=22 exceeds max_alns_targets=16 |

## 4. Thermal Proxy and HotSpot Validation

The thermal proxy is used during scheduling and broad evaluation because it is fast enough to apply across many cases.
HotSpot is used only as representative offline validation, not as an inner-loop solver.
The M12b HotSpot peak range is 60.61 C to 63.69 C.
The proxy-best and HotSpot-best schedule rankings agree in 3 out of 3 representative cases.

| case | proxy-best schedule | HotSpot-best schedule | ranking match |
| --- | --- | --- | --- |
| m10_medium_p22810_3d_stack | m4_greedy | m4_greedy | True |
| m10_medium_p22810_5_5d_multi_tower | m4_greedy | m4_greedy | True |
| m10_small_d695_5_5d_multi_tower | m4_greedy | m4_greedy | True |

This result supports using the proxy for trend guidance, but it does not make the proxy a replacement for detailed thermal simulation.
The current HotSpot export is block-level and simplified, so the wording should remain representative validation rather than signoff-grade thermal analysis.

## 5. Figure and Table Usage

| figure id | recommended role in paper |
| --- | --- |
| m13_m10_speedup_nominal_lane8 | Uses m4_greedy rows at power_profile=nominal and lane_count=8. |
| m13_m11_algorithm_makespan | Averages successful rows across M11 representative cases; lower is better. |
| m13_m12b_proxy_hotspot_peak_comparison | Two-panel plot avoids implying direct numeric equivalence between proxy and HotSpot temperatures. |
| m13_hotspot_trace_heatmap_medium_3d_m4_greedy | Uses the representative medium 3D m4_greedy HotSpot .ttrace output. |
| m13_representative_m4_greedy_gantt | Plots scan/capture phases from the existing representative schedule CSV. |

Recommended table usage:

- M10 benchmark coverage and sensitivity: `results/tables/m10_benchmark_sweep.csv`.
- M11 algorithm comparison: `results/tables/m11_algorithm_comparison.csv`.
- M12b HotSpot validation summary: `results/tables/m12_hotspot_validation_summary.csv`.
- M13 figure index: `results/tables/m13_figure_index.csv`.

## 6. Limitations

- The benchmark cases are derived from public ITC'02-style workload information and synthetic package mappings.
- M10 emphasizes scalable benchmark coverage; only selected methods are used in the broad sweep.
- M11 gives a richer algorithm comparison, but currently focuses on small and medium representative cases.
- M12b validates representative schedules offline with HotSpot; it is not a full-chip industrial thermal signoff flow.
- CP-SAT feasible results should be described as feasible refined schedules unless optimal status is explicitly available.

## 7. Draft Conclusion

The experimental results indicate that IEEE 1838-aware recipe generation and resource-constrained scheduling can substantially reduce test time compared with pure serial access while keeping the access-path constraints explicit.
Across the M10 benchmark suite, the method scales across 2.5D interposer, 3D stack, and 5.5D multi-tower organizations.
M11 shows that the proposed M4/M5 scheduling flow is competitive with fixed-path and TAM-like baselines under the modeled constraints.
M12b further shows that the thermal proxy preserves the representative method ranking under offline HotSpot validation, although the thermal conclusion should be stated as trend validation rather than signoff.
