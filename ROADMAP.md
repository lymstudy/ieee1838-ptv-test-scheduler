# 项目路线图 ROADMAP

## Milestone 0：仓库脚手架与基础模型

目标：
建立项目结构、配置加载、基础 stack/task/access/thermal/voltage 模型。

状态：
已完成。

主要产出：
- YAML 配置加载
- 基础模型对象
- thermal sanity trace
- voltage sanity trace
- 基础 sanity plots

## Milestone 1：Serial Baseline

目标：
实现 deterministic serial IEEE 1838-style baseline scheduler。

状态：
已完成。

预期产出：
- serial_schedule.csv
- serial_metrics.csv
- serial_gantt.svg
- serial_temperature_curve.svg
- serial_ir_drop_curve.svg

验收标准：
- 每个 task 被调度且只被调度一次。
- 所有 task 串行执行，不存在 overlap。
- TAT 等于最后一个 task 的 end_time。
- pytest 全部通过。

## Milestone 2：Bandwidth-Greedy Baseline

状态：
已完成。

目标：
实现只考虑访问资源和 FPP lane 约束、但不考虑 thermal/voltage 的激进并行调度器。

预期观察：
- TAT 相比 serial baseline 明显降低。
- peak temperature 和 peak IR drop 可能升高。
- 可能出现 thermal 或 voltage violation。

## Milestone 3：PTV-Aware Scheduler

状态：
已完成。

目标：
实现 power-, thermal-, and voltage-aware scheduler。

机制：
- 访问路径约束
- FPP lane 约束
- DWR segment 冲突约束
- thermal constraint
- IR drop constraint
- capture staggering
- dummy cycle insertion

预期观察：
- TAT 低于 serial baseline。
- peak temperature 和 peak IR drop 低于 bandwidth-greedy。
- violation count 尽可能为 0。

## Milestone 4：结果对比与可视化

状态：
基础 MVP 图表已完成。

目标：
生成论文/组会可用图表。

需要生成：
- Gantt chart
- TAT comparison
- peak temperature comparison
- peak IR drop comparison
- temperature curves
- IR drop curves
- scheduler metrics summary

## Milestone 5：参数扫描实验

目标：
验证算法对不同参数的敏感性和可扩展性。

扫描参数：
- FPP lane count
- thermal limit Tmax
- voltage drop limit
- die count
- task规模

## Milestone 6：Benchmark-derived Workload and RTL Mock Validation

目标：
将调度器输入从纯 synthetic task 扩展为由公开 RTL benchmark 或 small RTL mock stack 派生的 task set。

预期产出：
- benchmark_workload.csv
- rtl_mock_4die_stack.v
- VCD toggle statistics
- benchmark-derived scheduling results
- synthetic vs benchmark workload comparison

验收标准：
- workload 参数不再完全手工设定
- scan duration 与 FF/scan chain 数相关
- power 与 toggle activity 相关
- 调度结果可复现
## Milestone 4A：Stress Workload Mechanism Validation

状态：
已完成。

目标：
在原始 clean 4-die MVP case 之外，新增 synthetic stress workload，用于验证 PTV-aware scheduler 的 thermal constraint、IR drop constraint 和 capture staggering 机制是否生效。

主要产出：
- configs/case_4die_stress.yaml
- experiments/run_case_4die_stress.py
- results/case_4die_stress/scheduler_metrics_summary.csv
- results/case_4die_stress/serial_schedule.csv
- results/case_4die_stress/greedy_schedule.csv
- results/case_4die_stress/ptv_schedule.csv
- results/case_4die_stress/tat_comparison.svg
- results/case_4die_stress/peak_temperature_comparison.svg
- results/case_4die_stress/peak_ir_drop_comparison.svg

观察：
- bandwidth_greedy 在 stress case 中出现 thermal / voltage violation。
- ptv_aware 在 stress case 中降低 violation count。
- capture staggering 生效。
- dummy cycle insertion 框架未在该 stress case 中触发，仍由 synthetic unit test 覆盖。
