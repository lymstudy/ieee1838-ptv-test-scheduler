# 项目状态 STATUS

## 当前里程碑

MVP：4-die IEEE 1838-style PTV-aware test scheduling prototype。

## 当前阶段进度

- [x] 仓库脚手架与基础模型
- [x] 通用 Scheduler 接口
- [x] Serial IEEE 1838 baseline scheduler
- [x] Bandwidth-greedy baseline scheduler
- [ ] PTV-aware scheduler
- [ ] 三类调度器对比图表
- [ ] 参数扫描实验
- [ ] 论文/组会可用结果总结

## 最近完成任务

日期：2026-05-15

已完成：
- 创建项目基础目录结构。
- 实现配置文件加载。
- 实现 stack、task、access、thermal、voltage 等基础模型。
- 实现基础 sanity experiment。
- 定义 common scheduler interface。
- 实现 Serial IEEE 1838-style baseline scheduler。
- 实现 Bandwidth-greedy baseline scheduler。
- 在 4-die experiment 中同时运行 SerialScheduler 和 BandwidthGreedyScheduler。
- 生成 serial 与 greedy 的 schedule、metrics、Gantt、temperature curve 和 IR drop curve。
- 生成 scheduler_metrics_summary.csv。
- 完成 Bandwidth-greedy 资源占用一致性检查。
- 增加 greedy scheduler 测试。
- 通过 pytest 测试。

测试结果：
- pytest: 13 passed, 1 warning

已生成文件：
- results/case_4die/model_summary.csv
- results/case_4die/thermal_sanity.csv
- results/case_4die/voltage_sanity.csv
- results/case_4die/temperature_curve.svg
- results/case_4die/ir_drop_curve.svg
- results/case_4die/serial_schedule.csv
- results/case_4die/serial_metrics.csv
- results/case_4die/serial_gantt.svg
- results/case_4die/serial_temperature_curve.svg
- results/case_4die/serial_ir_drop_curve.svg
- results/case_4die/greedy_schedule.csv
- results/case_4die/greedy_metrics.csv
- results/case_4die/greedy_gantt.svg
- results/case_4die/greedy_temperature_curve.svg
- results/case_4die/greedy_ir_drop_curve.svg
- results/case_4die/scheduler_metrics_summary.csv

## 模型一致性检查

- greedy TAT 小于 serial TAT。
- greedy 每个 task 只出现一次。
- greedy 未超过 FPP lane capacity。
- greedy 不存在同一 DWR segment overlap。
- scheduler_metrics_summary.csv 包含 serial_ieee1838_style 和 bandwidth_greedy 两行。

## 当前限制

- 尚未实现 PTV-aware scheduler。
- 尚未实现 thermal/voltage-aware 调度约束。
- 尚未实现 capture staggering。
- 尚未实现 dummy cycle insertion。
- 尚未生成三类 scheduler 的最终 comparison plots。
- Bandwidth-greedy baseline 不在调度过程中避免 thermal 或 voltage violation，只在调度后计算指标。
- 当前 thermal 和 voltage model 仍是 sanity-level 简化模型。

## 下一步任务

实现 PTV-aware scheduler。

预期输出：
- results/case_4die/ptv_schedule.csv
- results/case_4die/ptv_metrics.csv
- results/case_4die/ptv_gantt.svg
- results/case_4die/ptv_temperature_curve.svg
- results/case_4die/ptv_ir_drop_curve.svg
- 三类 scheduler 的 comparison plots
