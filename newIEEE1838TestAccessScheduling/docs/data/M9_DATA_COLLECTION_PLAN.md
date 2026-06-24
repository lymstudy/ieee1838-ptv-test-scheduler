# M9 Real-Data Collection Plan

## Purpose

M9 extends the already working 3D-stack flow to `2.5d_interposer` and
`5.5d_multi_tower` cases. This stage must not invent numbers and then describe
them as real data. Every numeric value used for a paper figure, table, or case
JSON must be traceable as one of:

- `public_measured_or_benchmark`: directly copied from a public benchmark,
  standard, paper table, or vendor document.
- `derived_from_public_data`: computed from public values with an explicit
  formula.
- `model_assumption`: required by the scheduler but not available from public
  data; must be labeled as an assumption and swept where possible.
- `project_generated_result`: produced by this repository by running an
  experiment script on an auditable input case.

Only the first two categories should be called "real data" in the paper.

## Collection Workflow

1. Collect source metadata before using any value.
2. Enter candidate values in `M9_DATA_PROVENANCE.md`.
3. Mark each value as real, derived, assumption, or generated result.
4. Build M9 case JSON files only from approved provenance rows.
5. For every assumption-heavy field, add a sensitivity sweep instead of making a
   single unsupported claim.
6. Run the existing M8 comparison script on each M9 case and record outputs as
   `project_generated_result`.

## Required M9 Data Groups

| Group | Needed fields | Acceptable real-data sources | If unavailable |
| --- | --- | --- | --- |
| Topology | topology type, die count, tower count, die size, x/y/z position | public 2.5D/3D benchmark, floorplan, product paper | use benchmark-derived synthetic topology and label as assumption |
| Test objects | core names, scan chains, chain lengths, pattern counts, test data volume | ITC'02 SoC test benchmarks or other open test benchmark | use benchmark totals only; do not claim per-core realism |
| IEEE 1838 access | PTAP/STAP/DWR/FPP existence and abstract roles | IEEE 1838 standard pages and IEEE 1838 papers | keep structural only; bit widths become assumptions |
| Interposer links | lane count, lane rate, link direction, route class | UCIe public specification/white paper | map to scheduler FPP-like resource as derived abstraction |
| 3D links | TSV/micro-bump existence, tested link endpoints | public 3D benchmark or paper | keep route count/capacity as assumption |
| Power | shift/capture/BIST/access power | benchmark power model, McPAT, vendor/paper data | label as modeling input and sweep |
| Thermal | floorplan regions, thermal boundary, hotspot model parameters | HotSpot examples, Open3DBench, public 3D-IC thermal benchmark | label RC proxy parameters as assumptions |
| Baseline outputs | makespan, peak power, peak temperature, utilization | repository scripts run on fixed input | generated result, not external real data |

## Minimum Deliverables

- `configs/cases/2_5d_interposer_m9_public.json`
- `configs/cases/5_5d_multi_tower_m9_public.json`
- `docs/data/M9_DATA_PROVENANCE.md`
- `results/tables/m9_scenario_comparison.csv`
- `results/reports/m9_scenario_expansion_report.md`

## Paper Wording Rule

Safe wording:

> The M9 scenarios are constructed from public benchmark data and explicitly
> stated modeling assumptions. The results are reproducible scheduler outputs,
> not measurements from a commercial chip.

Unsafe wording:

> The M9 cases are real industrial 2.5D/3D chips.

