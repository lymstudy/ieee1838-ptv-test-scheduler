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

目标：
实现只考虑访问资源和 FPP lane 约束、但不考虑 thermal/voltage 的激进并行调度器。

预期观察：
- TAT 相比 serial baseline 明显降低。
- peak temperature 和 peak IR drop 可能升高。
- 可能出现 thermal 或 voltage violation。

## Milestone 3：PTV-Aware Scheduler

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
