# M21 Innovation Pressure Suite

M21 用来替换“普通 benchmark 上 joint 和 fixed 几乎一样”的弱证据。

它不是再造两个完全手工 case，而是从 M10 的 12 个 ITC'02 派生 case 出发，保留 workload、封装拓扑、die 数和 interconnect 结构，然后加入受控压力条件：

- 共享 BIST engine，使单 target 最快的 BIST 路径在全局调度中形成瓶颈。
- 受限 FPP bandwidth/lane，使 FPP 不是永远最优，而是作为可并行替代路径。
- 拓扑相关 BIST bank 数和热耦合参数，使 2.5D/3D/5.5D 不再只是换名字。
- 放大热 RC 参数，使 thermal proxy 能产生可比较的温度差异。

M21 仍然保留 IEEE 1838 访问语义：BIST、FPP 和 hybrid recipe 都需要先经过 PTAP/STAP 串行配置；
FPP 只表示批量数据传输通道，不表示任务可以绕过 TAP 启动。
调度器还会对 scan/FPP/capture/BIST run 阶段施加 test-session 互斥资源，避免把不能并行的测试任务错误地并行化。

## Commands

```powershell
python experiments/generate_m21_innovation_pressure_suite.py
python experiments/run_m21_innovation_pressure_suite.py --time-limit-s 3
```

## Outputs

- `configs/cases/m21/`
- `data/derived/m21_innovation_pressure_manifest.csv`
- `results/tables/m21_innovation_pressure_detail.csv`
- `results/tables/m21_topology_pressure_summary.csv`
- `results/tables/m21_claim_support.csv`
- `results/reports/m21_innovation_pressure_report.md`

## Current Result

当前 M21 结果：

- 12 个 pressure case 全部成功调度。
- best joint 相对 fixed-fastest 的平均收益约 `27.10%`。
- 最低收益约 `10.00%`，最高收益约 `46.67%`。
- 三类拓扑平均收益不同：
  - 2.5D interposer: about `19.27%`
  - 3D stack: about `38.01%`
  - 5.5D multi-tower: about `24.00%`
- thermal proxy 平均方法间温度差异：
  - 2.5D interposer: about `4.42 C`
  - 3D stack: about `10.65 C`
  - 5.5D multi-tower: about `11.69 C`

## Paper Positioning

可以写：

> 在 ITC'02 派生的共享资源压力 benchmark 中，所有 recipe 仍先经过 PTAP/STAP 配置；固定选择每个 target 的最快访问路径会导致共享 BIST engine 串行化；联合 recipe 选择与调度能够在 TAP 启动之后混合 BIST 本地运行与 FPP 数据传输路径，在 12 个压力场景中获得 10.00% 到 46.67% 的测试时间收益。

不能写：

> 所有真实 benchmark 上 joint 都优于 fixed。

M21 是 controlled pressure suite。它比 M18 更有说服力，因为覆盖 12 个 ITC'02 派生 case；但它仍然不是工业真实芯片数据。
