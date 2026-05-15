# 项目状态 STATUS

## 当前里程碑

MVP：4-die IEEE 1838-style PTV-aware test scheduling prototype。

## 当前阶段进度

- [x] 仓库脚手架与基础模型
- [ ] 通用 Scheduler 接口
- [ ] Serial IEEE 1838 baseline scheduler
- [ ] Bandwidth-greedy baseline scheduler
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
- 通过 pytest 测试。

测试结果：
- pytest: 4 passed

已生成文件：
- results/case_4die/model_summary.csv
- results/case_4die/thermal_sanity.csv
- results/case_4die/voltage_sanity.csv
- results/case_4die/temperature_curve.svg
- results/case_4die/ir_drop_curve.svg

## 当前限制

- 尚未实现任何调度算法。
- 尚未生成 schedule table。
- 尚未生成 Gantt chart。
- 尚未生成 TAT comparison。
- 尚未生成 peak temperature comparison。
- 尚未生成 peak IR drop comparison。
- 当前 thermal 和 voltage model 仍是 sanity-level 简化模型。

## 下一步任务

实现 common scheduler interface 和 Serial IEEE 1838 baseline scheduler。

预期输出：
- results/case_4die/serial_schedule.csv
- results/case_4die/serial_metrics.csv
- results/case_4die/serial_gantt.svg
- results/case_4die/serial_temperature_curve.svg
- results/case_4die/serial_ir_drop_curve.svg
