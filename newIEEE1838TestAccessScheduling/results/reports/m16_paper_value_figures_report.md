# M16 Paper Value Figures Report

M16 replaces the weak small-case Gantt view with paper-oriented figures that emphasize the project value.

- Representative schedule case: `m10_xlarge_p93791_5_5d_multi_tower`
- Selected recipes: 36
- Scheduled phases: 202
- Makespan: 0.004779760 s
- Peak scheduled power: 2.3853 W

## Figures

| figure | path | role |
| --- | --- | --- |
| `m16_ieee1838_resource_gantt_xlarge` | `results/figures/m16/m16_ieee1838_resource_gantt_xlarge.png` | Formal xlarge p93791 5.5D schedule, showing PTAP/STAP, FPP lanes, DWR/scan, local/BIST, and representative target activity. |
| `m16_power_temperature_hotspot_composite` | `results/figures/m16/m16_power_temperature_hotspot_composite.png` | Composite view for medium p22810 3D stack, using proxy traces for curves and HotSpot block peaks for hotspot maps. |
| `m16_method_comparison_normalized` | `results/figures/m16/m16_method_comparison_normalized.png` | Multi-metric tradeoff view using M11 successful rows. It shows time reduction, thermal/power side effects, and FPP utilization rather than claiming every metric improves. |
| `m16_benchmark_coverage_matrix` | `results/figures/m16/m16_benchmark_coverage_matrix.png` | Shows that the formal benchmark spans 4/6/8/12 dies, three package topologies, target counts, recipe counts, and average M4 speedup. |

## Notes

- The Gantt chart is generated from a formal xlarge M10 case, not the early 4-die M1 example.
- The power and temperature curves use M12 proxy traces, while hotspot maps use M12b HotSpot outputs.
- M16 figures are intended as main paper figures; the M13 representative Gantt should be treated as an explanatory appendix figure.
