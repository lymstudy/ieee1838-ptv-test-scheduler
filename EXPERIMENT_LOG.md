# 实验日志 EXPERIMENT_LOG

## Experiment 001：Scaffold Sanity Check

日期：
2026-05-15

Commit：
待填写

运行命令：

```bash
pytest
python experiments/run_case_4die.py
```

实验目的：
验证配置加载、基础模型构造、thermal sanity model 和 voltage sanity model 是否可以正常运行。

输入配置：
- configs/case_4die.yaml
- configs/default_params.yaml

输出文件：
- results/case_4die/model_summary.csv
- results/case_4die/thermal_sanity.csv
- results/case_4die/voltage_sanity.csv
- results/case_4die/temperature_curve.svg
- results/case_4die/ir_drop_curve.svg

结果：
通过。

测试结果：
pytest: 4 passed

备注：
当前尚未实现调度算法，因此该实验只验证基础模型和 sanity traces。

## Experiment 002：Serial Baseline Scheduler

日期：
2026-05-15

Commit：
待填写

运行命令：

```bash
pytest
python experiments/run_case_4die.py
```

实验目的：
验证 common scheduler interface 和 Serial IEEE 1838-style baseline scheduler 是否可以正常调度 4-die case，并生成 serial schedule、metrics 和可视化结果。

输入配置：
- configs/case_4die.yaml
- configs/default_params.yaml

输出文件：
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

结果：
通过。

测试结果：
pytest: 8 passed, 1 warning

备注：
当前只实现 Serial baseline。该 baseline 按 die order、task type priority 和 task_id 确定性排序，所有 task 串行执行，不实现 Bandwidth-greedy、PTV-aware、参数扫描或三类调度器对比。

## Experiment 003：Bandwidth-Greedy Baseline Scheduler

日期：
2026-05-15

Commit：
待填写

运行命令：

```bash
pytest
python experiments/run_case_4die.py
```

实验目的：
验证 BandwidthGreedyScheduler 是否可以在只考虑 task readiness/dependency、FPP lane capacity、DWR segment conflict 和基础 access resource conflict 的前提下并行调度 4-die case，并生成 greedy schedule、metrics 和可视化结果。

输入配置：
- configs/case_4die.yaml
- configs/default_params.yaml

输出文件：
- results/case_4die/greedy_schedule.csv
- results/case_4die/greedy_metrics.csv
- results/case_4die/greedy_gantt.svg
- results/case_4die/greedy_temperature_curve.svg
- results/case_4die/greedy_ir_drop_curve.svg
- results/case_4die/scheduler_metrics_summary.csv

结果：
通过。

测试结果：
pytest: 13 passed, 1 warning

备注：
Bandwidth-greedy baseline 不考虑 thermal/voltage 约束，不实现 capture staggering，也不插入 dummy cycle。thermal 和 IR drop 只在调度完成后用于计算 trace、peak value 和 violation count。
## Experiment 004：Model Consistency Check

日期：
2026-05-15

Commit：
待填写

运行命令：

```bash
pytest
python experiments/run_case_4die.py
```

实验目的：
在进入 PTV-aware scheduler 前，检查 Bandwidth-greedy baseline 的资源占用逻辑和 serial/greedy metrics summary 是否一致。

检查内容：
- greedy TAT 小于或等于 serial TAT。
- greedy 每个 task 只出现一次。
- greedy 未超过 FPP lane capacity。
- greedy 不存在同一 DWR segment overlap。
- scheduler_metrics_summary.csv 包含 serial_ieee1838_style 和 bandwidth_greedy 两行。

结果：
通过。

测试结果：
pytest: 13 passed, 1 warning

备注：
本次只做模型一致性检查和建模决策记录，不实现 PTV-aware scheduler。