# M18 Resource-Pressure Study Report

- Total rows: 10
- Successful rows: 10
- Best joint gain: 46.67%

## Claim Impact

M18 upgrades path-schedule joint optimization from a weak general-sweep claim to a supported controlled-ablation claim.
The correct wording is still limited: the current evidence shows value under explicit shared-resource pressure, not universal dominance on all M10 cases.

## Best Joint Gain Per Case

| case | topology | targets | fixed_fastest_s | best_joint | best_joint_s | gain_vs_fixed_fastest | recipe mix |
| --- | --- | ---: | ---: | --- | ---: | ---: | --- |
| m18_shared_bist_12die_5_5d_multi_tower | 5_5d_multi_tower | 12 | 0.072008640 | m5_cpsat | 0.038404520 | 46.67% | B:6;F:6 |
| m18_shared_bist_8die_3d_stack | 3d_stack | 8 | 0.048015040 | m5_cpsat | 0.025604520 | 46.67% | B:4;F:4 |

## Interpretation

M18 intentionally stresses the case where the individually fastest recipe is a shared BIST path.
A fixed fastest-path policy serializes all targets on the shared BIST engine.
Joint recipe selection can mix BIST and FPP paths, using otherwise idle package lanes while the shared BIST engine is busy.
These cases are controlled ablations, not public industrial chip measurements.
