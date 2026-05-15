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
