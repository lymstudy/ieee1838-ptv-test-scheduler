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
## Voltage Limit Sweep

The voltage limit sweep uses `configs/case_4die_stress.yaml` as the base workload and evaluates IR-drop limits `[0.10, 0.15, 0.20, 0.30, 0.50]` V by overriding `voltage.max_ir_drop_v` in a copied config.

Summary CSV:

- results/sweeps/voltage_limits/voltage_limit_sweep_summary.csv

Generated figures:

- results/sweeps/voltage_limits/tat_vs_voltage_limit.svg
- results/sweeps/voltage_limits/peak_ir_drop_vs_voltage_limit.svg
- results/sweeps/voltage_limits/voltage_violations_vs_voltage_limit.svg

Key observations:

- Serial scheduling is insensitive to the voltage limit in TAT because the schedule itself is unchanged. At the tight 0.10 V limit, serial has 24 voltage-violation samples because some individual tasks exceed that limit under the simplified shared-PDN model.
- Bandwidth-greedy keeps the same schedule across voltage limits and therefore keeps the same TAT of 0.0168 s and peak IR-drop of 0.571875 V. Its voltage-violation count decreases as the limit is relaxed, from 86 at 0.10 V to 17 at 0.30 V and 0.50 V.
- PTV-aware responds to tighter voltage limits by increasing TAT and reducing concurrency. At 0.10 V, the limit is too tight for several individual tasks, so PTV-aware cannot eliminate all voltage violations and records 27 voltage-violation samples with 320 dummy cycles.
- For limits 0.15 V and above, PTV-aware keeps voltage_violation_count = 0.
- PTV-aware voltage violations are no worse than bandwidth-greedy for every swept voltage limit.
- Relaxing the voltage limit gives PTV-aware lower TAT: 0.1078 s at 0.10 V, 0.0420 s at 0.15 V, 0.0252 s at 0.20 V, 0.0182 s at 0.30 V, and 0.0178 s at 0.50 V.

Representative sweep rows:

| voltage_limit | scheduler | TAT | peak_ir_drop | voltage_violation_count | dummy_cycle_count |
|---:|---|---:|---:|---:|---:|
| 0.10 | serial_ieee1838_style | 0.0454 | 0.1125 | 24 | 0 |
| 0.10 | bandwidth_greedy | 0.0168 | 0.571875 | 86 | 0 |
| 0.10 | ptv_aware | 0.1078 | 0.1125 | 27 | 320 |
| 0.50 | serial_ieee1838_style | 0.0454 | 0.1125 | 0 | 0 |
| 0.50 | bandwidth_greedy | 0.0168 | 0.571875 | 17 | 0 |
| 0.50 | ptv_aware | 0.0178 | 0.496875 | 0 | 1 |
## Thermal Limit Sweep

The thermal limit sweep uses `configs/case_4die_stress.yaml` as the base workload and evaluates thermal limits `[25.5, 26.0, 26.5, 27.0, 28.0]` C by overriding `thermal.max_temp_c` in a copied config.

Summary CSV:

- results/sweeps/thermal_limits/thermal_limit_sweep_summary.csv

Generated figures:

- results/sweeps/thermal_limits/tat_vs_thermal_limit.svg
- results/sweeps/thermal_limits/peak_temperature_vs_thermal_limit.svg
- results/sweeps/thermal_limits/temperature_violations_vs_thermal_limit.svg
- results/sweeps/thermal_limits/dummy_cycles_vs_thermal_limit.svg

Key observations:

- Serial and bandwidth-greedy schedules do not change with thermal limit because these baselines do not use thermal constraints during scheduling.
- Greedy temperature violations decrease as the limit is relaxed: 89 at 25.5 C, 74 at 26.0 C, and 0 at 26.5 C or higher.
- PTV-aware keeps temperature_violation_count = 0 for thermal limits 26.0 C and above.
- The 25.5 C point is over-constrained in this stress case. The stack starts at about 25.55 C, so the initial condition already exceeds the limit. PTV-aware records 117 temperature-violation samples and inserts 63 dummy cycles at this point.
- PTV-aware TAT is 0.0524 s at 25.5 C, then returns to 0.0386 s for 26.0 C and above. This indicates that the thermal constraint only changes scheduling behavior in the tightest case for the current simplified thermal model.
- This trend should be interpreted with caution because the current thermal model is a simplified per-die RC model without die-to-die thermal coupling.

Representative sweep rows:

| thermal_limit | scheduler | TAT | peak_temperature | temperature_violation_count | dummy_cycle_count | over_constrained |
|---:|---|---:|---:|---:|---:|---|
| 25.5 | serial_ieee1838_style | 0.0454 | 26.2233591261 | 229 | 0 | True |
| 25.5 | bandwidth_greedy | 0.0168 | 26.4709087381 | 89 | 0 | True |
| 25.5 | ptv_aware | 0.0524 | 25.7416956875 | 117 | 63 | True |
| 26.0 | serial_ieee1838_style | 0.0454 | 26.2233591261 | 50 | 0 | False |
| 26.0 | bandwidth_greedy | 0.0168 | 26.4709087381 | 74 | 0 | False |
| 26.0 | ptv_aware | 0.0386 | 25.8033739302 | 0 | 0 | False |
| 28.0 | serial_ieee1838_style | 0.0454 | 26.2233591261 | 0 | 0 | False |
| 28.0 | bandwidth_greedy | 0.0168 | 26.4712650818 | 0 | 0 | False |
| 28.0 | ptv_aware | 0.0386 | 25.8033739302 | 0 | 0 | False |
## Workload Scale Sweep

The workload scale sweep uses a deterministic synthetic workload generator in `src/workload/synthetic.py`. It evaluates die counts `[4, 8, 12]` and task densities `[small, medium, large]`.

This experiment is still synthetic mechanism validation. It is not a benchmark-derived workload and does not claim correspondence to real RTL, ATPG, HotSpot, 3D-ICE, RedHawk, Voltus, or Tessent SSN results.

Summary CSV:

- results/sweeps/workload_scale/workload_scale_summary.csv

Generated figures:

- results/sweeps/workload_scale/tat_vs_workload_scale.svg
- results/sweeps/workload_scale/peak_ir_drop_vs_workload_scale.svg
- results/sweeps/workload_scale/peak_temperature_vs_workload_scale.svg
- results/sweeps/workload_scale/voltage_violations_vs_workload_scale.svg
- results/sweeps/workload_scale/temperature_violations_vs_workload_scale.svg
- results/sweeps/workload_scale/task_count_vs_workload_scale.svg

Task count trend:

| die_count | small | medium | large |
|---:|---:|---:|---:|
| 4 | 19 | 27 | 46 |
| 8 | 39 | 55 | 94 |
| 12 | 59 | 83 | 142 |

Key observations:

- Task count increases with both die count and density.
- Serial TAT increases with task count, from 0.0271 s for 4-small to 0.24339 s for 12-large.
- Bandwidth-greedy is consistently the fastest scheduler, but its voltage violations increase with workload scale. Greedy voltage violations grow from 18 for 4-small to 243 for 12-large.
- PTV-aware keeps voltage_violation_count = 0 and temperature_violation_count = 0 for every generated workload in this sweep.
- PTV-aware TAT is consistently below serial TAT and above greedy TAT, which matches the expected constrained scheduling tradeoff.
- Capture staggering is active for PTV-aware workloads. Dummy cycles are not triggered in this sweep because the generated workloads are not over-constrained under the selected thermal and voltage limits.
- No over-constrained workload-scale point appears in the current sweep.

Representative rows:

| workload | scheduler | num_tasks | TAT | peak_ir_drop | temperature_violation_count | voltage_violation_count |
|---|---|---:|---:|---:|---:|---:|
| 4-small | serial_ieee1838_style | 19 | 0.0271 | 0.088125 | 0 | 0 |
| 4-small | bandwidth_greedy | 19 | 0.0061 | 0.558125 | 0 | 18 |
| 4-small | ptv_aware | 19 | 0.0102 | 0.235000 | 0 | 0 |
| 12-large | serial_ieee1838_style | 142 | 0.24339 | 0.091250 | 0 | 0 |
| 12-large | bandwidth_greedy | 142 | 0.04866 | 2.070625 | 0 | 243 |
| 12-large | ptv_aware | 142 | 0.09030 | 0.239375 | 0 | 0 |
## Example Benchmark-derived Workload

The benchmark-derived workload example validates the statistics schema and adapter path. It is not a real benchmark result and does not parse RTL.

Inputs:

- benchmarks/schema.md
- benchmarks/example_benchmark_stats.yaml
- src/workload/benchmark_adapter.py

Generated outputs:

- results/benchmarks/example/benchmark_task_summary.csv
- results/benchmarks/example/serial_schedule.csv
- results/benchmarks/example/greedy_schedule.csv
- results/benchmarks/example/ptv_schedule.csv
- results/benchmarks/example/scheduler_metrics_summary.csv
- results/benchmarks/example/serial_gantt.svg
- results/benchmarks/example/greedy_gantt.svg
- results/benchmarks/example/ptv_gantt.svg
- results/benchmarks/example/tat_comparison.svg
- results/benchmarks/example/peak_ir_drop_comparison.svg
- results/benchmarks/example/peak_temperature_comparison.svg

The example adapter generated 21 abstract tasks from benchmark statistics. The task set includes scan shift, scan capture, BIST, instrument access, and DWR EXTEST tasks.

Example scheduler metrics:

| scheduler | TAT | peak_temperature | peak_ir_drop | temperature_violation_count | voltage_violation_count |
|---|---:|---:|---:|---:|---:|
| serial_ieee1838_style | 0.065206 | 26.0838020315 | 0.105000 | 0 | 0 |
| bandwidth_greedy | 0.043492 | 26.0783665049 | 0.565625 | 0 | 26 |
| ptv_aware | 0.042852 | 26.2690151238 | 0.183750 | 0 | 0 |

The result only shows that the schema-level adapter can generate scheduler-compatible workload objects and that the existing schedulers can consume them. It should not be interpreted as a real public benchmark conclusion.
## Example Benchmark Audit

A schedule audit was added for the example benchmark-derived workload to explain why PTV-aware has a slightly lower TAT than bandwidth-greedy in this schema-level example.

Audit outputs:

- results/benchmarks/example/audit/greedy_schedule_audit.csv
- results/benchmarks/example/audit/ptv_schedule_audit.csv
- results/benchmarks/example/audit/schedule_comparison_audit.md

Audit conclusion:

- No scheduler bug was found.
- Both bandwidth-greedy and PTV-aware satisfy FPP lane capacity in the audited schedule.
- Both schedules have no DWR segment overlap.
- Both schedules have no global idle time.
- Bandwidth-greedy final finishing task: `scan_capture_die3`.
- PTV-aware final finishing task: `scan_capture_die3`.
- Bandwidth-greedy first scan-shift start: 0.00192 s.
- PTV-aware first scan-shift start: 0 s.
- Bandwidth-greedy FPP idle lane-seconds: 0.002203.
- PTV-aware FPP idle lane-seconds: 0.000923.

In this example benchmark, PTV-aware can slightly outperform bandwidth-greedy in TAT because the heuristic priority ordering avoids resource blocking while also satisfying voltage constraints. Specifically, PTV-aware starts a long FPP scan-shift task immediately, while bandwidth-greedy first fills the ready queue using its deterministic local order and occupies FPP lanes with short DWR EXTEST tasks. Since the scan-shift tasks require all available FPP lanes, that early ordering difference shortens the serialized FPP scan tail for PTV-aware.

This result is workload-specific and should not be generalized into a claim that PTV-aware is always faster than bandwidth-greedy. Bandwidth-greedy remains a local ready-task packing baseline, not a global TAT optimizer.
## Realistic UART Statistics Workload

The realistic UART workload is a manually specified realistic statistics case for a small UART-like controller partitioned into four modules: `uart_rx_ctrl`, `uart_tx_ctrl`, `fifo_ctrl`, and `bus_if_ctrl`.

This workload is not parsed from RTL and is not real chip validation. It is intended to validate the benchmark-derived workload flow using circuit-level statistics that are closer to a small communication controller than the schema-only example.

Input and outputs:

- benchmarks/realistic_uart_stats.yaml
- results/benchmarks/realistic_uart/benchmark_task_summary.csv
- results/benchmarks/realistic_uart/serial_schedule.csv
- results/benchmarks/realistic_uart/greedy_schedule.csv
- results/benchmarks/realistic_uart/ptv_schedule.csv
- results/benchmarks/realistic_uart/scheduler_metrics_summary.csv
- results/benchmarks/realistic_uart/serial_gantt.svg
- results/benchmarks/realistic_uart/greedy_gantt.svg
- results/benchmarks/realistic_uart/ptv_gantt.svg
- results/benchmarks/realistic_uart/tat_comparison.svg
- results/benchmarks/realistic_uart/peak_ir_drop_comparison.svg
- results/benchmarks/realistic_uart/peak_temperature_comparison.svg
- results/benchmarks/realistic_uart/audit/greedy_schedule_audit.csv
- results/benchmarks/realistic_uart/audit/ptv_schedule_audit.csv
- results/benchmarks/realistic_uart/audit/schedule_comparison_audit.md

The adapter generated 21 abstract tasks from the manually specified UART statistics.

| scheduler | TAT | peak_temperature | peak_ir_drop | temperature_violation_count | voltage_violation_count |
|---|---:|---:|---:|---:|---:|
| serial_ieee1838_style | 0.010149 | 25.2698906020 | 0.066000 | 0 | 0 |
| bandwidth_greedy | 0.002128 | 25.3505638342 | 0.360000 | 0 | 17 |
| ptv_aware | 0.007661 | 25.2631210476 | 0.074000 | 0 | 0 |

Audit conclusion:

- No scheduler bug was found.
- Bandwidth-greedy and PTV-aware have no FPP capacity violation and no DWR overlap.
- Bandwidth-greedy is fastest but creates voltage violations under the simplified shared-PDN evaluator.
- PTV-aware increases TAT relative to bandwidth-greedy because it limits physical-risk concurrency, reducing voltage violations from 17 to 0.
- PTV-aware final finishing task: `scan_capture_die0`.
- Bandwidth-greedy final finishing task: `scan_capture_die3`.

This result should be interpreted as manually specified statistics-flow validation, not as a real benchmark conclusion.
## 6. Known Limitations

- The thermal model is still a simplified per-die RC model.
- There is no die-to-die thermal coupling yet.
- The stress workload is for mechanism validation, not a real benchmark.
- There is no benchmark-derived workload yet.
- There is no RTL mock validation yet.
- There is no HotSpot, 3D-ICE, or industrial PDN validation yet.
- The simplified shared-PDN voltage model is an MVP abstraction, not a signoff-quality PDN model.







