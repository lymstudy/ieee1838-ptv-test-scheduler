# DESIGN SPEC: IEEE 1838-Aware Layered Test Access Path Generation and Predictive Physical-Aware Scheduling

## 1. 当前 A0 原型总结

A0 原型已经完成一个可复现的 task-level physical-aware scheduling framework。当前已经具备：

- IEEE 1838-compatible access abstraction 的初步建模，包括 PTAP、STAP、Die Wrapper Register (DWR) segment 和 optional FPP lane。
- Serial IEEE 1838-style baseline scheduler。
- Bandwidth-greedy baseline scheduler。
- PTV-aware scheduler。
- Unified schedule-based evaluator。
- Simplified shared-PDN IR-drop model。
- Simplified per-die RC thermal model。
- Clean 4-die MVP case。
- Stress workload mechanism validation case。
- FPP lane sweep。
- Voltage limit sweep。
- Thermal limit sweep。
- Workload scale sweep。
- Benchmark-derived workload statistics schema。
- Example benchmark adapter。
- Manually specified realistic UART statistics case。

A0 的定位是：task-level physical-aware scheduling prototype。它用于验证调度器、资源约束、schedule overlap 物理评估、参数扫描和 benchmark statistics adapter 的基础可行性。

A0 不是完整 IEEE 1838 behavior model。当前模型没有完整展开 IEEE 1838 access sequence，也没有建模 3DCR/STAP/DWR/FPP 的细粒度访问行为。

## 2. 当前 A0 原型的不足

### 2.1 物理模型仍较简化

1. Voltage model 主要是 simplified shared-PDN：`Vdrop = R_shared * I_total`。
2. Thermal model 是 simplified per-die RC update。
3. 尚未建模 die-to-die thermal coupling。
4. 尚未体现 local hotspot 或 spatial power density。
5. 尚未体现 die-specific PDN path、TSV、micro-bump、C4 等非对称供电路径。

### 2.2 IEEE 1838 行为体现仍浅

1. 当前只是抽象 PTAP/STAP/DWR/FPP 资源。
2. 尚未建模 3DCR select/bypass 行为。
3. 尚未建模 STAP path opening。
4. 尚未建模 DWR mode configuration、shift、capture、update。
5. 尚未建模 FPP configuration 和 FPP 仅作为 data transport 的限制。
6. 尚未建模 first-die PTAP bottleneck。

### 2.3 当前 task 只有单一 duration

1. 尚未拆分 access/config time、local execution time、readback time。
2. 尚未体现 BIST start 后本地运行、PTAP 释放的语义。
3. 尚未体现 instrument access network 的层级或 SIB/daisy-chain 开销。

### 2.4 “预测性”和“分层”还不够

1. 当前 PTV-aware 更像 one-step risk-aware heuristic。
2. 尚未实现 rolling horizon、look-ahead、path-blocking-aware scheduling。
3. 尚未实现 TestIntent -> AccessOp -> ExecutionPhase 的分层展开。

### 2.5 真实性仍有限

1. Realistic UART 是 manually specified statistics case。
2. 尚未 RTL-extracted benchmark。
3. 尚未 RTL mock validation。
4. 尚未 industrial PDN / thermal tool correlation。

## 3. B 阶段目标架构

B 阶段目标是将 A0 的 task-level scheduler 升级为：

Predictive access-path and physical-aware layered test scheduling for IEEE 1838-compatible 3D ICs.

目标 pipeline：

```text
Benchmark / Synthetic / RTL-derived Stats
    ↓
Test Intent Layer
    ↓
IEEE 1838 Access Path Generator
    ↓
Layered Task Expansion
    ↓
Predictive Physical-Aware Scheduler
    ↓
Schedule Evaluator
    ↓
Reports / Figures / Audit
```

各层作用：

- Benchmark / Synthetic / RTL-derived Stats：提供 workload 输入，可来自 synthetic generator、benchmark statistics YAML 或未来 RTL-derived reports。
- Test Intent Layer：描述“我要测什么”，不直接描述访问路径。
- IEEE 1838 Access Path Generator：根据 target die、DWR/FPP/STAP/3DCR 需求生成 abstract access path。
- Layered Task Expansion：把高层 test intent 展开为 access/config、data transfer、local execution、capture、readback 等 phases。
- Predictive Physical-Aware Scheduler：在访问路径、资源占用和物理风险预测下调度 phases。
- Schedule Evaluator：基于完整 schedule overlap 计算 thermal、IR-drop、parallelism、resource utilization 和 violation。
- Reports / Figures / Audit：生成可复现实验表格、图、审计报告和论文/组会材料。

## 4. Test Intent Layer 设计

TestIntent 表示“我要测什么”，不是具体访问序列。它是 scheduler 前的 workload semantic layer。

计划支持的 TestIntent 类型：

- InternalScanIntent
- ScanCaptureIntent
- BISTIntent
- DWRExTestIntent
- InstrumentReadIntent
- InstrumentWriteIntent
- BypassIntent
- FPPDataTransferIntent

通用字段示例：

- intent_id
- target_die
- target_core / module
- test_type
- estimated_pattern_count
- scan_chain_length
- power_profile
- requires_fpp
- requires_dwr
- requires_readback
- dependencies

示例字段：InternalScanIntent 可包含 target_die、target_core、estimated_pattern_count、scan_chain_length、shift/capture power_profile、requires_fpp、requires_dwr 和 readback dependency。BISTIntent 可包含 local engine、estimated local cycles、trigger/readback requirement。InstrumentReadIntent / InstrumentWriteIntent 可包含 target instrument、network depth、read/write width 和 optional readback。BypassIntent 用于表达非目标 die 的 bypass。FPPDataTransferIntent 用于表达 bulk data transfer，而不是完整控制路径。

## 5. IEEE 1838 Access Operation 设计

AccessOp 是 access-level operation，用于估算访问时间和资源占用。它比 TestIntent 更接近执行序列，但仍保持抽象，不声称是标准条文实现。

计划支持的 AccessOp：

- SELECT_DIE_PATH
- CONFIG_3DCR
- OPEN_STAP
- BYPASS_DIE
- CONFIG_DWR_MODE
- SHIFT_DWR
- CAPTURE_DWR
- UPDATE_DWR
- CONFIG_FPP
- FPP_SHIFT_IN
- FPP_SHIFT_OUT
- TRIGGER_BIST
- READ_BIST_RESULT
- ACCESS_INSTRUMENT
- INSERT_DUMMY_CYCLE

每个 AccessOp 至少包含 op_id、op_type、target_die、bit_length、estimated_time、occupied_resources、produces_state、consumes_state 和 power_hint。

AccessOp 可用于估算 PTAP/STAP config time、DWR shift/capture/update time、FPP data transport time、BIST trigger/readback time、instrument network traversal time，以及 cooling / voltage recovery 的 dummy cycle。

## 6. Access Path Generator 设计

AccessPath 表示从外部 test access entry 到 target die/test resource 的抽象路径。

必须体现：

- 访问 deeper die 需要通过前级 die。
- First die / PTAP path 可能成为访问瓶颈。
- 3DCR / STAP select/bypass 会带来配置开销。
- Target die 越深，access overhead 越大。
- FPP 可以提供 data transfer，但通常仍需要 PTAP 配置。

AccessPath 字段：

- target_die
- path_dies
- selected_staps
- bypassed_dies
- required_3dcr_bits
- required_dwr_segments
- required_fpp_lanes
- access_bit_length
- estimated_access_time
- occupied_resources

MVP access time 估计公式：

```text
access_time = instruction_bits / tck_freq
            + config_bits / tck_freq
            + data_bits / transfer_bandwidth
            + readback_bits / tck_freq
```

其中 instruction_bits 表示 PTAP/STAP/3DCR instruction overhead；config_bits 表示 select/bypass/DWR/FPP configuration bits；data_bits 表示 scan/DWR/FPP payload；readback_bits 表示 result/status readback；transfer_bandwidth 可根据 PTAP serial path、STAP path、DWR shift width 或 FPP lanes 估计。

该公式是 MVP 抽象公式，后续可替换为更真实的 IEEE 1838 access timing model 或 measured report model。

## 7. Layered Task Expansion 设计

LayeredTask 表示从一个 TestIntent 展开的多个 ExecutionPhase。调度器不再直接调度单个 monolithic task，而是调度 phases。

ExecutionPhase 字段：

- phase_id
- parent_intent_id
- phase_type
- start_dependency
- duration
- power
- occupied_resources
- target_die
- fpp_lanes
- dwr_segment
- uses_ptap
- uses_fpp
- is_local_execution
- is_capture_phase
- requires_readback

### 示例 1：BIST(die2)

- phase 1: configure access path through PTAP/STAP
- phase 2: trigger BIST start
- phase 3: local BIST running，释放 PTAP，可与其他 die access 并行
- phase 4: re-access die2
- phase 5: read BIST result

关键语义：local BIST running 不持续占用 PTAP_CONTROL_PATH，但占用 LOCAL_BIST_ENGINE、POWER_DOMAIN 和 THERMAL_REGION。

### 示例 2：Internal Scan(die3)

- phase 1: configure die3 access path
- phase 2: configure scan / FPP path
- phase 3: FPP shift-in
- phase 4: capture
- phase 5: FPP shift-out
- phase 6: result readback / status check

关键语义：shift phase 主要占用 FPP_LANE/DWR_SEGMENT，capture phase 可能带来高瞬态电流，需要 staggering。

### 示例 3：DWR EXTEST(die1, die2)

- phase 1: configure both adjacent die wrappers
- phase 2: configure DWR mode
- phase 3: shift boundary values
- phase 4: capture die-to-die interconnect response
- phase 5: shift out response

关键语义：DWR segment 和 target adjacent interconnect 需要避免 overlap conflict。

### 示例 4：Instrument access

- phase 1: select target die
- phase 2: access instrument network
- phase 3: read/write instrument register
- phase 4: optional readback

Instrument network 后续可扩展为 flat network、SIB hierarchical network 或 daisy chain network。

## 8. Timing Model 设计

B 阶段必须区分：

1. access/config time
2. data transfer time
3. local execution time
4. capture time
5. readback time
6. dummy cycle time

Task execution time 不等于 test access time。不同测试类型的主导时间不同：

- Scan 主要受 shift data volume / FPP or TAM bandwidth 影响。
- BIST 主要是短访问 + 长本地执行 + 短回读。
- DWR EXTEST 受 DWR length 和 access path 影响。
- Instrument access 受 instrument network depth 和 SIB/daisy-chain 结构影响。
- Dummy cycle 用于 cooling / voltage recovery。

Timing model 初期应保持可解释，不追求 bit-accurate 标准仿真。目标是让 access overhead、local execution 和 readback 的资源占用语义进入 scheduler。

## 9. Resource Model 设计

计划资源类型：

- PTAP_CONTROL_PATH
- STAP_PATH
- 3DCR_CONFIG
- DWR_SEGMENT
- FPP_LANE
- LOCAL_BIST_ENGINE
- INSTRUMENT_NETWORK
- POWER_DOMAIN
- THERMAL_REGION

资源并行语义：

- PTAP/STAP config 阶段通常串行。
- FPP 是可选高带宽 data path，不是万能控制路径。
- FPP lane 数增加会带来硬件、面积、引脚、路由代价。
- BIST local execution 不持续占用 PTAP。
- Scan data phase 可能主要占用 FPP/TAM。
- Capture phase 会带来高瞬态电流，需要 staggering。

资源 exclusivity 初始规则：PTAP_CONTROL_PATH exclusive；STAP_PATH per-path exclusive；3DCR_CONFIG config phase exclusive；DWR_SEGMENT per segment exclusive；FPP_LANE 是 capacity resource；LOCAL_BIST_ENGINE per die or per engine exclusive；INSTRUMENT_NETWORK 根据 flat/SIB/daisy-chain model 决定；POWER_DOMAIN 和 THERMAL_REGION 是 risk resources。

## 10. Predictive Physical-Aware Scheduling 设计

B 阶段 scheduler 不应只做 one-step risk。规划两条算法路线。

### 路线 A：Look-ahead heuristic

初期优先实现路线 A。

```text
score(task_or_phase) =
benefit
- lambda1 * access_path_cost
- lambda2 * path_blocking_cost
- lambda3 * predicted_voltage_risk
- lambda4 * predicted_thermal_risk
- lambda5 * fpp_hardware_cost
- lambda6 * readback_delay_risk
```

其中 access_path_cost 表示 deeper die、select/bypass、3DCR/STAP config overhead；path_blocking_cost 表示当前 phase 对 future access path 的阻塞；predicted_voltage_risk 表示未来短窗口 IR-drop 风险；predicted_thermal_risk 表示未来短窗口温度风险；fpp_hardware_cost 表示使用更多 FPP lane 的硬件代价权重；readback_delay_risk 表示推迟 readback 可能引起的 dependency 或 result latency。

### 路线 B：Rolling-horizon / MPC-style scheduling

在未来 H 个时间窗口内预测 TAT increment、peak IR-drop、peak temperature、path blocking、dummy cycle need 和 readback delay。只执行第一个调度动作，然后滚动更新。

路线 B 作为后续增强，不作为 B1 的第一目标。

## 11. Asymmetric Physical Model Roadmap

Voltage model 从：

```text
Vdrop = R_shared * I_total
```

升级为：

```text
Vdrop_i(t) = sum_j R_ij * I_j(t)
```

其中 R_ij 表示不同 die / power path 的耦合。

Thermal model 从 per-die RC 升级为：

```text
T(t+1) = A_T * T(t) + B_T * P(t)
```

其中 A_T 表示 die-to-die thermal coupling；B_T 表示功耗到温升；不同 die 可有不同 thermal limit；可扩展 local thermal region / hotspot model。

后续可选模型：HotSpot、3D-ICE、compact thermal RC、small PDN matrix、SPICE-like RC network。RedHawk / Voltus 可作为长期可选验证，不作为 MVP 依赖。

## 12. Validation Ladder

验证阶梯：

- Level 0：Python task-level simulation，目前已完成。
- Level 1：IEEE 1838 access behavior mock，计划中。
- Level 2：benchmark-derived workload，已完成 schema 和 manually specified UART stats，后续接公开 benchmark。
- Level 3：RTL mock validation，验证 simplified PTAP/STAP/DWR/FPP/scan/BIST 行为。
- Level 4：thermal / IR-drop model correlation，例如 HotSpot/3D-ICE/simple PDN matrix。
- Level 5：FPGA semi-hardware playback，验证 scheduler command flow，不声称真实 3D thermal/IR-drop。
- Level 6：industrial tool correlation，RedHawk / Voltus，可选长期目标。

FPGA 不能直接验证 3D IC 真实 thermal/IR-drop，只能验证控制流和访问序列执行。

## 13. Implementation Milestones

### B0：Design spec and interface planning

- goal: 冻结 A0 原型定位，完成 IEEE 1838-aware layered scheduler 设计规格。
- expected output: `docs/DESIGN_SPEC_1838_LAYERED_SCHEDULER.md` 和 `docs/NEXT_PHASE_PLAN.md`。
- acceptance criteria: 文档明确 A0 不足、B 阶段 pipeline、核心对象、milestones 和下一步任务。

### B1：AccessPath data model and path cost estimator

- goal: 建模 target die access path、select/bypass、3DCR/STAP/DWR/FPP resource occupancy 和 access overhead。
- expected output: `src/access_path/model.py`、`src/access_path/generator.py`、`tests/test_access_path_generator.py`。
- acceptance criteria: 能为不同 target die 生成 path_dies、bypassed_dies、required bits、estimated_access_time 和 occupied_resources。

### B2：TestIntent to ExecutionPhase layered expander

- goal: 将 TestIntent 展开为 ExecutionPhase 序列。
- expected output: `src/intent/model.py`、`src/layered/expander.py`、phase-level workload examples。
- acceptance criteria: BIST、scan、DWR EXTEST、instrument access 都能展开为多 phase。

### B3：Access-time-aware scheduler

- goal: 在调度中区分 access/config、data transfer、local execution 和 readback。
- expected output: access-time-aware baseline scheduler。
- acceptance criteria: BIST local execution 可以释放 PTAP；scan shift/capture/readback 资源占用分离。

### B4：Predictive path-blocking-aware PTV scheduler

- goal: 在 PTV-aware scheduler 中加入 access path cost、path blocking risk 和 readback delay risk。
- expected output: predictive heuristic scheduler。
- acceptance criteria: 相比 B3 baseline，能够减少 physical violation 和 path-blocking-induced idle gaps。

### B5：Asymmetric voltage matrix and thermal coupling model

- goal: 引入 R_ij PDN matrix 和 A_T/B_T thermal coupling model。
- expected output: asymmetric voltage evaluator 和 coupled thermal evaluator。
- acceptance criteria: 并发任务在不同 die 上产生不同 IR-drop / thermal response。

### B6：Ablation study

- goal: 评估各机制贡献。
- expected output: without voltage risk、without thermal risk、without path blocking、without capture staggering、without dummy cycle 的对比。
- acceptance criteria: 生成 ablation summary CSV 和 plots。

### B7：Small-scale MILP optimal baseline

- goal: 为小规模 case 提供 optimal 或 near-optimal baseline。
- expected output: small MILP formulation and solver wrapper。
- acceptance criteria: 小 case 可与 heuristic TAT/violation tradeoff 对比。

### B8：RTL mock validation

- goal: 验证 simplified PTAP/STAP/DWR/FPP/scan/BIST 行为和 scheduler command flow。
- expected output: RTL mock stack、command trace、simulation logs。
- acceptance criteria: mock 可以 replay access sequence，不声称验证真实 3D thermal/IR-drop。

### B9：Public benchmark-derived statistics case

- goal: 接入公开 benchmark statistics 或人工提取报告。
- expected output: benchmark stats YAML、schedule results、audit report。
- acceptance criteria: 明确来源，不编造实验结果。

### B10：Paper/slide consolidation

- goal: 固化论文/组会材料。
- expected output: method figures、result tables、ablation plots、limitations。
- acceptance criteria: 每个结论都能追溯到 repo 文件和实验日志。

## 14. Immediate Next Task Recommendation

根据本 SPEC，下一步不建议继续加 sweep，而是进入 B1：AccessPath data model and path cost estimator。

预期输出：

- `src/access_path/model.py`
- `src/access_path/generator.py`
- `tests/test_access_path_generator.py`
- docs 中给出 access path 示例

本次 B0 只完成设计规格和路线规划，不实现 B1。

## 15. Frontier Idea Integration Addendum

B0 设计规格的后续前沿启发整合见：[`FRONTIER_IDEA_INTEGRATION_PLAN.md`](FRONTIER_IDEA_INTEGRATION_PLAN.md)。该文档是 future roadmap，不表示当前 A0/B0 已实现对应功能。

### 15.1 Resource Model 增量规划

在第 9 节 resource model 的后续版本中，可增加以下规划级资源对象：

- `PowerPillar`：用于 power-pillar-aware capture staggering，不是当前代码对象。
- `PackageProfile`：用于 package/substrate-aware boundary condition，不是材料验证结论。
- `HealthEventInterface`：用于 external health/throttle/status event，不是 UCIe 实现。
- `SSNInspiredTAM`：用于 streaming-scan-inspired die-level TAM abstraction，不是 Siemens SSN 实现，也不是 IEEE 1838 内容。
- `InterposerTestBus`：用于 future interposer test-bus-aware routing，不是 B1/B2 immediate scope。

这些对象均需要硬件/面积/引脚/路由/控制复杂度成本建模，不允许声称 zero hardware overhead。

### 15.2 Predictive Scheduling 增量规划

第 10 节 predictive scheduler 后续应显式加入：

- `path_blocking_cost`：衡量当前 access path 对后续 deeper die / readback / bypass path 的阻塞。
- `health_event_safe_mode`：当 external health event 进入 throttle 或 emergency state 时，只允许低功耗 readback、instrument access 或 safe dummy cycles。
- package-aware constraints：通过 `PackageProfile` 更新 thermal limit、cooling beta、PDN resistance matrix、max shift frequency 和 FPP bandwidth limit。
- per-power-pillar capture staggering：同一 `PowerPillar` / `VerticalPDNGroup` 内的 capture concurrency 需要受限。

### 15.3 Validation Ladder 增量规划

第 12 节 validation ladder 后续扩展项：

- External health event-aware playback：验证 scheduler command flow 如何响应 health/throttle/status event；不验证真实 UCIe PHY。
- Package-aware boundary modeling：比较不同 PackageProfile 下的仿真边界条件；不声称材料实测结论。
- SSN-inspired TAM / FPP co-allocation：研究 stack-level FPP lane 和 die-level TAM bandwidth 的共同分配；不实现 Siemens Tessent SSN。
- Interposer test-bus-aware routing：作为 B11 之后的长期扩展，不进入 B1 immediate implementation。

B1 下一步仍是 AccessPath data model and path cost estimator。本 addendum 不改变 B1 范围。
