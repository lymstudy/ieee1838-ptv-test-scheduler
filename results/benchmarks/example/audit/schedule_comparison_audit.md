# Example Benchmark Schedule Audit

## Summary

No scheduler bug was found in this audit.

PTV-aware TAT is slightly smaller than bandwidth-greedy TAT in this schema-level example because the PTV-aware benefit/risk priority starts a long FPP scan task immediately, while bandwidth-greedy fills ready tasks using its deterministic local order and initially occupies both FPP lanes with short DWR EXTEST tasks. Since each scan-shift task in this example requires all available FPP lanes, that early ordering difference shortens the serialized FPP scan tail for PTV-aware.

This is a reasonable heuristic ordering difference, not evidence that PTV-aware is generally faster than bandwidth-greedy. Bandwidth-greedy is a local ready-task packing baseline, not a global TAT optimizer.

## Scheduler Metrics

| scheduler | TAT | final finishing task | peak IR-drop | voltage violations | max parallelism |
|---|---:|---|---:|---:|---:|
| bandwidth_greedy | 0.043492 | scan_capture_die3 | 0.565625 | 26 | 8 |
| ptv_aware | 0.042852 | scan_capture_die3 | 0.18375 | 0 | 3 |

## Resource Checks

| scheduler | FPP capacity violation intervals | DWR overlap violation intervals | global idle time | FPP idle lane-seconds |
|---|---:|---:|---:|---:|
| bandwidth_greedy | 0 | 0 | 0 | 0.002203 |
| ptv_aware | 0 | 0 | 0 | 0.000923 |

## Ordering Audit

- Bandwidth-greedy first scan-shift start: 0.00192 s.
- PTV-aware first scan-shift start: 0 s.
- TAT difference, greedy - PTV-aware: 0.00064 s.
- Bandwidth-greedy voltage violations: 26.
- PTV-aware voltage violations: 0.

Bandwidth-greedy satisfies the implemented baseline definition: at each event time it considers ready tasks in deterministic order and starts tasks that fit the current FPP, DWR, and exclusive access resources. It does not perform look-ahead to reserve FPP lanes for longer future-tail tasks.

PTV-aware does not violate FPP lane capacity or DWR segment exclusivity in this audit. Its priority ordering chooses high-benefit candidates that can satisfy predicted voltage and thermal constraints, which avoids the initial DWR-before-scan ordering that lengthens the greedy FPP tail.

## FPP Task Order

Bandwidth-greedy FPP task order:

```text
dwr_extest_die0_die1 -> dwr_extest_die1_die2 -> dwr_extest_die2_die3 -> scan_shift_die0 -> scan_capture_die0 -> scan_shift_die1 -> scan_capture_die1 -> scan_shift_die2 -> scan_capture_die2 -> scan_shift_die3 -> scan_capture_die3
```

PTV-aware FPP task order:

```text
scan_shift_die1 -> scan_shift_die2 -> scan_shift_die0 -> scan_shift_die3 -> dwr_extest_die0_die1 -> dwr_extest_die1_die2 -> dwr_extest_die2_die3 -> scan_capture_die1 -> scan_capture_die2 -> scan_capture_die0 -> scan_capture_die3
```

## Interpretation

PTV-aware can slightly outperform bandwidth-greedy in TAT in this example because heuristic priority ordering avoids resource blocking while also satisfying voltage constraints. This observation is workload-specific and should not be generalized to claim that PTV-aware is always faster than bandwidth-greedy.
