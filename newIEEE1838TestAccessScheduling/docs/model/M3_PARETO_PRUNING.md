# M3：候选 Recipe 帕累托剪枝

## 目标

M3 在 M2 生成的候选 Test Access Recipe 上执行帕累托剪枝，删除明显劣质的候选，降低后续调度搜索空间。

本阶段不进行全局调度，不改变 M2 的 recipe 生成逻辑。

## 剪枝原则

剪枝按 `target_id` 分组，只在同一个待测对象或互连的候选 recipe 之间比较。

若 recipe `a` 在以下所有维度上不差于 recipe `b`，并且至少一个维度严格优于 `b`，则认为 `a` 支配 `b`，删除 `b`：

| 维度 | 方向 | 含义 |
| --- | --- | --- |
| `total_time_s` | 越小越好 | 估算总测试时间 |
| `peak_power_w` | 越小越好 | 峰值功耗 |
| `fpp_lanes_required` | 越小越好 | FPP lane 占用 |
| `serial_resource_time_s` | 越小越好 | 估算串行访问资源占用时间 |
| `thermal_risk` | 越小越好 | 热风险代理指标 |

这组维度保留了时间、功耗、FPP lane、串行资源和热风险之间的权衡。比如一个 FPP recipe 虽然更快，但如果使用更多 lane，就不会直接支配串行 recipe。

## 代码入口

核心文件：

```text
src/recipes/pruning.py
experiments/run_m3_pareto_pruning.py
tests/test_m3_pareto_pruning.py
```

运行默认 M3 剪枝：

```powershell
python experiments/run_m3_pareto_pruning.py
```

默认输出：

```text
results/tables/m3_recipe_pruned.csv
results/reports/m3_pruning_summary.csv
```

## 输出说明

`m3_recipe_pruned.csv` 保存剪枝后的 recipe。它继承 M2 字段，并增加：

| 字段 | 含义 |
| --- | --- |
| `serial_resource_time_s` | 由 recipe 类型和 phase 语义估算的串行访问资源占用时间 |

`m3_pruning_summary.csv` 按 target 汇总：

| 字段 | 含义 |
| --- | --- |
| `target_id` | 待测对象或互连 |
| `before_count` | 剪枝前候选数 |
| `after_count` | 剪枝后候选数 |
| `removed_count` | 删除数量 |
| `kept_recipe_ids` | 保留 recipe |
| `removed_recipe_ids` | 删除 recipe |
| `dominance_notes` | 支配关系说明 |

## 当前 M1 样例结果

默认 4-die 3D stack case 中，M2 生成 32 条候选 recipe。M3 删除被支配候选后保留 20 条。

保留数量仍大于 target 数量，说明剪枝没有退化成“每个对象只留最快一个”，而是保留了时间、lane、功耗和热风险之间的候选权衡。

## M3 到 M4 的接口

M4 基础调度器应优先读取：

```text
results/tables/m3_recipe_pruned.csv
```

或在代码中调用：

```text
RecipeGenerator -> rows_from_recipes -> pareto_prune -> kept_rows
```

M4 不应重新执行 M2/M3 的内部估算逻辑，只消费剪枝后的 recipe 字段。
