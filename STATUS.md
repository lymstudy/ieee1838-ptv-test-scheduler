# 项目状态 STATUS

## 当前里程碑

MVP：IEEE 1838-style PTV-aware test scheduling prototype。

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
- [ ] 真实公开 benchmark statistics 接入
- [ ] RTL mock validation
- [ ] 论文/组会最终版结果总结

## 最近完成任务

日期：2026-05-15

已完成：
- 新增 benchmark-derived workload statistics schema。
- 新增 example benchmark statistics YAML。
- 新增 benchmark workload adapter，将统计字段转换为 scheduler-compatible tasks。
- 新增 example benchmark workload experiment。
- 生成 example benchmark task summary、三类 schedule、Gantt chart 和 comparison plots。
- 增加 benchmark adapter pytest 覆盖。
- 通过 pytest 测试。

测试结果：
- pytest: 68 passed, 1 warning

## Example benchmark workload 最新结果

输入：
- benchmarks/example_benchmark_stats.yaml

性质：
- schema-level validation。
- 不是 RTL parser。
- 不是真实 benchmark 结论。

主要观察：
- adapter 生成 21 个 abstract test tasks。
- task set 包含 scan shift、scan capture、BIST、instrument access 和 DWR EXTEST。
- capture task 使用 is_capture_phase=True。
- scan / capture duration 从 scan_chain_length 和 scan_chain_count 派生。
- DWR EXTEST duration 从 dwr_length 派生。
- Serial、Bandwidth-greedy、PTV-aware 三类 scheduler 均可消费该 workload。

Example scheduler metrics：
- serial_ieee1838_style: TAT = 0.065206 s, peak IR-drop = 0.105000 V, voltage violation = 0。
- bandwidth_greedy: TAT = 0.043492 s, peak IR-drop = 0.565625 V, voltage violation = 26。
- ptv_aware: TAT = 0.042852 s, peak IR-drop = 0.183750 V, voltage violation = 0。

## 已生成文件

- benchmarks/schema.md
- benchmarks/example_benchmark_stats.yaml
- src/workload/benchmark_adapter.py
- experiments/run_example_benchmark_workload.py
- results/benchmarks/example/benchmark_task_summary.csv
- results/benchmarks/example/serial_schedule.csv
- results/benchmarks/example/greedy_schedule.csv
- results/benchmarks/example/ptv_schedule.csv
- results/benchmarks/example/scheduler_metrics_summary.csv
- results/benchmarks/example/serial_gantt.svg
- results/benchmarks/example/greedy_gantt.svg
- results/benchmarks/example/ptv_gantt.svg
- results/benchmarks/example/tat_comparison.svg
- results/benchmarks/example/peak_ir_drop_comparison.svg
- results/benchmarks/example/peak_temperature_comparison.svg

## 当前限制

- benchmark adapter 当前只接收统计 YAML，不解析 Verilog 或 gate-level netlist。
- example benchmark workload 是 schema validation，不是真实 benchmark validation。
- 尚未接入真实公开 benchmark statistics。
- 尚未实现 RTL mock validation。
- Thermal model 仍是 simplified per-die RC model，尚未实现 die-to-die thermal coupling。
- Voltage model 仍是 simplified shared-PDN model，尚未实现 PDN matrix 或工业级验证。
- 未引入 HotSpot、3D-ICE、RedHawk、Voltus 或 Tessent SSN。

## 下一步任务

建议下一步进入：
- 真实公开 benchmark statistics 接入
- RTL mock validation

保留后续方向：
- thermal coupling model improvement
- PDN matrix model improvement
- 论文/组会图表整理
