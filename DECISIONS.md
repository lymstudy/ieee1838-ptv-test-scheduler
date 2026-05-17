# 研究与工程决策 DECISIONS

## D1：DWR 术语

DWR 表示 Die Wrapper Register。

禁止将 DWR 写成 Design for Test Wrapper。

## D2：IEEE 1838 的范围

IEEE 1838 提供 3D stacked IC 的 test access architecture。

IEEE 1838 不定义测试调度算法。

本项目是在 IEEE 1838-compatible access resources 的基础上，研究测试任务调度优化。

## D3：SSN

MVP 阶段不实现真实 Siemens Tessent SSN。

如后续需要表达类似思想，只允许使用：
“streaming-scan-inspired die-level TAM model”。

禁止声称 IEEE 1838 包含 SSN。

## D4：物理模型

MVP 使用抽象但物理上合理的 thermal 和 IR drop 模型。

Thermal model：
Discrete RC-style temperature update。

Voltage model：
Equivalent PDN resistance-based IR drop estimation。

## D5：第一阶段目标

第一阶段目标是 4-die stack MVP。

需要比较的 scheduler：
1. Serial baseline
2. Bandwidth-greedy baseline
3. PTV-aware scheduler

## D6：研究诚信约束

禁止编造论文引用、会议结果、标准条文或实验结果。

如果需要引用外部论文或标准，必须明确来源。

## D7：硬件开销表述

禁止声称 zero hardware overhead。

如果需要表达低硬件代价，可以使用：
“no additional test access pins in the abstract model”
或
“reuse IEEE 1838-compatible test access resources”。

## D8：Scheduler 接口与结果格式

调度器统一继承 BaseScheduler，并通过 ScheduleEntry 表示单个任务区间，通过 ScheduleResult 表示完整调度结果、PTV trace 和 metrics。

Serial baseline 的 metrics CSV 使用单行 summary 格式，字段包括 scheduler_name、tat、peak_temperature、peak_ir_drop、temperature_violation_count、voltage_violation_count 和 num_tasks。

Serial baseline 是 IEEE 1838-style access resources 上的串行基线，不表示 IEEE 1838 标准定义了调度算法。

## D9：Bandwidth-greedy 资源规则

Bandwidth-greedy baseline 是激进并行调度器，只考虑 task readiness/dependency、FPP lane capacity、DWR segment conflict 和基础 access resource conflict。

默认 FPP lane 需求集中定义在 BandwidthGreedyScheduler 中：scan 使用 1 lane，DWR_EXTEST 使用 1 lane，BIST 使用 0 lane，instrument_access 使用 0 lane。若 task 显式提供 fpp_lanes_required、required_fpp_lanes 或 fpp_lanes_used，则优先使用 task 字段。

DWR segment conflict 规则：同一 Die Wrapper Register segment 不能被多个 overlap task 同时占用。

基础 access resource conflict 规则：当前只将 PTAP_STAP_SERIAL 视为独占访问资源；FPP lane pool 通过 lane capacity 约束，不用字符串资源名禁止并行。

该 baseline 不在调度过程中避免 thermal 或 voltage violation，只在调度后计算 temperature trace、IR drop trace 和 violation count。
## D10：FPP 与 PTAP/STAP 的并行抽象

在当前 MVP 抽象模型中，PTAP/STAP 主要表示低带宽配置、触发和 instrument access 路径，FPP 表示可选高带宽 bulk test data transfer 路径。

因此，在 Bandwidth-greedy 和后续 PTV-aware scheduler 中，FPP_SCAN 或 FPP_DWR 类型任务可以与 BIST_LOCAL 或低带宽 PTAP_STAP_SERIAL instrument access 并行执行，前提是：
- 不超过 FPP lane capacity；
- 不冲突同一个 DWR segment；
- 不违反 task dependency；
- 后续 PTV-aware scheduler 还需要满足 thermal 和 IR drop constraints。

该决策是 MVP 阶段的抽象建模假设，不代表 IEEE 1838 标准强制规定 FPP 与 PTAP 必然可完全并行。
## D11：PTV-aware 调度抽象

PTV-aware scheduler 在 Bandwidth-greedy 的 task readiness/dependency、FPP lane capacity、DWR segment conflict 和基础 access resource conflict 约束上，额外加入 thermal prediction、IR drop prediction、capture staggering 和 dummy cycle insertion。

Priority score 使用 benefit / risk 形式。当前 MVP 中 benefit 与任务持续时间和 FPP lane 使用相关；risk 包含 predicted_temperature_ratio、predicted_ir_drop_ratio、fpp_pressure 和 capture_pressure。该公式用于确定候选任务顺序，不声称是最优算法。

Thermal prediction 使用 conservative one-step prediction：将当前正在运行任务功耗与候选任务功耗相加，调用 discrete RC-style thermal model 预测下一时间片的 peak temperature。

Voltage prediction 使用当前正在运行任务功耗与候选任务功耗之和，调用 equivalent PDN resistance-based IR drop model 预测 peak IR drop。

Capture staggering 使用 max_concurrent_capture 约束，默认值为 1。若当前 workload 没有 is_capture_phase=True 的任务，metrics 中 capture_staggering_applied=False。

Dummy cycle insertion 使用 dummy_cycle_duration_s，默认值为 0.0001 s。当 ready tasks 只因 thermal 或 IR drop prediction 被阻塞且无 running task 可自然推进时间时，插入 idle step。若约束仍不可解除，调度器允许强制启动并通过 violation count 记录结果，避免死循环。

该 PTV-aware scheduler 是 MVP 阶段的启发式调度器，不代表 IEEE 1838 标准定义了 PTV-aware scheduling。
## D12：Stress workload mechanism validation 建模原则

`case_4die_stress.yaml` 是 synthetic mechanism validation workload，不等同于真实 benchmark workload，也不代表来自真实 RTL、ATPG、HotSpot、RedHawk、Voltus 或 Tessent SSN 的结果。

Stress workload 的目标是验证 PTV-aware scheduler 的机制是否能在更高并行度、更高功耗和更紧 thermal / IR drop limit 下生效。该 workload 使用：
- 较高 power 的 scan shift、scan capture 和 BIST task；
- 显式 `fpp_lanes_required` 表示 FPP lane 需求；
- 显式 `is_capture_phase=True` 表示 capture phase；
- 显式 `dependencies` 表示 capture task 依赖对应 scan shift task；
- 显式 `dwr_segment` 表示 Die Wrapper Register segment 占用；
- `DWR_NONE` 表示该 task 在当前 MVP 抽象中不占用 DWR segment，例如本地 BIST 或低带宽 instrument access。

该设计用于验证调度机制，不用于声称 IEEE 1838 标准规定这些任务必须以该方式并行，也不用于声称 PTV-aware scheduler 在真实工业 workload 上必然取得相同数值优势。

## D13：Schedule-based evaluator 与 simplified shared-PDN model

所有 scheduler 的物理评估必须使用统一 schedule evaluator。Evaluator 基于完整 schedule overlap 计算：
- `active_tasks(t) = entries with start_time <= t < end_time`；
- `die_power_i(t) = sum(power of active tasks on die i)`；
- `total_power(t) = sum_i die_power_i(t)`；
- temperature trace、IR-drop trace、peak metrics、violation count、average_parallelism、max_parallelism 和 FPP utilization。

Serial、Bandwidth-greedy 和 PTV-aware scheduler 不应各自维护重复的 metrics 计算逻辑。

MVP 阶段新增 simplified shared-PDN voltage mode：

```text
ir_drop(t) = shared_resistance * total_current(t)
total_current(t) = total_power(t) / Vdd
```

在该模式下，所有 active die 的电流都会叠加到 shared resistance 上，因此并行 schedule 的 peak IR drop 可以高于串行 schedule。

该 shared-PDN model 是抽象机制验证模型，不等同于 RedHawk、Voltus 或其他 signoff 工具，也不表示真实 3D IC PDN 的完整矩阵模型。后续若需要更高物理可信度，可以扩展为：

```text
ir_drop_i(t) = sum_j R_ij * current_j(t)
```

Thermal evaluator 当前仍使用 per-die discrete RC-style update，并按 `die_power_i(t)` 更新温度；尚未实现 die-to-die thermal coupling。

## D14: Thermal Sweep Over-Constrained Marker

Thermal limit sweep rows may include an `over_constrained` field.

For the MVP sweep experiments, `over_constrained=True` means the PTV-aware scheduler still records at least one temperature violation at that thermal limit. This marks a limit that is too tight for the current workload and simplified thermal model, so the result should not be interpreted as a scheduler failure or hidden advantage.

In `sweep_thermal_limits.py`, the field is derived from the PTV-aware result for the corresponding thermal limit:

```text
over_constrained = ptv_aware.temperature_violation_count > 0
```

For the current stress workload, the 25.5 C point is over-constrained because the initial die temperatures are about 25.55 C, already above the thermal limit.

This marker is an experiment reporting convention, not an IEEE 1838 concept.

## D15: Deterministic Synthetic Workload Generator

The synthetic workload generator in `src/workload/synthetic.py` is for mechanism validation only. It is not a benchmark-derived workload and does not represent real RTL, ATPG output, HotSpot, 3D-ICE, RedHawk, Voltus, Tessent SSN, or silicon validation.

Design principles:

- Deterministic generation with no uncontrolled randomness.
- Supported die counts for the current sweep: 4, 8, and 12.
- Supported density labels: small, medium, and large.
- Each generated workload includes scan shift tasks, scan capture tasks, BIST tasks, instrument access tasks, and adjacent-die DWR EXTEST tasks.
- Capture tasks use `is_capture_phase=True` and depend on scan shift tasks on the same die.
- Local BIST and low-bandwidth instrument tasks use `DWR_NONE` when they do not occupy a Die Wrapper Register segment in the MVP abstraction.
- Adjacent-die DWR EXTEST tasks use explicit synthetic DWR segment names such as `dwr_die0_die1`.

This generator exists to test scheduler scaling behavior and physical-constraint mechanisms before benchmark-derived or RTL-mock workloads are added.

## D16: Benchmark-Derived Workload Statistics Schema

The benchmark-derived workload path uses a statistics schema rather than direct RTL parsing.

Design principles:

- Schedulers do not parse RTL, Verilog, gate-level netlists, synthesis reports, or scan reports directly.
- The adapter receives benchmark statistics from YAML and converts them into the existing abstract workload shape: stack, access, thermal, voltage, scheduler, and tasks.
- Task duration is derived from statistics such as `scan_chain_length`, `scan_chain_count`, `flip_flop_count`, and interconnect `dwr_length`.
- Task power is derived from estimated per-mode power fields such as `estimated_shift_power`, `estimated_capture_power`, `estimated_bist_power`, `estimated_instrument_power`, and `estimated_extest_power`.
- Capture tasks generated by the adapter use `is_capture_phase=True` and depend on the corresponding scan shift task.
- DWR EXTEST tasks are generated from `interconnects` entries and use explicit Die Wrapper Register segment names.
- The current example is schema validation only. It is not a real benchmark conclusion and does not validate against real ATPG, HotSpot, 3D-ICE, RedHawk, Voltus, Tessent SSN, or silicon data.

This schema prepares the repository for future public benchmark statistics or manually extracted RTL report data without coupling scheduler algorithms to parser-specific details.

## D19: A0 Freeze and B-Stage Layered Scheduling Direction

A0 is frozen as a task-level physical-aware scheduling prototype. It should not be presented as a complete IEEE 1838 behavior framework.

B-stage work will use IEEE 1838-compatible access behavior and layered scheduling as the main research direction:

- TestIntent describes what should be tested.
- AccessOp describes abstract IEEE 1838-style access operations.
- AccessPath captures target-die path cost, selected STAPs, bypassed dies, DWR segments, FPP lanes, and occupied resources.
- ExecutionPhase separates access/config time, data transfer time, local execution time, capture time, readback time, and dummy cycle time.
- Predictive scheduling should account for access path blocking, physical risk, FPP usage, readback delay, and future schedule impact.

FPP is an optional high-bandwidth data transport resource. It is not a universal control path and usually still requires PTAP/STAP configuration before use.

BIST local execution may release the PTAP control path after trigger, while still consuming local BIST engine, power-domain, and thermal-region resources.

Future B-stage models must distinguish access/config time, execution time, and readback time. Monolithic task duration is retained only as an A0 simplification.

This decision does not claim IEEE 1838 defines scheduling algorithms. It defines the repository's next modeling direction.

## D20: Frontier Idea Terminology and Claim Boundaries

SSN is not part of IEEE 1838. Later B-stage work may introduce an `SSNInspiredTAM` or streaming-scan-inspired die-level TAM abstraction, but it must not be described as Siemens Tessent SSN implementation or as IEEE 1838 functionality.

UCIe is not part of IEEE 1838. A future `HealthEventInterface` may be inspired by external fast throttle, emergency shutdown, or open-drain event mechanisms, but it must not be described as UCIe implementation or UCIe PHY validation.

SIB is not assumed to directly control FPP lane width. SIB-style ideas may influence instrument-network or access-network hierarchy, while FPP configuration is modeled through FPP configuration elements.

3DCR/STAP configuration remains the main stack-level access path control abstraction for B-stage IEEE 1838-aware modeling.

FPP remains an optional high-bandwidth data transport resource. It is not a universal control path, is not zero-cost, and any optional FPP/SSN-like TAM/delay/sensor/controller resource must be costed in hardware, area, pins, routing, timing, or control complexity.

Bottom-thermal/top-voltage behavior is not hard-coded. Later asymmetric voltage and thermal models should represent physical asymmetry through PDN matrices, thermal coupling matrices, die/package profiles, and workload placement rather than fixed slogans.

Package/material effects are modeled through `PackageProfile` boundary conditions. The project must not claim that glass substrate or any specific package material universally improves all scenarios unless supported by explicit external evidence.

The zero hardware overhead claim remains forbidden. Acceptable language must be narrower and traceable, such as reuse of existing IEEE 1838-compatible abstract access resources under stated modeling assumptions.

## D21: B1 MVP AccessPath Timing Model

B1 introduces an abstract access path estimator for IEEE 1838-compatible scheduling research. It is not a bit-accurate implementation of IEEE 1838 and does not claim complete IEEE 1838 behavior modeling.

The MVP access time model is:

```text
access_time =
  path_select_bits / tck_frequency
+ config_bits / tck_frequency
+ data_bits / transfer_bandwidth
+ readback_bits / tck_frequency
```

PTAP/STAP/3DCR/DWR serial configuration and shift time are estimated with `bits / tck_frequency_hz`. FPP bulk data transfer time is estimated with `data_bits / (fpp_bandwidth_bits_per_s * lanes)`.

DWR access paths must include basic die path setup plus DWR mode configuration, DWR serial shift, and readback overhead.

FPP data paths must include PTAP/STAP target path setup and FPP configuration overhead before `FPP_TRANSFER`. FPP is modeled as an optional data transport resource, not a universal control path and not zero-cost.

The B1 estimator is deliberately independent of A0 scheduler internals. It prepares inputs for later TestIntent / ExecutionPhase expansion without changing existing scheduler behavior.

## D22: Repository State Must Match Landed Files

Project state documents must not claim that an experiment, workload, benchmark case, script, test, or result has been completed unless the corresponding files are present in the current repository checkout.

If a planned experiment is discussed before implementation, it must be labeled as future work or planned work. This applies especially to benchmark-derived workloads, realistic statistics cases, RTL mock validation, FPGA playback, and industrial tool correlation.

For the current checkout, the benchmark-derived workload schema and example adapter are completed, while the realistic UART statistics case is not completed because the expected YAML, experiment scripts, audit script, tests, and result directory are absent. The example benchmark audit is also not completed in this checkout because the expected audit script, audit test, and audit result directory are absent.
