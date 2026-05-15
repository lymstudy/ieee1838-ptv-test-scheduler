# 研究与工程决策 DECISIONS

## D1：DWR 术语

DWR 表示 Die Wrapper Register。

禁止将 DWR 写成 Design for Test Wrapper。

## D2：IEEE 1838 的范围

IEEE 1838 提供 3D stacked IC 的 test access architecture。

IEEE 1838 不定义测试调度算法。

本项目是在 IEEE 1838-compatible access resources 的基础上，研究测试任务调度优化。

## D3：SSN

MVP 阶段不实现真实 Siemens Tessent SSN。

如后续需要表达类似思想，只允许使用：
“streaming-scan-inspired die-level TAM model”。

禁止声称 IEEE 1838 包含 SSN。

## D4：物理模型

MVP 使用抽象但物理上合理的 thermal 和 IR drop 模型。

Thermal model：
Discrete RC-style temperature update。

Voltage model：
Equivalent PDN resistance-based IR drop estimation。

## D5：第一阶段目标

第一阶段目标是 4-die stack MVP。

需要比较的 scheduler：
1. Serial baseline
2. Bandwidth-greedy baseline
3. PTV-aware scheduler

## D6：研究诚信约束

禁止编造论文引用、会议结果、标准条文或实验结果。

如果需要引用外部论文或标准，必须明确来源。

## D7：硬件开销表述

禁止声称 zero hardware overhead。

如果需要表达低硬件代价，可以使用：
“no additional test access pins in the abstract model”
或
“reuse IEEE 1838-compatible test access resources”。

## D8：Scheduler 接口与结果格式

调度器统一继承 BaseScheduler，并通过 ScheduleEntry 表示单个任务区间，通过 ScheduleResult 表示完整调度结果、PTV trace 和 metrics。

Serial baseline 的 metrics CSV 使用单行 summary 格式，字段包括 scheduler_name、tat、peak_temperature、peak_ir_drop、temperature_violation_count、voltage_violation_count 和 num_tasks。

Serial baseline 是 IEEE 1838-style access resources 上的串行基线，不表示 IEEE 1838 标准定义了调度算法。

## D9：Bandwidth-greedy 资源规则

Bandwidth-greedy baseline 是激进并行调度器，只考虑 task readiness/dependency、FPP lane capacity、DWR segment conflict 和基础 access resource conflict。

默认 FPP lane 需求集中定义在 BandwidthGreedyScheduler 中：scan 使用 1 lane，DWR_EXTEST 使用 1 lane，BIST 使用 0 lane，instrument_access 使用 0 lane。若 task 显式提供 fpp_lanes_required、required_fpp_lanes 或 fpp_lanes_used，则优先使用 task 字段。

DWR segment conflict 规则：同一 Die Wrapper Register segment 不能被多个 overlap task 同时占用。

基础 access resource conflict 规则：当前只将 PTAP_STAP_SERIAL 视为独占访问资源；FPP lane pool 通过 lane capacity 约束，不用字符串资源名禁止并行。

该 baseline 不在调度过程中避免 thermal 或 voltage violation，只在调度后计算 temperature trace、IR drop trace 和 violation count。
## D10：FPP 与 PTAP/STAP 的并行抽象

在当前 MVP 抽象模型中，PTAP/STAP 主要表示低带宽配置、触发和 instrument access 路径，FPP 表示可选高带宽 bulk test data transfer 路径。

因此，在 Bandwidth-greedy 和后续 PTV-aware scheduler 中，FPP_SCAN 或 FPP_DWR 类型任务可以与 BIST_LOCAL 或低带宽 PTAP_STAP_SERIAL instrument access 并行执行，前提是：
- 不超过 FPP lane capacity；
- 不冲突同一个 DWR segment；
- 不违反 task dependency；
- 后续 PTV-aware scheduler 还需要满足 thermal 和 IR drop constraints。

该决策是 MVP 阶段的抽象建模假设，不代表 IEEE 1838 标准强制规定 FPP 与 PTAP 必然可完全并行。