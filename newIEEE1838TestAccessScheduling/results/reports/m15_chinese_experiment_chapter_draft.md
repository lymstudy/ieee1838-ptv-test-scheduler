# M15 中文实验章节初稿

## 1 实验设置

本文实验基于前述 IEEE 1838 可计算模型和 Test Access Recipe 生成方法展开。实验目标不是仅验证单个手写示例，而是考察所提出的测试访问路径生成与协同调度方法在不同规模、不同先进封装拓扑以及不同调度策略下的表现。
M10 benchmark suite 共包含 12 个测试场景，覆盖 4 个 ITC'02 派生 workload（d695, p22810, p34392, p93791）、4 个规模等级（small, medium, large, xlarge）以及 3 类封装拓扑（2_5d_interposer, 3d_stack, 5_5d_multi_tower）。
M10 共生成 216 行调度实验结果，其中 216 行成功得到合法调度。

在算法对比方面，M11 选取小规模和中等规模代表性场景，对 8 类方法进行比较，共得到 45 行成功结果，占全部 48 行实验的主要部分。
这些方法包括纯串行访问、固定最快路径、TAM-like 基线、低功耗优先策略、M4 贪心调度、M5 CP-SAT 精修以及受规模限制的 M6 ALNS 外层搜索。

热验证方面，M12b 对 3 个代表性场景执行 HotSpot 离线验证，共得到 6 行成功 HotSpot 输出。HotSpot 在本文中作为离线代表性验证工具使用，不嵌入主调度闭环。

## 2 规模与拓扑覆盖实验

M10 实验用于说明本文方法并不依赖某一个固定 3D stack 示例，而是可以迁移到 2.5D interposer、3D stack 和 5.5D multi-tower 三类结构。
在 nominal 功耗配置和 8 条 FPP lane 的设置下，M4 贪心调度相对于纯串行 IEEE 1838 访问的平均加速比为 35.67x，平均归一化完成时间为 0.1026。
这一结果说明，在显式考虑串行访问、FPP lane、DWR segment 和功耗约束后，路径选择与调度协同仍然能够显著缩短测试完成时间。

| 拓扑类型 | M4 结果行数 | 平均归一化完成时间 | 平均加速比 |
| --- | ---: | ---: | ---: |
| 2_5d_interposer | 36 | 0.1009 | 37.01 |
| 3d_stack | 36 | 0.1050 | 31.30 |
| 5_5d_multi_tower | 36 | 0.1033 | 35.92 |

各规模下 M4 的最佳结果如下：

| 规模 | 场景 | FPP lane 数 | 功耗配置 | 归一化完成时间 | 加速比 |
| --- | --- | ---: | --- | ---: | ---: |
| small | m10_small_d695_2_5d_interposer | 2 | tight | 0.3361 | 2.97 |
| medium | m10_medium_p22810_2_5d_interposer | 8 | tight | 0.0228 | 43.94 |
| large | m10_large_p34392_5_5d_multi_tower | 16 | tight | 0.0145 | 69.16 |
| xlarge | m10_xlarge_p93791_5_5d_multi_tower | 16 | tight | 0.0273 | 36.62 |

## 3 算法对比与消融分析

M11 实验进一步比较不同调度策略的影响。纯串行方法保留 IEEE 1838 串行访问路径，但无法利用 FPP 和 BIST 并行性，因此作为最保守基线。固定最快路径和 TAM-like 方法能够降低测试时间，但它们弱化了 IEEE 1838 访问层级、配置开销和资源互斥的表达。本文的 M4/M5 方法在保留这些约束的同时进行 recipe 选择和时隙安排。

| 方法 | 类型 | 成功行数 | 平均归一化完成时间 | 平均加速比 |
| --- | --- | ---: | ---: | ---: |
| pure_serial | baseline | 6 | 1.0000 | 1.00 |
| fixed_fastest | baseline | 6 | 0.1819 | 22.80 |
| tam_like | baseline | 6 | 0.1819 | 22.80 |
| low_power | baseline | 6 | 0.1929 | 20.47 |
| m4_all_recipes | ablation | 6 | 0.1819 | 22.80 |
| m4_greedy | proposed | 6 | 0.1819 | 22.80 |
| m5_cpsat | proposed | 6 | 0.1814 | 22.86 |
| m6_alns | proposed | 3 | 0.3394 | 2.95 |

从结果看，M5 CP-SAT 精修在当前代表性场景中取得最低平均归一化完成时间。需要注意的是，CP-SAT 输出为满足约束的可行调度；除非求解器状态明确给出最优性证明，否则不应在论文中表述为全局最优。
M6 ALNS 当前只在目标数不超过阈值的场景中运行，这是为了避免将算法对比实验变成不可控的长时间搜索。该部分更适合作为中大规模搜索框架的原型证据，而不是最终性能上界。

## 4 热代理与 HotSpot 离线验证

调度器内部使用快速热代理模型评估不同 recipe 和时隙安排的热风险。该模型适合在大量候选方案上快速比较趋势，但不应被描述为完整热仿真工具。
为避免热结论只依赖代理模型，M12b 将代表性调度结果导出为 HotSpot 可读的 `.flp/.ptrace` 输入，并在 Linux/EDA VM 上执行离线 HotSpot 验证。
当前 HotSpot 峰值温度范围为 60.61 C 到 63.69 C。代理模型选出的最佳调度与 HotSpot 峰值温度排序在 3 / 3 个代表性场景中一致。

| 场景 | 代理模型最佳调度 | HotSpot 最佳调度 | 排序是否一致 |
| --- | --- | --- | --- |
| m10_medium_p22810_3d_stack | m4_greedy | m4_greedy | True |
| m10_medium_p22810_5_5d_multi_tower | m4_greedy | m4_greedy | True |
| m10_small_d695_5_5d_multi_tower | m4_greedy | m4_greedy | True |

上述结果支持将热代理模型用于调度过程中的趋势引导，但不能说明代理模型与 HotSpot 在数值上完全等价。当前 HotSpot 输入仍是简化 block-level floorplan，因此论文中应将其表述为代表性离线验证，而不是工业级 signoff 热分析。

## 5 图表安排

本阶段整理的图表可以按以下方式放入论文实验章节：

| 图表编号 | 建议标题 | 用途 |
| --- | --- | --- |
| m16_ieee1838_resource_gantt_xlarge | 图 1 xlarge 5.5D 场景下 IEEE 1838-aware 测试调度资源层甘特图 | 用于展示 PTAP/STAP、FPP lane、DWR/scan 和目标测试事务在正式大规模 case 中的资源占用关系。 |
| m16_power_temperature_hotspot_composite | 图 2 功耗曲线、温度曲线与 HotSpot 热点分布综合图 | 用于展示调度方法对系统功耗、热代理温度趋势和 HotSpot block-level 热点分布的影响。 |
| m16_method_comparison_normalized | 图 3 不同调度方法的多指标归一化对比 | 用于说明测试时间收益、功耗/温度代价和 FPP 利用之间的权衡关系。 |
| m16_benchmark_coverage_matrix | 图 4 benchmark 规模与拓扑覆盖矩阵 | 用于直接说明正式实验覆盖 4/6/8/12 die、三类封装拓扑、目标数和 recipe 数，而不是早期小示例。 |
| m10_benchmark_sweep | 表 1 M10 benchmark suite 的规模、拓扑和资源敏感性实验结果 | 用于支撑大规模覆盖实验和 M4 贪心调度的加速比分析。 |
| m11_algorithm_comparison | 表 2 M11 不同基线与本文方法的调度结果对比 | 用于支撑算法对比和消融实验叙述。 |
| m12b_hotspot_validation | 表 3 M12b 代表性调度结果的 HotSpot 离线验证结果 | 用于支撑热代理趋势验证和热模型局限性讨论。 |

## 6 局限性

第一，benchmark workload 来自公开 ITC'02 信息并经过封装结构映射，仍然属于研究原型级输入，而不是某一真实工业芯片的完整 DFT 数据。
第二，M10 用于覆盖规模和拓扑敏感性，因此只选择了少数方法进行大范围 sweep；更丰富的算法比较集中在 M11。
第三，M11 当前主要覆盖 small 和 medium 场景，large/xlarge 场景下的 CP-SAT/ALNS 全量对比仍可作为后续补充。
第四，HotSpot 验证只覆盖代表性 case，不应夸大为完整工业 3D 热仿真流程。

## 7 本章小结

实验结果表明，基于 Test Access Recipe 的 IEEE 1838-aware 路径生成与调度方法能够在保持访问路径和资源约束显式建模的同时，显著降低整体测试完成时间。
M10 证明了该方法在 2.5D、3D 和 5.5D 场景中的可扩展性；M11 进一步说明 M4/M5 调度框架相对于纯串行和固定路径基线具有竞争力；M12b 则通过代表性 HotSpot 离线验证补充了热代理模型的可信度边界。
因此，本文方法的主要价值不在于单一启发式规则，而在于将 IEEE 1838 访问路径生成、资源约束调度和电热风险评估组织到同一套可计算实验框架中。
