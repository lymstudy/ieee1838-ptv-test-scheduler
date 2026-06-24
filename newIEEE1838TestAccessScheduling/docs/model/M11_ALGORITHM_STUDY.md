# M11: Algorithm And Ablation Study

## Goal

M11 turns the M10 benchmark suite into algorithm evidence. It compares fixed
baselines, the M4 greedy scheduler, M5 CP-SAT, and a limited M6 ALNS run on
representative cases.

M11 is not a full thermal validation milestone. Thermal values still come from
the M7 proxy evaluator. HotSpot-level validation remains M12.

## Default Case Set

M11 uses the small and medium M10 workloads across all three topology families:

```text
configs/cases/m10/m10_small_d695_3d_stack.json
configs/cases/m10/m10_small_d695_2_5d_interposer.json
configs/cases/m10/m10_small_d695_5_5d_multi_tower.json
configs/cases/m10/m10_medium_p22810_3d_stack.json
configs/cases/m10/m10_medium_p22810_2_5d_interposer.json
configs/cases/m10/m10_medium_p22810_5_5d_multi_tower.json
```

The default resource setting is `8` FPP lanes and nominal package power. This
matches the middle M10 sweep point.

## Compared Methods

| Method | Purpose |
| --- | --- |
| `pure_serial` | Lower-bound baseline for IEEE 1838 serial-only access assumptions |
| `fixed_fastest` | Path fixed to fastest recipe before scheduling |
| `tam_like` | Simplified TAM/FPP packing baseline |
| `low_power` | Fixed low-power recipe baseline |
| `m4_all_recipes` | Ablation: M4 greedy without Pareto pruning |
| `m4_greedy` | M4 greedy on Pareto-pruned recipes |
| `m5_cpsat` | CP-SAT constrained scheduling on Pareto recipes |
| `m6_alns` | Limited ALNS refinement on cases below the target threshold |

## Commands

```bash
python experiments/run_m11_algorithm_study.py
```

Formal outputs:

```text
results/tables/m11_algorithm_comparison.csv
results/reports/m11_algorithm_study_report.md
```

## Interpretation Rules

- `m5_cpsat` rows with `FEASIBLE` are valid schedules but not global optimality
  proofs.
- `m6_alns` is run only on cases below `--max-alns-targets` by default to keep
  the experiment bounded.
- M11 can support algorithm ranking claims only for the selected cases and
  resource setting.
- M12 is still required before making strong thermal claims.

## Current M11 Result Snapshot

The first M11 run used 6 representative cases:

- small `d695`: `3d_stack`, `2_5d_interposer`, `5_5d_multi_tower`;
- medium `p22810`: `3d_stack`, `2_5d_interposer`, `5_5d_multi_tower`;
- 8 FPP lanes and nominal package power.

Rows generated:

- 48 total rows;
- 45 successful schedule rows;
- 3 skipped `m6_alns` rows because medium cases exceed the default ALNS target
  threshold.

Average normalized makespan versus pure serial:

| Method | Rows | Avg normalized makespan | Avg speedup |
| --- | ---: | ---: | ---: |
| `pure_serial` | 6 | 1.0000 | 1.00 |
| `fixed_fastest` | 6 | 0.1819 | 22.80 |
| `tam_like` | 6 | 0.1819 | 22.80 |
| `low_power` | 6 | 0.1929 | 20.47 |
| `m4_all_recipes` | 6 | 0.1819 | 22.80 |
| `m4_greedy` | 6 | 0.1819 | 22.80 |
| `m5_cpsat` | 6 | 0.1814 | 22.86 |
| `m6_alns` | 3 | 0.3394 | 2.95 |

The current selected cases do not strongly separate `fixed_fastest`, `tam_like`,
and `m4_greedy`; this means M11 should be followed by tighter resource and
thermal-stress ablations before final claims. The equality between
`m4_all_recipes` and `m4_greedy` in this run is still useful: it indicates that
Pareto pruning did not degrade the M4 schedule on these cases.
