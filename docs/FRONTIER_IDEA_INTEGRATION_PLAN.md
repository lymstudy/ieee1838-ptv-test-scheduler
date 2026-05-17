# FRONTIER IDEA INTEGRATION PLAN: PTVA-SSN-Inspired Extensions for IEEE 1838-Aware Layered Scheduling

## 1. Purpose and Scope

本文件用于把若干前沿启发纳入 B 阶段之后的长期研究规划，包括 PTVA-SSN-inspired scheduling ideas、interposer test-bus、UCIe-inspired health-event interface、HBM-like capture staggering、package/substrate-aware boundary condition 等。

本文件只做规划和伪代码设计，不表示当前系统已经实现这些功能。当前已实现系统仍然是：

- A0 task-level PTV scheduling prototype。
- B0 IEEE 1838-aware layered scheduler design spec。

后续任何实现都必须遵守术语边界和研究诚信约束：

- SSN is not part of IEEE 1838。
- UCIe is not part of IEEE 1838。
- FPP is optional and not zero-cost。
- SIB is not assumed to directly control FPP lane width。
- Zero hardware overhead claim is forbidden。
- DWR 表示 Die Wrapper Register。
- 不得声称当前项目已经实现真实 Siemens Tessent SSN、UCIe、HotSpot、RedHawk、Voltus 或真实芯片验证。

## 2. Idea A: Interposer Test-Bus / BNH / MBB Inspiration

2.5D interposer、active interposer 或 passive interposer 中可能存在的 test-bus 可以作为 future stack-level test traffic routing resource 的启发。当前项目不实现真实 BNH/MBB，而是保留以下抽象对象用于后续架构规划：

- `InterposerTestBus`：表示可在 stack/interposer 层转发 test data 或 test control tokens 的抽象总线。
- `BusNetworkHostLikeController`：BNH-like bus network host controller，用于未来建模 traffic gate、bandwidth arbitration 或 test-data router。
- `MidBondBypassSwitch`：MBB-like mid-bond bypass switch，用于启发 mid-bond / post-bond 阶段下的 bypass / partial-stack access modeling。

这些对象的潜在作用包括：

- mid-bond / post-bond test data routing。
- bypass partial stack。
- reduce dependence on purely serial PTAP path。
- isolate overheated or physically unsafe region。
- support traffic gating or bandwidth throttling。

当前 B1/B2 不实现这些功能。它们应进入后续 milestone：

- B11: Interposer Test-Bus-Aware Routing Extension。

## 3. Idea B: UCIe-Inspired Health Event / Throttling Interface

UCIe 3.0 中 fast throttle、emergency shutdown、open-drain event 这类低延迟健康/节流信号，对后续 scheduler/controller 的外部事件接口有启发意义。本项目不实现 UCIe，也不声称 IEEE 1838 包含 UCIe。这里只抽象为 external physical health event input。

建议抽象信号：

- `Cooling_Health_Status[1:0]`
- `Voltage_Health_Status[1:0]`
- `Package_Stress_Event`
- `Emergency_Throttle_Event`

状态编码建议：

```text
00 = normal
01 = warning
10 = throttle_required
11 = emergency_safe_mode
```

调度器或 playback controller 可将这些信号作为 external event input：

- `warning`：reduce FPP bandwidth。
- `throttle_required`：block high-power scan/capture。
- `emergency_safe_mode`：allow only BIST result readback, instrument access, or safe dummy cycles。

该接口是 future external-event interface inspiration：

- 不是 UCIe 实现。
- 不是 IEEE 1838 标准内容。
- 不能用于声称 FPGA 或本项目能验证真实 UCIe 3.0 PHY。
- 后续可用于 controller / FPGA playback / external health hook 的抽象接口。

建议加入 future milestone：

- B12: External Health Event-Aware Schedule Playback。

## 4. Idea C: HBM-like Vertical PDN and Capture Staggering

高层堆叠、TSV / vertical PDN、hybrid bonding 等场景会放大 capture transient current 导致的 IR-drop 风险。因此后续应将 capture staggering 从全局限制扩展为 power-pillar-aware 机制。

建议定义：

- `PowerPillar`：一个 vertical power delivery path 或近似供电柱抽象。
- `VerticalPDNGroup`：共享局部 vertical PDN 风险的一组 die/core/scan region。

每个 die、core 或 scan region 可映射到一个 `power_pillar_id`。Capture phase 需要满足：同一 `power_pillar_id` 内同一 capture window 最多允许 `max_capture_per_pillar` 个 capture。

伪代码：

```text
for each candidate capture phase:
    if active_capture_count[power_pillar_id] >= max_capture_per_pillar:
        delay candidate or insert capture offset
```

Capture staggering 后续应从当前简单 `max_concurrent_capture` 扩展为：

- global capture limit。
- per-power-pillar capture limit。
- per-die capture limit。
- capture offset assignment。
- dummy cycle / capture offset / capture window assignment to reduce peak current。

建议加入 future milestone：

- B4.1: PowerPillar-Aware Capture Staggering。

## 5. Idea D: Package/Substrate-Aware Boundary Condition

不同 substrate / package material 会改变 thermal、warpage、contact resistance 和 PDN boundary condition。当前项目不声称已经验证 glass substrate，也不声称 glass substrate 一定优于所有场景。后续只通过 `PackageProfile` 抽象改变仿真边界条件。

建议定义 `PackageProfile`：

- `package_type`
- `substrate_material`
- `thermal_boundary_factor`
- `cooling_beta_scale`
- `pdn_resistance_scale`
- `max_shift_frequency_scale`
- `fpp_bandwidth_scale`
- `warpage_margin_factor`
- `contact_resistance_variation_factor`

示例 profiles：

1. `organic_substrate`
2. `glass_substrate`
3. `silicon_interposer`
4. `advanced_interposer`

`PackageProfile` 只改变仿真边界条件，例如 thermal limit、cooling beta、PDN resistance matrix、max shift frequency、FPP bandwidth limit 和 contact/warpage margin。它不是材料优劣结论，也不是实测封装验证。

建议加入 future milestone：

- B13: PackageProfile-Aware Constraint Boundary Modeling。

## 6. Netlist / RTL Architecture Planning

以下是规划级 RTL / netlist 架构草案，不实现代码，不声称兼容完整 IEEE 1838 RTL。

- `ieee1838_access_controller`：负责 PTAP/STAP/3DCR/DWR/FPP 配置抽象，是顶层访问控制入口。
- `ptap_stap_path_controller`：管理 PTAP/STAP path select、open、bypass、path occupation。
- `dwr_mode_controller`：管理 Die Wrapper Register mode configuration、shift、capture、update/readout 抽象。
- `fpp_config_controller`：管理 optional FPP lane configuration、availability、bandwidth limit 和 data transport setup。
- `bist_trigger_readback_controller`：触发本地 BIST，管理本地执行状态和 result readback。
- `instrument_access_controller`：管理 instrument network read/write，可扩展 flat network、SIB hierarchical network 或 daisy chain network。
- `scan_stream_interface`：连接 scan shift/capture/readback phase 和 FPP/TAM-like data transfer。
- `ssn_like_tam_adapter`：future optional die-level streaming scan/TAM abstraction，不是 Siemens SSN 实现。
- `physical_health_event_interface`：future optional，用于接入外部 health/throttle/status event。
- `schedule_playback_controller`：用于 FPGA/RTL mock 阶段回放 scheduler 生成的 command sequence。
- `capture_stagger_controller`：执行 capture offset、global capture limit 和 per-pillar capture limit。
- `dummy_cycle_controller`：执行 cooling / voltage recovery dummy cycle。

禁止使用以下表述：

- 完全兼容 IEEE 1838 RTL。
- zero hardware overhead。
- 已实现 UCIe。
- 已实现 Siemens SSN。

## 7. Algorithm Pseudocode Extensions

### 7.1 Predictive Access-Path and Physical-Aware Scheduler

输入：

- ExecutionPhase graph。
- AccessPath cost。
- Physical state。
- PackageProfile。
- PowerPillar map。
- HealthEvent status。

伪代码：

```text
while unfinished phases exist:
    update physical state
    read external health event
    generate ready phase set

    for each candidate:
        estimate access_path_cost
        estimate path_blocking_cost
        predict thermal risk over horizon H
        predict voltage risk over horizon H
        check capture pillar conflict
        check FPP/TAM resource
        check health-event safe mode
        compute score

    choose feasible phases

    if no feasible phase:
        insert dummy cycle or safe low-power phase

    update schedule
```

### 7.2 Health-event-triggered Safe Mode

```text
if Emergency_Throttle_Event:
    block scan shift and capture
    allow only low-power instrument readback or BIST status readback
    reduce FPP bandwidth to safe level
    insert dummy cycles until health state recovers
```

### 7.3 FPP + SSN-like TAM Co-allocation

```text
for each scan transfer:
    allocate stack-level FPP lanes
    allocate die-level TAM/SSN-like bandwidth
    effective_bandwidth = min(FPP_bandwidth, TAM_bandwidth)
    compute transfer_time
```

这里的 SSN-like TAM 只表示 streaming-scan-inspired die-level TAM abstraction，不是 Siemens Tessent SSN 实现，也不是 IEEE 1838 标准内容。

### 7.4 PackageProfile-aware Constraint Update

```text
thermal_limit_i = base_thermal_limit_i * package.thermal_boundary_factor
R_matrix = base_R_matrix * package.pdn_resistance_scale
max_shift_frequency = base_shift_frequency * package.max_shift_frequency_scale
```

## 8. Updated Research Roadmap

- B1: AccessPath data model and path cost estimator。
- B2: TestIntent to ExecutionPhase layered expander。
- B3: Access-time-aware scheduler。
- B4: Predictive path-blocking-aware PTV scheduler。
- B4.1: PowerPillar-aware capture staggering。
- B5: Asymmetric voltage matrix and thermal coupling。
- B6: SSN-inspired die-level TAM abstraction。
- B7: FPP/SSN co-allocation。
- B8: FPP hardware cost model。
- B9: Ablation study。
- B10: MILP small optimal baseline。
- B11: Interposer test-bus-aware routing extension。
- B12: External health event-aware schedule playback。
- B13: PackageProfile-aware constraint boundary modeling。
- B14: RTL mock validation。
- B15: public benchmark-derived statistics case。
- B16: optional FPGA playback。
- B17: optional tool correlation。

B1 仍是下一步立即任务。B4.1 及 B6-B17 均为后续路线，不是当前已实现功能。

## 9. What Not to Claim

禁止表述：

- 不要声称已实现完整 IEEE 1838。
- 不要声称 IEEE 1838 包含 SSN。
- 不要声称 SIB 直接控制 FPP lane width。
- 不要声称已实现 UCIe。
- 不要声称 zero hardware overhead。
- 不要声称 FPGA 能验证真实 3D thermal/IR-drop。
- 不要声称 glass substrate 一定提升所有场景。
- 不要把 manually specified realistic stats 写成 RTL-extracted benchmark。
- 不要把 future external health event interface 写成已实现硬件接口。
- 不要把 InterposerTestBus、PowerPillar、PackageProfile 写成当前代码已有对象。
