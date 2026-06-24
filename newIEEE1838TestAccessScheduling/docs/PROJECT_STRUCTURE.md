# 项目目录结构

本项目采用少目录、强分区的组织方式。目录存在不代表当前阶段已经实现对应功能。

```text
newIEEE1838TestAccessScheduling/
  assets/                 # 图、PDF、流程图等静态资料
  configs/
    cases/                # 可复现实验输入案例
  data/
    raw/                  # 原始外部数据或手工提取 benchmark 资料
    derived/              # 清洗、转换后的派生数据
  docs/
    model/                # 模型、输入格式、约束定义
    paper/                # 摘要、论文初稿、图表清单
  experiments/            # 可重复运行的实验入口
  results/
    figures/              # 正式图
    tables/               # 正式 CSV/表格
    schedules/            # 调度时序输出
    reports/              # 实验报告、审计报告
  src/
    model/                # IEEE 1838 可计算模型与输入解析
    recipes/              # Test Access Recipe 生成
    schedulers/           # 贪心、CP-SAT、ALNS 等调度器
    evaluators/           # 资源、电热、调度结果评估
    visualization/        # 甘特图、曲线、论文图生成
  tests/                  # 单元测试和回归测试
```

## 分区原则

- `configs/cases/` 是后续算法的主输入来源，不直接把实验参数写死在代码里。
- `src/model/` 先承接 M1 阶段的 IEEE 1838 结构对象；后续代码应从这里读取统一模型。
- `src/recipes/` 只负责从模型生成候选 Test Access Recipe，不负责全局调度。
- `src/schedulers/` 只负责选择 recipe 和安排时间，不直接散落输入解析逻辑。
- `src/evaluators/` 统一计算 TAT、资源利用率、功耗、温度、违规次数等指标。
- `results/` 只保存正式输出；调试临时产物不放入这里。

## 当前阶段产物

- M1 模型说明：`docs/model/M1_COMPUTABLE_IEEE1838_MODEL.md`
- M1 输入样例：`configs/cases/3d_stack_m1_example.json`
- M2 recipe 说明：`docs/model/M2_TEST_ACCESS_RECIPE.md`
- M2 生成脚本：`experiments/generate_m2_recipes.py`
- M2 默认输出：`results/tables/m2_recipe_summary_refined.csv` 和 `results/tables/m2_recipe_phase_summary.csv`
- M3 剪枝说明：`docs/model/M3_PARETO_PRUNING.md`
- M3 剪枝脚本：`experiments/run_m3_pareto_pruning.py`
- M3 默认输出：`results/tables/m3_recipe_pareto.csv` 和 `results/reports/m3_pruning_report.md`
- M4 调度器说明：`docs/model/M4_GREEDY_SCHEDULER.md`
- M4 调度脚本：`experiments/run_m4_greedy_scheduler.py`
- M4 默认输出：`results/schedules/m4_greedy_schedule.csv` 和 `results/reports/m4_greedy_schedule_report.md`
- M5 精修说明：`docs/model/M5_REFINEMENT_SCHEDULER.md`
- M5 精修脚本：`experiments/run_m5_refinement_scheduler.py`
- M5 默认输出：`results/schedules/m5_refined_schedule.csv` 和 `results/reports/m5_refinement_report.md`
- M6 ALNS 说明：`docs/model/M6_ALNS_SCHEDULER.md`
- M6 ALNS 脚本：`experiments/run_m6_alns_scheduler.py`
- M6 默认输出：`results/schedules/m6_alns_schedule.csv`、`results/tables/m6_alns_convergence.csv` 和 `results/reports/m6_alns_report.md`
- M7 热代理说明：`docs/model/M7_THERMAL_PROXY.md`
- M7 热评估脚本：`experiments/run_m7_thermal_evaluation.py`
- M7 默认输出：`results/tables/m7_temperature_trace.csv`、`results/tables/m7_hotspots.csv`、`results/tables/m7_thermal_summary.csv` 和 `results/reports/m7_thermal_report.md`
- M8 对比实验说明：`docs/model/M8_BASELINE_COMPARISON.md`
- M8 对比实验脚本：`experiments/run_m8_baseline_comparison.py`
- M8 默认输出：`results/tables/m8_baseline_comparison.csv`、`results/tables/m8_temperature_trace.csv`、`results/tables/m8_hotspots.csv`、`results/tables/m8_thermal_summary.csv` 和 `results/reports/m8_baseline_comparison_report.md`
- M9 场景扩展说明：`docs/model/M9_SCENARIO_EXPANSION.md`
- M9 真实数据收集计划：`docs/data/M9_DATA_COLLECTION_PLAN.md`
- M9 数据溯源台账：`docs/data/M9_DATA_PROVENANCE.md`

## M9 Scenario Expansion Artifacts

- ITC'02 parser: `src/model/itc02.py`
- M9 case generator: `experiments/generate_m9_cases.py`
- M9 scenario comparison runner: `experiments/run_m9_scenario_suite.py`
- M9 generated cases: `configs/cases/2_5d_interposer_m9_public.json` and `configs/cases/5_5d_multi_tower_m9_public.json`
- M9 derived data: `data/derived/m9_itc02_module_summary.csv`
- M9 outputs: `results/tables/m9_scenario_comparison.csv` and `results/reports/m9_scenario_expansion_report.md`

## M10 Benchmark Suite Artifacts

- M10 benchmark suite docs: `docs/model/M10_BENCHMARK_SUITE.md`
- M10 case generator: `experiments/generate_m10_benchmark_suite.py`
- M10 sweep runner: `experiments/run_m10_benchmark_sweep.py`
- M10 generated cases: `configs/cases/m10/`
- M10 manifest: `data/derived/m10_benchmark_suite_manifest.csv`
- M10 outputs: `results/tables/m10_benchmark_sweep.csv` and `results/reports/m10_benchmark_sweep_report.md`

## M11 Algorithm Study Artifacts

- M11 algorithm study docs: `docs/model/M11_ALGORITHM_STUDY.md`
- M11 algorithm study runner: `experiments/run_m11_algorithm_study.py`
- M11 outputs: `results/tables/m11_algorithm_comparison.csv` and `results/reports/m11_algorithm_study_report.md`
