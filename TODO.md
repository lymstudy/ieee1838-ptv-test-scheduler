# TODO

## 已完成任务

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
- [x] 新增 RESULTS.md。
- [x] 在 README.md 中链接 RESULTS.md。
- [x] 完成 MVP result consolidation。
- [x] FPP lane sweep。
- [x] 新增 FPP lane sweep plots。
- [x] 新增 FPP lane sweep tests。

## 下一阶段任务

- [ ] thermal limit sweep。
- [ ] voltage limit sweep。
- [ ] richer workload generation。
- [ ] 生成论文/组会可用的结果表格。
- [ ] 生成论文/组会可用的图表版本。
- [ ] 构造 benchmark-derived workload。
- [ ] 构造 small RTL mock validation。
- [ ] 对 stress workload 尝试更明确触发 dummy cycle 的独立配置或机制测试。

## 参数扫描任务

- [x] FPP lane sweep。
- [ ] thermal limit sweep。
- [ ] voltage limit sweep。
- [ ] die count sweep。
- [ ] task规模 sweep。

## 模型改进任务

- [ ] thermal coupling model。
- [ ] 改进 IR drop model，加入 PDN matrix 或更细粒度供电模型。
- [ ] benchmark-derived workload。
- [ ] RTL mock validation。
- [ ] 准备论文 method section。
- [ ] 准备组会 PPT 图表。
