# TODO

## 立即任务

- [x] 定义 common scheduler interface。
- [x] 实现 ScheduleEntry dataclass。
- [x] 实现 ScheduleResult dataclass。
- [x] 实现 BaseScheduler 抽象类。
- [x] 实现 SerialScheduler。
- [x] 生成 serial_schedule.csv。
- [x] 生成 serial_metrics.csv。
- [x] 生成 serial_gantt.svg。
- [x] 生成 serial_temperature_curve.svg。
- [x] 生成 serial_ir_drop_curve.svg。
- [x] 增加 serial scheduler 测试。
- [x] 实现 BandwidthGreedyScheduler。
- [x] 增加 scheduler comparison metrics。
- [x] 生成 greedy_schedule.csv。
- [x] 生成 greedy_metrics.csv。
- [x] 生成 greedy_gantt.svg。
- [x] 生成 greedy_temperature_curve.svg。
- [x] 生成 greedy_ir_drop_curve.svg。
- [x] 增加 greedy scheduler 测试。
- [x] 完成 Bandwidth-greedy 资源一致性检查。

## 下一阶段任务

- [ ] 实现 PTVAwareScheduler。
- [ ] 加入 thermal constraint。
- [ ] 加入 voltage constraint。
- [ ] 加入 capture staggering。
- [ ] 加入 dummy cycle insertion。
- [ ] 生成三类 scheduler 对比图。

## 后续任务

- [ ] 增加 FPP lane sweep。
- [ ] 增加 thermal limit sweep。
- [ ] 增加 voltage limit sweep。
- [ ] 增加更大 die count case。
- [ ] 改进 thermal model。
- [ ] 改进 IR drop model。
- [ ] 准备论文 method section。
- [ ] 准备组会 PPT 图表。
