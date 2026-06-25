# M13: Visualization Summary

## Goal

M13 turns existing M10, M11, and M12b outputs into a small fixed set of
publication-oriented figures. It does not rerun scheduling, thermal proxy
evaluation, or HotSpot.

## Inputs

```text
results/tables/m10_benchmark_sweep.csv
results/tables/m11_algorithm_comparison.csv
results/tables/m12_hotspot_validation_summary.csv
results/schedules/m8_m4_greedy_schedule.csv
results/hotspot/m12b_outputs/m10_medium_p22810_3d_stack__m4_greedy.ttrace
```

## Outputs

```text
results/figures/m13/
results/tables/m13_figure_index.csv
results/reports/m13_visual_summary.md
```

Current figure set:

- `m13_m10_speedup_nominal_lane8.png`: M10 scale/topology speedup view.
- `m13_m11_algorithm_makespan.png`: M11 algorithm makespan comparison.
- `m13_m12b_proxy_hotspot_peak_comparison.png`: proxy vs HotSpot peak
  comparison.
- `m13_hotspot_trace_heatmap_medium_3d_m4_greedy.png`: block-level HotSpot
  temperature heatmap.
- `m13_representative_m4_greedy_gantt.png`: representative schedule Gantt view.

## Command

```powershell
python experiments/generate_m13_visualizations.py
```

## Interpretation Rules

- Use M10/M11 figures to support scale and algorithm comparison.
- Use M12b figures as representative offline HotSpot validation evidence.
- Do not claim the proxy model is numerically equivalent to HotSpot; use it as a
  trend/ranking proxy.
- The HotSpot heatmap is block-level and simplified. It is not industrial
  thermal signoff.

## Scope

M13 intentionally produces only a few stable figures. Extra ad hoc plots should
not be committed unless they become part of the formal figure index.

## Current Status

M13 is complete. The current artifact set contains 5 PNG figures, one figure
index CSV, and one Markdown summary report:

```text
results/figures/m13/
results/tables/m13_figure_index.csv
results/reports/m13_visual_summary.md
```

The latest full regression check passed with 55 tests.

## Next Stage

M14 organizes the existing M10-M13 evidence into a paper-ready experiment
chapter draft. It does not add new algorithms by default. The output explains:

- benchmark scale and topology coverage;
- algorithm comparison results;
- thermal proxy and HotSpot validation relationship;
- limitations of the simplified block-level thermal model;
- which figures and tables should be used in the final thesis/paper.

See `docs/model/M14_EXPERIMENT_CHAPTER_DRAFT.md`.
