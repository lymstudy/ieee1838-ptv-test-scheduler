# FPP in IEEE 1838-2019

## Status

FPP (Flexible Parallel Port) is an **OPTIONAL but standard-defined** component of
IEEE 1838-2019. It is defined at multiple points in the standard:

- **Clause 5.5.3**: "Flexible parallel port configuration register" -- "Another
  expansion of the IEEE 1149.1 two-dimensional architecture is the addition of a
  Flexible Parallel Port and associated Flexible Parallel Port configuration elements"
- **Clause 6.5**: "Parallel access to the DWR" -- "IEEE Std 1838 provides for an
  optional parallel wrapper access mechanism called the Flexible Parallel Port (FPP)"
- **Clause 7** (pages 57-66): Full chapter titled "Flexible parallel port" with
  complete specification

FPP uses independent physical lanes, configured via TAP, and can operate
simultaneously with serial TAP activity.

## How FPP is Used in Our Model

- FPP is modeled as configurable multi-lane parallel channels between dies, following
  the IEEE 1838 Clause 7 specification.
- Each FPP recipe (type F and type H) begins with **standard IEEE 1838 serial
  configuration** (PTAP/STAP/3DCR access), then switches to FPP for bulk data transfer.
  This matches the standard: FPP is configured via TAP and serves as a data-transport
  accelerator.
- FPP lanes consume capacity resources that the scheduler must respect; they are
  NOT zero-cost or "free bandwidth."
- FPP does NOT bypass TAP control -- the TAP is still used to configure and
  release FPP paths, per the standard.
- The `ieee1838_access` JSON key in input files includes `fpp_channels` and
  `fpp_lanes` for describing the FPP channel and lane topology.

## Which Recipes Use FPP

| Recipe Type | Uses FPP? | Notes |
| ----------- | --------- | ----- |
| S           | No        | Pure serial PTAP/STAP/DWR access (standard IEEE 1838). |
| F           | Yes (IEEE 1838 Clause 7, optional) | Serial configuration + FPP parallel shift-in/shift-out. |
| B           | No        | Serial BIST configuration/readback; local execution does not use FPP or serial path. |
| H           | Yes (IEEE 1838 Clause 7, optional) | Serial configuration + FPP bulk transfer + short serial status/signature readback. |
| I           | No        | DWR EXTEST-style interconnect test via serial access (standard IEEE 1838). |

## Why FPP Matters for Scheduling

1. **Addresses the serial bottleneck**: IEEE 1838's single-external-PTAP serial
   access is the dominant bottleneck for test time in deep 3D stacks. FPP (IEEE 1838
   Clause 7) provides a standard-defined mechanism to add parallel data lanes that
   accelerate test data transfer without altering the TAP control model.

2. **Optional**: The scheduling framework works with or without FPP. When FPP is
   disabled (lane count = 0), the model degrades to pure serial IEEE 1838 access.
   FPP is an optional acceleration mechanism whose benefit is empirically quantified.

3. **Standard-defined**: FPP is not a proprietary extension. It is fully specified
   in IEEE 1838-2019 Clause 7. Our model implements the standard's FPP concept.

## Key Distinctions

- IEEE 1838-2019 defines: PTAP, STAP, 3DCR, DWR, serial TAP control, AND FPP
  (Flexible Parallel Port, Clause 7, optional).
- We do NOT modify or redefine any IEEE 1838-2019 standard component.
- FPP in our model represents the **scheduling abstraction** of the standard-defined
  parallel port -- it models lane counts, bandwidth, and channel assignment as
  scheduling resources.
