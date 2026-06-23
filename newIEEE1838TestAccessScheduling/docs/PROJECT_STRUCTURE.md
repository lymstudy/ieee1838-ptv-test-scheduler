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
- M2 默认输出：`results/tables/m2_recipe_summary.csv`
- M3 剪枝说明：`docs/model/M3_PARETO_PRUNING.md`
- M3 剪枝脚本：`experiments/run_m3_pareto_pruning.py`
- M3 默认输出：`results/tables/m3_recipe_pruned.csv` 和 `results/reports/m3_pruning_summary.csv`
