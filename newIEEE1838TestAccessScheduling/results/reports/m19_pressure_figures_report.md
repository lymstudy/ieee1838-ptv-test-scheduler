# M19 Pressure Figures Report

M19 turns the M18 controlled pressure ablation into paper-facing figures.

- Representative case: `m18_shared_bist_8die_3d_stack`
- Fixed-fastest makespan: 0.048015040 s
- M5 CP-SAT joint makespan: 0.025604520 s
- Joint gain vs fixed-fastest: 46.67%
- M18 table source: `results/tables/m18_pressure_study.csv`

## Figures

| figure | path | purpose |
| --- | --- | --- |
| `m19_pressure_gantt_fixed_vs_joint` | `results/figures/m19/m19_pressure_gantt_fixed_vs_joint.png` | Shows shared BIST serialization in fixed-fastest and BIST/FPP overlap in joint scheduling. |
| `m19_resource_occupancy_fixed_vs_joint` | `results/figures/m19/m19_resource_occupancy_fixed_vs_joint.png` | Explains that fixed-fastest underuses FPP lanes while serializing on BIST; joint scheduling overlaps both resources. |
| `m19_pressure_summary_gain_and_mix` | `results/figures/m19/m19_pressure_summary_gain_and_mix.png` | Summarizes the 46% gain and shows that joint schedules deliberately mix BIST and FPP recipes. |

## Paper Use

Use these figures to support a controlled claim: under shared-resource pressure, path selection must be coupled with scheduling.
Do not use them to claim universal dominance on every benchmark; M17 keeps that limitation explicit.
