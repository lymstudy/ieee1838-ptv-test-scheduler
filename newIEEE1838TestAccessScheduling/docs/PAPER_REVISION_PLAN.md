# 论文修正计划：故事线重构、实验修补与重点绘图方案

> 状态：v3，整合 IEEE 1838 标准物理模型审计
> 基于：IEEE 1838-2019 标准全文 + M17/M22 自审计结论 + 4 篇参考文献深度阅读 + 代码模型审计

---

## 〇、物理模型审计（v3 新增）

### 0.1 审计来源

三线并行审计：
1. IEEE 1838-2019 标准全文（`REFERENCE/IEEE Standard for Test Access Architecture for Three-Dimensional Stacked Integrated Circuits.pdf`）
2. 现有代码模型审计（`src/model/system_model.py`、`src/recipes/generator.py`、`src/schedulers/*.py`、`configs/cases/*.json`）
3. 四篇文献的物理建模方式对比

### 0.2 现有模型做对了什么

| 建模点 | 代码实现 | 与标准一致性 |
|--------|---------|------------|
| 多 target 同属一个 die | 每个 die 可包含多个 test_object（core/memory），各自独立调度 | ✅ 正确——标准中每个 die 可测试多个模块 |
| BIST 是可选的非强制的 | `bist.enabled: true/false`，M10 中只有 memory 类型有 BIST | ✅ 正确——标准明确 BIST 是 design-specific |
| PTAP/STAP 串行路径是共享资源 | greedy 用 `ptap_ports=1` + `AddNoOverlap`，CP-SAT 同理 | ✅ 正确——串行 TDI→TDO 链是唯一共享通路 |
| 访问深层 die 有 STAP 配置开销 | `die_path_to()` 计算路径上所有 STAP/3DCR 的 setup bits | ✅ 正确——必须先配 Die1 STAP → 再配 Die2 STAP 级联 |
| BIST 执行期间释放串行通路 | `LOCAL_BIST_RUN` 阶段 `serial_required: false` | ✅ 正确——BIST 本地跑，外部 TAP 可做其他事 |
| DWR 按 die 分配冲突组 | `exclusive_resource = test_session_{die_id}` | ✅ 正确——同一 die 不能同时跑两个占用 DWR 的测试 |
| 互联测试需要两侧 die | I recipe 建模 EXTEST 需要双方 DWR 段 | ✅ 正确 |

### 0.3 现有模型做错了什么——需要修正

#### 🔴 严重问题 1：FPP 和串行 TAP 被建模为互斥替代路径（而非同时工作的互补资源）

**事实：** FPP IS 定义在 IEEE 1838-2019 标准中：
- Clause 5.5.3: "Flexible parallel port configuration register"
- Clause 6.5: "Parallel access to the DWR" -- optional parallel wrapper access mechanism called FPP
- Clause 7 (pages 57-66): Full specification of the Flexible Parallel Port
FPP 使用独立的物理 lane，与串行 TAP 信号（TCK/TMS/TDI/TDO）是物理分离的。

**代码现状：** S recipe（纯串行）、F recipe（FPP 数据传输）被建模为互斥的替代选择 -- schedule 只能选一个 recipe 类型。但实际上 FPP 可以在串行 TAP 用于控制和配置的**同时**传输测试数据。

**影响：**
- 代码把 FPP 和串行 TAP 建模为互斥 recipe 类型（per target pick one），忽略了 FPP 和串行 TAP 可同时工作的物理事实
- 论文可以正确声称 IEEE 1838 兼容（FPP 是标准定义的可选组件），但代码的"互斥替代"模型未充分利用 FPP 的并行潜力

**修正方向：**
- FPP 不需要标注为 "proposed extension" -- 它是 IEEE 1838 标准定义的可选组件（Clause 7）
- 不需要引用 UCIe 来证明 FPP 的可行性 -- FPP 有自己的标准定义
- 真正的建模问题是：是否改进 recipe 模型以支持串行 TAP 和 FPP 的并行操作

#### 🔴 严重问题 2：代码建模细节 -- FPP 和串行 TAP 应是互补的，非互斥替代

**事实：** IEEE 1838-2019 Clause 7 定义的 FPP 使用独立的物理 lane，与串行 TAP 信号（TCK/TMS/TDI/TDO）是物理分离的。FPP 可以在串行 TAP 用于控制和配置的**同时**传输测试数据。

**代码现状：** S recipe（纯串行）、F recipe（FPP 数据传输）被建模为互斥的替代选择——schedule 只能选一个 recipe 类型。

**物理真相：**
```
时间轴上的正确画法：
  PTAP/STAP: |--cfg die1--|--cfg die2--|--start BIST die2--|--cfg die3 scan--|--shift scan data--|--read BIST die2--|
  FPP lanes:  |            |            |                   |                 |--parallel data--||                  |
  BIST die2:               |            |--LOCAL RUN (不占 PTAP)--------------------------------------|
```

- 串行 TAP 负责**所有**路径配置和控制
- FPP 只是一个**更快的数据传输通道**（替代串行 shift），不替代控制路径
- BIST 是本地执行，释放串行 TAP 但不占用 FPP
- **一个 die 上可以有多个不同类型的测试任务**（BIST + scan + EXTEST），它们是独立的调度单元

**修正方向：**
- 将 "recipe 类型互斥选择" 改为 **"测试类型 × 传输方式"的二维组合**
  - 测试类型：INTEST（内部扫描）、EXTEST（互联测试）、BIST（自测试）、IJTAG instrument access
  - 传输方式：Serial shift（标准）/ FPP parallel（标准, Clause 7, optional）
- 串行 TAP 的调度变成：**谁先用这条共享的总线做配置和数据传输**
- BIST 任务的特征：配置阶段占用 TAP → 本地执行释放 TAP → 读回阶段重新占用 TAP
- Scan 任务的特征：配置→shift→capture→shift→读回，全程占用 TAP
- FPP 的调度变成：**数据阶段可以用 FPP 替代串行 shift，但控制阶段必须走 TAP**

#### 🟡 中等问题 3：测试任务应该按"测试类型"划分而非按"芯粒"

**事实：** IEEE 1838 标准中，每个 die 的测试包括：
- **INTEST**（内部测试）：通过 DWR 的 IF（inward-facing）模式访问 die 内部 scan chain
- **EXTEST**（互联测试）：通过 DWR 的 OF（outward-facing）模式测试 die-to-die 互联
- **BIST**（可选）：本地自测试引擎
- **IJTAG instrument access**（可选）：通过 IEEE 1687 SIB 网络访问 die 内 instruments

**代码现状：** 每个 target（core/memory）有多个 recipe 类型（S/F/B/H/I），但 **S/F/B/H 四种替代关系混淆了测试类型和传输方式**：
- S recipe = INTEST via serial scan
- F recipe = INTEST via FPP parallel（传输方式变了，测试类型没变）
- B recipe = BIST（测试类型变了）
- H recipe = BIST + FPP 混合（混淆）

**物理真相：** 一个 target 的真实选择空间应该是：
```
target "core_A on die1":
  测试方式: 只能 scan（没有 BIST 硬件）→ 这是物理约束
  传输方式: serial 或 FPP（取决于设计是否有 FPP lane 连到这个 die）
  
target "memory_B on die1":
  测试方式: BIST 或 scan → 两种都物理可行
  传输方式: BIST 不需要大量数据传输（本地跑），scan 需要 serial 或 FPP
```

**修正方向：**
- 把 "recipe 类型"（S/F/B/H/I）拆成两层：
  1. **测试方式层**：INTEST / EXTEST / BIST / IJTAG（物理决定，不可互换）
  2. **传输方式层**：Serial shift / FPP parallel（加速选项，不改变测试内容）
- 修正后的 recipe 模型：recipe 不改变测试类型，只提供**同一种测试的不同执行方案**（不同 TAM width / 不同 lane count / 不同 phase 编排）

#### 🟡 中等问题 4：互联测试（EXTEST）的建模不完整

**事实：** IEEE 1838 的 EXTEST 需要**两侧 die 的 DWR 同时参与**——驱动端 die 的 DWR 输出单元施加激励，接收端 die 的 DWR 输入单元捕获响应。

**代码现状：** I recipe 作为一个独立的 recipe 存在，但它是针对单个 target（interconnect 类型的 target）的。物理上，这个操作涉及两个 die 的资源。

**修正方向：**
- EXTEST 任务应该显式地占用**两个 die** 的 DWR 资源
- 互联测试应该是一个跨越 die 边界的调度单元

#### 🟢 轻微问题 5-7

| 问题 | 描述 | 严重程度 | 修正成本 |
|------|------|---------|---------|
| TAP 状态机开销 | 串行时间用 `bits/tck_hz`，忽略了 Capture-DR/Update-DR/IR scan 的额外周期 | 轻微（shift 主导的场景下影响 <1%） | 低 |
| 3DCR 位域未细分 | IEEE 1838 定义 STAP_Control/DWR_Control 等独立字段，代码用 flat bit_length | 轻微（总和正确就不影响时间） | 低 |
| BIST 优先级硬编码 | greedy scheduler 中 `{"B": 0, "F": 1, ...}` 是启发式而非物理保证 | 轻微（只影响 tie-breaking） | 极低 |

### 0.4 修正后的物理模型——IEEE 1838 测试访问的正确抽象

```
3D Stack 测试访问的正确时间线模型：

Stack: Die0 (bottom, with external I/O) → Die1 → Die2 → Die3 (top)

串行 TAP 通路 (TCK/TMS/TDI/TDO) —— 整个栈只有一条，共享资源，容量=1
FPP 通路 (IEEE 1838-2019 Clause 7, optional) —— 独立物理 lane，与串行 TAP 可同时工作

测试任务列表（每个任务是独立的调度单元）：
  Die0: [INTEST_core0, INTEST_core1, EXTEST_die0_die1, BIST_memory0]
  Die1: [INTEST_core2, EXTEST_die0_die1, EXTEST_die1_die2]
  Die2: [INTEST_core3, EXTEST_die1_die2, EXTEST_die2_die3, BIST_memory1]
  Die3: [INTEST_core4, EXTEST_die2_die3]

每个任务的执行阶段（以 Die2 BIST_memory1 为例）：
  Phase 1: CONFIG_PATH —— 通过 TAP 配置 Die0 STAP(select) → Die1 STAP(select) → 到达 Die2
  Phase 2: CONFIG_BIST —— 通过 TAP 配置 Die2 的 BIST 控制器（指令+参数）
  Phase 3: BIST_RUN —— BIST 本地执行，释放 TAP，释放 FPP
  Phase 4: READ_RESULT —— 重新通过 TAP 访问 Die2，读出 BIST 签名

每个任务的资源占用签名：
  INTEST via serial: 全程占用 TAP（Phase1→Phase2→Phase3→Phase4 都串行）
  INTEST via FPP:    Phase1+2 占用 TAP，Phase3 通过 FPP 传数据（TAP 可被其他任务用）
  BIST:              Phase1+2 占用 TAP，Phase3 本地执行（释放 TAP），Phase4 占用 TAP
  EXTEST:            占用两侧 die 的 DWR + 全程占用 TAP（或 Phase3 用 FPP）

关键调度洞察（这才是真正的研究贡献）：
  - TAP 是瓶颈资源 → BIST 任务可以"使用 TAP → 释放 → 再使用"，在释放期间让其他任务用 TAP
  - 调度问题变成：如何安排 TAP 的时分复用，使得总 makespan 最短
  - 如果引入 FPP：Phase3 的数据传输可以走 FPP 而不是 TAP（但 Phase1/2/4 必须走 TAP）
  - FPP 不改变"需要 TAP 配置"这个事实——FPP 是数据通路的加速器，不是控制通路的替代品
```

### 0.5 修正后的论文定位

**旧定位：** "联合路径选择与调度"（BIST vs FPP 互斥选择）

**新定位：** **"IEEE 1838 串行 TAP 的时分复用调度——利用 BIST 本地执行期间释放的 TAP 时间窗口，配合可选的 FPP 并行数据通路加速"**

核心创新从 "joint path selection" 变为 **"TAP time-multiplexed scheduling with local-BIST-aware window exploitation"**。

这更诚实、更符合物理、也更有学术价值——因为它解决的是 IEEE 1838 标准内真实存在的串行瓶颈问题。

---

## 一、现状诊断（保留原内容，更新关键判断）

### 1.1 四篇文献的核心发现

| 论文 | 核心发现 | 对本研究的启示 |
|------|---------|--------------|
| **Habiby 2020** (DFT) | Dijkstra 最短路径 + BFS 并发表 + 二叉决策树功率剪枝 | 图建模方法对应本研究的 Recipe 生成，**应作为 baseline** |
| **Habiby 2022** (Microelectronics Reliability) | SAT/CNF 网络结构建模 + PBO 增量优化 + ILP 全局优化 + Glover 线性化 | 四篇中方法最成熟，直接对应本研究的 CP-SAT 框架，**必须实现为 baseline** |
| **Patmanathan 2024** (ICSE) | Pareto cube + ACO 选择 + RHDF 散热因子 + 邻接排斥 + HotSpot 6.0 验证 | 与本研究的 Recipe 概念高度对应，实验改善仅 **0.2%**——说明此领域方法差异小是正常的 |
| **Sen Gupta 2011** (DELTA) | 三种策略 (SP/PO/RS) + Session Pair 重组 + BIST 控制线 trade-off | 最大 TAT 减少 **17.1%**，平均 **7.7%**——给出了本领域合理的增益预期，**应作为 baseline** |

**关键结论：** Patmanathan 2024 只有 0.2% 改善，Sen Gupta 2011 平均只有 7.7%——这个领域的已发表论文本身增益就不大。本研究在普通 benchmark 上得到 0% gain 并不反常，反常的是论文叙事把它包装成了"普遍有效的方法"。

### 1.2 当前核心矛盾

论文标题声称的方法是"电热感知测试访问路径生成与协同调度方法"，暗示一个**普遍有效**的方法。但 M17/M22 的自审计显示：

| 场景 | 联合调度增益 | 意味着什么 |
|------|------------|-----------|
| 普通 M10 benchmark（12 个 case） | **0.00%** | 一般场景下，固定路径 + 调度已经足够 |
| 共享 BIST + 无替代路径（12 个 case） | **0.00%** | 有瓶颈但没得选，等于没优化空间 |
| 私有 BIST（12 个 case） | **0.00%** | 没有瓶颈就不需要联合优化 |
| 共享 BIST + 有替代路径（12 个 case） | **25.84%** | 瓶颈与替代共存时才产生增益 |

**结论：联合调度只在"共享资源瓶颈 + 替代路径共存"的双条件同时满足时才有效。现有论文叙事没有诚实反映这个限制。**

### 1.3 文献对比揭示的六个额外问题

**a) 没有实现任何文献方法作为对比基线（最致命）**

M11 对比的 8 个方法全是自己写的（pure_serial, fixed_fastest, tam_like, low_power, m4, m5, m6）。没有实现 Habiby 2022 的 PBO、Sen Gupta 2011 的 PO/RS 等已发表基线。审稿人会问："你和谁比？"

**b) ALNS 不是真正的 ALNS**

ALNS 的定义性特征是**自适应权重更新**（根据 destroy/repair 的历史表现调整算子选择概率）。当前实现是 round-robin 循环——这只是一个随机局部搜索，不是 ALNS。M11 中 ALNS 比所有非 serial 方法都差（avg speedup 2.95），medium 场景全部被跳过（max_alns_targets=16）。

**c) 热模型是装饰品**

| 指标 | M7 代理模型 | HotSpot 6.0 |
|------|------------|------------|
| d695 5.5D peak temp | 25.09 °C | 60.79 °C |
| p22810 3D peak temp | 25.12 °C | 60.61 °C |
| 跨方法温差 | ~0.1 °C | ~2 °C |

- 一阶 RC 代理的绝对温度不可信（比环境温度 25°C 只高了不到 0.5°C）
- 所有 scheduler 的温度差异仅 0.1 °C 量级——**热约束实际上没有生效**
- "电热感知"这个说法名不副实

**d) CP-SAT 从未证明最优性**

M11 的 solver status 全部是 **FEASIBLE**，没有一行 **OPTIMAL**。无法区分 M5 比 M4 好 0.0005 是因为算法好还是搜索运气好。没有 optimality gap 分析。

**e) Benchmark 数据全是模型假设**

所有功耗、热阻、热容、FPP 带宽等参数标签为 `model_assumption`。没有真实 Chiplet/HBM/interposer 的测试数据。所有"加速比"都在自己设定的参数空间内循环。

**f) B 阶段核心建模未完成**

原 ROADMAP 中 B3-B10 全部未完成。PTAP/STAP 串行级联配置时间、DWR shift/capture/update 阶段细分、3DCR select/bypass 行为均明确列为"尚未建模"。

### 1.4 现有 12 张图的质量问题

| 现有图 | 致命问题 |
|--------|---------|
| `m13_m10_speedup` | 单一配置的柱状图，信息密度极低 |
| `m13_m11_algorithm_makespan` | 所有方法几乎一样高（0.339 → 0.338），读者一眼判定"方法没用" |
| `m13_proxy_hotspot_comparison` | 25°C vs 60°C 的巨大偏差并列，审稿人会质疑代理模型无意义 |
| `m13_hotspot_heatmap` | 孤立的单张热力图，无对比、无变化、无结论 |
| `m13_gantt` | 早期 4-die 例子，空荡荡的 Gantt |
| `m16_resource_gantt` | xlarge case 塞了 12 个 target，bar 细得像线 |
| `m16_power_temp_hotspot` | 三条曲线 + 两个方块 + cbar，信息过载无焦点 |
| `m16_method_comparison` | 四个子图所有 bar 几乎等高，展示不出任何 tradeoff |
| `m16_coverage_matrix` | 本质是表伪装成图，无信息增量 |
| `m19_pressure_gantt` | 仅用 M18 手工 case，标签挤爆、说服力弱 |
| `m19_resource_occupancy` | 仅 2 个手工 case 的数据点，无法泛化 |
| `m19_pressure_summary` | 同样是 2 个 case，共 4 个 bar |

**共同问题：要么展示"没差异"（平 bar），要么只展示极端手写特例（2 个手工 case），要么信息密度低到没有存在价值。**

---

## 二、修正后的论文故事线

### 2.1 论文定位

从"提出一个通用的联合调度方法"修正为：

> **"发现、刻画并证明了 IEEE 1838 测试访问中路径-调度联合优化的生效条件"**

这是一个 **characterization paper**（特征刻画型论文），不是 performance claim paper（性能宣称型论文）。

**这一修正有文献支撑：** Patmanathan 2024 在相似问题上仅获得 0.2% 的改善，Sen Gupta 2011 的 session 重组方法平均只有 7.7% 的 TAT 减少。这说明该领域在普通场景下的优化空间本身就很小——你的 0% gain 不是失败，而是与文献一致的发现。真正的学术贡献在于**严格刻画了"什么时候联合优化才有用"**。

### 2.2 修改后的论文叙事结构

**Step 1 — 建模（贡献 1：Recipe 抽象 + IEEE 1838 可计算模型）**

> 我们将 IEEE 1838 标准定义的串行访问（PTAP/STAP）、FPP 并行传输、BIST 本地执行等异质测试模式，统一抽象为 Test Access Recipe（S/F/B/H/I）。每个 recipe 包含完整的资源占用签名（PTAP 串行时间、FPP lane 需求、DWR 配置阶段、BIST 执行时间、峰值功耗、热区域标记），使路径选择变成一个可优化的组合问题。这类似于 Patmanathan 2024 的 Pareto cube，但我们的 recipe 显式建模了 IEEE 1838 的多资源互斥约束，而不仅仅是 TAM width × test time × power 的三维 tradeoff。

**Step 2 — 发现（贡献 2：条件性机制的发现）**

> 在 12 个 ITC'02 衍生 benchmark × 3 种拓扑 (2.5D/3D/5.5D) = 216 行调度实验后，我们发现了一个与直觉相反的结果：在 8 FPP lane + nominal power 的默认配置下，固定选最快路径 + CP-SAT 约束调度就已经是最优解，联合路径-调度优化没有任何额外增益（0.00%）。这与 Habiby 2022 的发现一致——他们的 PBO 增量优化在大多数 benchmark 上也无法超越固定路径策略。也与 Sen Gupta 2011 的发现一致——Partial Overlapping 在不拆分 session 的情况下与 ReScheduling 结果相同。

**Step 3 — 假设与验证（贡献 3：双条件消融实验）**

> 我们提出假说：联合优化只有在（A）存在共享资源瓶颈 AND（B）存在替代访问路径时，才可能产生增益。通过 4 组受控消融实验 × 12 个 ITC'02 衍生 case = 192 行调度数据，我们严格验证了这一假说：
> - 无压力（control）：0.00% gain
> - 有压力但无共享瓶颈（private BIST）：0.00% gain
> - 有共享瓶颈但无替代路径（shared BIST, no FPP/hybrid）：0.00% gain
> - 共享瓶颈 + 替代路径共存（shared BIST, with FPP/hybrid）：平均 **25.84%** gain，范围 10.00%-37.50%

**Step 4 — 量化刻画（贡献 4：压力梯度连续响应）**

> 我们进一步对资源压力程度和替代路径多样性做了参数扫描，刻画了增益从 0% 到 ~47% 的连续响应曲线，为设计者提供了一个可操作的决策参考："当你的设计有 X 程度的资源共享和 Y 条替代路径时，预期能获得 Z% 的测试时间改善。"

**Step 5 — 拓扑分析（贡献 5：拓扑差异的物理解释）**

> 在三种封装拓扑中，3D stack 受益最大（35.3%），因为其垂直 TSV 密度低（FPP lane 少）且热耦合强，共享 BIST 瓶颈最严重。2.5D interposer 受益最小（19.1%），因为 interposer 提供了充足的 FPP lane，瓶颈相对缓和。这与 Patmanathan 2024 的发现一致——3D 堆叠的热邻接问题比 2.5D 更严重，布局规划在 3D 场景中更有价值。

**Step 6 — 讨论：与文献方法的关联**

> 我们将结果与 Habiby 2022 的 PBO 方法和 Sen Gupta 2011 的 PO 方法进行了对比，分析了它们在不同 benchmark 类型上的表现差异，并讨论了 CP-SAT 编码相对于 SAT/PBO 编码在 IEEE 1838 多资源约束表达上的优势。

### 2.3 各创新点的诚实表述

| 创新点 | 原宣称 | 修正后的表述 |
|--------|--------|------------|
| Recipe 模型 | "提出了 Test Access Recipe" | 同左，但强调这是**建模贡献**——类似于 Patmanathan 2024 的 Pareto cube 但显式建模了 IEEE 1838 的多资源互斥约束 |
| 路径-调度联合优化 | "联合优化优于固定路径" | **"我们发现联合优化仅在共享瓶颈+替代路径共存时有效，并通过 4 组消融 × 12 case = 192 行实验严格证明了双条件必要性"** |
| 统一 2.5D/3D/5.5D 建模 | "统一建模框架" | **"统一模型中，三种拓扑的资源差异导致不同的瓶颈特征和增益幅度"** |
| 热感知验证 | "电热闭环优化" | 降级为 **"热代理趋势验证 + HotSpot 离线抽样确认"**；代理模型仅在调度排名上与 HotSpot 一致（3/3），绝对温度不可信 |
| CP-SAT+ALNS 混合 | "混合求解器创新" | 降级为 **"CP-SAT 作为精修调度后端"**；ALNS 当前实现缺少自适应权重更新（为 round-robin），不满足 ALNS 的定义性特征，降为扩展原型 |

---

## 三、实验修补方案

### 3.1 P0（必须做）：实现文献对比基线

**目标：** 在相同的 benchmark 上，与至少 2 篇已发表论文的方法进行公平对比。

#### Baseline 1：Habiby 2022 PBO 增量调度

**对应原文：** Habiby 2022, Section 6 (PBO-based Incremental Optimization)

**算法：**
1. 将 Recipe 选择建模为 SAT/CNF：
   - 每个 recipe 对应布尔变量 `xᵢ ∈ {0,1}`
   - 互斥约束（PTAP 串行）= SAT 分支节点 CNF（Habiby 2022 Eq. 2）
   - 资源容量约束（FPP lane）= PBO 求和约束 `Σ lanesᵢ · xᵢ ≤ max_lanes`
   - 功耗约束 = `Σ powerᵢ · xᵢ ≤ Pmax`
2. 目标函数：`F = Σ weightᵢ · xᵢ`（最大化当轮覆盖的 test targets）
3. 增量求解：
   - 每轮求解 PBO，最大化该 session 的并发 active instruments
   - 覆盖够访问次数的 instrument 从 pool 中移除
   - 最多 N 轮（N = instrument 数量），上界保证
4. 使用开源 clasp solver（https://github.com/potassco/clasp）或 OR-Tools SAT

**Habiby 2022 原论文指标参考：**
- 适用范围：1000+ instruments
- 解的质量：局部最优，与 ILP 全局最优的 MAPE < 10%
- Runtime：秒级

#### Baseline 2：Sen Gupta 2011 Partial Overlapping (PO)

**对应原文：** Sen Gupta 2011, Section IV (Strategies for Post-bond Test Scheduling)

**算法：**
1. 将每个 die 的 pre-bond schedule 作为独立 session
2. Post-bond 阶段：检查不同 die 的 session 是否可以功率兼容地并置
   - 从两个 chip 各取 session (Sx, Sy)
   - 如果 `P(Sx) + P(Sy) ≤ Pmax`，则它们可以并行
3. 贪心匹配最大的可并置 session pair
4. 报告 TAT vs. Serial Processing baseline 的减少量

**注意：** Sen Gupta 的 ReScheduling (RS) 策略需要拆分 session 并重组测试，这对应的正是 ALNS 的 destroy/repair 操作。如果 ALNS 被降级，RS 可作为此方向的 literature baseline 引用。

#### 实现优先级

| Baseline | 工作量 | 依赖 |
|----------|--------|------|
| Habiby 2022 PBO | 3-5 天 | 需安装 clasp solver 或使用 OR-Tools SAT |
| Sen Gupta 2011 PO | 1-2 天 | 无额外依赖 |

### 3.2 重构 Benchmark 分类：A 类（覆盖验证）/ B 类（机制验证）

**目标：** 让方法差异在合理的场景中显现，而不是用无效场景。

#### A 类 — 规模与覆盖验证（原 M10）

- **用途：** 展示方法在多种规模/拓扑下**能跑、能正确建模、可扩展**，不用于宣称方法优势
- **对比方法：** serial baseline, fixed-fastest, M4 greedy, Habiby 2022 PBO, Sen Gupta 2011 PO
- **指标：** 归一化 makespan（相对 serial = 1.0）, runtime, FPP 利用率
- **预期结果：** fixed-fastest ≈ M4 greedy ≈ Habiby PBO ≈ Sen Gupta PO（均大幅优于 serial），差异在 1% 以内

#### B 类 — 机制验证（原 M21/M22，扩展）

- **用途：** 展示在共享资源压力场景下，联合调度的**真实增益**
- **为什么 B 类场景在 3D-IC 中普遍：**
  - 多个 die 共享有限 TSV 做 BIST 访问——这是 IEEE 1838 3D stack 的根本特征
  - 多个 die 共享 FPP lanes——物理 lane 数受限于 interposer/bridge 金属层
  - 热邻接冲突——3D 堆叠中 die 上下紧贴，Patmanathan 2024 明确的 Layout Rule 1: hot modules 不邻接
- **对比方法：** 全方法对比（包括 Habiby 2022 PBO、Sen Gupta 2011 PO）
- **预期结果：** M5 CP-SAT ≈ M4 greedy > 所有 baseline，增益来源于 recipe mix（BIST + FPP 混合而非纯 BIST）

### 3.3 P1（强烈建议）：修复 ALNS 使其成为真正的 ALNS

若不修复，当前 round-robin 循环不满足 ALNS 的定义性特征（自适应权重更新）。

**修复内容：**
1. 实现自适应权重更新：`w_d = λ·w_d + (1-λ)·score`（基于 destroy/repair 的历史表现）
2. 扩大支持范围（当前 max_alns_targets=16 太受限，应至少覆盖 medium case 的 22 targets）
3. 在 B 类 benchmark 上展示 ALNS 能改善 CP-SAT feasible 解

**如果时间不够：** 直接砍掉 ALNS 作为核心贡献，论文改为 "CP-SAT based constrained optimization"，ALNS 降为 Appendix 中的 "extension prototype"。

### 3.4 P1（强烈建议）：升级热模型使其至少能区分调度策略

当前热代理的跨方法温差仅 0.1 °C，相当于没有生效。

**最小可行改进：**

1. **实现 die-to-die thermal coupling：**
   - 在 RC 网络中加入相邻 die 之间的热传导路径（R_inter_die, C_inter_die）
   - 参考 Patmanathan 2024 的 VHDF（垂直散热函数）概念：下层 die 的热量通过上层 die 向上传导至 heat sink，距离 heat sink 越远的 die 散热越差

2. **计算每 die 的等效 RHDF（相对散热因子）：**
   - RHDF = HHDF × VHDF × Power trace（Patmanathan 2024 Eq. 2）
   - HHDF = die 到层四边水平距离之和
   - VHDF = 层到 heat sink 的垂直距离
   - 按 RHDF 降序排列调度优先级：散热差的 die 先调度

3. **将 RHDF 作为 CP-SAT 的软约束或目标函数惩罚项**

4. **扩展 HotSpot 验证：** 从当前 6 行扩展到 20+ 行，覆盖 3 种拓扑 × 3 种规模 × 2-3 种调度方法

**效果验证标准：** 确保热代理在不同调度策略间产生至少 5-10 °C 的温差，使其有意义地区分"热感知调度"和"非热感知调度"。

### 3.5 P2（建议）：补充 CP-SAT Optimality Gap 分析

- 对 small 场景，增大 time limit 让 CP-SAT 跑到 OPTIMAL
- 对 medium/large 场景，报告 best bound 和 optimality gap
- 绘制 gap vs. problem size 曲线
- 这比声称"我们用了 CP-SAT"有说服力得多

### 3.6 P2（建议）：补 B 阶段核心建模

至少完成：
- PTAP/STAP 串行级联的配置时间模型（参考 Habiby 2020 的 Dijkstra 延迟计算——只需两次 Dijkstra 即可得到所有 instrument 的 write + read latency）
- DWR 的 shift/capture/update 阶段细分
- 将 AccessPath 的时间估算校准到至少一个已知参考值

---

## 四、重点绘图方案（10 张）

### 图 1 — 问题动机与概念图
- **类型：** 概念示意图（非数据图）
- **要传达的信息：** IEEE 1838 的测试访问不是自由并行的，每条路径的选择都会影响共享资源的排队
- **内容：**
  - 左：3D stack 剖面图，标注 PTAP / STAP / DWR / FPP lane / shared BIST 五种资源的物理位置
  - 中：每个 target 可选的 3 条路径（S/B/F），标注"测试用时"和"占用资源"
  - 右：固定最快 vs 联合选择的调度方案对比，BIST 排队成为瓶颈的示意图
- **数据来源：** 手工绘制（draw.io / SVG / matplotlib）
- **预期效果：** 读者不需要读正文就能理解"为什么固定选最快不一定最优"

### 图 2 — Benchmark 覆盖全景图（气泡矩阵）
- **类型：** 数据可视化
- **要传达的信息：** 实验覆盖是系统性的，且清晰区分 A 类（覆盖验证）/ B 类（机制验证）
- **主图：** 4（scale）× 3（topology）= 12 格气泡矩阵
  - 气泡大小 = recipe_count（模型丰富度）
  - 气泡颜色深浅 = M4 greedy speedup（并行潜力）
  - 边框样式区分 A/B 类：虚线框 = A 类（覆盖验证），实线粗框 = B 类（机制验证）
- **侧面板：** 4 个消融条件（M22）的标注——control / private / shared-no-escape / shared-with-escape
- **数据来源：** `m10_benchmark_sweep.csv`（216 行）+ `m22_mechanism_ablation_detail.csv`（192 行）
- **预期效果：** 一眼看出 xlarge case 气泡大 + 颜色深，且清楚哪些 case 用于机制验证

### 图 3 🔴 核心机制 Box Plot（论文最重要的一张图）
- **类型：** 统计可视化
- **要传达的信息：** "联合调度只有在瓶颈+替代共存时才有效"——这是整篇论文的封面图
- **主图：** 4 个并列 box plot，X 轴 = 4 个消融条件，Y 轴 = joint gain vs fixed-fastest（%）
  - `m10_control` → 12 个点全部压在 0%
  - `bist_private` → 12 个点全部压在 0%
  - `shared_no_escape` → 12 个点全部压在 0%
  - `shared_with_escape` → 12 个点分散在 10%-37.5%，有清晰分布
- **叠加信息：**
  - 每个 box 上方一句话标注条件含义（"no bottleneck" / "no alternative" / "both exist → 25.8% avg gain"）
  - 在前三个 0% box 旁边用小字引用文献支撑："Consistent with Habiby 2022 (PBO ≈ fixed-path on ordinary benchmarks) and Sen Gupta 2011 (PO = RS when no session split needed)"
- **底部标注：** "12 ITC'02-derived source cases × 4 ablation conditions = 192 schedule rows"
- **数据来源：** `m22_mechanism_ablation_detail.csv`
- **预期效果：** 前三个 box 完全平坦在零线，第四个 box 陡然跳起——读者不需要读任何文字就能理解核心发现。文献引用为 0% 提供了正当性，不是失败而是与 prior work 一致的发现。

### 图 4 — 压力梯度连续响应曲线
- **类型：** 参数扫描曲线（需要新增实验）
- **要传达的信息：** 增益不是"有或无"，而是随资源压力程度和替代路径多样性连续变化的
- **左图（压力梯度）：**
  - X 轴 = 共享 BIST engine 数量（1, 2, 4, 8, ∞/私有）
  - Y 轴 = joint gain（%）
  - 三条线分别代表 3 种拓扑
  - X=∞ 时三条线交汇于 0%；X=1 时 3D stack 线最高（~38%），2.5D 最低（~19%）
- **右图（路径多样性梯度）：**
  - X 轴 = 可用替代路径类型（only BIST → BIST+FPP → BIST+FPP+Hybrid）
  - Y 轴 = joint gain（%）
  - 单调递增趋势线
- **需要新增的实验：**
  - 对 3 个代表性 case，扫描共享 BIST 数量（1/2/4/8/∞）→ 15 行
  - 对 3 个代表性 case，扫描替代路径可用性（3 档）→ 9 行
  - 预计总新增约 50 行调度数据
- **预期效果：** 两条单调曲线证明你的发现是连续机制、不是 cherry-pick

### 图 5 — 调度前后对比 Gantt 图
- **类型：** 调度可视化
- **要传达的信息：** 直观展示固定策略 vs 联合策略在同一个 case 上的差异
- **布局：** 上下两栏，共享时间轴
  - **上栏（Fixed-fastest）：** 资源行 = Shared BIST | FPP lanes | PTAP/STAP serial
    - BIST 行：一个接一个排队（无重叠），FPP 行：大面积空白
  - **下栏（Joint scheduling）：** 相同资源行
    - BIST 行：仍有排队但减少了，FPP 行：出现并行数据传输（bar 重叠）
- **颜色编码：** BIST = 绿，FPP 数据传输 = 橙，PTAP/STAP 配置 = 紫
- **关键标注：**
  - 在上栏 BIST 行标注 "共享瓶颈导致串行化"
  - 在下栏 FPP 行标注 "替代路径利用"
  - 右上角大字体标注 gain 数值
- **数据来源：** M21 pressure suite 中的一个 3D stack 代表性 case
- **注意：** 只保留资源行（最多 3-4 行），target 名放 bar 内或省略，避免标签挤爆

### 图 6 — 资源利用率时间线对比
- **类型：** 时序面积图
- **要传达的信息：** 从资源利用角度解释 gain 的来源——固定策略浪费了 FPP 带宽
- **布局：** 上下两栏
  - **上栏（Fixed）：** X 轴 = 时间，填充面积 = FPP lane 占用数（蓝色半透明），叠加虚线 = 总 FPP 容量。橙色面积 = BIST engine busy（二值 0/1）
  - **下栏（Joint）：** 相同坐标系。FPP 占用曲线明显更高，BIST 占用仍然存在但总时间缩短
- **关键标注：**
  - 上栏标注 "FPP bandwidth wasted"
  - 下栏标注 "FPP bandwidth utilized"
  - 底部标注平均利用率数字
- **数据来源：** 与图 5 同一个 case 的 phase 数据
- **预期效果：** 两张填充面积图并排，FPP 利用率的差异一目了然

### 图 7 — 拓扑差异分析图
- **类型：** 比较柱状图 + 热分布图
- **要传达的信息：** 联合调度在不同拓扑上效果不同，且有物理解释
- **主图：** 3 组 bar（每组 2 根：fixed vs joint makespan），分别代表 2.5D/3D/5.5D
  - 3D stack gain 最高（35%），2.5D 最低（19%）
- **叠加信息：** 每个拓扑 bar 上方标注资源特征
  - 2.5D: 多 FPP lane，低热耦合，BIST 瓶颈轻 → gain 小
  - 3D: 少 FPP lane（TSV 密度低），强热耦合，BIST 瓶颈重 → gain 大
  - 5.5D: 多 tower 分组，混合特征 → gain 居中
- **右侧小图：** 热分布 spread（max temp - min temp across dies），3D 最宽（~10.6°C），2.5D 最窄（~4.4°C）
- **数据来源：** M22 topology split + M21 topology summary
- **预期效果：** Bar 的高度差异本身就暗示了拓扑差异 → 再叠加文字标注解释原因 → 形成完整的故事

### 图 8 — Recipe 选择策略演化图
- **类型：** 堆叠柱状图 + 散点趋势图
- **要传达的信息：** 联合调度不是简单"换一条路"，而是在 BIST 和 FPP 之间做了精细搭配
- **左图（堆叠柱状图）：**
  - X 轴 = 12 个 pressure case
  - Y 轴 = target 数
  - 每个 case 两根 bar：Fixed（纯 BIST 色 = 单色）、Joint（BIST + FPP 拼色）
  - 一目了然：Fixed 是单色柱子，Joint 是拼色柱子
- **右图（散点趋势图）：**
  - X 轴 = FPP 选择占比（joint 中选择 FPP 的 target 比例）
  - Y 轴 = gain（%）
  - 拟合趋势线：FPP 选择越多 → gain 越大（边际递减）
- **数据来源：** M22 `shared_bist_with_parallel_escape` 的 12 行 detail 数据
- **预期效果：** 左图视觉冲击——Fixed 全绿（BIST only），Joint 绿橙拼色（BIST+FPP mix）

### 图 9 — 方法对比与文献基线
- **类型：** 多方法柱状图对比
- **要传达的信息：** 在 B 类 benchmark 上，我们的方法（M4/M5）与文献方法（Habiby 2022 PBO、Sen Gupta 2011 PO）的公平对比
- **主图：** 分组柱状图
  - X 轴 = 6 个代表性 B 类 case（2 种拓扑 × 3 种规模）
  - Y 轴 = 归一化 makespan（relative to serial = 1.0）
  - 每组 5-6 根 bar：pure_serial / Sen Gupta PO / Habiby PBO / fixed_fastest / M4 greedy / M5 CP-SAT
- **关键标注：**
  - 顶部标注每种方法在所有 case 上的平均排名
  - M4/M5 不是在所有 case 上都最好，但在 pressure case 上显著优于文献方法
- **右侧面板：** runtime 对比（求解时间）
- **数据来源：** 新增的 baseline 实验 + M21 pressure suite

### 图 10 — 方法总览框架图
- **类型：** 流程示意图（非数据图）
- **要传达的信息：** 方法的完整 pipeline、输入/输出、online vs offline 的区分
- **内容：** 从左到右的流程图
  ```
  ITC'02 Benchmark → System Model → Recipe Generation → Pareto Pruning
                                                              ↓
  HotSpot Validation ← Thermal Proxy ← Joint Scheduling (CP-SAT)
  ```
- **每个阶段旁标注：** 产生的 artifacts（JSON / CSV / schedule），以及对应的文献方法（如"Pareto Pruning → similar to Patmanathan 2024 Pareto cubes"）
- **底部标注：** online（调度内循环）vs offline（验证）的区分
- **数据来源：** 手工绘制
- **位置：** Introduction 末尾或 Methodology 开头

---

## 五、图的优先级与执行顺序

| 优先级 | 图号 | 图名 | 为什么重要 | 需要新实验？ |
|--------|------|------|-----------|------------|
| **P0** | 图 3 | 核心机制 Box Plot | 论文封面图，M22 数据已有，只缺图 | 不需要 |
| **P0** | 图 5 | Gantt 对比图 | 直观展示方法效果，比数字有说服力 | 不需要（改善现有） |
| **P0** | 图 8 | Recipe 混合演化 | 证明联合调度是"混合"，不是乱选 | 不需要 |
| **P1** | 图 9 | 文献基线对比 | 填补"没和任何人比"的致命缺陷 | **需要（实现 baseline）** |
| **P1** | 图 4 | 压力梯度曲线 | 从特例变成连续机制，大大增强说服力 | **需要** |
| **P1** | 图 6 | 资源利用率时间线 | 解释 why，不只说 that | 不需要 |
| **P1** | 图 7 | 拓扑差异分析 | 让"统一建模"有数据支撑 | 不需要 |
| **P2** | 图 2 | Benchmark 全景 | 实验覆盖面的交代 | 不需要 |
| **P2** | 图 1 | 问题动机 | 概念图，边际收益有限 | 不需要 |
| **P2** | 图 10 | 框架总览 | 方法论总览 + 与文献方法的关联标注 | 不需要 |

**注意：** 原方案中的热感知效果图（原图 9）已移除。原因是当前热代理的跨方法温差仅 0.1 °C，无法产生有意义的可视化。待热模型升级完成后（§3.4），再重新设计热感知相关图表。

---

## 六、需要新增的实验

### 实验 0a：Habiby 2022 PBO Baseline（P0）

**目的：** 实现文献对比基线

**方法：**
1. 在 OR-Tools CP-SAT 中编码简化的 PBO 模型（或安装 clasp solver）
2. 对 6 个代表性 case（A 类 3 个 + B 类 3 个）运行 PBO 增量调度
3. 记录 TAT、session 数量、runtime

**预计规模：** 6 cases × 1 method = 6 行（增量求解每行内含多轮）

### 实验 0b：Sen Gupta 2011 PO Baseline（P0）

**目的：** 实现文献对比基线

**方法：**
1. 对每个 die 生成 pre-bond schedule（最快的 recipe）
2. 在 post-bond 阶段贪心匹配功率兼容的 session pair
3. 记录 TAT vs. Serial 的减少量

**预计规模：** 6 cases × 1 method = 6 行

### 实验 A：资源压力梯度扫描（为图 4 左图，P1）

**目的：** 刻画 joint gain 随共享 BIST 数量的连续变化

**方法：**
1. 选 3 个代表性 source case（每种拓扑选一个）
2. 对每个 case，变化共享 BIST engine 数量：1, 2, 4, 8, ∞（私有）
3. 每个配置跑 fixed-fastest + M4 greedy + M5 CP-SAT

**预计规模：** 3 cases × 5 BIST levels × 3 methods = 45 行

### 实验 B：替代路径多样性扫描（为图 4 右图，P1）

**目的：** 刻画 joint gain 随替代路径类型数量的变化

**方法：**
1. 使用 3 个代表性 pressure case（共享 BIST = 1）
2. 限制可用 recipe 类型：only BIST / BIST+FPP / BIST+FPP+Hybrid
3. 每个配置跑 scheduling

**预计规模：** 3 cases × 3 path levels × 3 methods = 27 行

### 实验 C：热模型升级 + HotSpot 扩展验证（P1-P2）

**目的：** 让热代理产生有意义的跨方法温差

**方法：**
1. 实现 die-to-die thermal coupling（在 RC 网络中加入 R_inter_die, C_inter_die）
2. 计算每 die 的 RHDF 并作为调度软约束
3. 扩展 HotSpot：3 拓扑 × 3 规模 × 2-3 方法 = 20+ 行
4. 用 HotSpot 结果反拟合、报告代理模型误差

---

## 七、时间线与执行建议

### 第一批（P0，无新实验依赖，可直接出图）
- 写 `experiments/generate_revised_figure3_boxplot.py`
- 写 `experiments/generate_revised_figure5_gantt.py`
- 写 `experiments/generate_revised_figure8_recipe_mix.py`
- 这三张图出来之后，先把论文的核心实验部分 rewrite

### 第二批（P0-P1，需要实现 baseline + 新实验）
- 实现 `experiments/run_sen_gupta_po_baseline.py`
- 实现 `experiments/run_habiby_pbo_baseline.py`
- 写 `experiments/run_resource_pressure_sweep.py`（BIST 数量扫描 + 替代路径扫描）
- 写 `experiments/generate_revised_figure9_baseline_comparison.py`
- 写 `experiments/generate_revised_figure4_gradient.py`
- 写 `experiments/generate_revised_figure6_occupancy.py`
- 写 `experiments/generate_revised_figure7_topology.py`

### 第三批（P2 及以后）
- 热模型升级（die-to-die coupling + RHDF）+ HotSpot 扩展
- 图 1、图 2、图 10：概念图和总览图
- CP-SAT optimality gap 分析

---

## 八、与原计划的关键差异

| 维度 | 原做法 | 修正做法 |
|------|--------|---------|
| 论文定位 | 提出通用优化方法 | 发现并刻画生效条件（characterization paper） |
| 核心 claim | "联合调度优于固定路径" | "联合调度在双条件下有效，消融实验严格证明" |
| 普通 benchmark 0% gain | 避而不谈或视为"失败" | 正文论述：有价值的发现，与 Habiby 2022 / Sen Gupta 2011 一致——一般场景下无需联合优化 |
| 对比基线 | 全部自比（8 个全是自己的方法） | 加入 Habiby 2022 PBO、Sen Gupta 2011 PO 作为文献基线 |
| M10 的角色 | 主要的实验证据 | 降级为 A 类（覆盖验证）；mechanism proof 由 M21/M22（B 类）承担 |
| M22 的角色 | 附录/补充 | 升级为论文最核心的实验证据 |
| Benchmark 分类 | 无区分 | A 类（覆盖验证）/ B 类（机制验证） |
| 图表风格 | 柱状图展示平 bar | Box plot + 梯度曲线 + 对比大图 + 文献基线对比图 |
| 热感知 | 声称"闭环" | P1 升级热模型使其产生有意义的温差 + HotSpot 扩展验证；升级前不画热感知图 |
| ALNS | 声称"混合求解器" | 要么修复自适应权重使其成为真正的 ALNS，要么降级为附录 |
| 文献引用 | 无 references | 四篇文献融入叙事：Habiby 2020 (图建模), Habiby 2022 (PBO baseline), Patmanathan 2024 (Pareto cube + RHDF), Sen Gupta 2011 (PO baseline + session split) |

---

## 九、关联文件

- 文献总结：`REFERENCE/文献总结与实验改进方案.md`
- 四篇参考文献全文：`REFERENCE/*.pdf` + `REFERENCE/*.txt`
- 现状审计：`results/reports/m17_innovation_support_report.md`
- 机制消融：`results/reports/m22_mechanism_ablation_report.md`
- 压力 suite：`results/reports/m21_innovation_pressure_report.md`
- 现有图生成脚本：`experiments/generate_m16_paper_value_figures.py`、`experiments/generate_m19_pressure_figures.py`
- 旧版项目路线图：`ieee1838-ptv-test-scheduler/ROADMAP.md`
- 项目架构：`docs/PROJECT_STRUCTURE.md`
- 项目规则：`docs/PROJECT_RULES.md`

## 参考文献

1. P. Habiby, S. Huhn, and R. Drechsler, "Power-aware Test Scheduling for IEEE 1687 Networks with Multiple Power Domains," in *IEEE DFT*, 2020.
2. P. Habiby, S. Huhn, and R. Drechsler, "Power-aware test scheduling framework for IEEE 1687 multi-power domain networks using formal techniques," *Microelectronics Reliability*, vol. 134, p. 114551, 2022.
3. G. Patmanathan, C. Y. Ooi, N. Ismail, and S. R. Aid, "Thermal-Aware Test Scheduling with Floorplanning for Three-Dimensional Stacked Integrated Circuit," in *IEEE ICSE*, 2024.
4. B. Sen Gupta, U. Ingelsson, and E. Larsson, "Scheduling Tests for 3D Stacked Chips under Power Constraints," in *IEEE DELTA*, 2011.
