# M9 Collection Status

## Completed Evidence Files

| File | Purpose | Status |
| --- | --- | --- |
| `docs/data/open3dbench_2503.12946.pdf` | Local evidence for Open3DBench topology, power, thermal, and HBT values. | Downloaded |
| `docs/data/itc02_aco_literature_0710.4687.pdf` | Local evidence for ITC'02-related literature comparison values. | Downloaded |
| `docs/data/ucie_specifications_page.html` | Local evidence for UCIe 2.0/3.0 public specification-page values. | Downloaded |
| `docs/data/ucie_1.1_white_paper.pdf` | UCIe 1.0/1.1 white paper by Debendra Das Sharma (2022). | Downloaded |
| `docs/data/ucie_2.0_manageability.pdf` | UCIe 1.1 enhancements: automotive, streaming, cost optimization, compliance. | Downloaded |
| `docs/data/ucie_3d_packaging_v2.pdf` | UCIe 2.0 full white paper: DFx/UDA manageability architecture + UCIe-3D specs. | Downloaded |
| `docs/data/itc02_benchmarks/` | **12 original ITC'02 .soc files** with per-module scan chains and pattern counts. | **FOUND (local)** |
| `docs/data/m9_open3dbench_public_values.csv` | Machine-readable Open3DBench values (expanded with design-level PPA data). | Updated |
| `docs/data/m9_ucie_public_values.csv` | Machine-readable UCIe values (expanded with confirmed white-paper data). | Updated |
| `docs/data/m9_itc02_literature_values.csv` | Machine-readable ITC'02 literature comparison values. | No change |
| `docs/data/M9_REAL_DATA_SUMMARY.md` | Human-readable summary of usable real data and current blockers. | Updated |
| `docs/data/M9_DATA_PROVENANCE.md` | Master provenance ledger with approved values. | Updated |
| `docs/data/M9_ITC02_SEARCH_LOG.md` | ITC'02 search log — **updated with successful local find**. | Updated |
| --- | --- | --- |
| `docs/data/open3dbench_2503.12946.pdf` | Local evidence for Open3DBench topology, power, thermal, and HBT values. | Downloaded |
| `docs/data/itc02_aco_literature_0710.4687.pdf` | Local evidence for ITC'02-related literature comparison values. | Downloaded |
| `docs/data/ucie_specifications_page.html` | Local evidence for UCIe 2.0/3.0 public specification-page values. | Downloaded |
| `docs/data/ucie_1.1_white_paper.pdf` | UCIe 1.0/1.1 white paper by Debendra Das Sharma (2022). | Downloaded |
| `docs/data/ucie_2.0_manageability.pdf` | UCIe 1.1 enhancements: automotive, streaming, cost optimization, compliance. | Downloaded |
| `docs/data/ucie_3d_packaging_v2.pdf` | UCIe 2.0 full white paper: DFx/UDA manageability architecture + UCIe-3D specs. | Downloaded |
| `docs/data/m9_open3dbench_public_values.csv` | Machine-readable Open3DBench values (expanded with design-level PPA data). | Updated |
| `docs/data/m9_ucie_public_values.csv` | Machine-readable UCIe values (expanded with confirmed white-paper data). | Updated |
| `docs/data/m9_itc02_literature_values.csv` | Machine-readable ITC'02 literature values. | No change |
| `docs/data/M9_REAL_DATA_SUMMARY.md` | Human-readable summary of usable real data and current blockers. | Needs update |
| `docs/data/M9_DATA_PROVENANCE.md` | Master provenance ledger with approved values. | Updated |

## Usable Now (Expanded)

### UCIe — Interconnect Specifications
- **Standard Package (2D)**: 16 lanes/cluster, 4–32 GT/s, 100–130 µm bump pitch, ≤25 mm reach
- **Advanced Package (2.5D)**: 64 lanes/cluster + spares, 4–32 GT/s, 25–55 µm bump pitch, ≤2 mm reach
- **UCIe-3D**: Up to 80 lanes/cluster, up to 4 GT/s, 1–9 µm bump pitch, full-area connection (no shoreline PHY)
- **UCIe 1.1**: Added 8/10/16-column arrangements for Advanced Package cost optimization; x32 native width (~40% area savings)
- **UCIe 2.0**: Added DFx Architecture (UDA) with Hub-Spoke model (DMH/DMS) for test/debug/telemetry; dedicated UCIe-S ports at 800 Mb/s (sideband) or 256 Gb/s per x8 at 32 GT/s (mainband)
- **UCIe 3.0**: 48 GT/s and 64 GT/s data rates; 64 GT/s doubles UCIe 2.0 bandwidth
- **Bandwidth density**: Standard/Advanced ~1300+ GB/s/mm (at 45 µm); UCIe-3D: 4,000–300,000 GB/s/mm²
- **Power efficiency**: ~0.5 pJ/b (Standard), ~0.25 pJ/b (Advanced), <0.05 pJ/b (3D at 9 µm), >0.01 pJ/b (3D at 1 µm)

### Open3DBench — Design-Level Public Data
- **13 test cases** across MoL (8 designs) and LoL (5+8 macro-free) flows
- **Design metrics available** (area, power, Tmax, HBT count) for: ariane133, ariane136, bp_be, bp_fe, bp_multi, swerv_wrapper, bp_quad, black_parrot (+ LoL-only: aes, dynamic_node, ibex, jpeg, swerv)
- **Key reference values**:
  - ariane133: 2D area 2.25 mm², MoL area 1.00 mm², power ~0.37 W, Tmax ~55–59°C, HBTs ~4934
  - bp_multi: 2D area 1.21 mm², MoL area 0.64 mm², power ~1.01 W, Tmax ~79–106°C, HBTs ~7151
  - swerv_wrapper: 2D area 12.96 mm², MoL area 6.25 mm², power ~1.78 W, Tmax ~65°C
- **Aggregate results**: MoL vs 2D: 51.19% area reduction, 20.06% HPWL reduction, 2.35% power reduction, **12.73% Tmax increase** (thermal-density trade-off)
- **HBT geometry**: 1 µm × 1 µm, 2 µm pitch, 1 µm spacing (NanGate45 3D PDK)
- **Thermal methodology**: HotSpot 7.0 with 10×10 grid per die
- **GitHub org**: lamda-bbo (Open3DBench repositories)

### ITC'02 — Benchmark Summary Data
- **Full benchmark table** obtained from hitech-projects.com: 12 SOCs with module/I/O/SFF counts
- **.soc format** fully documented (format.html captured and archived)
- **d695 per-core data** available from secondary literature (thesis): 10 modules, scan chains per module, pattern counts, I/O counts
- **p22810 per-core data**: 29 modules, 30 tests, per-core test lengths available from literature
- **Literature comparison ranges** for test lengths and ATE channels for d695, p22810, p34392, p93791 from DATE'05 paper

## Not Usable As Raw Scheduler Input Yet

- **IEEE 1838 implementation-specific bit widths** (PTAP control bits, STAP select bits, 3DCR registers): Still model assumptions.
- **Per-phase scan shift/capture/BIST power**: Open3DBench provides only design-level total power, not per-operation power breakdown.
- **Complete industrial 2.5D or multi-tower IEEE 1838 test-access configuration**: No public source found.

## RESOLVED: ITC'02 Raw Data

The original ITC'02 .soc benchmark package has been **found locally** at the user's
`d:/studydoc/master/research/ict02/` directory and extracted to
`docs/data/itc02_benchmarks/`. All 12 SOCs with complete per-module scan chain
lengths, pattern counts, and I/O counts are now available as
`public_measured_or_benchmark` data. This was the main blocking gap — now resolved.

## Current Decision (Updated)

Given the data collected, the recommended path:

1. **Topology/Link parameters**: Use real UCIe/Open3DBench data (confirmed public_measured_or_benchmark).
2. **Design-level references**: Use Open3DBench Table II/III values for area, power, thermal as public benchmark references.
3. **Test parameters**: Use ITC'02 summary data and secondary literature per-core data as derived_from_public_data with explicit citations. Raw per-core .soc file scan parameters remain model_assumption where not covered by secondary sources.
4. **IEEE 1838 structural fields**: Keep structural (from standard), bit widths as model_assumption + sweep.
5. **M9 case JSONs**: Can now be built as "public benchmark-derived + explicit assumptions" with proper labeling.

## Evidence File Inventory

```
docs/data/
├── open3dbench_2503.12946.pdf        (4.7 MB) — Open3DBench full paper
├── itc02_aco_literature_0710.4687.pdf (330 KB) — DATE'05 ITC'02 literature paper
├── ucie_1.1_white_paper.pdf          (1.1 MB) — UCIe 1.0/1.1 white paper
├── ucie_2.0_manageability.pdf        (0.5 MB) — UCIe 1.1 spec enhancements
├── ucie_3d_packaging_v2.pdf          (1.8 MB) — UCIe 2.0: DFx + UCIe-3D
├── ucie_specifications_page.html     (HTML) — UCIe 3.0 spec page snapshot
├── m9_open3dbench_public_values.csv  — 27 rows of extracted values
├── m9_ucie_public_values.csv         — 34 rows of extracted values
├── m9_itc02_literature_values.csv    — 13 rows of literature comparison values
├── M9_DATA_PROVENANCE.md             — Master provenance ledger
├── M9_DATA_COLLECTION_PLAN.md        — Collection plan (original)
├── M9_REAL_DATA_SUMMARY.md           — Human-readable summary
├── M9_ITC02_SEARCH_LOG.md            — ITC'02 raw file search log
└── M9_COLLECTION_STATUS.md           — This file
```
