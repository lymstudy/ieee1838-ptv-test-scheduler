# M15: Chinese Experiment Chapter Draft

## Goal

M15 converts the M10-M14 evidence into a Chinese experiment chapter draft and a
caption index for figures and tables. It does not rerun any experiment.

## Inputs

```text
results/tables/m10_benchmark_sweep.csv
results/tables/m11_algorithm_comparison.csv
results/tables/m12_hotspot_validation_summary.csv
results/tables/m13_figure_index.csv
```

## Outputs

```text
results/reports/m15_chinese_experiment_chapter_draft.md
results/tables/m15_caption_index.csv
```

## Command

```powershell
python experiments/generate_m15_chinese_experiment_chapter.py
```

## Writing Rules

- Use Chinese academic prose, but keep method names such as M4, M5, HotSpot,
  CP-SAT, ALNS, and Test Access Recipe unchanged.
- State HotSpot as representative offline validation, not as an inner-loop
  solver or industrial signoff flow.
- Keep limitations explicit so the chapter does not overclaim.
- Use the caption index as the source of figure/table titles.

## Current Status

M15 is complete. The generated Chinese draft contains the experimental setup,
scale/topology coverage analysis, algorithm comparison, HotSpot validation
discussion, figure/table placement, limitations, and chapter summary. The latest
full regression check passed with 59 tests.
