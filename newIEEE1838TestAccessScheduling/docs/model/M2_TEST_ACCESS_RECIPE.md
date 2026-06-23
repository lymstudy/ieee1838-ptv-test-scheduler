# M2：Test Access Recipe 生成

## 目标

M2 将 M1 的 IEEE 1838-compatible 系统模型转换为候选 Test Access Recipe。Recipe 是后续调度器选择和排序的基本单元。

本阶段实现内容：

- 读取并校验 M1 JSON 输入。
- 为可测试 core、memory、instrument 生成 S/F/B/H recipe。
- 为 die-to-die interconnect 生成 I recipe。
- 估算每个 recipe 的访问时间、数据传输时间、本地执行时间、读回时间、峰值功耗、FPP lane 占用、DWR segment 占用和热风险。
- 输出候选 recipe CSV 表。

本阶段不做全局调度，不做帕累托剪枝，也不声称 bit-accurate IEEE 1838 仿真。

## Recipe 类型

| 类型 | 含义 | 主要资源语义 |
| --- | --- | --- |
| `S` | Serial recipe | PTAP/STAP/DWR 串行访问 |
| `F` | FPP recipe | 串行配置 + FPP bulk data transfer |
| `B` | BIST recipe | 串行配置/读回 + 本地 BIST 执行 |
| `H` | Hybrid recipe | 串行配置 + FPP 数据传输 + 短串行状态读回 |
| `I` | Interconnect recipe | DWR EXTEST 风格互连测试 |

## 代码入口

核心文件：

```text
src/model/system_model.py
src/recipes/generator.py
experiments/generate_m2_recipes.py
tests/test_m2_recipe_generator.py
```

生成默认 M2 recipe 表：

```powershell
python experiments/generate_m2_recipes.py
```

默认输出：

```text
results/tables/m2_recipe_summary.csv
```

## 输出字段

| 字段 | 含义 |
| --- | --- |
| `recipe_id` | recipe 唯一 ID |
| `target_id` | core、memory、instrument 或 interconnect ID |
| `target_kind` | 目标类型 |
| `die_id` | 主要访问 die |
| `recipe_type` | `S/F/B/H/I` |
| `variant` | lane 数或访问变体 |
| `phases` | 阶段序列，使用 `|` 分隔 |
| `total_time_s` | 估算总时间 |
| `access_time_s` | PTAP/STAP/3DCR/DWR/FPP 配置时间 |
| `data_time_s` | scan/DWR/FPP 数据传输时间 |
| `local_execution_time_s` | BIST 本地执行时间 |
| `readback_time_s` | 结果或状态读回时间 |
| `peak_power_w` | 估算峰值功耗 |
| `thermal_risk` | 热风险代理指标 |
| `serial_access_required` | 是否需要串行访问阶段 |
| `fpp_lanes_required` | 占用 FPP lane 数 |
| `fpp_channel` | 使用的 FPP channel |
| `dwr_segments` | 引用的 DWR segment |
| `route_resource` | 互连测试相关 routing 资源 |
| `estimated_bits` | 估算处理 bit 数 |
| `notes` | 建模说明 |

## 估算公式

串行访问时间：

```text
serial_time = bits / ptap_tck_hz
```

FPP 数据传输时间：

```text
fpp_time = data_bits / (lanes * lane_bandwidth_bps)
```

BIST 时间：

```text
bist_time =
  serial(config_path_bits + bist_config_bits)
+ local_cycles / bist_clock_hz
+ serial(config_path_bits + readout_bits)
```

热风险代理：

```text
thermal_risk =
  peak_power_w * (peak_power_w / area_mm2) * adjacency_factor / cooling_factor
```

该热风险只用于候选 recipe 排序、剪枝和后续调度启发，不等同于 HotSpot 或真实热仿真结果。

## M2 到 M3 的接口

M3 帕累托剪枝应直接读取 `m2_recipe_summary.csv` 或调用 `RecipeGenerator.generate_all()`，按以下维度筛掉被支配 recipe：

- `total_time_s`
- `peak_power_w`
- `fpp_lanes_required`
- `thermal_risk`
- 串行访问占用
- DWR / route 资源占用
