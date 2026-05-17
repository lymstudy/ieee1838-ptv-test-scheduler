# 项目路线图 ROADMAP

## A0：Task-Level PTV Scheduling Prototype

状态：
已完成并冻结。

定位：
A0 是 task-level physical-aware scheduling prototype。它验证调度器、资源约束、物理评估和 workload adapter 的基础可行性，不是完整 IEEE 1838 behavior model。

主要产出：
- YAML 配置加载
- stack/task/access/thermal/voltage 基础模型
- Serial IEEE 1838-style baseline scheduler
- Bandwidth-greedy baseline scheduler
- PTV-aware scheduler
- Unified schedule evaluator
- Simplified shared-PDN voltage model
- Simplified per-die RC thermal model
- clean 4-die case
- stress 4-die case
- FPP lane sweep
- voltage limit sweep
- thermal limit sweep
- workload scale sweep
- benchmark-derived workload schema
- example benchmark adapter
- RESULTS.md 结果总结

核心结论：
- Bandwidth-greedy 能降低 TAT，但会增加 physical violation 风险。
- PTV-aware 能以一定 TAT 代价降低或消除 voltage / thermal violation。
- A0 的调度粒度仍是 monolithic task，不具备完整 IEEE 1838 access behavior 展开。

## B0：Design Spec and Interface Planning

状态：
已完成。

目标：
冻结 A0 原型定位，规划 IEEE 1838-aware layered access scheduling。

主要产出：
- `docs/DESIGN_SPEC_1838_LAYERED_SCHEDULER.md`
- `docs/NEXT_PHASE_PLAN.md`
- STATUS / TODO / DECISIONS / EXPERIMENT_LOG 更新

验收标准：
- 明确 A0 不足。
- 明确 B 阶段 pipeline。
- 定义 TestIntent、AccessOp、AccessPath、LayeredTask、ExecutionPhase。
- 明确 B1 下一步任务。

## B1：AccessPath Data Model and Path Cost Estimator

状态：
已完成初版 MVP。

目标：
建立 IEEE 1838-compatible access path 的数据模型和成本估计器。

预期产出：
- `src/access_path/model.py`
- `src/access_path/generator.py`
- `tests/test_access_path_generator.py`
- docs 中的 access path 示例

验收标准：
- 能为不同 target die 生成 path_dies。
- 能区分 selected_staps 和 bypassed_dies。
- 能估算 required_3dcr_bits、access_bit_length 和 estimated_access_time。
- 能列出 occupied_resources。
- 能体现 deeper die access overhead 更高。

实际产出：
- `src/access_path/model.py`
- `src/access_path/generator.py`
- `experiments/demo_access_path_generation.py`
- `tests/test_access_path_generator.py`
- `results/access_path/access_path_summary.csv`
- `results/access_path/access_path_summary.md`

## B2：TestIntent to ExecutionPhase Layered Expander

状态：
计划中。

目标：
将高层 test intent 展开为多阶段 execution phases。

预期产出：
- TestIntent model
- AccessOp model
- ExecutionPhase model
- LayeredTask model
- Layered task expander
- BIST / scan / DWR EXTEST / instrument access 展开示例

验收标准：
- BIST 可展开为 config、trigger、local execution、re-access、readback。
- Scan 可展开为 access path config、FPP shift-in、capture、FPP shift-out、readback。
- DWR EXTEST 可展开为 DWR mode config、shift、capture、update/readout。
- Instrument access 可展开为 select、network access、read/write、optional readback。

## B3：Access-Time-Aware Scheduler

状态：
计划中。

目标：
调度器区分 access/config time、data transfer time、local execution time、capture time 和 readback time。

预期产出：
- Access-time-aware baseline scheduler
- phase-level schedule CSV
- phase-level Gantt chart

验收标准：
- BIST local execution 不持续占用 PTAP。
- PTAP/STAP config 阶段能够表现为串行 bottleneck。
- FPP data phase 与 PTAP control phase 分离。

## B4：Predictive Path-Blocking-Aware PTV Scheduler

状态：
计划中。

目标：
从 one-step PTV heuristic 升级为 predictive access-path and physical-aware scheduler。

预期产出：
- Look-ahead heuristic scheduler
- path-blocking risk metrics
- readback delay risk metrics
- predictive schedule audit

验收标准：
- score 包含 access_path_cost、path_blocking_cost、predicted_voltage_risk、predicted_thermal_risk、fpp_hardware_cost、readback_delay_risk。
- 能展示 path blocking 对 TAT 和 idle gap 的影响。
- PTV-aware 结果不伪造优势，所有结论可由 audit 支撑。

## B5：Asymmetric Physical Model

状态：
计划中。

目标：
将 simplified shared-PDN 和 per-die RC thermal 升级为非对称物理模型。

预期产出：
- PDN matrix voltage model
- thermal coupling model
- per-die / per-region limit config

验收标准：
- 支持 `Vdrop_i(t) = sum_j R_ij * I_j(t)`。
- 支持 `T(t+1) = A_T * T(t) + B_T * P(t)`。
- 不同 die 的 IR-drop / temperature response 可以不同。

## B6：Ablation Study

状态：
计划中。

目标：
评估各机制贡献。

预期产出：
- without voltage risk
- without thermal risk
- without path blocking
- without capture staggering
- without dummy cycle
- ablation summary CSV and plots

验收标准：
- 每个 ablation 都可复现。
- 结论来自 CSV 和 audit，不靠主观描述。

## B7：Small-Scale MILP Optimal Baseline

状态：
计划中。

目标：
为小规模 case 提供 optimal 或 near-optimal baseline。

预期产出：
- MILP formulation
- small-case solver wrapper
- heuristic vs MILP comparison

验收标准：
- 小规模 workload 可求解。
- 能明确 heuristic optimality gap 或 tradeoff。

## B8：RTL Mock Validation

状态：
计划中。

目标：
验证 simplified PTAP/STAP/DWR/FPP/scan/BIST 行为和 scheduler command flow。

预期产出：
- RTL mock stack
- command trace
- simulation logs

验收标准：
- 能 replay access sequence。
- 只验证控制流和访问序列执行，不声称验证真实 3D thermal/IR-drop。

## B9：Public Benchmark-Derived Statistics Case

状态：
计划中。

目标：
接入真实公开 benchmark statistics 或人工提取报告。

预期产出：
- benchmark stats YAML
- schedule results
- audit report

验收标准：
- 明确来源。
- 不编造实验结果、论文引用或标准条文。

## B10：Paper / Slide Consolidation

状态：
计划中。

目标：
整理论文/组会可用材料。

预期产出：
- method figure
- result tables
- sweep plots
- audit-supported claims
- limitations

验收标准：
- 每个结论都能追溯到 repo 文件和实验日志。

## B0 Addendum：Frontier Idea Integration Planning

状态：
已完成。该补充规划不实现新功能，只把若干前沿启发纳入 B 阶段之后的研究路线。

主要产出：
- `docs/FRONTIER_IDEA_INTEGRATION_PLAN.md`
- DESIGN_SPEC / NEXT_PHASE_PLAN 增量引用
- ROADMAP / TODO / DECISIONS / STATUS / EXPERIMENT_LOG / README 更新

纳入长期路线的方向：
- SSN-inspired die-level TAM abstraction，明确不是 Siemens SSN 实现，也不是 IEEE 1838 内容。
- FPP/SSN-like TAM co-allocation，研究 stack-level FPP 与 die-level TAM bandwidth 的共同分配。
- PowerPillar-aware capture staggering，强化 capture IR-drop 风险控制。
- PackageProfile-aware boundary modeling，用 profile 改变仿真边界条件，不声称材料实测结论。
- External health event interface，受 fast throttle / emergency shutdown 类机制启发，但不实现 UCIe。
- Interposer test-bus-aware routing，作为 B11 之后的长期扩展。

B1 已完成初版 MVP；下一步推进 B2：TestIntent to ExecutionPhase layered expander。

## B4.1：PowerPillar-Aware Capture Staggering

状态：
计划中，位于 B4 之后。

目标：
将 capture staggering 从 global limit 扩展为 global / per-die / per-power-pillar / capture-window assignment。

预期产出：
- PowerPillar / VerticalPDNGroup planning model
- capture offset assignment heuristic
- capture IR-drop risk audit

验收标准：
- 同一 power_pillar_id 的 capture concurrency 可被限制。
- 不声称已验证 HBM4 或真实 hybrid bonding PDN。

## B6-B8：SSN-Inspired TAM and FPP Cost Extensions

状态：
计划中。

目标：
规划 die-level streaming-scan-inspired TAM abstraction、FPP/TAM co-allocation 和 FPP hardware cost model。

验收标准：
- 不声称 IEEE 1838 包含 SSN。
- 不声称实现 Siemens Tessent SSN。
- FPP lane 增加必须体现硬件/面积/引脚/路由/控制成本。

## B11-B13：Interposer / Health Event / Package Boundary Extensions

状态：
长期计划。

目标：
- B11: Interposer test-bus-aware routing extension。
- B12: External health event-aware schedule playback。
- B13: PackageProfile-aware constraint boundary modeling。

验收标准：
- 不声称实现 UCIe。
- 不声称 FPGA 能验证真实 3D IC thermal/IR-drop。
- 不声称 glass substrate 一定优于所有场景。
- 不把这些 future objects 写成当前代码已实现对象。
