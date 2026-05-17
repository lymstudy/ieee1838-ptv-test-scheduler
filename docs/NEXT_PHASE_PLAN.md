# NEXT PHASE PLAN

## 1. 当前 A0 已完成内容

A0 原型已经完成：

- Serial IEEE 1838-style baseline scheduler
- Bandwidth-greedy baseline scheduler
- PTV-aware scheduler
- Unified schedule evaluator
- Simplified shared-PDN voltage model
- Simplified per-die RC thermal model
- Clean 4-die MVP case
- Stress workload mechanism validation
- FPP lane sweep
- Voltage limit sweep
- Thermal limit sweep
- Workload scale sweep
- Benchmark-derived workload schema
- Example benchmark adapter
- Realistic UART statistics case
- Schedule audit reports

A0 已经证明：Bandwidth-greedy 可以降低 TAT，但会提高 voltage / thermal risk；PTV-aware 可以用一定 TAT 代价降低或消除 physical violation。

## 2. 为什么 A0 不够

A0 仍主要是 task-level PTV scheduling prototype。

不足包括：

- IEEE 1838 behavior 体现不足，只抽象了 PTAP/STAP/DWR/FPP 资源。
- 没有 3DCR select/bypass、STAP path opening、DWR mode/shift/capture/update 语义。
- Task 只有单一 duration，没有拆分 access/config、local execution、readback。
- BIST local execution 释放 PTAP 的语义尚未体现。
- PTV-aware 仍是 one-step risk-aware heuristic，不是 predictive layered scheduler。
- Physical model 仍是 simplified shared-PDN 和 per-die RC。

## 3. B 阶段主线

B 阶段目标是：

Predictive access-path and physical-aware layered test scheduling for IEEE 1838-compatible 3D ICs.

主线包括：

- IEEE 1838 behavior：建模 3DCR、STAP path、DWR mode、FPP data transport。
- Layered task expansion：TestIntent -> AccessOp -> ExecutionPhase。
- Access time model：区分 access/config time、data transfer time、local execution time、capture time、readback time。
- Predictive scheduling：加入 access path cost、path blocking risk、voltage/thermal look-ahead。
- Asymmetric physical model：升级到 PDN matrix 和 die-to-die thermal coupling。

## 4. 优先级

### P0：AccessPath + LayeredTask spec/code

下一步优先完成：

- AccessPath data model
- AccessPath generator
- Path cost estimator
- TestIntent model
- ExecutionPhase model
- Layered task expander

### P1：Predictive scheduling + ablation

完成 P0 后进入：

- Access-time-aware scheduler
- Predictive path-blocking-aware PTV scheduler
- Ablation study
- Small-scale MILP optimal baseline

### P2：RTL mock / benchmark / thermal coupling

后续增强：

- RTL mock validation
- Public benchmark-derived statistics case
- Asymmetric voltage matrix
- Thermal coupling model
- Paper/slide consolidation

## 5. 不建议立刻做的事情

当前不建议：

- 直接上 FPGA。
- 直接接 RedHawk / Voltus。
- 继续盲目做 sweep。
- 把当前 A0 包装成完整 IEEE 1838 framework。

FPGA 后续只能用于验证控制流和访问序列执行，不能直接验证真实 3D IC thermal/IR-drop。

## 6. Immediate Next Task

推荐下一步：

B1：AccessPath data model and path cost estimator。

预期输出：

- `src/access_path/model.py`
- `src/access_path/generator.py`
- `tests/test_access_path_generator.py`
- Access path examples in docs

## 7. Frontier Idea Integration

更长期的前沿启发整合见：[`FRONTIER_IDEA_INTEGRATION_PLAN.md`](FRONTIER_IDEA_INTEGRATION_PLAN.md)。这些内容是 future roadmap，不是当前已实现功能，也不是 B1 immediate scope。

B1 仍然是下一步：AccessPath data model and path cost estimator。

### P1/P2/P3 补充方向

P1 后续可纳入：

- PowerPillar-aware capture staggering。
- Predictive health-event safe mode pseudocode。
- FPP hardware cost model。

P2 后续可纳入：

- SSN-inspired TAM abstraction。
- FPP/SSN co-allocation。
- PackageProfile-aware boundary modeling。
- External health event interface。

P3 长期方向可纳入：

- Interposer test-bus routing model。
- Optional FPGA playback of command sequence。
- Optional tool correlation。

这些方向不得被写成已实现 SSN、已实现 UCIe、完整 IEEE 1838 RTL、zero hardware overhead 或真实 3D thermal/IR-drop 验证。
