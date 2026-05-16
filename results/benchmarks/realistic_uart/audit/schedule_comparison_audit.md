# Realistic UART Schedule Audit

This audit covers a manually specified realistic statistics case. It is not RTL-extracted benchmark validation.

## Summary

No scheduler bug was found in this audit.

PTV-aware TAT is greater than bandwidth-greedy TAT in this manually specified UART statistics case. This is the expected constrained-scheduling tradeoff when PTV-aware limits physical-risk concurrency.

## Scheduler Metrics

| scheduler | TAT | final finishing task | peak temperature | peak IR-drop | temperature violations | voltage violations | max parallelism |
|---|---:|---|---:|---:|---:|---:|---:|
| bandwidth_greedy | 0.002128 | scan_capture_die3 | 25.3505638342 | 0.36 | 0 | 17 | 8 |
| ptv_aware | 0.007661 | scan_capture_die0 | 25.2631210476 | 0.074 | 0 | 0 | 3 |

## Resource Checks

| scheduler | FPP capacity violation intervals | DWR overlap violation intervals | global idle time | FPP idle lane-seconds | first scan-shift start |
|---|---:|---:|---:|---:|---:|
| bandwidth_greedy | 0 | 0 | 0 | 0.000107 | 0 |
| ptv_aware | 0 | 0 | 0 | 0.011173 | 0 |

## Violation Comparison

- Bandwidth-greedy voltage violations: 17.
- PTV-aware voltage violations: 0.
- Bandwidth-greedy temperature violations: 0.
- PTV-aware temperature violations: 0.
- TAT delta, PTV-aware - bandwidth-greedy: 0.005533 s.

## Interpretation

The realistic UART statistics workload is manually specified from circuit-level estimates. The audit should be used to check consistency of the generated schedules and resource usage, not to claim real chip validation.

If PTV-aware is close to or faster than bandwidth-greedy in this case, the explanation is heuristic ordering and reduced resource blocking. If PTV-aware is slower, the explanation is physical-risk-aware throttling. In either case, the result should not be generalized beyond this workload without additional benchmark-derived data.

## FPP Task Order

Bandwidth-greedy FPP task order:

```text
dwr_extest_die0_die1 -> scan_shift_die0 -> dwr_extest_die1_die2 -> scan_capture_die0 -> scan_shift_die1 -> dwr_extest_die2_die3 -> scan_capture_die1 -> scan_shift_die2 -> scan_shift_die3 -> scan_capture_die2 -> scan_capture_die3
```

PTV-aware FPP task order:

```text
dwr_extest_die0_die1 -> scan_shift_die2 -> scan_shift_die3 -> dwr_extest_die1_die2 -> scan_shift_die0 -> dwr_extest_die2_die3 -> scan_shift_die1 -> scan_capture_die2 -> scan_capture_die3 -> scan_capture_die1 -> scan_capture_die0
```
