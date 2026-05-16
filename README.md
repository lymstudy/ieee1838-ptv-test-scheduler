# IEEE 1838 PTV Test Scheduler

This repository is a research prototype for power-, thermal-, and voltage-aware test access scheduling for IEEE 1838-compatible 3D IC test access resources.

The current MVP compares three schedulers on 3D stack test workloads:

1. Serial IEEE 1838-style baseline
2. Bandwidth-greedy baseline
3. PTV-aware scheduler

The prototype includes configuration loading, abstract stack/task/access models, a unified schedule evaluator, a simplified thermal model, a simplified shared-PDN voltage model, clean and stress 4-die experiments, parameter sweeps, deterministic synthetic workload-scale sweeps, a benchmark-derived workload statistics schema with example and realistic UART adapters, plots, and tests.

## Scope

The prototype uses abstract but physically reasonable models:

- IEEE 1838 access resources: PTAP, STAP, DWR segments, optional FPP lanes
- DWR means Die Wrapper Register
- Test tasks: scan, BIST, DWR EXTEST, and instrument access
- Thermal model: simplified per-die discrete RC-style temperature update
- Voltage model: simplified shared-PDN equivalent resistance IR-drop estimation

This project does not implement real ATPG, Tessent SSN, commercial EDA tool interfaces, HotSpot, 3D-ICE, RedHawk, Voltus, FPGA validation, or direct RTL parsing.

## Current Results

Current MVP results are summarized in [RESULTS.md](RESULTS.md).

The key observation is that PTV-aware scheduling reduces physical constraint violations compared with bandwidth-greedy scheduling, while retaining much shorter TAT than purely serial scheduling.

## Benchmark-Derived Workload Schema

The benchmark-derived workload path currently uses a statistics schema, not a Verilog or gate-level parser.

- Schema: `benchmarks/schema.md`
- Example stats: `benchmarks/example_benchmark_stats.yaml`
- Realistic UART stats: `benchmarks/realistic_uart_stats.yaml`
- Adapter: `src/workload/benchmark_adapter.py`

The adapter converts benchmark statistics such as flip-flop count, scan-chain count, scan-chain length, estimated task powers, and DWR interconnect lengths into scheduler-compatible abstract tasks. It is intended as a bridge for future public benchmark statistics or manually extracted RTL report data.

Run the schema-level example workload:

```powershell
python experiments/run_example_benchmark_workload.py
python experiments/audit_example_benchmark_schedule.py
```

Run the manually specified realistic UART statistics workload:

```powershell
python experiments/run_realistic_uart_workload.py
python experiments/audit_realistic_uart_schedule.py
```

## Realistic UART Statistics Case

The realistic UART case demonstrates the benchmark-derived workload flow with manually specified circuit-level statistics for a small UART-like controller. It is not parsed from RTL and is not real chip validation.

Results are written under:

```text
results/benchmarks/realistic_uart/
```

## Experiments

Run the clean MVP case:

```powershell
python experiments/run_case_4die.py
```

Run the stress mechanism-validation case:

```powershell
python experiments/run_case_4die_stress.py
```

Run the FPP lane sweep:

```powershell
python experiments/sweep_fpp_lanes.py
```

Run the voltage-limit sweep:

```powershell
python experiments/sweep_voltage_limits.py
```

Run the thermal-limit sweep:

```powershell
python experiments/sweep_thermal_limits.py
```

Run the synthetic workload-scale sweep:

```powershell
python experiments/sweep_workload_scale.py
```

Experiment outputs are written under:

- `results/case_4die/`
- `results/case_4die_stress/`
- `results/sweeps/fpp_lanes/`
- `results/sweeps/voltage_limits/`
- `results/sweeps/thermal_limits/`
- `results/sweeps/workload_scale/`
- `results/benchmarks/example/`
- `results/benchmarks/realistic_uart/`

## Quick Start

```powershell
python -m pip install -r requirements.txt
pytest
python experiments/run_case_4die.py
python experiments/run_case_4die_stress.py
python experiments/sweep_fpp_lanes.py
python experiments/sweep_voltage_limits.py
python experiments/sweep_thermal_limits.py
python experiments/sweep_workload_scale.py
python experiments/run_example_benchmark_workload.py
python experiments/audit_example_benchmark_schedule.py
python experiments/run_realistic_uart_workload.py
python experiments/audit_realistic_uart_schedule.py
```

## Research Integrity Notes

- DWR means Die Wrapper Register.
- IEEE 1838 is used as the die access architecture context; this repository does not claim IEEE 1838 defines scheduling algorithms.
- This repository does not claim that IEEE 1838 includes SSN.
- When discussing scan streaming ideas, use "streaming-scan-inspired" only where appropriate.
- Synthetic workloads are for mechanism validation and are not real benchmark-derived workloads.
- The example benchmark-derived workload is schema validation from statistics, not a real benchmark conclusion.
- The realistic UART case is a manually specified realistic statistics case, not RTL-extracted benchmark validation.
- Do not claim zero hardware overhead. Use narrower statements only when accurate, such as "reuse IEEE 1838-compatible test access resources".
