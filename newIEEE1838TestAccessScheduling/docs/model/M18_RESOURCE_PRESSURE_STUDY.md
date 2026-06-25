# M18 Resource-Pressure Study

M18 的目标是补强 M17 暴露出的核心缺口：普通 M10 sweep 中，固定最快路径和联合调度结果太接近，不能证明“路径-调度联合优化”的必要性。

这一阶段不再扩大普通 case 数量，而是构造受控压力场景，让固定路径策略暴露结构性问题。

## Core Idea

M18 case 中每个 target 都有两类候选 recipe：

- `B`: local BIST，单个 target 看起来最快。
- `F/H`: FPP 访问，单个 target 略慢，但可以利用 package lanes 并行。

所有 `B` recipe 共享一个 `shared_m18_bist_engine`，容量为 1。因此 fixed-fastest 会为每个 target 选择 BIST，随后被共享 BIST engine 串行化；联合调度可以混合 BIST 和 FPP，在 BIST engine 忙碌时使用空闲 FPP lane。

这正好对应论文里要表达的“访问路径选择不能脱离调度资源约束单独决定”。

## Generated Cases

生成入口：

```powershell
python experiments/generate_m18_pressure_cases.py
```

输出：

- `configs/cases/m18/m18_shared_bist_8die_3d_stack.json`
- `configs/cases/m18/m18_shared_bist_12die_5_5d_multi_tower.json`
- `data/derived/m18_pressure_case_manifest.csv`

这两个 case 分别覆盖 8-die 3D stack 和 12-die 5.5D multi-tower。它们是受控消融 benchmark，不是公开工业芯片实测。

## Experiment

运行入口：

```powershell
python experiments/run_m18_pressure_study.py
```

对比方法：

- `pure_serial`: 纯串行基线。
- `fixed_fastest`: 每个 target 固定选择单 target 最快 recipe。
- `tam_like`: 偏 FPP 的固定路径基线。
- `m4_greedy`: 联合 recipe 选择与贪心调度。
- `m5_cpsat`: CP-SAT 联合选择与调度。

输出：

- `results/tables/m18_pressure_study.csv`
- `results/reports/m18_pressure_study_report.md`

## Current Result

当前 M18 结果显示：

- 8-die 3D stack: best joint gain about `46.67%` vs fixed-fastest.
- 12-die 5.5D multi-tower: best joint gain about `46.65%` vs fixed-fastest.
- 最优/近优 recipe mix 为一半 BIST、一半 FPP，例如 `B:4;F:4` 或 `B:6;F:6`。

## Paper Wording

可以写：

> 在共享 BIST engine 与 FPP lane 并存的资源压力场景中，单独选择每个 target 的最快访问路径会导致全局共享资源串行化；所提出的 recipe-level 联合选择与调度能够混合 BIST/FPP 路径，使空闲 FPP lane 与 BIST 执行并行，从而显著缩短测试时间。

不要写：

> 本方法在所有 benchmark 上都显著优于固定路径。

M10/M17 已经显示普通 sweep 中 fixed-fastest 与 joint 的差距并不稳定。M18 支撑的是“联合优化在资源压力场景下有必要”，不是“全场景压倒性优势”。
