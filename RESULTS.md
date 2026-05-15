# RESULTS

## 1. Current MVP Status

The current MVP has completed the core 4-die IEEE 1838-style PTV-aware test scheduling prototype components:

- Serial baseline
- Bandwidth-greedy baseline
- PTV-aware scheduler
- Unified schedule evaluator
- Simplified shared-PDN voltage model
- Clean 4-die case validation
- 4-die stress workload mechanism validation

The prototype uses IEEE 1838-compatible access resources such as PTAP, STAP, Die Wrapper Register (DWR) segments, and optional FPP lanes. IEEE 1838 is used as the access-resource context; the standard is not treated as defining a scheduling algorithm.

## 2. Clean 4-die MVP Case

| scheduler | TAT | peak_temperature | peak_ir_drop | temperature_violation_count | voltage_violation_count |
|---|---:|---:|---:|---:|---:|
| serial_ieee1838_style | 0.0106 | 25.0070719229 | 0.034875 | 0 | 0 |
| bandwidth_greedy | 0.0040 | 25.0070712813 | 0.0928125 | 0 | 4 |
| ptv_aware | 0.0054 | 25.0070715562 | 0.0675 | 0 | 0 |

Bandwidth-greedy significantly reduces TAT, but it produces voltage violations under the simplified shared-PDN evaluator. PTV-aware scheduling slightly increases TAT compared with bandwidth-greedy, but eliminates the voltage violations.

This is the expected result after the schedule evaluator fix: concurrent tasks now contribute to the shared-PDN current, so the greedy schedule has a higher peak IR-drop than the serial schedule.

## 3. 4-die Stress Workload Case

| scheduler | TAT | peak_temperature | peak_ir_drop | temperature_violation_count | voltage_violation_count |
|---|---:|---:|---:|---:|---:|
| serial_ieee1838_style | 0.0454 | 26.2233591261 | 0.1125 | 9 | 0 |
| bandwidth_greedy | 0.0168 | 26.4709087381 | 0.571875 | 48 | 71 |
| ptv_aware | 0.0386 | 25.8033739302 | 0.159375 | 0 | 0 |

Bandwidth-greedy is the most aggressive scheduler in the stress workload and achieves the shortest TAT, but it creates severe thermal and voltage violations.

PTV-aware scheduling sacrifices part of the TAT improvement to reduce both thermal and voltage violation counts to 0.

Serial scheduling has no voltage violation in this stress workload, but its long test time still allows thermal accumulation and produces temperature violations in the simplified RC model.

## 4. Key Insight

PTV-aware scheduling is not designed to always minimize raw test time. Instead, it reduces physical constraint violations while retaining much shorter TAT than purely serial scheduling.

## 5. Generated Figures

Clean case:

- results/case_4die/tat_comparison.svg
- results/case_4die/peak_temperature_comparison.svg
- results/case_4die/peak_ir_drop_comparison.svg
- results/case_4die/serial_gantt.svg
- results/case_4die/greedy_gantt.svg
- results/case_4die/ptv_gantt.svg

Stress case:

- results/case_4die_stress/tat_comparison.svg
- results/case_4die_stress/peak_temperature_comparison.svg
- results/case_4die_stress/peak_ir_drop_comparison.svg
- results/case_4die_stress/serial_gantt.svg
- results/case_4die_stress/greedy_gantt.svg
- results/case_4die_stress/ptv_gantt.svg

## FPP Lane Sweep

The FPP lane sweep uses `configs/case_4die_stress.yaml` as the base workload and evaluates FPP lane counts `[1, 2, 3, 4, 6, 8]`.

Summary CSV:

- results/sweeps/fpp_lanes/fpp_lane_sweep_summary.csv

Generated figures:

- results/sweeps/fpp_lanes/tat_vs_fpp_lanes.svg
- results/sweeps/fpp_lanes/peak_ir_drop_vs_fpp_lanes.svg
- results/sweeps/fpp_lanes/peak_temperature_vs_fpp_lanes.svg
- results/sweeps/fpp_lanes/voltage_violations_vs_fpp_lanes.svg
- results/sweeps/fpp_lanes/temperature_violations_vs_fpp_lanes.svg

Key observations:

- Serial scheduling is insensitive to FPP lane count in TAT because it executes tasks one at a time. Its TAT remains 0.0454 s for all swept lane counts.
- Bandwidth-greedy TAT decreases as FPP lanes increase, from 0.0318 s at 1 lane to 0.0066 s at 8 lanes.
- Bandwidth-greedy peak IR-drop increases as FPP lanes increase, from 0.490625 V at 1 lane to 1.003125 V at 8 lanes, showing the risk of aggressive parallel access under the simplified shared-PDN model.
- Bandwidth-greedy violation counts are not strictly monotonic because higher FPP lane counts change both concurrency and total elapsed time. Voltage violations remain nonzero for all swept lane counts.
- PTV-aware scheduling keeps both thermal and voltage violation counts at 0 for all swept lane counts.
- PTV-aware TAT improves from 0.0438 s at 1 lane to 0.0386 s at 2 lanes, then shows diminishing returns for additional FPP lanes because physical constraints, not raw FPP bandwidth, become the binding factor.

Representative sweep endpoints:

| fpp_lanes | scheduler | TAT | peak_ir_drop | temperature_violation_count | voltage_violation_count |
|---:|---|---:|---:|---:|---:|
| 1 | serial_ieee1838_style | 0.0454 | 0.1125 | 9 | 0 |
| 1 | bandwidth_greedy | 0.0318 | 0.490625 | 36 | 16 |
| 1 | ptv_aware | 0.0438 | 0.1125 | 0 | 0 |
| 8 | serial_ieee1838_style | 0.0454 | 0.1125 | 9 | 0 |
| 8 | bandwidth_greedy | 0.0066 | 1.003125 | 26 | 35 |
| 8 | ptv_aware | 0.0386 | 0.159375 | 0 | 0 |
## 6. Known Limitations

- The thermal model is still a simplified per-die RC model.
- There is no die-to-die thermal coupling yet.
- The stress workload is for mechanism validation, not a real benchmark.
- There is no benchmark-derived workload yet.
- There is no RTL mock validation yet.
- There is no HotSpot, 3D-ICE, or industrial PDN validation yet.
- The simplified shared-PDN voltage model is an MVP abstraction, not a signoff-quality PDN model.

