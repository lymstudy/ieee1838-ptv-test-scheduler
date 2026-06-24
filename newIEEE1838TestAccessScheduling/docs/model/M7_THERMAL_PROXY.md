# M7：热代理模型

## 目标

M7 为已有 schedule 增加快速热评估，输出温度曲线、热点位置表和调度方案热指标对比。

本阶段不调用 HotSpot，也不声称得到物理精确温度。当前模型是 first-order RC proxy，用于比较调度方案的相对热趋势，并为后续 thermal cut / HotSpot feedback 预留接口。

## 输入

默认评估：

```text
results/schedules/m4_greedy_schedule.csv
results/schedules/m5_refined_schedule.csv
results/schedules/m6_alns_schedule.csv
```

也可以手动指定 schedule：

```powershell
python experiments/run_m7_thermal_evaluation.py --schedule custom results/schedules/m6_alns_schedule.csv
```

## 热代理模型

每个 thermal region 使用 die 上的热参数：

| 参数 | 来源 |
| --- | --- |
| `thermal_resistance_c_per_w` | `dies[].thermal` |
| `thermal_capacitance_j_per_c` | `dies[].thermal` |
| `max_temperature_c` | `resource_groups.thermal_regions` |
| `ambient_temperature_c` | `package` |

每个时间片内，region 的有效功耗为：

```text
P_eff(region) = self_heating_weight * P_self
              + sum(coupling_weight * type_weight * P_neighbor)
```

其中 vertical coupling 使用 `vertical_coupling_weight`，horizontal coupling 使用 `horizontal_coupling_weight`，若输入未提供 horizontal 权重则使用默认值。

温度更新使用一阶 RC 近似：

```text
T_next = T_ss + (T_prev - T_ss) * exp(-dt / (Rth * Cth))
T_ss   = T_ambient + P_eff * Rth
```

## 输出

运行：

```powershell
python experiments/run_m7_thermal_evaluation.py
```

默认输出：

```text
results/tables/m7_temperature_trace.csv
results/tables/m7_hotspots.csv
results/tables/m7_thermal_summary.csv
results/reports/m7_thermal_report.md
```

`m7_temperature_trace.csv` 是每个 schedule、每个 region 的温度采样曲线。

`m7_hotspots.csv` 是每个 schedule、每个 region 的峰值温度、峰值时间和超限统计。

`m7_thermal_summary.csv` 是每个 schedule 的总体热指标。
