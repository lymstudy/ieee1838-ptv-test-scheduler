# M12: Thermal Stress And HotSpot Export

## Goal

M12 strengthens the thermal evidence without overstating the current toolchain.
It runs proxy thermal validation under nominal and stressed thermal assumptions,
and exports HotSpot-compatible floorplan/power-trace files for a representative
case.

M12 does not claim that HotSpot has already been executed. The export files are
prepared so that a later run can feed a real HotSpot installation.

## Thermal Profiles

| Profile | Purpose | Treatment |
| --- | --- | --- |
| `nominal_proxy` | Compare schedules under the model used in M7-M11 | Original thermal parameters |
| `stress_proxy` | Reveal schedule thermal sensitivity | Higher thermal resistance, lower capacitance, stronger coupling |

The stress profile is a model stress test, not measured chip data.

## Default Cases

M12 focuses on thermally relevant vertical and multi-tower cases:

```text
configs/cases/m10/m10_small_d695_5_5d_multi_tower.json
configs/cases/m10/m10_medium_p22810_3d_stack.json
configs/cases/m10/m10_medium_p22810_5_5d_multi_tower.json
```

Default compared schedules:

- `fixed_fastest`
- `low_power`
- `thermal_min_risk`
- `m4_greedy`
- `m5_cpsat`

## Commands

```bash
python experiments/run_m12_thermal_validation.py
```

Formal outputs:

```text
results/tables/m12_thermal_validation_summary.csv
results/tables/m12_thermal_hotspots.csv
results/tables/m12_temperature_trace.csv
results/reports/m12_thermal_validation_report.md
results/hotspot/m12_hotspot_export_manifest.csv
results/hotspot/m12/
```

## Interpretation Rules

- `stress_proxy` rows are sensitivity evidence only.
- HotSpot `.flp` and `.ptrace` files are generated inputs, not HotSpot outputs.
- Strong physical thermal claims require running HotSpot or another validated
  thermal simulator after this export step.

## Current M12 Result Snapshot

The first M12 run evaluated 3 thermal-focused cases with 5 schedules and 2
thermal profiles:

- summary rows: 30;
- HotSpot export rows: 2;
- exported case: `m10_small_d695_5_5d_multi_tower`;
- exported schedules: `thermal_min_risk` and `m4_greedy`.

Peak temperature range:

| Profile | Rows | Max peak temperature |
| --- | ---: | ---: |
| `nominal_proxy` | 15 | 25.008395 C |
| `stress_proxy` | 15 | 25.566668 C |

Average peak temperature under `stress_proxy`:

| Method | Avg peak temperature | Avg rise |
| --- | ---: | ---: |
| `fixed_fastest` | 25.109100 C | 0.109100 C |
| `low_power` | 25.430873 C | 0.430873 C |
| `thermal_min_risk` | 25.430873 C | 0.430873 C |
| `m4_greedy` | 25.109100 C | 0.109100 C |
| `m5_cpsat` | 25.115519 C | 0.115519 C |

Observation: selecting a low-power or low-risk recipe independently can increase
thermal accumulation when it lengthens the schedule. This is useful evidence for
the paper: thermal-aware scheduling should optimize time, power, and heat
history jointly, not only choose the lowest-power recipe per target.
