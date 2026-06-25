# M12b HotSpot Remote Validation Report

- HotSpot executed: yes
- Total rows: 6
- Successful HotSpot rows: 6
- Non-success rows: 0

## Row Summary

| case | schedule | status | proxy_peak_c | hotspot_peak_c | hotspot_block | reason |
| --- | --- | --- | ---: | ---: | --- | --- |
| m10_small_d695_5_5d_multi_tower | thermal_min_risk | ok | 25.248649597020318 | 62.26000000000005 | thermal_die2 |  |
| m10_small_d695_5_5d_multi_tower | m4_greedy | ok | 25.09227646238526 | 60.79000000000002 | thermal_die0 |  |
| m10_medium_p22810_3d_stack | thermal_min_risk | ok | 25.566667719347862 | 62.879999999999995 | thermal_die3 |  |
| m10_medium_p22810_3d_stack | m4_greedy | ok | 25.117534898297777 | 60.610000000000014 | thermal_die5 |  |
| m10_medium_p22810_5_5d_multi_tower | thermal_min_risk | ok | 25.477302027376023 | 63.69 | thermal_die3 |  |
| m10_medium_p22810_5_5d_multi_tower | m4_greedy | ok | 25.11748975922204 | 60.84000000000003 | thermal_die0 |  |

## Method Ranking Check

- `m10_medium_p22810_3d_stack`: proxy best `m4_greedy`, HotSpot best `m4_greedy`, ranking_match=True.
- `m10_medium_p22810_5_5d_multi_tower`: proxy best `m4_greedy`, HotSpot best `m4_greedy`, ranking_match=True.
- `m10_small_d695_5_5d_multi_tower`: proxy best `m4_greedy`, HotSpot best `m4_greedy`, ranking_match=True.

## Interpretation Notes

- This report is HotSpot execution evidence only for rows with `status=ok`.
- Non-success rows must not be cited as HotSpot validation.
- The exported floorplan is block-level and simplified; it supports trend validation, not industrial signoff.
