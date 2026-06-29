# M10: Benchmark Suite Expansion

## Goal

M10 expands the experiment from the small M9 flow demonstration into a reusable
benchmark suite. The focus is scale and sensitivity, not final algorithm ranking.

M10 must answer:

- Does the model run on multiple ITC'02 workloads, not just one or two examples?
- Do the same 3D, 2.5D, and 5.5D topology generators work across small and large
  test workloads?
- How sensitive is the schedule to FPP lane count (optional, IEEE 1838-2019 Clause 7) and package power budget?

## Inputs

The workload source is the project-local ITC'02 mirror:

```text
docs/data/itc02_benchmarks/
```

Default workloads:

| Scale | ITC'02 source | Role in M10 |
| --- | --- | --- |
| small | `d695.soc` | sanity and low-complexity baseline |
| medium | `p22810.soc` | hierarchical medium workload |
| large | `p34392.soc` | larger module count and scan volume |
| xlarge | `p93791.soc` | stress case for greedy-scale experiments |

The scheduler-relevant workload fields come from ITC'02: module I/O, scan-chain
lengths, chain counts, and pattern counts. IEEE 1838 bit widths, DWR sizes,
per-phase power, and thermal RC coefficients remain model assumptions.

## Generated Suite

M10 generates three topology families for each workload:

- `3d_stack`
- `2_5d_interposer`
- `5_5d_multi_tower`

Default case output:

```text
configs/cases/m10/
```

Manifest output:

```text
data/derived/m10_benchmark_suite_manifest.csv
```

The manifest is the compact index of generated cases and should be used in
reports instead of manually listing every JSON detail.

## Sweep Plan

Default sweep dimensions:

| Dimension | Values | Reason |
| --- | --- | --- |
| FPP lanes (optional, IEEE 1838-2019 Clause 7) | 2, 8, 16 | narrow, nominal, and wide access capacity |
| Power budget | tight, nominal, relaxed | exposes power-constrained scheduling behavior |
| Methods | pure serial, M4 greedy | scalable first-pass comparison |

CP-SAT can be enabled for selected small cases, but it is off by default because
the purpose of M10 is benchmark scaling.

## Commands

```bash
python experiments/generate_m10_benchmark_suite.py
python experiments/run_m10_benchmark_sweep.py
```

Formal outputs:

```text
results/tables/m10_benchmark_sweep.csv
results/reports/m10_benchmark_sweep_report.md
```

## Interpretation Rules

- M10 results show scalability and sensitivity trends.
- Do not claim global optimality for greedy-only sweep rows.
- Do not treat model-assumption parameters as measured chip data.
- Use M11 for final algorithm ranking and M12 for thermal validation.

## Current M10 Result Snapshot

The first M10 run generated 12 cases:

- 4 ITC'02 workloads: `d695`, `p22810`, `p34392`, `p93791`;
- 3 topology families per workload: `3d_stack`, `2_5d_interposer`,
  `5_5d_multi_tower`;
- 216 sweep rows: 12 cases x 3 lane settings x 3 power profiles x 2 methods.

All 216 default rows were schedulable with pure serial and M4 greedy.

Average M4 normalized makespan versus pure serial:

| Topology | Rows | Avg normalized makespan | Avg speedup |
| --- | ---: | ---: | ---: |
| `2_5d_interposer` | 36 | 0.1009 | 37.01 |
| `3d_stack` | 36 | 0.1050 | 31.30 |
| `5_5d_multi_tower` | 36 | 0.1033 | 35.92 |

These numbers are scale/sensitivity evidence only. They should be followed by
M11 algorithm comparisons before being used as final paper claims.
