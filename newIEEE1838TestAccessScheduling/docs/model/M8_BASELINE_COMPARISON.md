# M8：Baseline 对比实验

## 目标

M8 把前面 M1-M7 的建模、recipe、剪枝、调度和热代理评估串成可复现实验表。当前阶段先在默认 4-die 3D stack case 上跑通对比流程，后续 M9 再扩展到 2.5D 和 multi-tower 场景。

## Baseline

当前实现的对比方法：

| method_id | 含义 |
| --- | --- |
| `pure_serial` | 只允许 S/I recipe，模拟纯串行 IEEE 1838 访问 |
| `fixed_fastest` | 每个 target 先固定最快 Pareto recipe，再用 M4 规则调度 |
| `tam_like` | 优先选择 FPP recipe，模拟简化 TAM/FPP packing，不显式联合优化 recipe |
| `low_power` | 每个 target 先固定最低峰值功耗 recipe，再调度 |
| `m4_greedy` | M4 贪心 recipe 选择与调度 |
| `m5_cpsat` | M5 OR-Tools CP-SAT 全局调度 |
| `m6_alns` | M6 CP-SAT-ALNS 外层搜索 |

`fixed_fastest` 用来模拟“先固定路径，再调度”的传统流程。它不在调度过程中联合选择 recipe。

`tam_like` 只作为普通 TAM 装箱思想的近似 baseline：它优先选择 FPP 数据通路，但不建模 IEEE 1838 配置层次之外的复杂 TAM 架构。

## 指标

输出指标：

| 指标 | 含义 |
| --- | --- |
| `makespan_s` | 总测试完成时间 |
| `normalized_makespan` | 相对 `pure_serial` 的归一化测试时间 |
| `peak_power_w` | 调度时序中的峰值功耗 |
| `peak_temperature_c` | M7 热代理峰值温度 |
| `fpp_utilization` | FPP lane-time / makespan / total lanes |
| `serial_busy_ratio` | 串行资源忙时 / makespan |
| `selected_recipe_types` | 选中 recipe 类型计数 |

## 输出

运行：

```powershell
python experiments/run_m8_baseline_comparison.py
```

默认输出：

```text
results/tables/m8_baseline_comparison.csv
results/tables/m8_temperature_trace.csv
results/tables/m8_hotspots.csv
results/tables/m8_thermal_summary.csv
results/reports/m8_baseline_comparison_report.md
results/schedules/m8_*_schedule.csv
```

当前热指标仍来自 M7 first-order RC proxy，不是 HotSpot 结果。
