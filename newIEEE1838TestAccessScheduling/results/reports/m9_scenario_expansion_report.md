# M9 Scenario Expansion Report

This report compares the same scheduling flow across the original 3D stack, a 2.5D interposer case, and a 5.5D multi-tower case.

| case | topology | dies | targets | recipes | method | makespan_s | norm_serial | peak_temp_c | recipes |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |
| 3d_stack_m1_example | 3d_stack | 4 | 8 | 17/26 | Pure serial IEEE 1838 | 0.063843440 | 1.0000 | 25.190125 | I:3;S:5 |
| 3d_stack_m1_example | 3d_stack | 4 | 8 | 17/26 | M4 greedy recipe scheduling | 0.005004640 | 0.0784 | 25.028299 | F:4;I:3;S:1 |
| 3d_stack_m1_example | 3d_stack | 4 | 8 | 17/26 | M5 CP-SAT | 0.003963920 | 0.0621 | 25.028282 | F:4;I:3;S:1 |
| 2_5d_interposer_m9_public | 2_5d_interposer | 4 | 15 | 47/77 | Pure serial IEEE 1838 | 0.004161160 | 1.0000 | 25.007133 | I:4;S:11 |
| 2_5d_interposer_m9_public | 2_5d_interposer | 4 | 15 | 47/77 | M4 greedy recipe scheduling | 0.001766160 | 0.4244 | 25.001258 | F:10;I:4;S:1 |
| 2_5d_interposer_m9_public | 2_5d_interposer | 4 | 15 | 47/77 | M5 CP-SAT | 0.001762160 | 0.4235 | 25.001255 | F:10;I:4;S:1 |
| 5_5d_multi_tower_m9_public | 5_5d_multi_tower | 6 | 18 | 54/94 | Pure serial IEEE 1838 | 0.091357560 | 1.0000 | 25.153871 | I:5;S:13 |
| 5_5d_multi_tower_m9_public | 5_5d_multi_tower | 6 | 18 | 54/94 | M4 greedy recipe scheduling | 0.002465461 | 0.0270 | 25.002344 | F:12;I:5;S:1 |
| 5_5d_multi_tower_m9_public | 5_5d_multi_tower | 6 | 18 | 54/94 | M5 CP-SAT | 0.002455400 | 0.0269 | 25.003748 | F:12;I:5;S:1 |

## Best Makespan Per Case

- `2_5d_interposer_m9_public`: `m5_cpsat` at 0.001762160 s (normalized 0.4235).
- `3d_stack_m1_example`: `m5_cpsat` at 0.003963920 s (normalized 0.0621).
- `5_5d_multi_tower_m9_public`: `m5_cpsat` at 0.002455400 s (normalized 0.0269).

## Data Notes

- ITC'02 `.soc` files provide public benchmark scan-chain lengths and pattern counts for generated M9 test objects.
- UCIe/Open3DBench values are used as public package-link and topology references.
- IEEE 1838 controller bit widths, DWR sizing, per-phase power, and thermal RC coefficients remain labeled model assumptions.
- Thermal values are first-order RC proxy results, not HotSpot outputs.
