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

## 6. Known Limitations

- The thermal model is still a simplified per-die RC model.
- There is no die-to-die thermal coupling yet.
- The stress workload is for mechanism validation, not a real benchmark.
- There is no benchmark-derived workload yet.
- There is no RTL mock validation yet.
- There is no HotSpot, 3D-ICE, or industrial PDN validation yet.
- The simplified shared-PDN voltage model is an MVP abstraction, not a signoff-quality PDN model.
