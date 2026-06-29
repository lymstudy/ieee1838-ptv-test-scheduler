# Resource Pressure Sweep Report

## Experiment Summary

- Total rows: 72
- Successful schedules: 72
- Failed schedules: 0

## Part A: Shared BIST Count Sweep

### Topology: 2_5d_interposer

| BIST Count | fixed_fastest (s) | M4 Greedy (s) | M4 Gain (%) | M5 CP-SAT (s) | M5 Gain (%) | M5 Status |
|-----------|-------------------|---------------|-------------|---------------|-------------|-----------|
| 1 | 0.052 | 0.027 | 48.70 | 0.027 | 48.72 | OPTIMAL |
| 2 | 0.026 | 0.021 | 20.00 | 0.021 | 20.02 | OPTIMAL |
| 4 | 0.021 | 0.016 | 24.90 | 0.016 | 24.97 | OPTIMAL |
| 8 | 0.016 | 0.016 | 0.06 | 0.016 | 0.06 | OPTIMAL |
| inf | 0.016 | 0.016 | 0.00 | 0.016 | 0.00 | OPTIMAL |

### Topology: 3d_stack

| BIST Count | fixed_fastest (s) | M4 Greedy (s) | M4 Gain (%) | M5 CP-SAT (s) | M5 Gain (%) | M5 Status |
|-----------|-------------------|---------------|-------------|---------------|-------------|-----------|
| 1 | 0.060 | 0.038 | 37.31 | 0.032 | 46.67 | FEASIBLE |
| 2 | 0.036 | 0.030 | 16.66 | 0.024 | 33.34 | OPTIMAL |
| 4 | 0.030 | 0.028 | 7.95 | 0.018 | 39.98 | OPTIMAL |
| 8 | 0.018 | 0.018 | -0.00 | 0.018 | 0.21 | OPTIMAL |
| inf | 0.018 | 0.018 | 0.00 | 0.018 | 0.21 | OPTIMAL |

### Topology: 5_5d_multi_tower

| BIST Count | fixed_fastest (s) | M4 Greedy (s) | M4 Gain (%) | M5 CP-SAT (s) | M5 Gain (%) | M5 Status |
|-----------|-------------------|---------------|-------------|---------------|-------------|-----------|
| 1 | 0.058 | 0.035 | 39.99 | 0.032 | 44.83 | OPTIMAL |
| 2 | 0.029 | 0.023 | 19.99 | 0.023 | 20.01 | OPTIMAL |
| 4 | 0.023 | 0.017 | 24.89 | 0.017 | 24.96 | OPTIMAL |
| 8 | 0.017 | 0.017 | 0.04 | 0.017 | 0.06 | OPTIMAL |
| inf | 0.017 | 0.017 | 0.00 | 0.017 | 0.00 | OPTIMAL |

## Part B: Path Diversity Sweep (shared BIST=1)

### Topology: 2_5d_interposer

| Allowed Types | fixed_fastest (s) | M4 Greedy (s) | M4 Gain (%) | M5 CP-SAT (s) | M5 Gain (%) | M5 Status |
|--------------|-------------------|---------------|-------------|---------------|-------------|-----------|
| BIST_only | 0.052 | 0.052 | 0.00 | 0.052 | 0.00 | OPTIMAL |
| BIST_FPP | 0.052 | 0.027 | 48.70 | 0.027 | 48.72 | FEASIBLE |
| BIST_FPP_Hybrid | 0.052 | 0.027 | 48.70 | 0.027 | 48.72 | OPTIMAL |

### Topology: 3d_stack

| Allowed Types | fixed_fastest (s) | M4 Greedy (s) | M4 Gain (%) | M5 CP-SAT (s) | M5 Gain (%) | M5 Status |
|--------------|-------------------|---------------|-------------|---------------|-------------|-----------|
| BIST_only | 0.060 | 0.060 | 0.00 | 0.060 | 0.00 | OPTIMAL |
| BIST_FPP | 0.060 | 0.038 | 37.31 | 0.032 | 46.67 | OPTIMAL |
| BIST_FPP_Hybrid | 0.060 | 0.038 | 37.31 | 0.032 | 46.67 | OPTIMAL |

### Topology: 5_5d_multi_tower

| Allowed Types | fixed_fastest (s) | M4 Greedy (s) | M4 Gain (%) | M5 CP-SAT (s) | M5 Gain (%) | M5 Status |
|--------------|-------------------|---------------|-------------|---------------|-------------|-----------|
| BIST_only | 0.058 | 0.058 | 0.00 | 0.058 | 0.00 | OPTIMAL |
| BIST_FPP | 0.058 | 0.035 | 39.99 | 0.032 | 44.83 | OPTIMAL |
| BIST_FPP_Hybrid | 0.058 | 0.035 | 39.99 | 0.032 | 44.83 | OPTIMAL |

## Interpretation Notes

1. **BIST pressure gradient (Part A):** As shared BIST count decreases (fewer engines shared by more targets), pressure increases. Joint scheduling gain should be largest at shared BIST=1 and approach 0% when BIST is private (inf). The gain curve by topology reveals which topologies benefit most from joint scheduling under resource pressure.
2. **Path diversity gradient (Part B):** When only BIST is available, all test must serialise on shared engines. Adding FPP creates an alternative path for concurrent scheduling. Adding Hybrid further increases flexibility. Gain should monotonically increase as path diversity increases.
3. **CP-SAT feasibility:** When CP-SAT status is FEASIBLE (not OPTIMAL), the reported makespan is an upper bound. The true optimal gain may be higher.