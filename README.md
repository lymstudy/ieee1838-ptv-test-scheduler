# IEEE 1838 PTV Test Scheduler

This repository is a research prototype for power-, thermal-, and
voltage-aware test access scheduling for IEEE 1838-compliant 3D ICs.

The first milestone is a reproducible 4-die experiment comparing:

1. Serial IEEE 1838 baseline
2. Bandwidth-greedy baseline
3. PTV-aware scheduler

The current scaffold only provides configuration files, model dataclasses, a
minimal 4-die experiment loader, and unit tests. Scheduling algorithms and MVP
comparison plots are intentionally not implemented yet.

## Scope

The prototype uses abstract but physically reasonable models:

- IEEE 1838 access resources: PTAP, STAP, DWR segments, optional FPP lanes
- Test tasks: scan, BIST, DWR EXTEST, and instrument access
- Thermal model: discrete RC-style temperature update
- Voltage model: equivalent PDN resistance and IR drop estimation

This project does not implement real ATPG, Tessent SSN, commercial EDA tool
interfaces, HotSpot, RedHawk, Voltus, or FPGA validation.

## Quick Start

```powershell
python -m pip install -r requirements.txt
pytest
python experiments/run_case_4die.py
```

The scaffold experiment writes model sanity CSVs and SVG figures under
`results/case_4die/`.

## Research Integrity Notes

- DWR means Die Wrapper Register.
- IEEE 1838 is used as the die access architecture; this repository does not
  claim that IEEE 1838 includes SSN.
- When discussing scan streaming ideas, use "SSN-inspired" or
  "streaming-scan-inspired" only where appropriate.
- Do not claim zero hardware overhead. Use "no additional test access pins" only
  when that narrower statement is accurate.
