# M4：基础调度器 MVP

## 目标

M4 实现一个确定性的贪心调度器，用于从 M3 的 Pareto recipe 集合中为每个 target 选择一个 recipe，并输出合法 phase-level schedule。

本阶段目标是先得到可检查、可复现的合法调度结果，不追求全局最优。

## 输入

默认读取：

```text
results/tables/m3_recipe_pareto.csv
```

M4 只消费 M3 输出字段，尤其是：

| 字段 | 用途 |
| --- | --- |
| `recipe_id` / `target_id` | recipe 选择与分组 |
| `phase_resources` | phase-level duration、资源和功耗 |
| `serial_time_s` / `fpp_time_s` | 候选排序 |
| `peak_power_w` / `thermal_risk` | 候选排序与报告 |

## 约束

当前 MVP 检查以下约束：

| 约束 | 当前实现 |
| --- | --- |
| phase precedence | 同一 recipe 的 phase 顺序执行 |
| recipe uniqueness | 每个 target 只选择一个 recipe |
| serial access mutex | `serial_required=true` 的 phase 受 `ptap_ports` 容量限制 |
| FPP lane capacity | 同时使用的 FPP lane 不超过 `total_fpp_lanes` 和 channel `max_lanes` |
| power limit | 同时活动 phase 的 `power_w` 不超过 `max_total_power_w` |
| BIST local execution | `LOCAL_BIST_RUN` 不占用外部 serial/FPP 资源，可与其他 phase 并行 |
| DWR conflict group | 同一 DWR conflict group 不超过其 capacity |
| capture concurrency | capture phase 不超过 `max_concurrent_capture` |

## 贪心策略

调度流程：

1. 按 target 的最大 `thermal_risk` 从高到低排序，高热风险对象优先安排。
2. 对每个 target，枚举其 Pareto recipe。
3. 对每个 recipe，按 phase 顺序寻找最早可行开始时间。
4. 选择完成时间最早的 recipe；若完成时间相同，再按功耗、lane 占用和 recipe 类型稳定排序。

该策略是 baseline/MVP，用来验证建模闭环和约束检查。后续 M5 的 CP-SAT 可以替换这一层搜索。

## 输出

默认运行：

```powershell
python experiments/run_m4_greedy_scheduler.py
```

默认输出：

```text
results/schedules/m4_greedy_schedule.csv
results/reports/m4_greedy_schedule_report.md
```

`m4_greedy_schedule.csv` 是 phase-level 调度表，包含 start/end、recipe、target、资源占用和功耗。

`m4_greedy_schedule_report.md` 汇总 makespan、峰值功耗、FPP lane 峰值，并给出文本版 Gantt preview。
