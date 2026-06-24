# ITC'02 Original Benchmark Package Search Log

## Target

Find the original ITC'02 SoC benchmark package or files containing raw
core-level test parameters, such as scan-chain counts, test lengths, pattern
counts, wrapper/TAM data, or per-core test data for benchmarks including:

- `d695`
- `p22810`
- `p34392`
- `p93791`

## Confirmed Primary Citation

Crossref query confirmed the original benchmark paper:

```text
E.J. Marinissen, V. Iyengar, K. Chakrabarty,
"A set of benchmarks for modular testing of SOCs,"
Proceedings IEEE International Test Conference (ITC), pp. 519-528, 2002.
DOI: 10.1109/TEST.2002.1041802
```

This confirms the source identity but does not provide the raw package.

## Checked Sources

| Source/query | Result | Status |
| --- | --- | --- |
| General web search for exact title | Found citations, no raw package | unresolved |
| General web search for `d695 p22810 p34392 p93791` | Found secondary literature references, no raw package | unresolved |
| GitHub web/code search | No accessible raw package found; GitHub code API requires authentication | unresolved |
| Crossref metadata | Confirmed DOI and page range | confirmed metadata |
| IEEE DOI / IEEE Xplore page | Access-controlled/JS page, no direct PDF obtained | unresolved |
| Historical Philips path `extra.research.philips.com/itc02socbenchm/` | Current site inaccessible; Wayback landing page exists but CDX did not list files during this attempt | unresolved |
| Internet Archive availability API for likely Philips URLs | No snapshots for `/itc02socbenchm/`, `/index.html`, `/itc02socbenchm.html`, `/itc02socbenchm.zip`, `/benchmarks.zip`, or `/d695.zip` | unresolved |
| Author/institution domain searches: Duke, NXP, imec | No raw package found | unresolved |
| Searches for raw terms: `scan chain`, `test length`, `wrapper TAM` with benchmark names | No core-level raw parameter table found | unresolved |
| DATE'05 arXiv paper `0710.4687` | Contains ITC'02 benchmark comparison table only | secondary evidence only |

## Important Constraint

The DATE'05 paper and other secondary literature must not be used as raw
ITC'02 benchmark input. They can support related-work discussion only.

## Next Search Targets

- Author pages for Erik Jan Marinissen, Vikram Iyengar, and Krishnendu
  Chakrabarty.
- Mirrors of the ITC 2002 SOC benchmarking initiative.
- IEEE supplementary material or old Philips/NXP research pages.
- University course repositories that may have mirrored the original `.txt`,
  `.dat`, `.xls`, `.zip`, or `.tgz` files.
- If institutional access is available, obtain the IEEE PDF for
  DOI `10.1109/TEST.2002.1041802` and inspect whether it contains a URL,
  appendix, or enough tables to reconstruct raw benchmark inputs.

## Current Assessment

As of this search pass, the original ITC'02 raw benchmark package has not been
found in publicly reachable web, GitHub, author-domain, or Internet Archive
queries. The benchmark identity and DOI are confirmed, but the raw package is
still missing.

## 2026-06-24: FOUND — Local copy located

The raw benchmark package was found locally at:
`d:/studydoc/master/research/ict02/itc02benchm.tar.gz`

### File Details
- **Format**: gzip compressed data, original tar name `itc02benchm.tar`
- **Date**: Last modified Mon Nov 4 16:52:35 2002
- **Size**: 4,813 bytes (matches the 4.8 KB reported on hitech-projects.com)
- **Contents**: 12 .soc files + README.txt

### Extracted Files (copied to `docs/data/itc02_benchmarks/`)

| File | Size (bytes) | SOC | Modules | Tests | Σ SFFs |
| --- | ---: | --- | ---: | ---: | ---: |
| d695.soc | 1,881 | d695 | 11 | 10 | 6,384 |
| p22810.soc | 4,698 | p22810 | 29 | 30 | 24,723 |
| p34392.soc | 3,028 | p34392 | 20 | 21 | 20,948 |
| p93791.soc | 6,415 | p93791 | 33 | 32 | 89,973 |
| u226.soc | 1,401 | u226 | 10 | 9 | 1,040 |
| d281.soc | 1,636 | d281 | 9 | 15 | 882 |
| h953.soc | 1,427 | h953 | 9 | 8 | 4,657 |
| g1023.soc | 2,126 | g1023 | 15 | 14 | 1,546 |
| f2126.soc | 781 | f2126 | 5 | 4 | 13,996 |
| q12710.soc | 740 | q12710 | 5 | 4 | 12,991 |
| t512505.soc | 4,634 | t512505 | 32 | 31 | 68,051 |
| a586710.soc | 1,183 | a586710 | 8 | 7 | 37,656 |

### Data Quality
- All files contain per-module: input/output/bidirectional counts, exact scan chain lengths (per chain), pattern counts
- All files use `TamUse 1` (TAM used) and `ScanUse 1` for all test records
- No Power or XY data (Options Power 0 XY 0 for all SOCs)
- This is the authentic ITC'02 benchmark package — every value is `public_measured_or_benchmark`

### Next Steps
- d695, p22810, p34392, p93791 .soc data can now be directly used as test-object input for M9 scheduler cases
- Scan chain lengths from these files constitute **real public benchmark data**, not model assumptions
