# Sen Gupta 2011 Partial Overlapping Baseline Report

- Cases processed: 6
- Total rows: 18
- Successful rows: 18
- Failed rows: 0
- Lane count: 8
- Power profile: nominal

## Results Table

| case_id | method_id | makespan_s | peak_power_w | fpp_utilization | num_sessions | status |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| m10_small_d695_3d_stack | po_sen_gupta_2011 | 0.001242134 | 5.270000 | 0.0029 | 14 | ok |
| m10_small_d695_3d_stack | pure_serial | 0.003620280 | 2.180000 | 0.0000 | 68 | ok |
| m10_small_d695_3d_stack | fixed_fastest | 0.001229440 | 2.249400 | 0.0030 | 68 | ok |
| m10_medium_p22810_3d_stack | po_sen_gupta_2011 | 0.002433860 | 5.270000 | 0.0583 | 22 | ok |
| m10_medium_p22810_3d_stack | pure_serial | 0.093207720 | 2.180000 | 0.0000 | 108 | ok |
| m10_medium_p22810_3d_stack | fixed_fastest | 0.002277820 | 2.258500 | 0.0623 | 110 | ok |
| m10_large_p34392_3d_stack | po_sen_gupta_2011 | 0.003833567 | 5.270000 | 0.0845 | 28 | ok |
| m10_large_p34392_3d_stack | pure_serial | 0.210895080 | 2.180000 | 0.0000 | 138 | ok |
| m10_large_p34392_3d_stack | fixed_fastest | 0.003492692 | 2.237700 | 0.0927 | 147 | ok |
| m21_pressure_medium_p22810_3d_stack | po_sen_gupta_2011 | 0.098344400 | 4.320000 | 0.0000 | 22 | ok |
| m21_pressure_medium_p22810_3d_stack | pure_serial | 158.421565840 | 2.480000 | 0.0000 | 108 | ok |
| m21_pressure_medium_p22810_3d_stack | fixed_fastest | 0.096012480 | 4.490000 | 0.0000 | 60 | ok |
| m21_pressure_large_p34392_3d_stack | po_sen_gupta_2011 | 0.123586160 | 4.320000 | 0.0000 | 28 | ok |
| m21_pressure_large_p34392_3d_stack | pure_serial | 425.693207280 | 2.480000 | 0.0000 | 138 | ok |
| m21_pressure_large_p34392_3d_stack | fixed_fastest | 0.120015040 | 4.530000 | 0.0000 | 78 | ok |
| m21_pressure_xlarge_p93791_3d_stack | po_sen_gupta_2011 | 0.150571440 | 4.320000 | 0.0000 | 36 | ok |
| m21_pressure_xlarge_p93791_3d_stack | pure_serial | 142.137757680 | 2.480000 | 0.0000 | 178 | ok |
| m21_pressure_xlarge_p93791_3d_stack | fixed_fastest | 0.144018880 | 4.610000 | 0.0000 | 105 | ok |

## Gain Analysis

### m10_large_p34392_3d_stack
- PO makespan: 0.003833567 s (sessions: 28)
- Pure serial makespan: 0.210895080 s
- Gain vs pure_serial: +98.18% (+0.207061513 s)
- Fixed fastest makespan: 0.003492692 s
- Gain vs fixed_fastest: -9.76% (-0.000340875 s)

### m10_medium_p22810_3d_stack
- PO makespan: 0.002433860 s (sessions: 22)
- Pure serial makespan: 0.093207720 s
- Gain vs pure_serial: +97.39% (+0.090773860 s)
- Fixed fastest makespan: 0.002277820 s
- Gain vs fixed_fastest: -6.85% (-0.000156040 s)

### m10_small_d695_3d_stack
- PO makespan: 0.001242134 s (sessions: 14)
- Pure serial makespan: 0.003620280 s
- Gain vs pure_serial: +65.69% (+0.002378146 s)
- Fixed fastest makespan: 0.001229440 s
- Gain vs fixed_fastest: -1.03% (-0.000012694 s)

### m21_pressure_large_p34392_3d_stack
- PO makespan: 0.123586160 s (sessions: 28)
- Pure serial makespan: 425.693207280 s
- Gain vs pure_serial: +99.97% (+425.569621120 s)
- Fixed fastest makespan: 0.120015040 s
- Gain vs fixed_fastest: -2.98% (-0.003571120 s)

### m21_pressure_medium_p22810_3d_stack
- PO makespan: 0.098344400 s (sessions: 22)
- Pure serial makespan: 158.421565840 s
- Gain vs pure_serial: +99.94% (+158.323221440 s)
- Fixed fastest makespan: 0.096012480 s
- Gain vs fixed_fastest: -2.43% (-0.002331920 s)

### m21_pressure_xlarge_p93791_3d_stack
- PO makespan: 0.150571440 s (sessions: 36)
- Pure serial makespan: 142.137757680 s
- Gain vs pure_serial: +99.89% (+141.987186240 s)
- Fixed fastest makespan: 0.144018880 s
- Gain vs fixed_fastest: -4.55% (-0.006552560 s)

## Notes

- PO strategy packs targets into concurrent sessions; sessions run sequentially.
- Session count reflects the degree of achievable parallelism under the resource model.
- Compare against pure_serial and fixed_fastest to isolate the PO contribution.
- Resource constraints honored: PTAP serial, FPP lanes/channels, DWR groups,
  BIST engine groups, exclusive test sessions, concurrent capture limit, and power budget.
