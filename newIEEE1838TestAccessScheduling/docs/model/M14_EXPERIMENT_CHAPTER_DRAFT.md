# M14: Experiment Chapter Draft

## Goal

M14 organizes M10-M13 outputs into a paper/thesis experiment chapter draft. It
does not rerun scheduling, thermal proxy evaluation, visualization, or HotSpot.

## Inputs

```text
results/tables/m10_benchmark_sweep.csv
results/tables/m11_algorithm_comparison.csv
results/tables/m12_hotspot_validation_summary.csv
results/tables/m13_figure_index.csv
```

## Outputs

```text
results/reports/m14_experiment_chapter_draft.md
results/tables/m14_experiment_artifact_index.csv
```

## Command

```powershell
python experiments/generate_m14_experiment_chapter.py
```

## Writing Rules

- Describe M10 as the broad scale/topology coverage experiment.
- Describe M11 as the richer algorithm comparison experiment.
- Describe M12b as representative offline HotSpot validation, not a full thermal
  signoff flow.
- Use M13 figures as curated visual evidence rather than adding ad hoc plots.
- CP-SAT `FEASIBLE` rows should be described as feasible refined schedules, not
  global optima.

## Current Scope

The draft is meant to be a structured experimental narrative. It is not the
final thesis text yet; it is the source material for the final chapter.

## Current Status

M14 is complete. The generated draft summarizes M10 benchmark coverage, M11
algorithm comparison, M12b HotSpot validation, and M13 figure usage. The latest
full regression check passed with 57 tests.
