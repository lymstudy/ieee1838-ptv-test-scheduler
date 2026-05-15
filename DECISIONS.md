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
