# M9 Real-Data Summary

## What Has Been Collected

### UCIe Official Data

Evidence files:
- `docs/data/ucie_1.1_white_paper.pdf` (UCIe 1.0/1.1 by Debendra Das Sharma)
- `docs/data/ucie_2.0_manageability.pdf` (UCIe 1.1 cost optimization + compliance)
- `docs/data/ucie_3d_packaging_v2.pdf` (UCIe 2.0: DFx/UDA + UCIe-3D)
- `docs/data/ucie_specifications_page.html` (UCIe 3.0 spec page snapshot)

Collected values:

**UCIe 1.0/1.1 (Standard & Advanced Package)**
- Standard Package (2D): 16 lanes/cluster, 4–32 GT/s, 100–130 µm bump pitch, ≤25 mm reach
- Advanced Package (2.5D): 64 lanes/cluster + spares, 4–32 GT/s, 25–55 µm bump pitch, ≤2 mm
- Bandwidth density: ~1300+ GB/s/mm at 45 µm bump pitch (~20× PCIe SERDES)
- Power efficiency: ~20× better than PCIe PHY (~10 pJ/b → ~0.5 pJ/b Standard, ~0.25 pJ/b Advanced)
- Sub-ns idle entry/exit latency (90+% power saving vs multi-µs SERDES)
- UCIe 1.1: 8/10/16-column arrangements; x32 native width for ~40% area savings

**UCIe 2.0 (Manageability & 3D)**
- DFx Architecture (UDA): Hub-Spoke model (DMH + DMS spokes) for test/debug/telemetry
- Management Transport Protocol with 8 virtual channels, credit-based flow control
- Dedicated UCIe-S ports: 800 Mb/s/dir (sideband, 4 bumps) or 256 Gb/s/dir per x8 (mainband, 32 GT/s)
- UCIe-3D: bump pitch 1–9 µm, up to 80 lanes/cluster, up to 4 GT/s
- UCIe-3D bandwidth density: 4,000–300,000 GB/s/mm²
- UCIe-3D power efficiency: <0.05 pJ/b (9 µm) to >0.01 pJ/b (1 µm)
- Full-area connection (no shoreline PHY limitation)

**UCIe 3.0 (Next-gen data rates)**
- 48 GT/s and 64 GT/s data rates (64 GT/s = 2× UCIe 2.0)

Allowed use:
- Use 32/48/64 GT/s as UCIe-like package link rates in 2.5D and multi-tower sweeps
- Use UCIe-3D 4 GT/s with 1–9 µm pitch as 3D interconnect reference
- Use UDA Hub-Spoke model as IEEE 1838-compatible DFx structural reference
- Do NOT call any UCIe link bandwidth "IEEE 1838 FPP bandwidth" (UCIe ≠ IEEE 1838 FPP)

### Open3DBench Public Data

Evidence file:
- `docs/data/open3dbench_2503.12946.pdf`

Collected values:

**Design Statistics (Table I & II)**
- 13 RTL designs sourced from OpenROAD-flow-scripts (ORFS), NanGate45 library
- 8 MoL designs: ariane133, ariane136, black_parrot, bp_be, bp_fe, bp_multi, swerv_wrapper, bp_quad
- 5 macro-free LoL designs: aes, dynamic_node, ibex, jpeg, swerv
- Design sizes range from ~15K cells (bp_quad) to ~1080K cells (swerv_wrapper)

**Post-Route PPA Metrics (Table II — MoL flow)**
| Design | 2D Area (mm²) | MoL Area (mm²) | 2D Power (W) | 2D Tmax (°C) | MoL Tmax (°C) |
| --- | ---: | ---: | ---: | ---: | ---: |
| ariane133 | 2.25 | 1.00 | 0.364 | 55.16 | 59.22 |
| ariane136 | 2.25 | 1.00 | 0.473 | 58.84 | 63.25 |
| bp_be | 0.56 | 0.30 | 0.152 | 51.65 | 59.25 |
| bp_fe | 0.48 | 0.24 | 0.298 | 78.38 | 79.25 |
| bp_multi | 1.21 | 0.64 | 1.095 | 79.05 | 102.39 |
| bp_quad | 1.10 | 0.56 | 0.243 | 52.77 | 61.87 |
| swerv_wrapper | 12.96 | 6.25 | 1.815 | 65.21 | 66.56 |

**Aggregate MoL vs 2D improvements:**
- Area: −51.19% | HPWL: −20.06% | Power: −2.35% | WNS: −42.09% | TNS: −61.13%
- **Thermal penalty: +12.73% Tmax increase**

**HBT / 3D Interconnect Data (Table III)**
- ariane133 HBT count: 4,934 terminals
- bp_multi HBT count: 7,151 terminals
- HBT geometry: 1 µm × 1 µm, 2 µm pitch, 1 µm spacing
- Uses HotSpot 7.0 with 10×10 grid per die for thermal simulation

Allowed use:
- Use design-level area/power/Tmax as public benchmark references for topology sizing
- Use HBT counts as 3D-net / inter-die link reference counts
- Use thermal penalty (+12.73%) as calibration for M7 thermal proxy
- Do NOT treat design-level power as scan-shift or capture power directly

### ITC'02 Literature Data

Evidence files:
- `docs/data/itc02_aco_literature_0710.4687.pdf`
- `docs/data/m9_itc02_literature_values.csv`
- hitech-projects.com/itc02socbenchm/ (HTML captured)

Collected values:

**Benchmark SOC Summary**
| SOC | Modules | Tests | Σ I/Os | Σ SFFs | Contributor |
| --- | ---: | ---: | ---: | ---: | --- |
| d695 | 11 | 10 | 1,845 | 6,384 | Duke University |
| p22810 | 29 | 30 | 4,283 | 24,723 | Philips Semiconductors |
| p34392 | 20 | 21 | 2,057 | 20,948 | Philips Semiconductors |
| p93791 | 33 | 32 | 6,943 | 89,973 | Philips Research |

**d695 per-core data (from secondary literature)**
| Core | Inputs | Outputs | ISCs | Total Chain Length | Patterns |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 32 | 32 | 0 | 0 | 12 |
| 2 | 207 | 108 | 0 | 0 | 73 |
| 3 | 34 | 1 | 1 | 32 | 75 |
| 4 | 36 | 39 | 1 | 211 | 105 |
| 5 | 38 | 304 | 32 | 1,426 | 110 |
| 6 | 62 | 152 | 16 | 638 | 234 |
| 7 | 77 | 150 | ~13 | 534 | 95 |
| 8 | 35 | 49 | 1 | 179 | 97 |
| 9 | 35 | 320 | 32 | 1,728 | 12 |
| 10 | 28 | 106 | ~25 | 1,636 | 68 |

**.soc File Format** is fully documented (from format.html).

Allowed use:
- Use benchmark names and summary statistics as related-work context
- Use d695 per-core data from secondary literature as derived_from_public_data
- Use .soc format spec to validate any reconstructed test parameter sets
- Do NOT claim raw .soc files were used as direct input without them being found

## Current Blocking Gap

The original ITC'02 benchmark `.soc` file package has not been found. The hitech-projects.com mirror returns HTML instead of the tar.gz file. Multiple search avenues (GitHub, Wayback Machine, author domains, academic repositories) have not yielded the raw files.

However, sufficient **derived data** exists to proceed:
- Full per-core d695 data from secondary literature
- Test length ranges for p22810, p34392, p93791 from literature
- Complete .soc file format specification for validation

## Honest Path Forward

**Recommended approach**: Build M9 JSONs as **"public benchmark-derived + explicit assumptions"**.

1. **Topology**: Use Open3DBench design sizes and UCIe bump-pitch ranges as real topology references
2. **Links**: Use UCIe 32/48/64 GT/s rates for 2.5D interposer; UCIe-3D 4 GT/s for 3D TSV/micro-bump
3. **Test parameters**: Use d695-derived per-core data (scan chains, patterns) as the test-object base for 2.5D and 5.5D scenario scaling
4. **Power**: Use Open3DBench design-level power as total-power envelope; derive per-operation power as assumption
5. **Thermal**: Use Open3DBench Tmax values and +12.73% thermal penalty as calibration targets
6. **IEEE 1838 fields**: Keep structural, label bit widths as model_assumption, include sensitivity sweeps
