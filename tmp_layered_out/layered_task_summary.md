# Layered Task Expansion Summary

This B2 demo expands high-level TestIntent objects into ExecutionPhase sequences.
It is not a complete IEEE 1838 behavior implementation and is not connected to the A0 scheduler.

## Key Semantics

- BIST is split into access, trigger, local run, re-access, and readback.
- LOCAL_BIST_RUN does not occupy PTAP, so future schedulers can overlap it with other die access phases.
- Scan is split into config, FPP shift-in, capture, FPP shift-out, and optional readback.
- DWR EXTEST is split into wrapper config, DWR shift-in, capture, and shift-out.
- Instrument access can later be expanded to SIB hierarchical or daisy-chain network timing.

## Layered Tasks

| layered_task_id | intent_type | phase_count | total_estimated_time_s |
| --- | --- | ---: | ---: |
| layered_scan_die3 | internal_scan | 6 | 1.0272e-05 |
| layered_bist_die2 | bist | 5 | 0.0025032 |
| layered_dwr_extest_die1_die2 | dwr_extest | 5 | 3.22e-05 |
| layered_instrument_die0 | instrument_access | 3 | 3.52e-06 |
