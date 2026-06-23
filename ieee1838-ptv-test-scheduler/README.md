# IEEE 1838 PTV Test Scheduler

This repository is a research prototype for power-, thermal-, and voltage-aware test access scheduling for IEEE 1838-compatible 3D IC test access resources.

A0 is now frozen as a task-level physical-aware scheduling prototype. The next phase is B-stage IEEE 1838-aware layered access scheduling.

## A0 Prototype Scope

A0 compares three schedulers on abstract 3D stack test workloads:

1. Serial IEEE 1838-style baseline
2. Bandwidth-greedy baseline
3. PTV-aware scheduler

A0 includes configuration loading, abstract stack/task/access models, a unified schedule evaluator, a simplified thermal model, a simplified shared-PDN voltage model, clean and stress 4-die experiments, parameter sweeps, deterministic synthetic workload-scale sweeps, benchmark-derived workload statistics schema, example benchmark adapter, plots, and tests.

A0 is a task-level scheduling prototype. It is not a full IEEE 1838 behavior model.

## Scope

The prototype uses abstract but physically reasonable models:

- IEEE 1838 access resources: PTAP, STAP, DWR segments, optional FPP lanes
- DWR means Die Wrapper Register
- Test tasks: scan, BIST, DWR EXTEST, and instrument access
- Thermal model: simplified per-die discrete RC-style temperature update
- Voltage model: simplified shared-PDN equivalent resistance IR-drop estimation

This project does not implement real ATPG, Tessent SSN, commercial EDA tool interfaces, HotSpot, 3D-ICE, RedHawk, Voltus, FPGA validation, direct RTL parsing, or real chip validation.

## Current Results

Current experiment artifacts are generated under `results/`. Run history and notes are tracked in [EXPERIMENT_LOG.md](EXPERIMENT_LOG.md).

The key observation is that PTV-aware scheduling reduces physical constraint violations compared with bandwidth-greedy scheduling, while retaining much shorter TAT than purely serial scheduling in many tested workloads.

## Next Phase: IEEE 1838-Aware Layered Scheduler

B-stage planning is tracked in [ROADMAP.md](ROADMAP.md), with the detailed scheduler design kept here:

- [DESIGN_SPEC_1838_LAYERED_SCHEDULER.md](docs/DESIGN_SPEC_1838_LAYERED_SCHEDULER.md)

B-stage goal:

Predictive access-path and physical-aware layered test scheduling for IEEE 1838-compatible 3D ICs.

B1 AccessPath data model and path cost estimator and B2 TestIntent to ExecutionPhase layered expander are implemented as initial MVPs. The next implementation task is B3: Access-time-aware scheduler.

## Benchmark-Derived Workload Schema

The benchmark-derived workload path currently uses a statistics schema, not a Verilog or gate-level parser.

- Schema: `benchmarks/schema.md`
- Example stats: `benchmarks/example_benchmark_stats.yaml`
- Adapter: `src/workload/benchmark_adapter.py`

The adapter converts benchmark statistics such as flip-flop count, scan-chain count, scan-chain length, estimated task powers, and DWR interconnect lengths into scheduler-compatible abstract tasks.

## Experiments

Run the clean MVP case:

```powershell
python experiments/run_case_4die.py
```

Run the stress mechanism-validation case:

```powershell
python experiments/run_case_4die_stress.py
```

Run parameter and workload sweeps:

```powershell
python experiments/sweep_fpp_lanes.py
python experiments/sweep_voltage_limits.py
python experiments/sweep_thermal_limits.py
python experiments/sweep_workload_scale.py
```

Run benchmark-statistics workloads:

```powershell
python experiments/run_example_benchmark_workload.py
python experiments/run_example_benchmark_workload.py --output-dir tmp_benchmark_out
```

Run the B1 access-path generation demo:

```powershell
python experiments/demo_access_path_generation.py
python experiments/demo_access_path_generation.py --output-dir tmp_access_path_out
```

Access-path demo outputs:

- `results/access_path/access_path_summary.csv`

Run the B2 layered task expansion demo:

```powershell
python experiments/demo_layered_task_expansion.py
python experiments/demo_layered_task_expansion.py --output-dir tmp_layered_out
```

Layered expansion demo outputs:

- `results/layered_expansion/layered_task_summary.csv`
- `results/layered_expansion/execution_phase_summary.csv`

Experiment outputs are written under:

- `results/case_4die/`
- `results/case_4die_stress/`
- `results/sweeps/fpp_lanes/`
- `results/sweeps/voltage_limits/`
- `results/sweeps/thermal_limits/`
- `results/sweeps/workload_scale/`
- `results/benchmarks/example/`
- `results/access_path/`
- `results/layered_expansion/`

## Quick Start

```powershell
python -m pip install -r requirements.txt
pytest
python experiments/run_case_4die.py
```

## Research Integrity Notes

- DWR means Die Wrapper Register.
- IEEE 1838 is used as the die access architecture context; this repository does not claim IEEE 1838 defines scheduling algorithms.
- This repository does not claim that IEEE 1838 includes SSN.
- When discussing scan streaming ideas, use "streaming-scan-inspired" only where appropriate.
- Synthetic workloads are for mechanism validation and are not real benchmark-derived workloads.
- The example benchmark-derived workload is schema validation from statistics, not a real benchmark conclusion.
- Realistic UART / public benchmark-derived statistics remain future work unless the corresponding files are present in the repository.
- Do not claim zero hardware overhead. Use narrower statements only when accurate, such as "reuse IEEE 1838-compatible test access resources".

## Frontier Idea Integration Roadmap

Future planning for PTVA-SSN-inspired extensions, interposer test-bus routing, external health-event interfaces, PowerPillar-aware capture staggering, and PackageProfile-aware boundary modeling is consolidated in [ROADMAP.md](ROADMAP.md), with claim boundaries recorded in [DECISIONS.md](DECISIONS.md).

These items are roadmap-only. They do not mean the repository has implemented SSN, UCIe, interposer routing hardware, PackageProfile models, PowerPillar models, or new scheduler algorithms. B1 and B2 are implemented as initial MVPs; B3 access-time-aware scheduling remains the next implementation step.
