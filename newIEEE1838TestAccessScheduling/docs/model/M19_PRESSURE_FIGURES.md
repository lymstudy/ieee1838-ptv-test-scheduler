# M19 Pressure Figures

M19 把 M18 的资源压力消融转成论文图。它不重新定义算法，也不扩大 benchmark；目标是把“为什么 joint recipe selection 有价值”画清楚。

## Inputs

- `configs/cases/m18/m18_shared_bist_8die_3d_stack.json`
- `results/tables/m18_pressure_study.csv`

M19 会重新生成 representative schedule，避免图和表脱节。

## Runner

```powershell
python experiments/generate_m19_pressure_figures.py
```

## Outputs

- `results/schedules/m19/m18_shared_bist_8die_3d_stack__fixed_fastest_schedule.csv`
- `results/schedules/m19/m18_shared_bist_8die_3d_stack__m5_cpsat_schedule.csv`
- `results/figures/m19/m19_pressure_gantt_fixed_vs_joint.png`
- `results/figures/m19/m19_resource_occupancy_fixed_vs_joint.png`
- `results/figures/m19/m19_pressure_summary_gain_and_mix.png`
- `results/tables/m19_figure_index.csv`
- `results/reports/m19_pressure_figures_report.md`

## Figure Roles

`m19_pressure_gantt_fixed_vs_joint.png`

Shows the mechanism. Fixed-fastest serializes all targets on the shared BIST engine. Joint scheduling mixes BIST and FPP so that BIST execution and FPP transfer overlap.

`m19_resource_occupancy_fixed_vs_joint.png`

Shows resource utilization directly. Fixed-fastest leaves FPP lanes idle; joint scheduling uses FPP lanes while the BIST engine is busy.

`m19_pressure_summary_gain_and_mix.png`

Summarizes both M18 pressure cases. It reports normalized test time, joint gain, and recipe mix.

## Paper Wording

Safe wording:

> 在共享 BIST engine 与 FPP lane 并存的资源压力场景中，固定最快路径会导致共享 BIST engine 串行化；联合 recipe 选择与调度能够混合 BIST/FPP 路径，使 FPP lane 与 BIST 执行重叠，从而获得约 46% 的测试时间收益。

Avoid:

> 本方法在所有 benchmark 上都显著优于 fixed-fastest。

M19 supports a controlled-ablation claim. M17 still records that the ordinary M10 sweep does not show universal dominance.
