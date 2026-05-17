# 项目状态 STATUS

## 当前里程碑

A0 原型已完成：task-level IEEE 1838-style PTV-aware test scheduling prototype。

B0 已启动并完成：IEEE 1838-aware layered access scheduling 设计规格。

## 当前阶段进度

- [x] 仓库脚手架与基础模型
- [x] 通用 Scheduler 接口
- [x] Serial IEEE 1838 baseline scheduler
- [x] Bandwidth-greedy baseline scheduler
- [x] PTV-aware scheduler
- [x] 三类调度器对比图表
- [x] Stress workload mechanism validation
- [x] Schedule-based physical evaluator consistency fix
- [x] MVP result consolidation
- [x] FPP lane sweep
- [x] voltage limit sweep
- [x] thermal limit sweep
- [x] richer synthetic workload generation
- [x] workload scale sweep
- [x] benchmark-derived workload schema
- [x] benchmark workload example adapter
- [ ] benchmark example schedule audit
- [ ] realistic benchmark statistics case
- [x] A0 原型冻结
- [x] B0 IEEE 1838-aware layered scheduler design spec
- [x] B1 AccessPath data model and path cost estimator
- [ ] B2 TestIntent to ExecutionPhase layered expander
- [ ] B3 Access-time-aware scheduler
- [ ] B4 Predictive path-blocking-aware PTV scheduler
- [ ] RTL mock validation
- [ ] 真实公开 benchmark statistics 接入
- [ ] 论文/组会最终版结果总结

## 最近完成任务

日期：2026-05-16

已完成：
- 冻结 A0 task-level PTV scheduling prototype 的定位。
- 新增 B0 设计规格书：`docs/DESIGN_SPEC_1838_LAYERED_SCHEDULER.md`。
- 新增下一阶段短路线图：`docs/NEXT_PHASE_PLAN.md`。
- 明确 A0 不是完整 IEEE 1838 behavior model。
- 明确 B 阶段主线为 IEEE 1838 access behavior、layered task expansion、access time model、predictive scheduling 和 asymmetric physical model。
- 更新 README、ROADMAP、TODO、DECISIONS 和 EXPERIMENT_LOG。

测试结果：
- pytest: 68 passed, 1 warning

## A0 原型重新定位

A0 是 task-level physical-aware scheduling prototype。

A0 已能证明：
- bandwidth_greedy 可以显著降低 TAT；
- aggressive concurrency 会提高 voltage / thermal violation 风险；
- ptv_aware 可以用一定 TAT 代价降低或消除 physical violation；
- schedule-based evaluator 能正确统计 overlap 下的 power、temperature 和 IR-drop。

A0 不再继续扩展为最终形态。后续进入 B 阶段，将访问路径、IEEE 1838 access operation、分层执行 phase 和预测性调度作为主线。

## B0 设计规格输出

- `docs/DESIGN_SPEC_1838_LAYERED_SCHEDULER.md`
- `docs/NEXT_PHASE_PLAN.md`

B0 定义的核心对象：
- TestIntent
- AccessOp
- AccessPath
- LayeredTask
- ExecutionPhase
- Predictive Physical-Aware Scheduler
- Asymmetric voltage / thermal model roadmap

## 当前限制

- 当前 scheduler 仍是 A0 task-level 实现。
- AccessPath data model / generator / path cost estimator 已完成初版 MVP，但仍是抽象估算。
- 尚未实现 TestIntent / ExecutionPhase。
- 尚未实现 layered task expander。
- 尚未建模 3DCR select/bypass、STAP path opening、DWR mode/shift/capture/update 的细粒度行为。
- 尚未实现 access/config time、local execution time、readback time 的分离。
- Thermal model 仍是 simplified per-die RC model。
- Voltage model 仍是 simplified shared-PDN model。
- realistic UART statistics case 当前 checkout 中尚未完成；不得写成 RTL-extracted benchmark 或已完成实验。
- 未引入 HotSpot、3D-ICE、RedHawk、Voltus 或 Tessent SSN。

## 下一步任务

推荐下一步进入：

B2：TestIntent to ExecutionPhase layered expander。

预期输出：
- `src/intent/model.py`
- `src/layered/model.py`
- `src/layered/expander.py`
- `tests/test_layered_expander.py`
- BIST / scan / DWR EXTEST / instrument access phase 展开示例


## Frontier Idea Integration Plan

日期：2026-05-17

已完成：
- 新增 `docs/FRONTIER_IDEA_INTEGRATION_PLAN.md`。
- 将 PTVA-SSN-inspired ideas、interposer test-bus、UCIe-inspired health event、HBM-like capture staggering、PackageProfile-aware boundary condition 纳入 B 阶段之后的长期规划。
- 更新 DESIGN_SPEC 和 NEXT_PHASE_PLAN 的增量引用。
- 明确这些 idea 是 future roadmap，不是当前已实现功能。

关键边界：
- SSN is not part of IEEE 1838。
- UCIe is not part of IEEE 1838。
- SIB is not assumed to directly control FPP lane width。
- FPP is optional and not zero-cost。
- Zero hardware overhead claim remains forbidden。

下一步任务已更新为：
B2：TestIntent to ExecutionPhase layered expander。

## B1 AccessPath Model and Path Cost Estimator

日期：2026-05-17

已完成：
- 新增 `src/access_path/model.py`。
- 新增 `src/access_path/generator.py`。
- 新增 `experiments/demo_access_path_generation.py`。
- 新增 `tests/test_access_path_generator.py`。
- 实现 basic die path、DWR access path、FPP data path 生成。
- 实现 PTAP shift time 和 FPP transfer time 估算。
- 生成 access path CSV / Markdown demo summary。

已生成文件：
- `results/access_path/access_path_summary.csv`
- `results/access_path/access_path_summary.md`

验证结果：
- pytest: 75 passed, 1 warning
- `python experiments/demo_access_path_generation.py`: passed
- `python experiments/run_case_4die.py`: passed

当前限制：
- B1 仍是 abstract access path estimator，不是 IEEE 1838 bit-accurate implementation。
- 尚未实现 TestIntent / ExecutionPhase / layered task expansion。
- 尚未把 AccessPath 接入现有 A0 scheduler。

下一步推荐：
B2：TestIntent to ExecutionPhase layered expander。

## Repository State Consistency Fix

日期：2026-05-17

检查结果：
- 当前 checkout 中不存在 `benchmarks/realistic_uart_stats.yaml`。
- 当前 checkout 中不存在 `experiments/run_realistic_uart_workload.py`。
- 当前 checkout 中不存在 `experiments/audit_realistic_uart_schedule.py`。
- 当前 checkout 中不存在 `tests/test_realistic_uart_workload.py`。
- 当前 checkout 中不存在 `results/benchmarks/realistic_uart/`。
- 当前 checkout 中不存在 `experiments/audit_example_benchmark_schedule.py`。
- 当前 checkout 中不存在 `tests/test_example_benchmark_audit.py`。
- 当前 checkout 中不存在 `results/benchmarks/example/audit/`。

真实已完成并保留：
- benchmark-derived workload schema：`benchmarks/schema.md`
- example benchmark stats：`benchmarks/example_benchmark_stats.yaml`
- benchmark adapter：`src/workload/benchmark_adapter.py`
- example benchmark runner：`experiments/run_example_benchmark_workload.py`
- benchmark adapter tests：`tests/test_benchmark_adapter.py`
- example benchmark results：`results/benchmarks/example/`

修复结论：
- realistic UART statistics case 尚未完成。
- realistic UART / public benchmark-derived statistics 属于后续任务。
- benchmark example schedule audit 当前 checkout 中也尚未完成。
- 下一步仍为 B2：TestIntent to ExecutionPhase layered expander。
