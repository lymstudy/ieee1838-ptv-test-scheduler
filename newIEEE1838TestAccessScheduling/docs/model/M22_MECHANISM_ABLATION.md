# M22 Mechanism Ablation

M22 is an experiment repair stage. It does not rewrite the paper narrative and does not create extra intermediate case files.
Its purpose is to prove the mechanism behind the path-schedule claim:

> Joint recipe selection matters only when shared-resource pressure and alternative access paths coexist.

## Why This Stage Exists

The ordinary M10 benchmark sweep is useful for coverage, but it is weak evidence for path-schedule joint optimization because fixed-fastest and joint scheduling often select the same access style.
M18 exposed the mechanism, but only on two hand-built cases.
M22 keeps the 12 ITC'02-derived M10 source cases and runs four controlled ablations in memory.
All recipe choices still include PTAP/STAP serial setup before a test is enabled.
FPP is modeled as a data-transfer channel after TAP configuration, and scan/FPP/capture/BIST execution phases use exclusive test-session resources so non-parallelizable work is not freely overlapped.

## Ablations

| ablation | controlled condition | expected conclusion |
| --- | --- | --- |
| `m10_original_control` | original M10 model | coverage only; do not claim joint path-schedule gain |
| `bist_private_control` | pressure workload, but each target has a private BIST engine | no shared bottleneck, so fixed-fastest and joint converge |
| `shared_bist_no_parallel_escape` | shared BIST pressure, but FPP/hybrid paths are removed | bottleneck alone is insufficient when every method must use BIST |
| `shared_bist_with_parallel_escape` | shared BIST pressure with FPP/hybrid alternatives | joint scheduling can mix paths and relieve BIST serialization |

## Commands

```powershell
python experiments/run_m22_mechanism_ablation.py
```

## Outputs

- `results/tables/m22_mechanism_ablation_detail.csv`
- `results/tables/m22_mechanism_ablation_summary.csv`
- `results/tables/m22_topology_ablation_summary.csv`
- `results/reports/m22_mechanism_ablation_report.md`

## Current Result

The current run uses 12 ITC'02-derived source cases and produces 192 successful schedule rows.

| ablation | avg gain vs fixed-fastest | gain range | key observation |
| --- | ---: | --- | --- |
| `m10_original_control` | `0.00%` | `0.00% - 0.00%` | ordinary M10 is not path-schedule evidence |
| `bist_private_control` | `0.00%` | `0.00% - 0.00%` | without shared BIST contention, joint selection has no advantage |
| `shared_bist_no_parallel_escape` | `0.00%` | `0.00% - 0.00%` | without alternative paths, scheduling cannot escape the bottleneck |
| `shared_bist_with_parallel_escape` | `25.84%` | `10.00% - 37.50%` | joint scheduling mixes BIST local execution and FPP data-transfer paths after TAP setup |

Topology split in the full mechanism case:

| topology | cases | avg gain | gain range |
| --- | ---: | ---: | --- |
| `2_5d_interposer` | 4 | `19.12%` | `10.00% - 24.99%` |
| `3d_stack` | 4 | `35.25%` | `30.00% - 37.50%` |
| `5_5d_multi_tower` | 4 | `23.14%` | `12.52% - 33.33%` |

## Paper Boundary

This supports a controlled mechanism claim:

> Under ITC'02-derived shared-resource pressure, every test is still enabled through PTAP/STAP configuration. Fixing each target to its individually fastest path can serialize shared BIST resources; joint recipe selection and scheduling reduce test time by selecting a mixture of BIST local execution and FPP data-transfer paths under explicit test-session constraints.

Do not write:

> Joint scheduling is better on all real benchmarks.

M22 is stronger than the old M18-only evidence because it covers all 12 M10-derived cases, but it is still a controlled pressure experiment rather than industrial chip signoff data.
