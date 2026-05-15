# IEEE 1838 PTV Test Scheduler

This repository is a research prototype for power-, thermal-, and voltage-aware test access scheduling for IEEE 1838-compatible 3D IC test access resources.

The current MVP compares three schedulers on a 4-die stack:

1. Serial IEEE 1838-style baseline
2. Bandwidth-greedy baseline
3. PTV-aware scheduler

The prototype includes configuration loading, abstract stack/task/access models, a unified schedule evaluator, a simplified thermal model, a simplified shared-PDN voltage model, clean and stress 4-die experiments, plots, and tests.

## Scope

The prototype uses abstract but physically reasonable models:

- IEEE 1838 access resources: PTAP, STAP, DWR segments, optional FPP lanes
- DWR means Die Wrapper Register
- Test tasks: scan, BIST, DWR EXTEST, and instrument access
- Thermal model: simplified per-die discrete RC-style temperature update
- Voltage model: simplified shared-PDN equivalent resistance IR-drop estimation

This project does not implement real ATPG, Tessent SSN, commercial EDA tool interfaces, HotSpot, 3D-ICE, RedHawk, Voltus, or FPGA validation.

## Current Results

Current MVP results are summarized in [RESULTS.md](RESULTS.md).

The key observation is that PTV-aware scheduling reduces physical constraint violations compared with bandwidth-greedy scheduling, while retaining much shorter TAT than purely serial scheduling.

## Quick Start

```powershell
python -m pip install -r requirements.txt
pytest
python experiments/run_case_4die.py
python experiments/run_case_4die_stress.py
```

Experiment outputs are written under:

- `results/case_4die/`
- `results/case_4die_stress/`

## Research Integrity Notes

- DWR means Die Wrapper Register.
- IEEE 1838 is used as the die access architecture context; this repository does not claim IEEE 1838 defines scheduling algorithms.
- This repository does not claim that IEEE 1838 includes SSN.
- When discussing scan streaming ideas, use "streaming-scan-inspired" only where appropriate.
- Do not claim zero hardware overhead. Use narrower statements only when accurate, such as "reuse IEEE 1838-compatible test access resources".
