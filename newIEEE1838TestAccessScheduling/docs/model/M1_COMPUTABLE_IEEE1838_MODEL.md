# M1：IEEE 1838 结构可计算模型

## 目标

M1 的目标是把 IEEE 1838-compatible 测试结构从论文概念转成后续程序可读取、可检查、可扩展的输入模型。

本阶段不实现调度算法，也不声称实现 IEEE 1838 bit-accurate 行为仿真。M1 只定义用于路径生成、recipe 生成和调度优化的抽象数据结构。

验收标准：

- 能用一个 JSON 文件描述一个 3D stack 测试系统。
- 能表示 die、core、PTAP、STAP、3DCR、DWR segment、FPP lane、BIST、TSV/interposer route 和热邻接。
- 能让后续阶段计算访问路径、资源占用、测试时长、功耗和热风险。

当前样例文件：

```text
configs/cases/3d_stack_m1_example.json
```

## 顶层模型

顶层对象定义为 `SystemModel`：

```text
SystemModel = {
  model_version,
  case_id,
  units,
  package,
  timing,
  resource_limits,
  thermal_model,
  dies,
  ieee1838_access,
  test_objects,
  interconnects,
  resource_groups,
  thermal_adjacency
}
```

### 1. `package`

描述封装拓扑与全局边界条件。

关键字段：

| 字段 | 含义 |
| --- | --- |
| `topology_type` | `2.5d_interposer`、`3d_stack` 或 `5.5d_multi_tower` |
| `tower_count` | tower 数量，单 3D stack 为 1 |
| `die_count` | die 数量 |
| `primary_entry_die` | 外部 PTAP 所在 die |
| `thermal_boundary` | 例如 `top_heat_sink` |
| `ambient_temperature_c` | 环境温度 |

### 2. `dies`

每个 die 是访问路径、物理位置、功耗和热模型的基础对象。

关键字段：

| 字段 | 含义 |
| --- | --- |
| `die_id` | 全局唯一 ID |
| `role` | `primary` 或 `secondary` |
| `tower_id` | 所属 tower |
| `layer_index` | 垂直层编号，靠近 PTAP 的 first die 建议为 0 |
| `position_um` | 三维位置 |
| `size_um` | 平面尺寸 |
| `access_parent_die` | 访问该 die 前需要经过的下级 die；primary die 为 `null` |
| `thermal` | 热阻、热容、功率密度等简化参数 |
| `pdn` | 供电电压、等效电阻等简化参数 |

### 2.5 `thermal_model`

M1 可选定义一个轻量三参数层间热传导代理模型：

| 字段 | 含义 |
| --- | --- |
| `self_heating_weight` | 本 die 自热权重 |
| `vertical_coupling_weight` | 垂直相邻 die 的耦合权重 |
| `layer_distance_decay` | 跨层距离衰减系数 |

该模型只用于 recipe 阶段的热风险/热负载估计，不等同于 HotSpot 或 3D-ICE。

### 3. `ieee1838_access`

描述 IEEE 1838-compatible 测试访问资源。它不是标准条文的完整实现，而是调度所需的抽象资源集合。

包含对象：

| 子对象 | 含义 |
| --- | --- |
| `ptap` | 外部 primary TAP 入口 |
| `staps` | secondary TAP 列表 |
| `three_dcrs` | 3D configuration register 抽象 |
| `dwr_segments` | Die Wrapper Register segment |
| `fpp_channels` | FPP channel |
| `fpp_lanes` | FPP lane |

#### PTAP

关键字段：

| 字段 | 含义 |
| --- | --- |
| `ptap_id` | PTAP ID |
| `die_id` | PTAP 所在 die |
| `tck_hz` | 串行访问时钟 |
| `exclusive` | 是否按全局互斥资源建模 |
| `control_bits_per_access` | 每次访问的控制位开销估计 |

#### STAP

关键字段：

| 字段 | 含义 |
| --- | --- |
| `stap_id` | STAP ID |
| `die_id` | 所属 die |
| `parent_die` | 访问链上游 die |
| `select_bits` | select 开销 |
| `bypass_bits` | bypass 开销 |
| `exclusive_path_group` | 路径互斥组 |

#### 3DCR

关键字段：

| 字段 | 含义 |
| --- | --- |
| `register_id` | 3DCR ID |
| `die_id` | 所属 die |
| `bit_length` | 配置位长 |
| `controls` | 可控制对象，如 STAP、DWR、FPP |

#### DWR Segment

关键字段：

| 字段 | 含义 |
| --- | --- |
| `segment_id` | DWR segment ID |
| `die_id` | 所属 die |
| `bit_length` | segment 位长 |
| `supported_modes` | `INTEST`、`EXTEST`、`IF`、`OF`、`MISSION` 等 |
| `serial_access` | 是否支持串行访问 |
| `fpp_access` | 是否支持 FPP 访问 |
| `parallel_group` | 可并行或互斥分组 |
| `mode_config_bits` | 模式配置位开销 |

#### FPP Channel / Lane

关键字段：

| 字段 | 含义 |
| --- | --- |
| `channel_id` | FPP channel ID |
| `lane_id` | lane ID |
| `direction` | `primary_to_secondary`、`secondary_to_primary` 或 `bidirectional` |
| `bandwidth_bps` | 单 lane 带宽 |
| `registered` | 是否 registered |
| `requires_clock_lane` | 是否需要 clock lane |
| `connects` | 可连接 die、core 或 DWR segment |
| `mutual_exclusion_group` | 双向或共享 lane 的互斥组 |

### 4. `test_objects`

描述可测试对象，包括 core、memory、die-level wrapper 或 instrument。

关键字段：

| 字段 | 含义 |
| --- | --- |
| `object_id` | 可测试对象 ID |
| `object_type` | `core`、`memory`、`die_wrapper`、`instrument` |
| `die_id` | 所属 die |
| `scan` | scan chain、pattern、数据量 |
| `bist` | BIST engine、执行周期、读回位数 |
| `power` | shift/capture/bist/access 等功耗估计 |
| `thermal_region` | 热区域 ID |
| `supported_recipes` | 后续可生成的 S/F/B/H/I recipe 类型 |
| `required_resources` | 固定需求，如 DWR segment、FPP channel、BIST engine |

### 5. `interconnects`

描述 die-to-die、TSV、micro-bump 或 interposer route 的可测试互连。

关键字段：

| 字段 | 含义 |
| --- | --- |
| `link_id` | 互连 ID |
| `source_die` / `target_die` | 两端 die |
| `link_type` | `tsv`、`micro_bump`、`interposer_route`、`die_to_die` |
| `test_mode` | 例如 `DWR_EXTEST` |
| `dwr_segments` | 测试该互连需要占用的 DWR segment |
| `route_resource` | TSV 或 interposer route 资源 |
| `estimated_test_bits` | 估算测试数据量 |
| `power_w` | 测试该互连的功耗估计 |

### 6. `resource_groups`

把后续调度需要的互斥资源和容量资源显式化。

常用组：

| 资源组 | 调度含义 |
| --- | --- |
| `serial_access_groups` | PTAP/STAP 串行路径互斥 |
| `fpp_capacity_groups` | FPP lane 容量 |
| `dwr_conflict_groups` | DWR segment / mode 冲突 |
| `bist_engine_groups` | BIST engine 互斥 |
| `power_domains` | 同域功耗上限 |
| `thermal_regions` | 热区域与热点约束 |

### 7. `thermal_adjacency`

描述热耦合关系，不直接替代热仿真模型，但可用于快速热风险估计和热点并行限制。

字段：

| 字段 | 含义 |
| --- | --- |
| `source_region` / `target_region` | 相邻或耦合区域 |
| `coupling_type` | `horizontal` 或 `vertical` |
| `coupling_weight` | 热耦合强度，0 到 1 |
| `avoid_concurrent_high_power` | 是否禁止高功耗并行 |

## 计算派生量

M1 输入应支持后续阶段派生以下量。

### 串行访问时间

```text
serial_time_s(bits, tck_hz) = bits / tck_hz
```

适用于 PTAP/STAP/3DCR/DWR serial shift/readback。

### FPP 传输时间

```text
fpp_time_s(bits, active_lanes, lane_bandwidth_bps)
  = bits / (active_lanes * lane_bandwidth_bps)
```

前提：`active_lanes > 0`，且 lane 均满足方向、channel 和互斥约束。

### Scan 数据量

```text
scan_stimulus_bits = pattern_count * max_chain_length_bits
scan_response_bits = pattern_count * max_chain_length_bits
```

如果后续引入 scan compression，可在输入中增加压缩比，而不是修改基础字段含义。

### BIST 访问时间

```text
bist_total_time =
  config_bits / tck_hz
+ local_cycles / bist_clock_hz
+ readout_bits / tck_hz
```

其中 local execution 不持续占用 PTAP，但需要计入功耗和热区域。

### 热风险初值

M1 使用可解释的代理指标：

```text
thermal_risk = peak_power_w * power_density_w_per_mm2
             * layer_conduction_factor
             / cooling_factor
```

`layer_conduction_factor` 由 `thermal_model` 和 `thermal_adjacency` 共同得到；`cooling_factor` 可由 die 的 `heat_sink_distance_rank`、热阻或经验参数给出。该指标只用于排序或剪枝，不等同于 HotSpot 结果。

## JSON 输入格式

JSON 是主输入格式。一个 case 用一个 JSON 文件完整描述，避免多表散落导致不一致。

必需顶层字段：

```text
model_version
case_id
units
package
timing
resource_limits
thermal_model
dies
ieee1838_access
test_objects
interconnects
resource_groups
thermal_adjacency
```

## CSV 表格式

CSV 只作为后续批量编辑或导出格式，不作为 M1 的主输入。若需要拆表，应至少保持以下表的主键一致：

| CSV 文件 | 主键 | 主要字段 |
| --- | --- | --- |
| `dies.csv` | `die_id` | `role,tower_id,layer_index,x_um,y_um,z_um,width_um,height_um,access_parent_die` |
| `dwr_segments.csv` | `segment_id` | `die_id,bit_length,supported_modes,serial_access,fpp_access,parallel_group` |
| `fpp_lanes.csv` | `lane_id` | `channel_id,direction,bandwidth_bps,registered,requires_clock_lane,mutual_exclusion_group` |
| `test_objects.csv` | `object_id` | `object_type,die_id,scan_chain_count,max_chain_length_bits,pattern_count,bist_enabled,thermal_region` |
| `interconnects.csv` | `link_id` | `source_die,target_die,link_type,test_mode,dwr_segments,estimated_test_bits` |
| `thermal_adjacency.csv` | `source_region,target_region` | `coupling_type,coupling_weight,avoid_concurrent_high_power` |

如果 JSON 和 CSV 同时存在，JSON 是权威输入；CSV 应由 JSON 导出或明确标注来源。

## 一致性检查规则

后续解析器至少应检查：

- 所有 `die_id`、`object_id`、`segment_id`、`lane_id` 全局引用必须存在。
- `primary_entry_die` 必须指向一个 role 为 `primary` 的 die。
- 每个 secondary die 的 `access_parent_die` 必须存在，并能追溯到 primary die。
- `staps[].parent_die` 与 die access chain 一致。
- DWR segment 的 `die_id` 必须存在。
- FPP lane 的 `connects` 引用对象必须存在。
- `supported_recipes` 不能声明资源上不可实现的 recipe。
- `thermal_adjacency` 引用的 region 必须在 `resource_groups.thermal_regions` 中存在。
- 功耗、频率、带宽、位长、面积必须为非负数；作为分母的频率、带宽、面积必须大于 0。

## M1 到 M2 的接口

M2 的 Test Access Recipe 生成器应从 M1 模型读取：

- 可测试对象：`test_objects`
- 访问资源：`ieee1838_access`
- 路径关系：`dies.access_parent_die`、`staps`、`three_dcrs`
- 数据量：scan、BIST、DWR、interconnect 字段
- 资源容量：`resource_limits`、`resource_groups`
- 功耗和热风险：`power`、`thermal`、`thermal_adjacency`

M2 输出的 recipe 不应重复定义 die/core/FPP/DWR 基础属性，只引用 M1 中的 ID。
