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
- [x] FPP lane sweep
- [ ] thermal limit sweep
- [ ] voltage limit sweep
- [ ] benchmark-derived workload 或 RTL mock workload
- [ ] 论文/组会最终版结果总结

## 最近完成任务

日期：2026-05-15

已完成：
- 完成 Serial / bandwidth_greedy / ptv_aware 三类 scheduler 的 MVP 实现。
- 完成 unified schedule evaluator。
- 完成 simplified shared-PDN voltage model。
- 完成 clean case_4die 与 stress case_4die_stress 验证。
- 固化当前 MVP 实验结论到 RESULTS.md。
- 新增 FPP lane sweep experiment。
- 生成 FPP lane sweep summary CSV 和五类 sweep plots。
- 增加 FPP lane sweep pytest 覆盖。
- 通过 pytest 测试。

测试结果：
- pytest: 36 passed, 1 warning

## FPP lane sweep 最新结果

输入：
- configs/case_4die_stress.yaml

扫描：
- fpp_lanes = [1, 2, 3, 4, 6, 8]

主要观察：
- Serial TAT 对 FPP lane 数不敏感，所有扫描点均为 0.0454 s。
- Bandwidth-greedy TAT 随 FPP lane 增加下降，从 1 lane 的 0.0318 s 降至 8 lanes 的 0.0066 s。
- Bandwidth-greedy peak IR-drop 随 FPP lane 增加上升，从 0.490625 V 增至 1.003125 V。
- Bandwidth-greedy violation count 不严格单调，因为更高并行度同时改变瞬时功耗和总执行时长；但所有扫描点均存在 voltage violation。
- PTV-aware 在所有扫描点保持 temperature_violation_count = 0 且 voltage_violation_count = 0。
- PTV-aware TAT 从 1 lane 的 0.0438 s 降至 2 lanes 的 0.0386 s，之后继续增加 FPP lane 基本没有收益，说明物理约束成为主要限制。

## 已生成文件

- results/sweeps/fpp_lanes/fpp_lane_sweep_summary.csv
- results/sweeps/fpp_lanes/tat_vs_fpp_lanes.svg
- results/sweeps/fpp_lanes/peak_ir_drop_vs_fpp_lanes.svg
- results/sweeps/fpp_lanes/peak_temperature_vs_fpp_lanes.svg
- results/sweeps/fpp_lanes/voltage_violations_vs_fpp_lanes.svg
- results/sweeps/fpp_lanes/temperature_violations_vs_fpp_lanes.svg

## 当前限制

- Thermal model 仍是 simplified per-die RC model。
- 尚未实现 die-to-die thermal coupling。
- Stress workload 与 FPP lane sweep 都是 mechanism validation，不是真实 benchmark。
- 尚未实现 benchmark-derived workload。
- 尚未实现 RTL mock validation。
- 尚未进行 HotSpot / 3D-ICE / industrial PDN validation。
- 尚未进行 thermal limit sweep 或 voltage limit sweep。

## 下一步任务

建议下一步进入：
- voltage limit sweep
- thermal limit sweep

保留后续方向：
- richer workload generation
- benchmark-derived workload
- RTL mock validation
- thermal coupling model improvement
