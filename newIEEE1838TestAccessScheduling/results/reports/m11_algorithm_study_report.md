# M11 Algorithm Study Report

- Total rows: 48
- Successful rows: 45
- Non-success rows: 3

## Average Normalized Makespan

| method | family | rows | avg_norm_vs_serial | avg_speedup |
| --- | --- | ---: | ---: | ---: |
| pure_serial | baseline | 6 | 1.0000 | 1.00 |
| fixed_fastest | baseline | 6 | 0.1819 | 22.80 |
| tam_like | baseline | 6 | 0.1819 | 22.80 |
| low_power | baseline | 6 | 0.1929 | 20.47 |
| m4_all_recipes | ablation | 6 | 0.1819 | 22.80 |
| m4_greedy | proposed | 6 | 0.1819 | 22.80 |
| m5_cpsat | proposed | 6 | 0.1814 | 22.86 |
| m6_alns | proposed | 3 | 0.3394 | 2.95 |

## Best Method Per Case

| case | topology | best method | makespan_s | norm | solver |
| --- | --- | --- | ---: | ---: | --- |
| m10_medium_p22810_2_5d_interposer | 2_5d_interposer | m5_cpsat | 0.002112520 | 0.0227 | FEASIBLE |
| m10_medium_p22810_3d_stack | 3d_stack | m5_cpsat | 0.002271880 | 0.0244 | FEASIBLE |
| m10_medium_p22810_5_5d_multi_tower | 5_5d_multi_tower | m5_cpsat | 0.002150920 | 0.0231 | FEASIBLE |
| m10_small_d695_2_5d_interposer | 2_5d_interposer | m5_cpsat | 0.001207560 | 0.3353 | FEASIBLE |
| m10_small_d695_3d_stack | 3d_stack | m5_cpsat | 0.001226440 | 0.3388 | FEASIBLE |
| m10_small_d695_5_5d_multi_tower | 5_5d_multi_tower | m5_cpsat | 0.001256840 | 0.3443 | FEASIBLE |

## Skipped Or Failed Rows

| case | method | status | reason |
| --- | --- | --- | --- |
| m10_medium_p22810_3d_stack | m6_alns | skipped | target_count=22 exceeds max_alns_targets=16 |
| m10_medium_p22810_2_5d_interposer | m6_alns | skipped | target_count=22 exceeds max_alns_targets=16 |
| m10_medium_p22810_5_5d_multi_tower | m6_alns | skipped | target_count=22 exceeds max_alns_targets=16 |

## Notes

- M11 compares algorithms on the selected small/medium cases at 8 FPP lanes and nominal power by default.
- CP-SAT `FEASIBLE` rows are valid schedules, not optimality proofs.
- M6 ALNS is bounded by `--max-alns-targets` to avoid turning this comparison into an uncontrolled long run.
- Thermal values remain M7 proxy estimates; HotSpot-level validation belongs to M12.
