# Benchmark-Derived Workload Statistics Schema

This schema defines a statistics-level input for generating scheduler workloads.
It is not an RTL netlist schema, and the current prototype does not parse
Verilog or gate-level netlists directly.

The intended flow is:

1. Collect benchmark statistics from synthesis reports, scan reports, VCD toggle
   summaries, ATPG summaries, or manual estimation.
2. Fill this YAML schema with per-die and interconnect statistics.
3. Use the benchmark workload adapter to generate abstract test tasks compatible
   with the Serial, Bandwidth-greedy, and PTV-aware schedulers.

## Top-Level Fields

- `benchmark_name`: Human-readable benchmark or design name.
- `die_count`: Number of dies in the 3D stack.
- `fpp_lanes`: Number of optional FPP lanes available in the abstract access model.
- `voltage_limit`: Maximum allowed IR drop in volts for the MVP evaluator.
- `thermal_limit`: Maximum allowed temperature in degrees Celsius.
- `max_concurrent_capture`: Maximum number of scan capture tasks allowed to run at
  the same time in the PTV-aware scheduler.
- `dummy_cycle_duration`: Idle time inserted by the PTV-aware scheduler when
  ready tasks cannot be launched without violating predicted physical limits.
- `simulation`: Test-clock and evaluator time-step settings.
- `dies`: Per-die benchmark statistics.
- `interconnects`: DWR EXTEST-style adjacent or cross-die interconnect statistics.
- `power_model`: Voltage and shared-PDN parameters used by the abstract evaluator.
- `thermal_model`: Simplified thermal parameters used by the abstract evaluator.

## Simulation

- `clock_hz`: Test clock frequency used to convert task cycles to seconds.
- `time_step_s`: Evaluator time step in seconds.

## Dies

Each entry under `dies` contains:

- `die_id`: Integer die identifier.
- `module_name`: Name of the module or benchmark partition assigned to this die.
- `flip_flop_count`: Number of flip-flops or scan cells represented on this die.
- `scan_chain_count`: Number of scan chains.
- `scan_chain_length`: Representative scan-chain length in cycles.
- `estimated_shift_power`: Estimated scan-shift power in watts.
- `estimated_capture_power`: Estimated scan-capture power in watts.
- `estimated_bist_power`: Estimated BIST power in watts.
- `estimated_instrument_power`: Estimated low-bandwidth instrument access power
  in watts.
- `bist_task_count`: Number of BIST tasks generated for this die.
- `instrument_task_count`: Number of instrument access tasks generated for this die.

Scan task duration is derived from `scan_chain_length` and `scan_chain_count`.
Capture task duration is derived from `scan_chain_length` and `scan_chain_count`.
BIST and instrument access durations are also derived from the scan statistics,
rather than being arbitrary hand-written durations.

## Interconnects

Each entry under `interconnects` contains:

- `src_die`: Source die id for an inter-die DWR EXTEST task.
- `dst_die`: Destination die id for an inter-die DWR EXTEST task.
- `dwr_length`: Abstract Die Wrapper Register or interconnect pattern length in bits.
- `estimated_extest_power`: Estimated DWR EXTEST power in watts.

DWR EXTEST task duration is derived from `dwr_length`.

## Power Model

- `vdd`: Nominal supply voltage in volts.
- `shared_resistance`: Simplified shared-PDN equivalent resistance in ohms.
- `power_scale`: Scalar applied to the estimated task power values.

This is a simplified MVP shared-PDN model, not a signoff-quality PDN model.

## Thermal Model

- `ambient_temperature`: Ambient temperature in degrees Celsius.
- `initial_temperature`: Initial per-die temperature in degrees Celsius.
- `thermal_alpha`: Effective per-die thermal resistance in C/W for the simplified
  RC evaluator.
- `cooling_beta`: Effective thermal capacitance in J/C for the simplified RC
  evaluator.

The current thermal evaluator is a simplified per-die RC model with no
die-to-die thermal coupling.

## Research Scope

This schema is for benchmark-derived workload construction from statistics. It
does not claim validation against real RTL, real ATPG, HotSpot, 3D-ICE, RedHawk,
Voltus, Tessent SSN, or silicon measurements.
