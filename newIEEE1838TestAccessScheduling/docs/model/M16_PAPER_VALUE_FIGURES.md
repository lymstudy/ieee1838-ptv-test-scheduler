# M16: Paper Value Figures

## Goal

M16 upgrades the visualization set from simple result plots to paper-oriented
figures that communicate the project value:

- large-case IEEE 1838 resource scheduling behavior;
- power, temperature, and HotSpot hotspot trends;
- multi-metric method tradeoffs;
- formal benchmark scale and topology coverage.

## Inputs

```text
configs/cases/m10/m10_xlarge_p93791_5_5d_multi_tower.json
results/tables/m10_benchmark_sweep.csv
results/tables/m11_algorithm_comparison.csv
results/tables/m12_thermal_validation_summary.csv
results/tables/m12_temperature_trace.csv
results/tables/m12_hotspot_validation_summary.csv
```

## Outputs

```text
results/schedules/m16_xlarge_5_5d_m4_greedy_schedule.csv
results/figures/m16/
results/tables/m16_figure_index.csv
results/reports/m16_paper_value_figures_report.md
```

## Command

```powershell
python experiments/generate_m16_paper_value_figures.py
```

## Figure Roles

- `m16_ieee1838_resource_gantt_xlarge.png`: replaces the small M13 Gantt as the
  main scheduling figure. It is generated from the xlarge p93791 5.5D case.
- `m16_power_temperature_hotspot_composite.png`: corresponds to a paper-style
  power/temperature/hotspot figure.
- `m16_method_comparison_normalized.png`: summarizes method tradeoffs rather
  than claiming every metric improves.
- `m16_benchmark_coverage_matrix.png`: directly shows the formal 4/6/8/12-die
  benchmark coverage.

## Interpretation Rules

- M16 figures are intended as main paper figures.
- The older M13 representative Gantt should be used only as an appendix or
  explanatory figure.
- The HotSpot maps are block-level representative validation, not industrial
  signoff thermal analysis.
- The multi-metric comparison should be described as a tradeoff view: the main
  gain is test-time reduction under IEEE 1838-aware resource constraints.

## Current Status

M16 is complete. The generated figure set contains four paper-oriented figures
and one xlarge 5.5D schedule CSV. The latest full regression check passed with
61 tests.
