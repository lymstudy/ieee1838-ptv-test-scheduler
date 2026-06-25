# M17 Innovation Support Audit

M17 用来回答一个比画图更关键的问题：当前实验到底能不能支撑论文里准备写的创新点。

这一阶段不新增主调度闭环，也不把弱结果包装成强结果。它把 M10-M12b/M11 的结果重新汇总成“创新点-证据-建议表述-剩余缺口”矩阵，明确哪些结论可以写进论文，哪些只能作为原型能力或后续工作。

## Inputs

- `configs/cases/m10/`: M10 benchmark case 集合。
- `results/tables/m10_benchmark_sweep.csv`: benchmark 规模、拓扑和调度结果。
- `results/tables/m11_algorithm_comparison.csv`: fixed-path、M4、M5、M6 算法对比结果。
- `results/tables/m12_hotspot_validation_summary.csv`: M12b HotSpot 离线验证结果。
- `results/tables/m18_pressure_study.csv`: M18 资源压力消融结果；若文件存在，会用于更新路径-调度联合优化的支撑判断。

## Runner

```powershell
python experiments/run_m17_innovation_support.py
```

默认设置：

- lane count: `8`
- power profile: `nominal`
- CP-SAT: 只在 target 数不超过 `22` 的 case 上运行，避免中大规模 case 被精确求解器拖慢。

## Outputs

- `results/tables/m17_path_schedule_ablation.csv`
  - 对所有 M10 case 固定 lane/power 后重跑路径-调度消融。
  - 方法包括 `pure_serial`、`fixed_fastest`、`fixed_low_power`、`fixed_thermal_min`、`tam_like`、`joint_m4_greedy`，以及小规模 case 的 `m5_cpsat`。
- `results/tables/m17_innovation_support_matrix.csv`
  - 汇总每个创新点的支撑等级、证据、建议写法和缺口。
- `results/reports/m17_innovation_support_report.md`
  - 面向论文写作的审计报告。

## Current Interpretation

当前结果应按以下口径使用：

- Test Access Recipe 建模：可以作为主要贡献之一。
- 2.5D/3D/5.5D 统一 benchmark 框架：可以作为实验平台和建模覆盖贡献。
- 热感知验证：只能说有 thermal proxy 与代表性 HotSpot 离线验证，不能说已经完成电热闭环优化。
- CP-SAT+ALNS：CP-SAT 可作为小规模精修求解器；ALNS 当前仍偏原型，不建议作为核心创新点强写。
- 路径-调度联合优化：普通 M10 sweep 中优势不稳定；M18 共享 BIST engine/FPP lane 压力消融已能支撑“资源压力场景下联合优化有必要”这一限定表述。

## Why This Matters

如果论文创新点过强，但实验只能支撑一部分，最终答辩和审稿时会很被动。M17 的目标是让后续工作有明确方向：

1. 保留已经站得住的建模贡献。
2. 降级目前证据不足的算法表述。
3. 把下一轮实验集中在能真正拉开差距的 case 和算法上。
