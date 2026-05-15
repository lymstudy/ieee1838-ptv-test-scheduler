# AGENTS.md

## Project Goal

This repository implements a Python simulation framework for power-, thermal-,
and voltage-aware test access scheduling for IEEE 1838-compliant 3D ICs.

The first milestone is a reproducible 4-die MVP experiment comparing:
1. Serial IEEE 1838 baseline
2. Bandwidth-greedy baseline
3. PTV-aware scheduler

## Scope

Do not implement real ATPG, real Tessent SSN, commercial EDA interfaces,
HotSpot, RedHawk, Voltus, or FPGA validation in the first milestone.

Use an abstract but physically reasonable model:
- IEEE 1838 access resources: PTAP, STAP, DWR segments, optional FPP lanes
- Test tasks: scan, BIST, DWR EXTEST, instrument access
- Thermal model: discrete RC-style temperature update
- Voltage model: equivalent PDN resistance and IR drop estimation

## Coding Rules

- Use Python 3.10+.
- Keep modules small and readable.
- Prefer dataclasses for model objects.
- Use YAML config files for experiment parameters.
- Do not hard-code experiment constants inside algorithm files.
- Add type hints where practical.
- Add docstrings for public classes and functions.

## Validation Rules

After each meaningful code change:
- Run unit tests with `pytest`
- Run the 4-die experiment:
  `python experiments/run_case_4die.py`
- Confirm that result CSV files and figures are generated under `results/`.

## Research Integrity Rules

- Do not invent paper citations.
- Do not claim IEEE 1838 contains SSN.
- Use "SSN-inspired" or "streaming-scan-inspired" only if needed.
- DWR means Die Wrapper Register, not Design for Test Wrapper.
- Do not claim zero hardware overhead. Use "no additional test access pins" only
  when appropriate.

## Project State Tracking Rules

This repository uses project state files as the single source of truth for
progress tracking.

The following files must be maintained:

- STATUS.md
- ROADMAP.md
- DECISIONS.md
- EXPERIMENT_LOG.md
- TODO.md

Rules:

- Every meaningful task must update STATUS.md.
- Every experiment run must append a record to EXPERIMENT_LOG.md.
- Any major modeling, terminology, or engineering decision must be recorded in
  DECISIONS.md.
- TODO.md must be updated after each task.
- ROADMAP.md must be updated if the milestone structure changes.
- Do not rely on chat history as the only memory of project progress.
- The repository files are the single source of truth.
- At the end of every task, report whether STATUS.md, TODO.md, and
  EXPERIMENT_LOG.md were updated.
- If a task changes research scope, report whether DECISIONS.md was updated.
- Do not implement features that contradict DECISIONS.md.

## Required Outputs for MVP

The 4-die experiment must generate:
- schedule table CSV
- Gantt chart
- temperature curve
- IR drop curve
- TAT comparison plot
- peak temperature comparison plot
- peak IR drop comparison plot

## Reporting Style

After completing a task, summarize:
- files changed
- tests run
- generated outputs
- known limitations
- next recommended task

## Planned Repository Layout

```text
ieee1838-ptv-test-scheduler/
|-- AGENTS.md
|-- README.md
|-- requirements.txt
|-- configs/
|   |-- case_4die.yaml
|   `-- default_params.yaml
|-- src/
|   |-- model/
|   |   |-- stack.py
|   |   |-- task.py
|   |   |-- access.py
|   |   |-- thermal.py
|   |   `-- voltage.py
|   |-- scheduler/
|   |   |-- serial.py
|   |   |-- greedy.py
|   |   `-- ptv_aware.py
|   |-- visualize/
|   |   |-- gantt.py
|   |   |-- curves.py
|   |   `-- comparison.py
|   `-- utils/
|-- experiments/
|   |-- run_case_4die.py
|   |-- sweep_fpp_lanes.py
|   |-- sweep_thermal_limit.py
|   `-- sweep_voltage_limit.py
|-- tests/
`-- results/
```

