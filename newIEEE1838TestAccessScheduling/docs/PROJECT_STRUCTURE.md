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
- `src/model/` 先承接 M1 阶段的 IEEE 1838 结构对象及可选组件（如 FPP，IEEE 1838-2019 Clause 7）；后续代码应从这里读取统一模型。
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

## M12 Thermal Validation Artifacts

- M12 thermal validation docs: `docs/model/M12_THERMAL_VALIDATION.md`
- M12 thermal validation runner: `experiments/run_m12_thermal_validation.py`
- HotSpot-compatible exporter: `src/evaluators/hotspot_export.py`
- M12 outputs: `results/tables/m12_thermal_validation_summary.csv`, `results/tables/m12_thermal_hotspots.csv`, `results/tables/m12_temperature_trace.csv`, and `results/reports/m12_thermal_validation_report.md`
- M12 HotSpot inputs: `results/hotspot/m12/` and `results/hotspot/m12_hotspot_export_manifest.csv`

## M12b HotSpot Remote Validation Artifacts

- M12b HotSpot validation docs: `docs/model/M12B_HOTSPOT_VALIDATION.md`
- M12b remote validation runner: `experiments/run_m12_hotspot_remote_validation.py`
- M12b outputs: `results/tables/m12_hotspot_validation_summary.csv` and `results/reports/m12_hotspot_validation_report.md`
- M12b pulled HotSpot outputs: `results/hotspot/m12b_outputs/`

## M13 Visualization Artifacts

- M13 visualization docs: `docs/model/M13_VISUALIZATION_SUMMARY.md`
- M13 visualization runner: `experiments/generate_m13_visualizations.py`
- M13 figures: `results/figures/m13/`
- M13 figure index: `results/tables/m13_figure_index.csv`
- M13 report: `results/reports/m13_visual_summary.md`

## M14 Paper Experiment Draft Artifacts

- M14 experiment chapter docs: `docs/model/M14_EXPERIMENT_CHAPTER_DRAFT.md`
- M14 experiment chapter runner: `experiments/generate_m14_experiment_chapter.py`
- M14 draft report: `results/reports/m14_experiment_chapter_draft.md`
- M14 artifact index: `results/tables/m14_experiment_artifact_index.csv`
- Scope: narrative and table/figure explanation only; do not rerun experiments unless a gap is found.

## M15 Chinese Experiment Chapter Artifacts

- M15 Chinese chapter docs: `docs/model/M15_CHINESE_EXPERIMENT_CHAPTER.md`
- M15 Chinese chapter runner: `experiments/generate_m15_chinese_experiment_chapter.py`
- M15 Chinese draft report: `results/reports/m15_chinese_experiment_chapter_draft.md`
- M15 caption index: `results/tables/m15_caption_index.csv`
- Scope: Chinese paper-style experiment narrative and figure/table captions only.

## M16 Paper Value Figures Artifacts

- M16 paper figure docs: `docs/model/M16_PAPER_VALUE_FIGURES.md`
- M16 paper figure runner: `experiments/generate_m16_paper_value_figures.py`
- M16 xlarge schedule: `results/schedules/m16_xlarge_5_5d_m4_greedy_schedule.csv`
- M16 figures: `results/figures/m16/`
- M16 figure index: `results/tables/m16_figure_index.csv`
- M16 report: `results/reports/m16_paper_value_figures_report.md`
- Scope: main paper figures that replace the weaker M13 representative Gantt.

## M17 Innovation Support Audit Artifacts

- M17 innovation support docs: `docs/model/M17_INNOVATION_SUPPORT.md`
- M17 innovation support runner: `experiments/run_m17_innovation_support.py`
- M17 path/schedule ablation table: `results/tables/m17_path_schedule_ablation.csv`
- M17 innovation support matrix: `results/tables/m17_innovation_support_matrix.csv`
- M17 report: `results/reports/m17_innovation_support_report.md`
- Scope: evidence audit for paper innovation claims; weak or partial support is reported explicitly.

## M18 Resource-Pressure Study Artifacts

- M18 resource-pressure docs: `docs/model/M18_RESOURCE_PRESSURE_STUDY.md`
- M18 pressure case generator: `experiments/generate_m18_pressure_cases.py`
- M18 pressure study runner: `experiments/run_m18_pressure_study.py`
- M18 generated cases: `configs/cases/m18/`
- M18 manifest: `data/derived/m18_pressure_case_manifest.csv`
- M18 outputs: `results/tables/m18_pressure_study.csv` and `results/reports/m18_pressure_study_report.md`
- Scope: controlled ablation showing why path selection must be coupled with resource-aware scheduling.

## M19 Pressure Figure Artifacts

- M19 pressure figure docs: `docs/model/M19_PRESSURE_FIGURES.md`
- M19 figure generator: `experiments/generate_m19_pressure_figures.py`
- M19 schedule exports: `results/schedules/m19/`
- M19 figures: `results/figures/m19/`
- M19 figure index: `results/tables/m19_figure_index.csv`
- M19 report: `results/reports/m19_pressure_figures_report.md`
- Scope: paper-facing figures explaining the M18 controlled resource-pressure result.

## M21 Innovation Pressure Suite Artifacts

- M21 pressure-suite docs: `docs/model/M21_INNOVATION_PRESSURE_SUITE.md`
- M21 pressure case generator: `experiments/generate_m21_innovation_pressure_suite.py`
- M21 pressure runner: `experiments/run_m21_innovation_pressure_suite.py`
- M21 generated cases: `configs/cases/m21/`
- M21 manifest: `data/derived/m21_innovation_pressure_manifest.csv`
- M21 outputs: `results/tables/m21_innovation_pressure_detail.csv`, `results/tables/m21_topology_pressure_summary.csv`, `results/tables/m21_claim_support.csv`, and `results/reports/m21_innovation_pressure_report.md`
- Scope: ITC'02-derived pressure suite for stronger path-schedule and topology evidence.

## M22 Mechanism Ablation Artifacts

- M22 mechanism-ablation docs: `docs/model/M22_MECHANISM_ABLATION.md`
- M22 mechanism-ablation runner: `experiments/run_m22_mechanism_ablation.py`
- M22 outputs: `results/tables/m22_mechanism_ablation_detail.csv`, `results/tables/m22_mechanism_ablation_summary.csv`, `results/tables/m22_topology_ablation_summary.csv`, and `results/reports/m22_mechanism_ablation_report.md`
- Scope: controlled ablation proving that path-schedule gains require shared-resource pressure plus alternative access paths.
