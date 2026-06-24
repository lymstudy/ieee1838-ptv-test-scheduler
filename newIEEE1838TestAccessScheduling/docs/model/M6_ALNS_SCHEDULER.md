# M6：ALNS 外层搜索

## 目标

M6 在 M5 CP-SAT 调度器外增加 Adaptive Large Neighborhood Search 外层。它的作用不是替代 CP-SAT，而是在规模增大时通过 destroy/repair 控制局部子问题规模。

当前 4-die 样例中，M5 CP-SAT 已能在短时间内证明最优；因此 M6 的默认结果会稳定复现同一最优 makespan，并输出 ALNS 收敛过程。后续中等规模 case 才能体现 ALNS 相比全局 CP-SAT 的运行时间优势。

## 输入

默认读取：

```text
results/tables/m3_recipe_pareto.csv
```

## 算法

M6 先用 repair backend 构造初始解，然后循环执行：

1. 选择 destroy operator。
2. 释放部分 target 的 recipe 选择。
3. 保持未释放 target 的当前 recipe 固定。
4. 对局部 neighborhood 调用 repair backend。
5. 若 candidate 不差于 incumbent，则接受；若优于 best，则更新 best。

当前 destroy operator：

| 算子 | 含义 |
| --- | --- |
| `critical_path` | 破坏接近 makespan 的尾部关键 target |
| `resource_congestion` | 破坏峰值功耗/FPP lane 拥塞窗口中的 target |
| `thermal_hotspot` | 破坏热风险最高的 target |
| `random` | 使用固定 seed 随机破坏 target |

当前 repair backend：

| backend | 含义 |
| --- | --- |
| `ortools` | 对局部 neighborhood 调用 OR-Tools CP-SAT |
| `greedy` | 使用 M4 贪心调度作为无依赖 fallback |

## 输出

运行：

```powershell
python experiments/run_m6_alns_scheduler.py
```

默认输出：

```text
results/schedules/m6_alns_schedule.csv
results/tables/m6_alns_convergence.csv
results/reports/m6_alns_report.md
```

`m6_alns_convergence.csv` 记录每轮 destroy operator、candidate makespan、incumbent makespan、best makespan 和是否接受/改善。
