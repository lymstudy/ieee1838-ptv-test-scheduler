# TODO

## A0 已完成任务

- [x] 定义 common scheduler interface。
- [x] 实现 ScheduleEntry dataclass。
- [x] 实现 ScheduleResult dataclass。
- [x] 实现 BaseScheduler 抽象类。
- [x] 实现 SerialScheduler。
- [x] 实现 BandwidthGreedyScheduler。
- [x] 实现 PTVAwareScheduler。
- [x] 加入 thermal constraint。
- [x] 加入 voltage constraint。
- [x] 加入 capture staggering。
- [x] 加入 dummy cycle insertion。
- [x] 生成三类 scheduler 对比图。
- [x] 新增 4-die stress workload。
- [x] 新增 stress workload experiment runner。
- [x] 增加 stress workload 测试。
- [x] 修复 schedule-based physical evaluator。
- [x] 统一 Serial / Bandwidth-greedy / PTV-aware 的 metrics evaluation。
- [x] 增加 MVP shared-PDN IR-drop mode。
- [x] 增加 serial-vs-parallel evaluator 一致性测试。
- [x] 将 A0 结果说明合并到 README / EXPERIMENT_LOG / results artifacts。
- [x] 完成 MVP result consolidation。
- [x] FPP lane sweep。
- [x] voltage limit sweep。
- [x] thermal limit sweep。
- [x] richer workload generation。
- [x] workload scale sweep。
- [x] 新增 synthetic workload generator tests。
- [x] 新增 workload scale sweep tests。
- [x] benchmark workload statistics schema。
- [x] example benchmark stats YAML。
- [x] benchmark workload adapter。
- [x] example benchmark workload experiment。
- [x] benchmark adapter tests。
- [x] A0 原型冻结。

## B0 已完成任务

- [x] IEEE 1838-aware layered scheduler design spec。
- [x] Next phase plan consolidated into ROADMAP。
- [x] A0/B 阶段路线图更新。
- [x] B 阶段研究决策记录。

## B 阶段立即任务

- [x] AccessPath model。
- [x] AccessPath generator。
- [x] AccessPath cost estimator。
- [x] TestIntent model。
- [ ] AccessOp model。
- [x] ExecutionPhase model。
- [x] LayeredTask model。
- [x] Layered task expander。
- [x] Access path examples tracked through generated CSV and ROADMAP/STATUS notes。
- [x] B2.5 output-dir robustness / demo output path support。
- [x] B3.1 ExecutionPhase-level access-time-aware scheduler prototype。
- [x] B3.1.5 layered schedule metrics/evaluator。
- [x] `tests/test_layered_evaluator.py`。
- [x] `experiments/demo_layered_schedule_metrics.py`。
- [x] `tests/test_layered_scheduler.py`。
- [x] `experiments/demo_access_time_scheduler.py`。
- [x] `tests/test_access_path_generator.py`。

## B 阶段后续任务

- [ ] Access-time-aware scheduler。
- [ ] B3.2 phase-level thermal / voltage prediction integration。
- [ ] B3.3 phase-level schedule reporting and physical trace integration。
- [ ] Predictive path-blocking-aware scheduler。
- [ ] Rolling-horizon / MPC-style scheduler prototype。
- [ ] asymmetric voltage matrix。
- [ ] thermal coupling model。
- [ ] ablation study。
- [ ] MILP small optimal baseline。
- [ ] RTL mock validation。
- [ ] public benchmark-derived statistics case。
- [ ] benchmark example schedule audit。
- [ ] realistic UART statistics case。
- [ ] realistic UART workload experiment。
- [ ] realistic UART schedule audit。
- [ ] realistic UART workload tests。
- [ ] benchmark-derived workload 与 synthetic workload 的结果表格对齐。
- [ ] 生成论文/组会可用的结果表格。
- [ ] 生成论文/组会可用的图表版本。

## 保留任务

- [ ] 真实公开 benchmark statistics 接入。
- [ ] RTL mock validation。
- [ ] die count sweep with alternative access assumptions。
- [ ] task规模 sweep with alternative workload mixes。
- [ ] 对 stress workload 尝试更明确触发 dummy cycle 的独立配置或机制测试。
- [ ] 改进 IR drop model，加入 PDN matrix 或更细粒度供电模型。
- [ ] 准备论文 method section。
- [ ] 准备组会 PPT 图表。

## B0 补充规划已完成

- [x] Frontier Idea Integration Plan consolidated into ROADMAP / TODO / DECISIONS。
- [x] DESIGN_SPEC frontier addendum。
- [x] ROADMAP frontier future milestones。
- [x] DECISIONS frontier terminology / claim boundaries。

## Repository Cleanup

- [x] Delete `tmp_*` temporary output files.
- [x] Add `.gitignore` for Python caches, pytest cache, and `tmp_*` outputs.
- [x] Remove stale README/ROADMAP/STATUS references to deleted Markdown files.
- [x] Create `portable_project/` clean migration copy.
- [ ] Remove already tracked `.pyc` files from Git index when `.git` write permission is available.
- [ ] Delete local `.pytest_cache/` directory when recursive deletion is available.

## B 阶段后排 Frontier 任务

- [ ] SSN-inspired TAM abstraction。
- [ ] FPP/SSN co-allocation。
- [ ] PowerPillar-aware capture staggering。
- [ ] PackageProfile model。
- [ ] external health event interface。
- [ ] interposer test-bus routing model。
- [ ] health-event safe mode pseudocode refinement。
- [ ] FPP hardware cost model。
- [ ] optional FPGA schedule playback planning。
- [ ] optional tool correlation planning。

