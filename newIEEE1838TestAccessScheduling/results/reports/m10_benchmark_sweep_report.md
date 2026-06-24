# M10 Benchmark Sweep Report

- Total rows: 216
- Successful schedule rows: 216
- Failed rows: 0

## M4 Greedy Average Normalized Makespan

| topology | rows | avg_norm_vs_serial | avg_speedup |
| --- | ---: | ---: | ---: |
| 2_5d_interposer | 36 | 0.1009 | 37.01 |
| 3d_stack | 36 | 0.1050 | 31.30 |
| 5_5d_multi_tower | 36 | 0.1033 | 35.92 |

## Best M4 Row Per Scale

| scale | case | lanes | power | norm | speedup |
| --- | --- | ---: | --- | ---: | ---: |
| large | m10_large_p34392_5_5d_multi_tower | 16 | tight | 0.0145 | 69.16 |
| medium | m10_medium_p22810_2_5d_interposer | 8 | tight | 0.0228 | 43.94 |
| small | m10_small_d695_2_5d_interposer | 2 | tight | 0.3361 | 2.97 |
| xlarge | m10_xlarge_p93791_5_5d_multi_tower | 16 | tight | 0.0273 | 36.62 |

## Notes

- M10 defaults to pure serial and M4 greedy because this milestone measures scale and sensitivity.
- CP-SAT can be enabled for selected small cases with `--include-cpsat`.
- These rows are not global optimality claims.
