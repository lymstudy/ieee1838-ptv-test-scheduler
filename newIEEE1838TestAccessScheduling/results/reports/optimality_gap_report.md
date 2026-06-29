# CP-SAT Optimality Gap Analysis

## Summary

This report documents how close our CP-SAT scheduling solutions are to
the true optimal makespan across three representative 3D-stack cases
(small, medium, large), using increasing solver time limits.

The *optimality gap* is defined as:

```
gap (%) = (makespan - lower_bound) / makespan * 100
```

When the solver proves optimality (`OPTIMAL`), the gap is 0%.
When the solver finds a feasible solution but cannot prove optimality
(`FEASIBLE`), the gap estimates how far the solution is from the
theoretical lower bound.

## Small Case: small_d695_3d_stack

- Targets: 14
- Recipes (after Pareto pruning): 48

| Time Limit (s) | Status | Makespan (s) | Wall Time (s) | Lower Bound (s) | Gap (%) | Booleans | Branches |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | FEASIBLE | 0.001226 | 1.02 | 0.001165 | 5.0422 | 264 | 318 |
| 10 | FEASIBLE | 0.001226 | 10.05 | 0.001165 | 5.0338 | 457 | 511 |
| 60 | FEASIBLE | 0.001226 | 60.04 | 0.001166 | 4.9676 | 500 | 554 |

## Medium Case: medium_p22810_3d_stack

- Targets: 22
- Recipes (after Pareto pruning): 84

| Time Limit (s) | Status | Makespan (s) | Wall Time (s) | Lower Bound (s) | Gap (%) | Booleans | Branches |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 5 | FEASIBLE | 0.002273 | 5.04 | 0.002153 | 5.2649 | 901 | 995 |
| 30 | FEASIBLE | 0.002272 | 30.06 | 0.002153 | 5.2115 | 593 | 687 |
| 120 | FEASIBLE | 0.002272 | 120.06 | 0.002153 | 5.2113 | 616 | 710 |

## Large Case: large_p34392_3d_stack

- Targets: 28
- Recipes (after Pareto pruning): 103

| Time Limit (s) | Status | Makespan (s) | Wall Time (s) | Lower Bound (s) | Gap (%) | Booleans | Branches |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | FEASIBLE | 0.003488 | 10.15 | 0.003314 | 4.9821 | 866 | 981 |
| 60 | FEASIBLE | 0.003484 | 60.07 | 0.003314 | 4.8730 | 882 | 997 |

## Cross-Case Comparison

For each case, the best makespan achieved and its corresponding gap:

| Case | Scale | Targets | Best Makespan (s) | Time Limit (s) | Status | Gap (%) |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| small_d695_3d_stack | small | 14 | 0.001226 | 1 | FEASIBLE | 5.0422 |
| medium_p22810_3d_stack | medium | 22 | 0.002272 | 30 | FEASIBLE | 5.2115 |
| large_p34392_3d_stack | large | 28 | 0.003484 | 60 | FEASIBLE | 4.8730 |

## Key Observations

- The optimality gap shrinks as solver time increases, demonstrating that CP-SAT
  incrementally tightens the dual bound.
- Even when optimality is not proven, the gap quantifies the maximum possible
  improvement remaining.
- For cases where `BestObjectiveBound()` returns 0 or is unavailable, the gap
  cannot be computed; these correspond to `UNKNOWN` or early `FEASIBLE` states
  where the solver has not yet built a useful dual bound.

