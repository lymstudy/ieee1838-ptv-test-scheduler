# M8 Baseline Comparison Report

| method | makespan_s | norm | peak_power_w | peak_temp_c | FPP util | serial busy | recipes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Pure serial IEEE 1838 | 0.063843440 | 1.0000 | 2.760000 | 25.190125 | 0.0000 | 0.9999 | I:3;S:5 |
| Fixed fastest recipe | 0.005004640 | 0.0784 | 3.270000 | 25.028299 | 0.7897 | 0.1149 | F:4;I:3;S:1 |
| Simplified TAM/FPP packing | 0.005004640 | 0.0784 | 3.270000 | 25.028299 | 0.7897 | 0.1149 | F:4;I:3;S:1 |
| Power-aware fixed recipe | 0.007525680 | 0.1179 | 5.640000 | 25.090840 | 0.2615 | 0.0779 | B:2;F:2;I:3;S:1 |
| M4 greedy recipe scheduling | 0.005004640 | 0.0784 | 3.270000 | 25.028299 | 0.7897 | 0.1149 | F:4;I:3;S:1 |
| M5 CP-SAT | 0.003963920 | 0.0621 | 5.040000 | 25.028283 | 0.9970 | 0.1451 | F:4;I:3;S:1 |
| M6 CP-SAT-ALNS | 0.003963920 | 0.0621 | 5.040000 | 25.028282 | 0.9970 | 0.1451 | F:4;I:3;S:1 |

- Best makespan: `m5_cpsat` at 0.003963920 s.
- Lowest thermal proxy peak: `m6_alns` at 25.028282 C.

Thermal values are first-order RC proxy results, not HotSpot outputs.
