# 项目状态 STATUS

## 当前里程碑

MVP：4-die IEEE 1838-style PTV-aware test scheduling prototype。

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
- [ ] 参数扫描实验
- [ ] benchmark-derived workload 或 RTL mock workload
- [ ] 论文/组会最终版结果总结

## 最近完成任务

日期：2026-05-15

已完成：
- 完成 Serial / bandwidth_greedy / ptv_aware 三类 scheduler 的 MVP 实现。
- 完成 unified schedule evaluator。
- 完成 simplified shared-PDN voltage model。
- 完成 clean case_4die 与 stress case_4die_stress 验证。
- 新增 RESULTS.md 固化当前 MVP 实验结论。
- 更新 README.md，链接 RESULTS.md。
- 通过 pytest 测试。

测试结果：
- pytest: 31 passed, 1 warning

## Clean 4-die MVP case 最新结果

- serial TAT = 0.0106 s
- bandwidth_greedy TAT = 0.0040 s
- ptv_aware TAT = 0.0054 s
- serial peak_ir_drop = 0.034875 V
- bandwidth_greedy peak_ir_drop = 0.0928125 V
- ptv_aware peak_ir_drop = 0.0675 V
- bandwidth_greedy voltage_violation_count = 4
- ptv_aware voltage_violation_count = 0

## Stress workload 最新结果

- serial TAT = 0.0454 s
- bandwidth_greedy TAT = 0.0168 s
- ptv_aware TAT = 0.0386 s
- serial peak_temperature = 26.2233591261 C
- bandwidth_greedy peak_temperature = 26.4709087381 C
- ptv_aware peak_temperature = 25.8033739302 C
- serial peak_ir_drop = 0.1125 V
- bandwidth_greedy peak_ir_drop = 0.571875 V
- ptv_aware peak_ir_drop = 0.159375 V
- bandwidth_greedy temperature_violation_count = 48
- bandwidth_greedy voltage_violation_count = 71
- ptv_aware temperature_violation_count = 0
- ptv_aware voltage_violation_count = 0

## 当前结论

PTV-aware scheduler 的目标不是总是最小化 raw TAT，而是在保持明显短于 serial baseline 的 TAT 的同时，降低 thermal / voltage constraint violations。

当前 MVP mechanism validation 已完成。详细结果见 RESULTS.md。

## 当前限制

- Thermal model 仍是 simplified per-die RC model。
- 尚未实现 die-to-die thermal coupling。
- Stress workload 是 mechanism validation，不是真实 benchmark。
- 尚未实现 benchmark-derived workload。
- 尚未实现 RTL mock validation。
- 尚未进行 HotSpot / 3D-ICE / industrial PDN validation。
- 尚未进行参数扫描。

## 下一步任务

建议下一步进入：
- richer workload generation
- FPP lane sweep
- thermal limit sweep
- voltage limit sweep
- benchmark-derived workload
- RTL mock validation
- thermal coupling model improvement
