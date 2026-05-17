# Access-Time-Aware Phase Schedule

This B3.1 demo schedules ExecutionPhase objects produced by the B2 layered expander.
It is a first phase-level scheduler prototype, not predictive PTV scheduling and not a full IEEE 1838 implementation.

- total_time_s: 0.0025032
- scheduled_phase_count: 19

| start_s | end_s | phase_id | phase_type | resources |
| ---: | ---: | --- | --- | --- |
| 0 | 8e-07 | bist_die2:config | CONFIG_ACCESS_PATH | PTAP |
| 8e-07 | 1.12e-06 | bist_die2:trigger_bist | TRIGGER_BIST | PTAP |
| 1.12e-06 | 0.00250112 | bist_die2:local_bist_run | LOCAL_BIST_RUN | LOCAL |
| 1.12e-06 | 2.16e-06 | scan_die3:config | CONFIG_ACCESS_PATH | PTAP |
| 2.16e-06 | 2.48e-06 | scan_die3:config_scan_fpp | CONFIG_SCAN_FPP | PTAP,FPP[2] |
| 2.48e-06 | 6.576e-06 | scan_die3:fpp_shift_in | FPP_SHIFT_IN | FPP[2] |
| 2.48e-06 | 3.28e-06 | dwr_extest_die1_die2:config | CONFIG_ACCESS_PATH | PTAP |
| 3.28e-06 | 3.92e-06 | dwr_extest_die1_die2:config_dwr_mode | CONFIG_DWR_MODE | PTAP,DWR:dwr_die1_die2 |
| 3.92e-06 | 4.24e-06 | instrument_die0:config | CONFIG_ACCESS_PATH | PTAP |
| 4.24e-06 | 6.8e-06 | instrument_die0:access_instrument | ACCESS_INSTRUMENT | PTAP |
| 6.576e-06 | 6.656e-06 | scan_die3:scan_capture | SCAN_CAPTURE | CAPTURE |
| 6.656e-06 | 1.0752e-05 | scan_die3:fpp_shift_out | FPP_SHIFT_OUT | FPP[2] |
| 6.8e-06 | 7.44e-06 | instrument_die0:readback | READBACK | PTAP |
| 1.0752e-05 | 1.1392e-05 | scan_die3:readback | READBACK | PTAP |
| 1.1392e-05 | 3.1872e-05 | dwr_extest_die1_die2:dwr_shift_in | DWR_SHIFT_IN | PTAP,DWR:dwr_die1_die2 |
| 3.1872e-05 | 3.1912e-05 | dwr_extest_die1_die2:dwr_capture | DWR_CAPTURE | DWR:dwr_die1_die2,CAPTURE |
| 3.1912e-05 | 4.2152e-05 | dwr_extest_die1_die2:dwr_shift_out | DWR_SHIFT_OUT | PTAP,DWR:dwr_die1_die2 |
| 0.00250112 | 0.00250192 | bist_die2:readback_access | CONFIG_ACCESS_PATH | PTAP |
| 0.00250192 | 0.0025032 | bist_die2:read_bist_result | READ_BIST_RESULT | PTAP |
