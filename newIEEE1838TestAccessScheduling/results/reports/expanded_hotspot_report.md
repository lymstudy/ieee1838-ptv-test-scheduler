# Expanded HotSpot Validation Report

This report covers 3 topologies x 3 scales x 2-3 scheduling methods.
HotSpot-compatible .flp and .ptrace files have been generated.
Actual HotSpot execution requires a Linux VM with the HotSpot simulator installed.

- Total method results: 18
- Total HotSpot export files: 18

## Summary Table

| topology | scale | case_id | method | makespan_s | peak_power_w | proxy_peak_c | proxy_peak_die |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| 2.5D | large | m10_large_p34392_2_5d_interposer | fixed_fastest | 0.003096080 | 2.286 | 29.01 | die0 |
| 2.5D | large | m10_large_p34392_2_5d_interposer | m4_greedy | 0.003096080 | 2.286 | 29.01 | die0 |
| 2.5D | medium | m10_medium_p22810_2_5d_interposer | fixed_fastest | 0.002117520 | 2.258 | 28.84 | die0 |
| 2.5D | medium | m10_medium_p22810_2_5d_interposer | m4_greedy | 0.002117520 | 2.258 | 28.84 | die0 |
| 2.5D | small | m10_small_d695_2_5d_interposer | fixed_fastest | 0.001210560 | 2.287 | 28.66 | die0 |
| 2.5D | small | m10_small_d695_2_5d_interposer | m4_greedy | 0.001210560 | 2.287 | 28.66 | die0 |
| 3D | large | m10_large_p34392_3d_stack | fixed_fastest | 0.003492692 | 2.238 | 89.94 | die5 |
| 3D | large | m10_large_p34392_3d_stack | m4_greedy | 0.003492692 | 2.238 | 89.94 | die5 |
| 3D | medium | m10_medium_p22810_3d_stack | fixed_fastest | 0.002277820 | 2.258 | 71.14 | die3 |
| 3D | medium | m10_medium_p22810_3d_stack | m4_greedy | 0.002277820 | 2.258 | 71.14 | die3 |
| 3D | small | m10_small_d695_3d_stack | fixed_fastest | 0.001229440 | 2.249 | 42.43 | die1 |
| 3D | small | m10_small_d695_3d_stack | m4_greedy | 0.001229440 | 2.249 | 42.43 | die1 |
| 5.5D | large | m10_large_p34392_5_5d_multi_tower | fixed_fastest | 0.003140372 | 2.586 | 68.25 | die0 |
| 5.5D | large | m10_large_p34392_5_5d_multi_tower | m4_greedy | 0.003140372 | 2.586 | 68.25 | die0 |
| 5.5D | medium | m10_medium_p22810_5_5d_multi_tower | fixed_fastest | 0.002157836 | 2.255 | 58.67 | die0 |
| 5.5D | medium | m10_medium_p22810_5_5d_multi_tower | m4_greedy | 0.002157836 | 2.255 | 58.67 | die0 |
| 5.5D | small | m10_small_d695_5_5d_multi_tower | fixed_fastest | 0.001259840 | 2.287 | 36.32 | die0 |
| 5.5D | small | m10_small_d695_5_5d_multi_tower | m4_greedy | 0.001259840 | 2.287 | 36.32 | die0 |

## Per-Topology Summary

### 2.5D
- Methods: fixed_fastest, m4_greedy
- Scales: large, medium, small
- Results: 6
- Temperature range: 28.66C - 29.01C

### 3D
- Methods: fixed_fastest, m4_greedy
- Scales: large, medium, small
- Results: 6
- Temperature range: 42.43C - 89.94C

### 5.5D
- Methods: fixed_fastest, m4_greedy
- Scales: large, medium, small
- Results: 6
- Temperature range: 36.32C - 68.25C

## Per-Method Temperature Comparison

- **fixed_fastest**: 9 runs, avg peak 50.36C, range 28.66-89.94C
- **m4_greedy**: 9 runs, avg peak 50.36C, range 28.66-89.94C

## HotSpot Export Files

All .flp and .ptrace files are in `results/hotspot/expanded/`.

| case_id | schedule_id | floorplan | ptrace | samples | regions |
| --- | --- | --- | --- | ---: | ---: |
| m10_large_p34392_2_5d_interposer | fixed_fastest | `m10_large_p34392_2_5d_interposer.flp` | `m10_large_p34392_2_5d_interposer__fixed_fastest.ptrace` | 310 | 8 |
| m10_large_p34392_2_5d_interposer | m4_greedy | `m10_large_p34392_2_5d_interposer.flp` | `m10_large_p34392_2_5d_interposer__m4_greedy.ptrace` | 310 | 8 |
| m10_medium_p22810_2_5d_interposer | fixed_fastest | `m10_medium_p22810_2_5d_interposer.flp` | `m10_medium_p22810_2_5d_interposer__fixed_fastest.ptrace` | 212 | 6 |
| m10_medium_p22810_2_5d_interposer | m4_greedy | `m10_medium_p22810_2_5d_interposer.flp` | `m10_medium_p22810_2_5d_interposer__m4_greedy.ptrace` | 212 | 6 |
| m10_small_d695_2_5d_interposer | fixed_fastest | `m10_small_d695_2_5d_interposer.flp` | `m10_small_d695_2_5d_interposer__fixed_fastest.ptrace` | 122 | 4 |
| m10_small_d695_2_5d_interposer | m4_greedy | `m10_small_d695_2_5d_interposer.flp` | `m10_small_d695_2_5d_interposer__m4_greedy.ptrace` | 122 | 4 |
| m10_large_p34392_3d_stack | fixed_fastest | `m10_large_p34392_3d_stack.flp` | `m10_large_p34392_3d_stack__fixed_fastest.ptrace` | 350 | 8 |
| m10_large_p34392_3d_stack | m4_greedy | `m10_large_p34392_3d_stack.flp` | `m10_large_p34392_3d_stack__m4_greedy.ptrace` | 350 | 8 |
| m10_medium_p22810_3d_stack | fixed_fastest | `m10_medium_p22810_3d_stack.flp` | `m10_medium_p22810_3d_stack__fixed_fastest.ptrace` | 228 | 6 |
| m10_medium_p22810_3d_stack | m4_greedy | `m10_medium_p22810_3d_stack.flp` | `m10_medium_p22810_3d_stack__m4_greedy.ptrace` | 228 | 6 |
| m10_small_d695_3d_stack | fixed_fastest | `m10_small_d695_3d_stack.flp` | `m10_small_d695_3d_stack__fixed_fastest.ptrace` | 123 | 4 |
| m10_small_d695_3d_stack | m4_greedy | `m10_small_d695_3d_stack.flp` | `m10_small_d695_3d_stack__m4_greedy.ptrace` | 123 | 4 |
| m10_large_p34392_5_5d_multi_tower | fixed_fastest | `m10_large_p34392_5_5d_multi_tower.flp` | `m10_large_p34392_5_5d_multi_tower__fixed_fastest.ptrace` | 315 | 8 |
| m10_large_p34392_5_5d_multi_tower | m4_greedy | `m10_large_p34392_5_5d_multi_tower.flp` | `m10_large_p34392_5_5d_multi_tower__m4_greedy.ptrace` | 315 | 8 |
| m10_medium_p22810_5_5d_multi_tower | fixed_fastest | `m10_medium_p22810_5_5d_multi_tower.flp` | `m10_medium_p22810_5_5d_multi_tower__fixed_fastest.ptrace` | 216 | 6 |
| m10_medium_p22810_5_5d_multi_tower | m4_greedy | `m10_medium_p22810_5_5d_multi_tower.flp` | `m10_medium_p22810_5_5d_multi_tower__m4_greedy.ptrace` | 216 | 6 |
| m10_small_d695_5_5d_multi_tower | fixed_fastest | `m10_small_d695_5_5d_multi_tower.flp` | `m10_small_d695_5_5d_multi_tower__fixed_fastest.ptrace` | 126 | 4 |
| m10_small_d695_5_5d_multi_tower | m4_greedy | `m10_small_d695_5_5d_multi_tower.flp` | `m10_small_d695_5_5d_multi_tower__m4_greedy.ptrace` | 126 | 4 |

## How to Run HotSpot Later

HotSpot is a C++ thermal simulator that must be compiled and run on Linux.
If the Linux VM with HotSpot is not currently available, follow these steps:

### Prerequisites

1. Linux VM with `hotspot` installed (e.g., Ubuntu 20.04+)
2. HotSpot binary compiled from: https://github.com/uvahotspot/HotSpot

### Running HotSpot

```bash
# On the Linux VM, copy the entire expanded/ directory
scp -r results/hotspot/expanded/ user@linux-vm:~/hotspot_inputs/

# SSH into the VM and run HotSpot for each case
ssh user@linux-vm
cd ~/hotspot_inputs/

# Example: run HotSpot for one case+method combination
hotspot -c hotspot.config -f m10_small_d695_3d_stack.flp \
  -p m10_small_d695_3d_stack__m4_greedy.ptrace \
  -o m10_small_d695_3d_stack__m4_greedy.ttrace

# Batch process all .ptrace files
for ptrace in *.ptrace; do
  base="${ptrace%.ptrace}"
  flp="${base%__*}.flp"
  hotspot -c hotspot.config -f "$flp" -p "$ptrace" -o "${base}.ttrace"
done
```

### Interpreting Results

- HotSpot outputs `.ttrace` files with per-block temperature traces
- Compare HotSpot peak temperatures with the proxy peak temperatures in this report
- The proxy should preserve the temperature ordering across methods even if absolute values differ

### Alternative: Automated Remote Execution

If the Linux VM is available and configured with SSH key access, use:

```bash
python experiments/run_m12_hotspot_remote_validation.py \
  --manifest results/hotspot/expanded_hotspot_manifest.csv \
  --ssh-user <user> --ssh-host <host> --ssh-key <path>
```

---
*Report generated by run_extended_hotspot_validation.py*
