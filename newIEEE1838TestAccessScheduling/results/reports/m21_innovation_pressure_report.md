# M21 Innovation Pressure Suite Report

M21 replaces the weak ordinary-sweep evidence with an ITC'02-derived pressure suite.

- Successful detail rows: 54
- Pressure cases: 12
- Best-joint average gain vs fixed-fastest: 27.06%
- Best-joint minimum gain vs fixed-fastest: 10.00%

## Claim Support

| claim | status | evidence | recommended wording | gap |
| --- | --- | --- | --- | --- |
| test_access_recipe_model | supported | 12 pressure cases, avg candidate recipes=147.5 | Test Access Recipe can express serial, FPP, BIST, hybrid and interconnect access choices as schedulable alternatives. | Still a research model, not automatic DFT extraction from industrial design databases. |
| path_schedule_joint_optimization | supported | cases=12, avg_gain=27.06%, min_gain=10.00%, max_gain=46.67% | Under shared-resource pressure, every task is still TAP-enabled first; joint selection mixes BIST local execution and FPP data-transfer paths under explicit test-session constraints. | Do not claim this gain on ordinary M10 sweep; it is a pressure-suite result. |
| unified_2_5d_3d_5_5d_model | supported | topologies=3, avg_gain_spread=18.64%, group_counts=[2.0, 1.0, 2.75] | The unified model can encode topology-dependent resource bottlenecks, not just rename the same workload. | Topology pressure parameters remain modeling assumptions and must be stated as such. |
| thermal_aware_validation | partial | avg_temperature_spread_by_topology=[4.419, 11.567, 11.694] C | Thermal proxy now produces visible stress differentiation and can be used for risk analysis; HotSpot remains offline validation. | Still not a closed HotSpot-in-the-loop optimizer. |
| cpsat_alns_hybrid | partial | m5_rows=6, m5_not_worse_than_m4=6; ALNS not promoted in M21 | CP-SAT is a useful exact/feasible refinement backend on small and medium pressure cases; ALNS remains an extension prototype. | ALNS still needs a stronger implementation before becoming a core contribution. |

## Topology Pressure Summary

| topology | cases | avg gain | gain range | avg BIST groups | avg temp spread |
| --- | ---: | ---: | --- | ---: | ---: |
| 2_5d_interposer | 4 | 19.27% | 10.00% - 25.02% | 2.00 | 4.419 C |
| 3d_stack | 4 | 37.91% | 30.00% - 46.67% | 1.00 | 11.567 C |
| 5_5d_multi_tower | 4 | 24.00% | 12.52% - 33.33% | 2.75 | 11.694 C |

## Interpretation

- M21 is not a new industrial dataset; it is an ITC'02-derived controlled pressure suite.
- It is designed to expose the mechanism that ordinary M10 sweep hides: fixed fastest-path selection can create shared-resource serialization.
- FPP is modeled as a post-TAP data-transfer channel, not as an independent task launcher.
- Scan/FPP/capture/BIST execution phases use exclusive test-session resources; non-parallelizable work is not freely overlapped.
- Thermal numbers are more differentiated than M10/M12 nominal proxy values, but they remain proxy estimates.
- ALNS is intentionally not upgraded here; CP-SAT is treated as the reliable refinement backend.
