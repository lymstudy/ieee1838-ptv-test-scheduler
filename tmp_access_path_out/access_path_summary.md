# Access Path Summary

This B1 demo uses an abstract IEEE 1838-compatible access-path estimator.
It is not a bit-accurate implementation of the IEEE 1838 standard.

## Observations

- Deeper die access overhead increases because more STAP/3DCR path configuration bits are required.
- DWR access adds wrapper configuration, shift, and readback overhead.
- FPP data path reduces bulk data transfer time but still requires PTAP/STAP/FPP configuration.

## Generated Paths

| path_id | target_die | path_dies | estimated_access_time_s | operations |
| --- | ---: | --- | ---: | ---: |
| basic_die0 | 0 | 0 | 3.2e-07 | 2 |
| basic_die1 | 1 | 0->1 | 5.6e-07 | 3 |
| basic_die2 | 2 | 0->1->2 | 8e-07 | 3 |
| basic_die3 | 3 | 0->1->2->3 | 1.04e-06 | 3 |
| dwr_die3_512b | 3 | 0->1->2->3 | 1.224e-05 | 6 |
| fpp_die3_8192b_2lanes | 3 | 0->1->2->3 | 5.456e-06 | 5 |

## Basic Path Depth Check

- die0 estimated access time: 3.2e-07 s
- die3 estimated access time: 1.04e-06 s
