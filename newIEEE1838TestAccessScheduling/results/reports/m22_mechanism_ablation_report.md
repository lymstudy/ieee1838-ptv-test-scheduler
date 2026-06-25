# M22 Mechanism Ablation Report

M22 is an experiment fix, not a paper-writing patch. It separates benchmark coverage from the mechanism claim.

- Successful schedule rows: 192
- Source cases: 12
- Ablation settings: 4

## Main Ablation

| ablation | cases | avg gain vs fixed-fastest | gain range | fixed/joint TAP time | joint FPP data time | joint exclusive test time | avg joint B/F/H | interpretation |
| --- | ---: | ---: | --- | --- | ---: | ---: | --- | --- |
| m10_original_control | 12 | 0.00% | 0.00% - 0.00% | 0.003023/0.003023 s | 0.000065 s | 0.002946 s | 0.00/17.50/0.00 | Coverage control: ordinary M10 cases should not be used to claim path-schedule joint gains. |
| bist_private_control | 12 | 0.00% | 0.00% - 0.00% | 0.003093/0.003093 s | 0.000000 s | 0.102030 s | 17.50/0.00/0.00 | Resource control: when BIST engines are private, fixed-fastest and joint scheduling should converge. |
| shared_bist_no_parallel_escape | 12 | 0.00% | 0.00% - 0.00% | 0.003093/0.003093 s | 0.000000 s | 0.102030 s | 17.50/0.00/0.00 | Path-diversity control: a bottleneck alone is insufficient if all schedulers must use the same path. |
| shared_bist_with_parallel_escape | 12 | 25.84% | 10.00% - 37.50% | 0.003093/0.003073 s | 0.036816 s | 0.112700 s | 12.92/4.58/0.00 | Mechanism case: joint recipe scheduling can mix BIST and FPP/hybrid paths to relieve serialization. |

## Topology Split

| ablation | topology | cases | avg gain | gain range | avg joint F/H | avg temp spread |
| --- | --- | ---: | ---: | --- | --- | ---: |
| m10_original_control | 2_5d_interposer | 4 | 0.00% | 0.00% - 0.00% | 17.50/0.00 | 0.10 C |
| m10_original_control | 3d_stack | 4 | 0.00% | 0.00% - 0.00% | 17.50/0.00 | 0.11 C |
| m10_original_control | 5_5d_multi_tower | 4 | 0.00% | 0.00% - 0.00% | 17.50/0.00 | 0.11 C |
| bist_private_control | 2_5d_interposer | 4 | 0.00% | 0.00% - 0.00% | 0.00/0.00 | 6.29 C |
| bist_private_control | 3d_stack | 4 | 0.00% | 0.00% - 0.00% | 0.00/0.00 | 23.84 C |
| bist_private_control | 5_5d_multi_tower | 4 | 0.00% | 0.00% - 0.00% | 0.00/0.00 | 19.79 C |
| shared_bist_no_parallel_escape | 2_5d_interposer | 4 | 0.00% | 0.00% - 0.00% | 0.00/0.00 | 2.29 C |
| shared_bist_no_parallel_escape | 3d_stack | 4 | 0.00% | 0.00% - 0.00% | 0.00/0.00 | 7.40 C |
| shared_bist_no_parallel_escape | 5_5d_multi_tower | 4 | 0.00% | 0.00% - 0.00% | 0.00/0.00 | 9.96 C |
| shared_bist_with_parallel_escape | 2_5d_interposer | 4 | 19.12% | 10.00% - 24.99% | 4.25/0.00 | 4.42 C |
| shared_bist_with_parallel_escape | 3d_stack | 4 | 35.25% | 30.00% - 37.50% | 6.25/0.00 | 9.22 C |
| shared_bist_with_parallel_escape | 5_5d_multi_tower | 4 | 23.14% | 12.52% - 33.33% | 3.25/0.00 | 11.69 C |

## What This Proves

- If there is no shared bottleneck, fixing the fastest path is already enough.
- If there is a bottleneck but no alternative path, joint scheduling cannot create meaningful path diversity.
- FPP is a data-transfer channel after TAP configuration, not an independent task launcher.
- Scan/FPP/capture/BIST execution phases use exclusive test-session resources, so non-parallelizable work is not freely overlapped.
- When shared BIST pressure and FPP/hybrid data-transfer alternatives coexist, joint recipe selection reduces serialization under those constraints.
- The result should be written as a controlled ITC'02-derived mechanism experiment, not as a claim over every ordinary benchmark.
