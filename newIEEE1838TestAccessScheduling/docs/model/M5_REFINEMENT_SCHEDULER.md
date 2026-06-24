# M5：约束精修调度器

## 目标

M5 在 M4 可行调度基础上做小规模约束精修，使调度层不只停留在贪心 baseline。

当前已经引入 OR-Tools CP-SAT 后端，并保留无外部依赖的 local refinement fallback。CP-SAT 后端显式建模 M5 所需的边界：recipe 唯一性、phase precedence、串行互斥、FPP lane capacity、DWR conflict、BIST precedence 和功耗约束。

依赖声明位于：

```text
requirements.txt
```

## 输入

默认读取 M3 输出：

```text
results/tables/m3_recipe_pareto.csv
```

M5 先调用 M4 贪心调度得到 baseline。默认 `--backend auto` 会优先使用 OR-Tools CP-SAT；若环境未安装 OR-Tools，则回退到 local refinement。

local backend 在 target 排序邻域内做局部精修。单 target recipe 替换邻域已经保留在实现中，但默认关闭；需要时可通过 `--enable-recipe-moves` 打开。

## 精修策略

OR-Tools backend 使用 optional interval variable 表示每个 candidate recipe 的每个 phase，并用 Boolean variable 表示 recipe 是否被选择：

| 变量/约束 | 含义 |
| --- | --- |
| `select_{recipe}` | recipe 是否被选中 |
| optional interval | phase start、duration、end |
| `AddExactlyOne` | 每个 target 只选一个 recipe |
| `AddNoOverlap` / `AddCumulative` | 串行、FPP、功耗、DWR、capture 资源约束 |
| `makespan` | 所有 selected recipe 结束时间的最大值 |

local backend 包含两类局部邻域：

| 邻域 | 含义 |
| --- | --- |
| order move | 对 target 调度顺序执行 insert/swap，并重新生成合法 phase schedule |
| recipe move | 对单个 target 尝试替换 Pareto recipe，再对顺序做局部精修；默认关闭，可用 `--enable-recipe-moves` 打开 |

接受准则是严格降低 `makespan_s`。目标函数目前采用字典序中的第一层目标：最小化总测试完成时间。功耗、lane 和热风险先作为约束与报告指标保留，后续 M6/M7 再加入多目标搜索。

## 约束

M5 复用 M4 的 phase-level 约束检查：

| 约束 | 当前实现 |
| --- | --- |
| recipe uniqueness | 每个 target 只保留一个 selected recipe |
| phase precedence | 同一 recipe 内 phase 顺序不变 |
| serial mutex | `serial_required=true` 的 phase 不超过 `ptap_ports` |
| FPP cumulative | FPP lane 占用不超过全局和 channel capacity |
| power cumulative | 活动 phase 总功耗不超过 `max_total_power_w` |
| BIST precedence | BIST config、execute、readout 按 phase 顺序执行 |
| BIST execution parallelism | `LOCAL_BIST_RUN` 不占用外部 serial/FPP 资源 |
| DWR conflict | DWR conflict group 不超过 capacity |
| capture concurrency | capture phase 不超过 `max_concurrent_capture` |

## 输出

运行：

```powershell
python experiments/run_m5_refinement_scheduler.py
```

强制使用 OR-Tools：

```powershell
python experiments/run_m5_refinement_scheduler.py --backend ortools
```

默认输出：

```text
results/schedules/m5_refined_schedule.csv
results/reports/m5_refinement_report.md
```

报告中会给出 M4 baseline makespan、M5 refined makespan、改善比例和接受的精修 move。
