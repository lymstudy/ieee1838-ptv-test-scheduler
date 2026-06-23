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
- [x] B2 TestIntent to ExecutionPhase layered expander
- [x] B2.5 Output path robustness fix
- [x] B3.1 ExecutionPhase-level access-time-aware scheduler prototype
- [x] B3.1.5 Layered schedule metrics/evaluator
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
- 将下一阶段计划合并到 `ROADMAP.md`。
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

B0 定义的核心对象：
- TestIntent
- AccessOp
- AccessPath
- LayeredTask
- ExecutionPhase
- Predictive Physical-Aware Scheduler
- Asymmetric voltage / thermal model roadmap

## 当前限制

- A0 scheduler 仍是 task-level 实现；B3.1 新增了独立 ExecutionPhase-level scheduler prototype。
- AccessPath data model / generator / path cost estimator 已完成初版 MVP，但仍是抽象估算。
- TestIntent / ExecutionPhase / layered task expander 已完成初版 MVP，并可由 B3.1 prototype 调度。
- 尚未建模 3DCR select/bypass、STAP path opening、DWR mode/shift/capture/update 的细粒度行为。
- B3.1.5 已支持 phase-level access/resource metrics，但尚未将 phase-level schedule 接入 thermal / voltage prediction 或 predictive physical-aware scheduler。
- Thermal model 仍是 simplified per-die RC model。
- Voltage model 仍是 simplified shared-PDN model。
- realistic UART statistics case 当前 checkout 中尚未完成；不得写成 RTL-extracted benchmark 或已完成实验。
- 未引入 HotSpot、3D-ICE、RedHawk、Voltus 或 Tessent SSN。

## 下一步任务

推荐下一步进入：

B3.2/B3.3：phase-level thermal / voltage prediction integration and reporting。

预期输出：
- phase-level thermal / voltage prediction metrics
- phase-level physical trace or report outputs
- conservative integration with the B3.1 scheduler and B3.1.5 metrics evaluator




## Frontier Idea Integration Plan

日期：2026-05-17

已完成：
- 将 Frontier idea planning 合并到 `ROADMAP.md` / `TODO.md` / `DECISIONS.md`。
- 将 PTVA-SSN-inspired ideas、interposer test-bus、UCIe-inspired health event、HBM-like capture staggering、PackageProfile-aware boundary condition 纳入 B 阶段之后的长期规划。
- 更新 README / ROADMAP / TODO / DECISIONS 的增量引用。
- 明确这些 idea 是 future roadmap，不是当前已实现功能。

关键边界：
- SSN is not part of IEEE 1838。
- UCIe is not part of IEEE 1838。
- SIB is not assumed to directly control FPP lane width。
- FPP is optional and not zero-cost。
- Zero hardware overhead claim remains forbidden。

下一步任务已更新为：
B3：Access-time-aware scheduler。

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

验证结果：
- pytest: 75 passed, 1 warning
- `python experiments/demo_access_path_generation.py`: B1 输出文件已存在；当前沙箱重跑时写 `results/access_path/access_path_summary.csv` 被拒绝
- `python experiments/run_case_4die.py`: passed

当前限制：
- B1 仍是 abstract access path estimator，不是 IEEE 1838 bit-accurate implementation。
- TestIntent / ExecutionPhase / layered task expansion 已完成初版 MVP。
- 尚未把 AccessPath 接入现有 A0 scheduler。

下一步推荐：
B3.2/B3.3：phase-level thermal / voltage prediction integration and reporting。

## B3.1 ExecutionPhase-Level Access-Time-Aware Scheduler

日期：2026-05-17

已完成：
- 新增 `src/layered/scheduler.py`。
- 新增 `ScheduledPhase`、`LayeredScheduleResult` 和 `AccessTimeAwareScheduler`。
- 实现 deterministic earliest-start list scheduler。
- 支持 phase dependency completion constraint。
- 支持 missing dependency 的清晰 `ValueError`。
- 支持 global PTAP、FPP lane capacity、DWR segment、global CAPTURE resource。
- `LOCAL_BIST_RUN` 只有在 `uses_ptap=True` 时才占用 PTAP；默认 local execution 不自动占用 PTAP。
- 新增 `tests/test_layered_scheduler.py`。
- 新增 `experiments/demo_access_time_scheduler.py`，支持 `--output-dir`，默认写 `results/access_time_scheduler/`。

验证结果：
- `pytest tests/test_layered_scheduler.py`: 8 passed, 1 warning。
- `pytest`: 89 passed, 1 warning。
- `python experiments/demo_access_time_scheduler.py --output-dir tmp_access_time_scheduler_out`: passed。

历史临时输出（已在 Repository Cleanup 中删除）：
- `tmp_access_time_scheduler_out/phase_schedule.csv`

范围边界：
- B3.1 是第一个 ExecutionPhase-level scheduling prototype。
- 未修改 A0 task-level schedulers 或 evaluator。
- 未实现 predictive physical-aware scheduling。
- 未实现完整 IEEE 1838 behavior framework。
- phase-level thermal / voltage prediction integration 仍是后续 B3.2/B3.3 工作。

下一步推荐：
B3.2/B3.3：将 phase-level schedule 接入 thermal / voltage prediction 和报告输出。

## B3.1.5 Layered Schedule Metrics/Evaluator

日期：2026-05-20

已完成：
- 新增 `src/layered/evaluator.py`。
- 新增 `LayeredScheduleMetrics` 和 `LayeredScheduleEvaluator`。
- 评估 B3.1 `LayeredScheduleResult` 的 phase-level access/resource behavior。
- 支持 PTAP busy/utilization、FPP lane-seconds/utilization、DWR busy、capture busy、local execution、access overhead、phase parallelism、resource busy time 和 phase type time。
- 新增 `tests/test_layered_evaluator.py`。
- 新增 `experiments/demo_layered_schedule_metrics.py`，支持 `--output-dir`，默认写 `results/layered_schedule_metrics/`。

验证结果：
- `pytest tests/test_layered_evaluator.py`: 8 passed, 1 warning。
- `pytest`: 97 passed, 1 warning。
- `python experiments/demo_layered_schedule_metrics.py --output-dir tmp_layered_schedule_metrics_out`: passed。

历史临时输出（已在 Repository Cleanup 中删除）：
- `tmp_layered_schedule_metrics_out/metrics_summary.csv`

范围边界：
- B3.1.5 只评估 phase-level access/resource metrics。
- 未修改 A0 task-level schedulers 或 evaluator。
- 未修改 AccessPath 或 LayeredTask expander。
- 未实现 thermal / voltage prediction。
- 未实现完整 IEEE 1838 behavior framework。

下一步推荐：
B3.2/B3.3：将 phase-level schedule 接入 thermal / voltage prediction 和报告输出。

## B2.5 Output Path Robustness Fix

日期：2026-05-17

已完成：
- `experiments/demo_access_path_generation.py` 支持 `--output-dir`，默认仍写 `results/access_path/`。
- `experiments/demo_layered_task_expansion.py` 支持 `--output-dir`，默认仍写 `results/layered_expansion/`。
- `experiments/run_example_benchmark_workload.py` 支持 `--output-dir`，默认仍写 `results/benchmarks/example/`。
- 相关测试改为使用 pytest `tmp_path`，不依赖固定 `results/` 可写。
- 输出目录不存在时自动创建；创建失败时抛出包含目标目录的清晰错误。

验证结果：
- pytest: 81 passed, 1 warning。
- `python experiments/demo_access_path_generation.py --output-dir tmp_access_path_out`: passed。
- `python experiments/demo_layered_task_expansion.py --output-dir tmp_layered_out`: passed。
- `python experiments/run_example_benchmark_workload.py --output-dir tmp_benchmark_out`: passed。

历史临时输出（已在 Repository Cleanup 中删除）：
- `tmp_access_path_out/access_path_summary.csv`
- `tmp_layered_out/layered_task_summary.csv`
- `tmp_layered_out/execution_phase_summary.csv`
- `tmp_benchmark_out/benchmark_task_summary.csv`
- `tmp_benchmark_out/scheduler_metrics_summary.csv`
- `tmp_benchmark_out/serial_schedule.csv`
- `tmp_benchmark_out/greedy_schedule.csv`
- `tmp_benchmark_out/ptv_schedule.csv`

本任务未修改 scheduler 核心算法、evaluator、AccessPath 逻辑或 LayeredTask expansion 逻辑。

下一步推荐：
B3：Access-time-aware scheduler。

## Repository Cleanup

日期：2026-06-10

已完成：
- 删除 `tmp_*` 临时输出文件，正式实验结果仍保留在 `results/`。
- 移除冗余/合并后的 Markdown 文档引用，将结果说明和后续计划集中到 README、ROADMAP、STATUS、TODO、DECISIONS 和 EXPERIMENT_LOG。
- 新增 `.gitignore`，忽略 `__pycache__/`、`*.py[cod]`、`.pytest_cache/` 和 `tmp_*/`。

保留文件：
- `AGENTS.md`
- `README.md`
- `STATUS.md`
- `TODO.md`
- `ROADMAP.md`
- `DECISIONS.md`
- `EXPERIMENT_LOG.md`
- `benchmarks/schema.md`
- `docs/DESIGN_SPEC_1838_LAYERED_SCHEDULER.md`

未完成清理：
- 55 个已被 Git 跟踪的 `.pyc` 文件仍需从索引中移除；当前沙箱无法写 `.git/index.lock`，`git rm` 被权限限制阻止。
- `.pytest_cache/` 目录未被 Git 跟踪，但当前递归删除命令被权限审查超时阻止；已通过 `.gitignore` 防止后续纳入版本控制。

验证说明：
- 本次只清理文档、临时输出和忽略规则，未修改 Python 源码。
- 未运行 pytest 或 4-die 实验。

## Portable Project Export

日期：2026-06-10

已完成：
- 新建迁移目录 `portable_project/`。
- 复制核心源码、配置、实验脚本、测试、benchmark schema/example、正式 `results/` 输出、项目状态文件和设计规格。
- 排除 `.git/`、`.pytest_cache/`、`__pycache__/`、`.pyc` 和 `tmp_*` 临时输出。
- 更新 `.gitignore`，忽略 `portable_project*/`，避免导出目录被当作仓库内容提交。

验证结果：
- `portable_project/` 共复制 149 个文件。
- 导出目录中 `.pyc` 文件数为 0。
- 导出目录中 `__pycache__`、`.pytest_cache`、`tmp_*` 目录数为 0。

范围边界：
- 本次没有修改 Python 源码、调度算法、配置参数或实验结果。
- 未运行 pytest 或 4-die 实验。

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
- 下一步仍为 B3：Access-time-aware scheduler。


## B2 TestIntent to ExecutionPhase Layered Expander

日期：2026-05-17

已完成：
- 新增 `src/layered/intent.py`。
- 新增 `src/layered/phase.py`。
- 新增 `src/layered/expander.py`。
- 新增 `experiments/demo_layered_task_expansion.py`。
- 新增 `tests/test_layered_expander.py`。
- 实现 InternalScanIntent、BISTIntent、DWRExTestIntent、InstrumentAccessIntent、BypassIntent。
- 实现 ExecutionPhase 和 LayeredTask。
- 实现 BIST / scan / DWR EXTEST / instrument access / bypass 的 MVP phase expansion。

关键语义：
- BIST 被拆成 access、trigger、local run、re-access、readback。
- `LOCAL_BIST_RUN` 使用 `uses_ptap=False`，体现 BIST 本地执行不持续占用 PTAP。
- Scan 被拆成 config、FPP shift-in、capture、FPP shift-out、optional readback。
- DWR EXTEST 被拆成 wrapper config、DWR shift-in、capture、shift-out。
- Instrument access 目前是 simplified network access，后续可扩展 SIB hierarchical / daisy-chain network。

预期输出路径：
- `results/layered_expansion/layered_task_summary.csv`
- `results/layered_expansion/execution_phase_summary.csv`

当前验证说明：
- pytest: 81 passed, 1 warning。
- `python experiments/run_case_4die.py`: passed。
- `tests/test_layered_expander.py` 已在临时目录验证 demo 写出逻辑。
- 命令行运行 `python experiments/demo_layered_task_expansion.py` 时，当前沙箱拒绝创建 `results/layered_expansion/`，因此这些固定路径结果尚未落盘。
- `python experiments/run_example_benchmark_workload.py` 当前沙箱写 `results/benchmarks/example/benchmark_task_summary.csv` 被拒绝，未刷新结果。

当前限制：
- B2 不实现 phase scheduler。
- B2 没有把 ExecutionPhase 接入现有 A0 scheduler。
- B2 不是完整 IEEE 1838 behavior model。

下一步推荐：
B3：Access-time-aware scheduler。

