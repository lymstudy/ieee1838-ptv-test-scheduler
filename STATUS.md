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
- [x] benchmark example schedule audit
- [x] realistic benchmark statistics case
- [ ] 真实公开 benchmark statistics 接入
- [ ] RTL mock validation
- [ ] 论文/组会最终版结果总结

## 最近完成任务

日期：2026-05-15

已完成：
- 新增 manually specified realistic UART statistics case。
- 新增 realistic UART workload experiment。
- 新增 realistic UART schedule audit。
- 使用 benchmark_adapter 从 circuit-level statistics 派生 task duration 和 power。
- 生成 realistic UART 的 task summary、三类 schedule、Gantt chart、comparison plots 和 audit 文件。
- 增加 realistic UART pytest 覆盖。
- 未修改 scheduler 核心算法。

测试结果：
- pytest: 81 passed, 1 warning

## Realistic UART 最新结果

输入：
- benchmarks/realistic_uart_stats.yaml

性质：
- manually specified realistic statistics case。
- 不是 RTL parser 自动提取结果。
- 不是真实芯片验证。

主要观察：
- adapter 生成 21 个 abstract test tasks。
- task set 包含 scan shift、scan capture、BIST、instrument access 和 DWR EXTEST。
- bandwidth_greedy: TAT = 0.002128 s, peak IR-drop = 0.360000 V, voltage violation = 17。
- ptv_aware: TAT = 0.007661 s, peak IR-drop = 0.074000 V, voltage violation = 0。
- serial_ieee1838_style: TAT = 0.010149 s, peak IR-drop = 0.066000 V, voltage violation = 0。
- audit 未发现 scheduler bug。
- Greedy 与 PTV-aware 均无 FPP capacity violation 和 DWR overlap。
- PTV-aware 比 greedy 慢，但降低 voltage violation；这是物理约束调度的预期 tradeoff。

## 已生成文件

- benchmarks/realistic_uart_stats.yaml
- experiments/run_realistic_uart_workload.py
- experiments/audit_realistic_uart_schedule.py
- tests/test_realistic_uart_workload.py
- results/benchmarks/realistic_uart/benchmark_task_summary.csv
- results/benchmarks/realistic_uart/serial_schedule.csv
- results/benchmarks/realistic_uart/greedy_schedule.csv
- results/benchmarks/realistic_uart/ptv_schedule.csv
- results/benchmarks/realistic_uart/scheduler_metrics_summary.csv
- results/benchmarks/realistic_uart/serial_gantt.svg
- results/benchmarks/realistic_uart/greedy_gantt.svg
- results/benchmarks/realistic_uart/ptv_gantt.svg
- results/benchmarks/realistic_uart/tat_comparison.svg
- results/benchmarks/realistic_uart/peak_ir_drop_comparison.svg
- results/benchmarks/realistic_uart/peak_temperature_comparison.svg
- results/benchmarks/realistic_uart/audit/greedy_schedule_audit.csv
- results/benchmarks/realistic_uart/audit/ptv_schedule_audit.csv
- results/benchmarks/realistic_uart/audit/schedule_comparison_audit.md

## 当前限制

- realistic UART case 是 manually specified statistics case，不是 RTL-extracted benchmark。
- 尚未接入真实公开 benchmark statistics。
- 尚未实现 RTL parser 或 RTL mock validation。
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
