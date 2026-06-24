# M9 Data Provenance Ledger

This ledger separates public data from model assumptions. Do not move a value
into an experiment JSON unless the `use_status` column allows it.

## Source Register

| source_id | Source | Public URL | Use in M9 | Notes |
| --- | --- | --- | --- | --- |
| IEEE1838_STD | IEEE Std 1838 standard page / public descriptions of IEEE 1838 test access architecture | https://standards.ieee.org/ieee/1838/6727/ | Structural terminology only | Use for PTAP/STAP/DWR/FPP terminology and architecture framing. Do not infer private implementation bit widths. |
| ITC02_SOC | ITC'02 SoC Test Benchmarks literature and benchmark naming convention | DOI: 10.1109/TEST.2002.1041802 | Candidate test-object source | Original paper is E.J. Marinissen, V. Iyengar, K. Chakrabarty, "A set of benchmarks for modular testing of SOCs," ITC 2002, pp. 519-528. Need original benchmark tables or package before extracting scan/pattern values. |
| ITC02_LIT_SECONDARY | DATE'05 multi-site testing paper using ITC'02 benchmarks | https://arxiv.org/abs/0710.4687 | Related-work source only | Contains literature comparison rows but not raw core-level scan-chain data. |
| UCIe_SPEC_PAGE | UCIe Consortium specifications page | https://www.uciexpress.org/specifications | Interposer/chiplet-link source | Use only published public numbers. Map to FPP-like scheduler resources as an abstraction, not as IEEE 1838 FPP itself. |
| UCIe_RESOURCES | UCIe Consortium resources page | https://www.uciexpress.org/ucie-resources | White-paper source index | Lists public UCIe white papers for versions 1.1, 2.0, and 3.0. |
| OPEN3DBENCH | Open3DBench: A Chiplet-based 3D IC Benchmark Suite | https://arxiv.org/abs/2503.12946 | Candidate 3D/topology/thermal source | Public benchmark-suite paper. Need benchmark repository or tables before extracting concrete floorplan values. |
| HOTSPOT | HotSpot compact thermal model and example inputs | https://lava.cs.virginia.edu/HotSpot/ | Candidate thermal-model source | Use for thermal-model methodology and possible example parameters if downloadable. |

## Approved Values

These values may be used, but only with the listed interpretation. They are not
complete M9 case files by themselves.

| field | value | unit | source_id | evidence | data_class | use_status |
| --- | ---: | --- | --- | --- | --- | --- |
| `fpp_lanes[*].bandwidth_bps` candidate | 32000000000 | bit/s/lane | UCIe_SPEC_PAGE | UCIe 3.0 page states that 64 GT/s doubles UCIe 2.0, which is 32 GT/s. Treat 32 GT/s as a UCIe-like package link rate, not IEEE 1838 FPP. | public_measured_or_benchmark | allowed_for_2_5d_link_sweep |
| `fpp_lanes[*].bandwidth_bps` candidate | 48000000000 | bit/s/lane | UCIe_SPEC_PAGE | UCIe 3.0 highlights support for 48 GT/s data rates. Treat as UCIe-like package link rate. | public_measured_or_benchmark | allowed_for_2_5d_link_sweep |
| `fpp_lanes[*].bandwidth_bps` candidate | 64000000000 | bit/s/lane | UCIe_SPEC_PAGE | UCIe 3.0 highlights support for 64 GT/s data rates. Treat as UCIe-like package link rate. | public_measured_or_benchmark | allowed_for_2_5d_link_sweep |
| `interconnects[*].route_resource` bump pitch candidate | 10-25 | um | UCIe_SPEC_PAGE | UCIe 2.0 page states UCIe-3D is optimized for hybrid bonding with bump pitch functional for bump pitches as big as 10-25 microns to as small as 1 micron or less. | public_measured_or_benchmark | allowed_for_notes_and_sweep |
| `interconnects[*].route_resource` HBT size candidate | 1 x 1 | um | OPEN3DBENCH | Open3DBench paper Section IV-A defines the HBT layer with dimensions of 1 um x 1 um. | public_measured_or_benchmark | allowed_for_3d_link_notes |
| `interconnects[*].route_resource` HBT pitch candidate | 2 | um | OPEN3DBENCH | Open3DBench paper Section IV-A defines HBT pitch of 2 um. | public_measured_or_benchmark | allowed_for_3d_link_notes |
| `scenario_count` Open3DBench test cases | 13 | cases | OPEN3DBENCH | Open3DBench paper states the framework provides 13 test cases. | public_measured_or_benchmark | allowed_for_related_work |
| `thermal_model` capability | 3D non-uniform thermal resistivity and heat capacity | text | HOTSPOT | HotSpot 6.0 page states improved 3D model supports layers with non-uniform thermal resistivity and heat capacity. | public_measured_or_benchmark | allowed_for_method_justification |
| `hbt_dimensions` | 1 x 1 | um | OPEN3DBENCH | Open3DBench paper Section IV-A and IV-F: HBT geometry is 1µm × 1µm with 1µm spacing. | public_measured_or_benchmark | allowed_for_3d_link_notes |
| `hbt_pitch` | 2 | um | OPEN3DBENCH | Open3DBench paper Section IV-A: HBT pitch is 2 µm. | public_measured_or_benchmark | allowed_for_3d_link_notes |
| `design_ariane133_2d_area` | 2.25 | mm² | OPEN3DBENCH | Open3DBench paper Table II: ariane133 2D post-route area. | public_measured_or_benchmark | allowed_for_topology_reference |
| `design_ariane133_mol_area` | 1.00 | mm² | OPEN3DBENCH | Open3DBench paper Table II: ariane133 MoL footprint. | public_measured_or_benchmark | allowed_for_topology_reference |
| `design_bp_multi_2d_area` | 1.21 | mm² | OPEN3DBENCH | Open3DBench paper Table II: bp_multi 2D post-route area. | public_measured_or_benchmark | allowed_for_topology_reference |
| `design_bp_multi_mol_area` | 0.64 | mm² | OPEN3DBENCH | Open3DBench paper Table II: bp_multi MoL footprint. | public_measured_or_benchmark | allowed_for_topology_reference |
| `design_swerv_wrapper_2d_area` | 12.96 | mm² | OPEN3DBENCH | Open3DBench paper Table II: swerv_wrapper 2D post-route area (largest design). | public_measured_or_benchmark | allowed_for_topology_reference |
| `design_swerv_wrapper_mol_area` | 6.25 | mm² | OPEN3DBENCH | Open3DBench paper Table II: swerv_wrapper MoL footprint. | public_measured_or_benchmark | allowed_for_topology_reference |
| `mol_area_reduction_percent` | 51.19 | % | OPEN3DBENCH | Open3DBench Table II: Average MoL area reduction vs 2D across 8 benchmarks. | public_measured_or_benchmark | allowed_for_related_work |
| `mol_tmax_increase_percent` | 12.73 | % | OPEN3DBENCH | Open3DBench Table II: Average Tmax increase MoL vs 2D (thermal-density trade-off). | public_measured_or_benchmark | allowed_for_thermal_reference |
| `ucie_standard_lanes` | 16 | lanes/cluster | UCIe_SPEC_PAGE | UCIe 1.0 white paper (ucie_1.1_white_paper.pdf): Standard package 16 data lanes. | public_measured_or_benchmark | allowed_for_2_5d_link_sweep |
| `ucie_advanced_lanes` | 64 | lanes/cluster | UCIe_SPEC_PAGE | UCIe 1.0 white paper: Advanced package 64 data lanes with spares. | public_measured_or_benchmark | allowed_for_2_5d_link_sweep |
| `ucie3d_lanes` | 80 | lanes/cluster | UCIe_SPEC_PAGE | UCIe 3.0 specification: UCIe-3D up to 80 lanes per cluster. | public_measured_or_benchmark | allowed_for_3d_link_sweep |
| `ucie_standard_reach` | 25 | mm | UCIe_SPEC_PAGE | UCIe 1.0 white paper: Standard package channel reach ≤ 25 mm. | public_measured_or_benchmark | allowed_for_2_5d_link_notes |
| `ucie_advanced_reach` | 2 | mm | UCIe_SPEC_PAGE | UCIe 1.0 white paper: Advanced package channel reach ≤ 2 mm. | public_measured_or_benchmark | allowed_for_2_5d_link_notes |
| `ucie3d_bump_pitch_range` | 1–9 | µm | UCIe_SPEC_PAGE | UCIe 2.0/3.0 white papers: UCIe-3D bump pitch from 9 µm down to 1 µm. | public_measured_or_benchmark | allowed_for_3d_link_sweep |
| `ucie3d_data_rate` | 4 | GT/s | UCIe_SPEC_PAGE | UCIe 3.0: UCIe-3D PHY data rate up to 4 GT/s per lane. | public_measured_or_benchmark | allowed_for_3d_link_sweep |
| `ucie3d_power_efficiency_9um` | <0.05 | pJ/bit | UCIe_SPEC_PAGE | UCIe 3.0: At 9 µm bump pitch. | public_measured_or_benchmark | allowed_for_3d_link_notes |
| `ucie3d_power_efficiency_1um` | >0.01 | pJ/bit | UCIe_SPEC_PAGE | UCIe 3.0: At 1 µm bump pitch. | public_measured_or_benchmark | allowed_for_3d_link_notes |
| `ucie3d_bandwidth_density_range` | 4000–300000 | GB/s/mm² | UCIe_SPEC_PAGE | UCIe 3.0: ~4 TB/s/mm² at 9 µm to ~300 TB/s/mm² at 1 µm. | public_measured_or_benchmark | allowed_for_3d_link_sweep |
| `ucie2_dfx_architecture` | Hub-Spoke model with DMH/DMS | text | UCIe_SPEC_PAGE | UCIe 2.0 white paper (ucie_3d_packaging_v2.pdf): UDA with Management Fabric. | public_measured_or_benchmark | allowed_for_ieee1838_structural |
| `itc02_raw_benchmark_package` | All 12 .soc files with per-module scan chain lengths and pattern counts | .soc files | ITC02_SOC | Original itc02benchm.tar.gz (2002-11-04) extracted to docs/data/itc02_benchmarks/. Contains d695, p22810, p34392, p93791, and 8 other SOCs. | public_measured_or_benchmark | allowed_for_scheduler_input |
| `itc02_soc_summary_table` | 12 SOCs with module/I/O/SFF counts | table | ITC02_SOC | hitech-projects.com/itc02socbenchm/: Full benchmark SOC table. | public_measured_or_benchmark | allowed_for_related_work |
| `itc02_benchmark_format` | .soc file format with scan chains and pattern data | text | ITC02_SOC | hitech-projects.com/itc02socbenchm/format.html: Complete format description. | public_measured_or_benchmark | allowed_for_format_reference |
| `itc02_d695_per_core_data` | 11 modules with exact I/O, per-chain scan lengths, pattern counts | .soc file | ITC02_SOC | Original d695.soc: Modules 1-10 (Module 0 = SOC top), 6,384 total SFFs, 10 tests. | public_measured_or_benchmark | allowed_for_scheduler_input |
| `itc02_p22810_per_core_data` | 29 modules with exact I/O, per-chain scan lengths, pattern counts | .soc file | ITC02_SOC | Original p22810.soc: Modules 0-28, 24,723 total SFFs, 30 tests. Multi-level hierarchy. | public_measured_or_benchmark | allowed_for_scheduler_input |
| `itc02_p34392_per_core_data` | 20 modules with exact I/O, per-chain scan lengths, pattern counts | .soc file | ITC02_SOC | Original p34392.soc: Modules 0-19, 20,948 total SFFs, 21 tests. Multi-level hierarchy. | public_measured_or_benchmark | allowed_for_scheduler_input |
| `itc02_p93791_per_core_data` | 33 modules with exact I/O, per-chain scan lengths, pattern counts | .soc file | ITC02_SOC | Original p93791.soc: Modules 0-32, 89,973 total SFFs, 32 tests. Multi-level hierarchy. Largest benchmark. | public_measured_or_benchmark | allowed_for_scheduler_input |

Machine-readable collected values:

- `docs/data/m9_open3dbench_public_values.csv`
- `docs/data/m9_itc02_literature_values.csv`
- `docs/data/m9_ucie_public_values.csv`
- `docs/data/M9_COLLECTION_STATUS.md`
- `docs/data/M9_REAL_DATA_SUMMARY.md`

The ITC'02 CSV contains literature benchmark results only. It does not contain
raw scan-chain or pattern-count data, so it must not be used to populate
`test_objects[*].scan` without an additional derivation step.

## Candidate Values To Extract

| target field | source_id | What to extract | Why it matters | Status |
| --- | --- | --- | --- | --- |
| `test_objects[*].scan.pattern_count` | ITC02_SOC | Pattern counts or test-data volumes for d695, p22810, p34392, p93791 | Scheduler makespan depends directly on scan payload | Partial: summary-level pattern count ranges available; raw per-core .soc files not found |
| `test_objects[*].scan.max_chain_length_bits` | ITC02_SOC | Scan-chain lengths or equivalent test-data parameters | Needed to avoid invented scan volume | Partial: per-SOC SFF totals and per-core d695 scan chain data available from literature |
| `test_objects[*].area_mm2` | OPEN3DBENCH | Die/block area or floorplan dimensions | Thermal risk uses power density | Collected: 13 designs with area, power, Tmax metrics from Table II/III |
| `dies[*].size_um` | OPEN3DBENCH | Die dimensions and positions | Needed for scenario diagrams and thermal adjacency | Collected: MoL footprint sizes (e.g., ariane133 1.00 mm², bp_multi 0.64 mm², swerv 6.25 mm²) |
| `ieee1838_access.*` structural fields | IEEE1838_STD | PTAP/STAP/DWR/FPP roles and access hierarchy | Needed for IEEE 1838-compatible modeling language | Structural use allowed |
| `fpp_lanes[*].bandwidth_bps` | UCIe_SPEC_PAGE | Public lane rate or aggregate bandwidth | Used as an interposer/FPP-like transfer capacity in 2.5D case | Confirmed: 32/48/64 GT/s for Standard/Advanced; 4 GT/s for UCIe-3D |
| `interconnects[*].link_type` | UCIe_SPEC_PAGE / OPEN3DBENCH | Interposer, die-to-die, TSV, or micro-bump link classes | Distinguishes 2.5D, 3D, and multi-tower bottlenecks | Confirmed: Standard 2D, Advanced 2.5D, UCIe-3D classes with detailed specs |
| `thermal_model` and `thermal_adjacency` | HOTSPOT / OPEN3DBENCH | Thermal boundary, floorplan adjacency, RC-like parameters if public | Needed for M7 proxy evaluation | Collected: Open3DBench uses HotSpot 7.0 with 10×10 grid; MoL thermal penalty ~12.7% |

## Assumption-Only Fields

These fields are unlikely to be public for a complete IEEE 1838-compatible
industrial package. If used, they must be labeled `model_assumption` and swept.

| Field | Why not safe as real data | Required treatment |
| --- | --- | --- |
| `ptap.control_bits_per_access` | Implementation-specific IEEE 1838 controller detail | Assumption + sweep |
| `staps[*].select_bits` | Implementation-specific hierarchy/control encoding | Assumption + sweep |
| `three_dcrs[*].bit_length` | Depends on private register design | Assumption + sweep |
| `dwr_segments[*].bit_length` | Depends on die wrapper implementation | Use public benchmark if available; otherwise assumption |
| `power.shift_power_w`, `capture_power_w`, `bist_power_w` | Workload and implementation dependent | Public power model or assumption + sweep |
| `pdn.self_resistance_ohm`, `shared_resistance_ohm` | Package/PDN implementation dependent | Assumption + sensitivity |
| `thermal.cooling_factor` | Simplified proxy parameter, not a physical measurement | Assumption + sensitivity |

## Immediate Next Actions

1. Keep `docs/data/itc02_benchmarks/` as the stable project-local mirror of the
   original ITC'02 `.soc` files found under `D:/studydoc/master/research/ict02/`.
2. Use `experiments/generate_m9_cases.py` to regenerate M9 JSON inputs whenever
   the ITC'02 mapping policy changes.
3. Add sensitivity sweeps for assumption-only fields: IEEE 1838 bit widths, DWR
   lengths, per-phase power, and thermal RC coefficients.
4. Add page/table references for UCIe and Open3DBench values used in captions or
   paper text, even when the scheduler JSON only stores the derived abstraction.
5. Treat `results/tables/m9_scenario_comparison.csv` as generated output, not a
   primary data source.
