# 瀹為獙鏃ュ織 EXPERIMENT_LOG

## Experiment 001锛歋caffold Sanity Check

鏃ユ湡锛?2026-05-15

Commit锛?寰呭～鍐?
杩愯鍛戒护锛?
```bash
pytest
python experiments/run_case_4die.py
```

瀹為獙鐩殑锛?楠岃瘉閰嶇疆鍔犺浇銆佸熀纭€妯″瀷鏋勯€犮€乼hermal sanity model 鍜?voltage sanity model 鏄惁鍙互姝ｅ父杩愯銆?
杈撳叆閰嶇疆锛?- configs/case_4die.yaml
- configs/default_params.yaml

杈撳嚭鏂囦欢锛?- results/case_4die/model_summary.csv
- results/case_4die/thermal_sanity.csv
- results/case_4die/voltage_sanity.csv
- results/case_4die/temperature_curve.svg
- results/case_4die/ir_drop_curve.svg

缁撴灉锛?閫氳繃銆?
娴嬭瘯缁撴灉锛?pytest: 4 passed

澶囨敞锛?褰撳墠灏氭湭瀹炵幇璋冨害绠楁硶锛屽洜姝よ瀹為獙鍙獙璇佸熀纭€妯″瀷鍜?sanity traces銆?
## Experiment 002锛歋erial Baseline Scheduler

鏃ユ湡锛?2026-05-15

Commit锛?寰呭～鍐?
杩愯鍛戒护锛?
```bash
pytest
python experiments/run_case_4die.py
```

瀹為獙鐩殑锛?楠岃瘉 common scheduler interface 鍜?Serial IEEE 1838-style baseline scheduler 鏄惁鍙互姝ｅ父璋冨害 4-die case锛屽苟鐢熸垚 serial schedule銆乵etrics 鍜屽彲瑙嗗寲缁撴灉銆?
杈撳叆閰嶇疆锛?- configs/case_4die.yaml
- configs/default_params.yaml

杈撳嚭鏂囦欢锛?- results/case_4die/model_summary.csv
- results/case_4die/thermal_sanity.csv
- results/case_4die/voltage_sanity.csv
- results/case_4die/temperature_curve.svg
- results/case_4die/ir_drop_curve.svg
- results/case_4die/serial_schedule.csv
- results/case_4die/serial_metrics.csv
- results/case_4die/serial_gantt.svg
- results/case_4die/serial_temperature_curve.svg
- results/case_4die/serial_ir_drop_curve.svg

缁撴灉锛?閫氳繃銆?
娴嬭瘯缁撴灉锛?pytest: 8 passed, 1 warning

澶囨敞锛?褰撳墠鍙疄鐜?Serial baseline銆傝 baseline 鎸?die order銆乼ask type priority 鍜?task_id 纭畾鎬ф帓搴忥紝鎵€鏈?task 涓茶鎵ц锛屼笉瀹炵幇 Bandwidth-greedy銆丳TV-aware銆佸弬鏁版壂鎻忔垨涓夌被璋冨害鍣ㄥ姣斻€?

## Experiment 003锛欱andwidth-Greedy Baseline Scheduler

鏃ユ湡锛?2026-05-15

Commit锛?寰呭～鍐?
杩愯鍛戒护锛?
```bash
pytest
python experiments/run_case_4die.py
```

瀹為獙鐩殑锛?楠岃瘉 BandwidthGreedyScheduler 鏄惁鍙互鍦ㄥ彧鑰冭檻 task readiness/dependency銆丗PP lane capacity銆丏WR segment conflict 鍜屽熀纭€ access resource conflict 鐨勫墠鎻愪笅骞惰璋冨害 4-die case锛屽苟鐢熸垚 greedy schedule銆乵etrics 鍜屽彲瑙嗗寲缁撴灉銆?
杈撳叆閰嶇疆锛?- configs/case_4die.yaml
- configs/default_params.yaml

杈撳嚭鏂囦欢锛?- results/case_4die/greedy_schedule.csv
- results/case_4die/greedy_metrics.csv
- results/case_4die/greedy_gantt.svg
- results/case_4die/greedy_temperature_curve.svg
- results/case_4die/greedy_ir_drop_curve.svg
- results/case_4die/scheduler_metrics_summary.csv

缁撴灉锛?閫氳繃銆?
娴嬭瘯缁撴灉锛?pytest: 13 passed, 1 warning

澶囨敞锛?Bandwidth-greedy baseline 涓嶈€冭檻 thermal/voltage 绾︽潫锛屼笉瀹炵幇 capture staggering锛屼篃涓嶆彃鍏?dummy cycle銆倀hermal 鍜?IR drop 鍙湪璋冨害瀹屾垚鍚庣敤浜庤绠?trace銆乸eak value 鍜?violation count銆?## Experiment 004锛歁odel Consistency Check

鏃ユ湡锛?2026-05-15

Commit锛?寰呭～鍐?
杩愯鍛戒护锛?
```bash
pytest
python experiments/run_case_4die.py
```

瀹為獙鐩殑锛?鍦ㄨ繘鍏?PTV-aware scheduler 鍓嶏紝妫€鏌?Bandwidth-greedy baseline 鐨勮祫婧愬崰鐢ㄩ€昏緫鍜?serial/greedy metrics summary 鏄惁涓€鑷淬€?
妫€鏌ュ唴瀹癸細
- greedy TAT 灏忎簬鎴栫瓑浜?serial TAT銆?- greedy 姣忎釜 task 鍙嚭鐜颁竴娆°€?- greedy 鏈秴杩?FPP lane capacity銆?- greedy 涓嶅瓨鍦ㄥ悓涓€ DWR segment overlap銆?- scheduler_metrics_summary.csv 鍖呭惈 serial_ieee1838_style 鍜?bandwidth_greedy 涓よ銆?
缁撴灉锛?閫氳繃銆?
娴嬭瘯缁撴灉锛?pytest: 13 passed, 1 warning

澶囨敞锛?鏈鍙仛妯″瀷涓€鑷存€ф鏌ュ拰寤烘ā鍐崇瓥璁板綍锛屼笉瀹炵幇 PTV-aware scheduler銆?## Experiment 005锛歅TV-Aware Scheduler

鏃ユ湡锛?2026-05-15

Commit锛?寰呭～鍐?
杩愯鍛戒护锛?
```bash
pytest
python experiments/run_case_4die.py
```

瀹為獙鐩殑锛?楠岃瘉 PTVAwareScheduler 鏄惁鍙互鍦?Bandwidth-greedy 鐨勮祫婧愮害鏉熷熀纭€涓婂姞鍏?thermal prediction銆両R drop prediction銆乧apture staggering 鍜?dummy cycle insertion锛屽苟鐢熸垚 serial銆乥andwidth_greedy銆乸tv_aware 涓夌被 scheduler 鐨勫熀纭€瀵规瘮缁撴灉銆?
杈撳叆閰嶇疆锛?- configs/case_4die.yaml
- configs/default_params.yaml

杈撳嚭鏂囦欢锛?- results/case_4die/ptv_schedule.csv
- results/case_4die/ptv_metrics.csv
- results/case_4die/ptv_gantt.svg
- results/case_4die/ptv_temperature_curve.svg
- results/case_4die/ptv_ir_drop_curve.svg
- results/case_4die/scheduler_metrics_summary.csv
- results/case_4die/tat_comparison.svg
- results/case_4die/peak_temperature_comparison.svg
- results/case_4die/peak_ir_drop_comparison.svg

缁撴灉锛?閫氳繃銆?
娴嬭瘯缁撴灉锛?pytest: 21 passed, 1 warning

澶囨敞锛?褰撳墠 4-die MVP case 涓?thermal銆両R drop銆乧apture 鍜?dummy cycle 绾︽潫鏈粦瀹氥€侾TV-aware 涓?bandwidth-greedy 鐨?TAT銆乸eak temperature銆乸eak IR drop 鍜?schedule 鐩稿悓鎴栫瓑浠枫€傝缁撴灉鏄綋鍓?workload 鍜?limit 璁剧疆涓嬬殑鐪熷疄缁撴灉锛屼笉浜轰负鍒堕€?PTV-aware 浼樺娍銆傚悗缁渶瑕?richer workload 鎴?tighter constraints 鏉ュ睍绀?PTV-aware 涓?bandwidth-greedy 鐨勫樊寮傘€?## Experiment 006锛?-die Stress Workload Mechanism Validation

鏃ユ湡锛?2026-05-15

Commit锛?寰呭～鍐?
杩愯鍛戒护锛?
```bash
pytest
python experiments/run_case_4die.py
python experiments/run_case_4die_stress.py
```

瀹為獙鐩殑锛?楠岃瘉 PTV-aware scheduler 鍦ㄦ洿楂樺苟琛屽害銆佹洿楂樺姛鑰椼€佹洿绱?thermal / IR drop limit銆乧apture phase 鍜屾樉寮?FPP lane 绾︽潫涓嬫槸鍚﹁兘浣撶幇鏈哄埗宸紓銆?
杈撳叆閰嶇疆锛?
```text
configs/case_4die_stress.yaml
```

杈撳嚭鏂囦欢锛?
```text
results/case_4die_stress/serial_schedule.csv
results/case_4die_stress/serial_metrics.csv
results/case_4die_stress/serial_gantt.svg
results/case_4die_stress/serial_temperature_curve.svg
results/case_4die_stress/serial_ir_drop_curve.svg
results/case_4die_stress/greedy_schedule.csv
results/case_4die_stress/greedy_metrics.csv
results/case_4die_stress/greedy_gantt.svg
results/case_4die_stress/greedy_temperature_curve.svg
results/case_4die_stress/greedy_ir_drop_curve.svg
results/case_4die_stress/ptv_schedule.csv
results/case_4die_stress/ptv_metrics.csv
results/case_4die_stress/ptv_gantt.svg
results/case_4die_stress/ptv_temperature_curve.svg
results/case_4die_stress/ptv_ir_drop_curve.svg
results/case_4die_stress/scheduler_metrics_summary.csv
results/case_4die_stress/tat_comparison.svg
results/case_4die_stress/peak_temperature_comparison.svg
results/case_4die_stress/peak_ir_drop_comparison.svg
```

鍏抽敭缁撴灉锛?
```text
serial_ieee1838_style: TAT=0.0454 s, peak_temperature=26.2234 C, peak_ir_drop=0.1125 V, temperature_violation_count=9, voltage_violation_count=0
bandwidth_greedy: TAT=0.0168 s, peak_temperature=26.4709 C, peak_ir_drop=0.28125 V, temperature_violation_count=48, voltage_violation_count=17
ptv_aware: TAT=0.0174 s, peak_temperature=26.1084 C, peak_ir_drop=0.1125 V, temperature_violation_count=0, voltage_violation_count=0
```

缁撴灉锛?閫氳繃銆?
娴嬭瘯缁撴灉锛?pytest: 29 passed, 1 warning

鏈哄埗瑙傚療锛?- bandwidth_greedy 鍑虹幇 thermal violation 鍜?voltage violation銆?- PTV-aware 灏?thermal / voltage violation count 闄嶄负 0銆?- PTV-aware 鐨?TAT 澶т簬 bandwidth_greedy锛岀鍚堢害鏉熷瀷璋冨害棰勬湡銆?- capture_staggering_applied=True锛宮ax_concurrent_capture=1 绾︽潫鐢熸晥銆?- constraints_were_binding=True銆?- dummy_cycle_count=0锛涙湰 stress case 鏈Е鍙?dummy cycle insertion锛屼絾 dummy cycle insertion 妗嗘灦宸插瓨鍦紝骞剁敱 synthetic unit test 瑕嗙洊銆?
澶囨敞锛?璇?workload 鏄?synthetic mechanism validation锛屼笉鏄湡瀹?benchmark workload銆傚叾鍙傛暟鐢ㄤ簬楠岃瘉 scheduler 鏈哄埗锛屼笉鐢ㄤ簬澹扮О鐪熷疄鑺墖鎴栧伐涓氬伐鍏风粨鏋溿€?

## Experiment 007锛歋chedule Evaluator Consistency Check

鏃ユ湡锛?2026-05-15

Commit锛?寰呭～鍐?
杩愯鍛戒护锛?
```bash
pytest
python experiments/run_case_4die.py
python experiments/run_case_4die_stress.py
```

瀹為獙鐩殑锛?璇婃柇骞朵慨澶?scheduler metrics 鏄惁姝ｇ‘浣跨敤 schedule overlap锛屽挨鍏舵槸骞跺彂 task 鐨?total power 鍜?shared-PDN total current 鏄惁琚彔鍔犮€?
淇鍐呭锛?- 鏂板缁熶竴 evaluator锛歚src/scheduler/evaluator.py`銆?- SerialScheduler銆丅andwidthGreedyScheduler銆丳TVAwareScheduler 鍧囧垏鎹㈠埌鍚屼竴涓?evaluator銆?- Voltage model 鏂板 MVP simplified shared-PDN mode銆?- 鏂板 serial-vs-parallel toy evaluator test銆?
Toy test 缁撴灉锛?- 涓や釜 1 W task 涓茶鎵ц鏃讹紝peak IR-drop = 0.1 V銆?- 涓や釜 1 W task 骞惰鎵ц鏃讹紝peak IR-drop = 0.2 V銆?- parallel peak IR-drop > serial peak IR-drop銆?- serial max_parallelism = 1銆?- parallel max_parallelism = 2銆?
Clean 4-die MVP case 鏈€鏂扮粨鏋滐細

```text
serial_ieee1838_style: TAT=0.0106 s, peak_temperature=25.0070719229 C, peak_ir_drop=0.034875 V, temperature_violation_count=0, voltage_violation_count=0
bandwidth_greedy: TAT=0.0040 s, peak_temperature=25.0070712813 C, peak_ir_drop=0.0928125 V, temperature_violation_count=0, voltage_violation_count=4
ptv_aware: TAT=0.0054 s, peak_temperature=25.0070715562 C, peak_ir_drop=0.0675 V, temperature_violation_count=0, voltage_violation_count=0
```

Stress workload 鏈€鏂扮粨鏋滐細

```text
serial_ieee1838_style: TAT=0.0454 s, peak_temperature=26.2233591261 C, peak_ir_drop=0.1125 V, temperature_violation_count=9, voltage_violation_count=0
bandwidth_greedy: TAT=0.0168 s, peak_temperature=26.4709087381 C, peak_ir_drop=0.571875 V, temperature_violation_count=48, voltage_violation_count=71
ptv_aware: TAT=0.0386 s, peak_temperature=25.8033739302 C, peak_ir_drop=0.159375 V, temperature_violation_count=0, voltage_violation_count=0
```

缁撴灉锛?閫氳繃銆?
娴嬭瘯缁撴灉锛?pytest: 31 passed, 1 warning

澶囨敞锛?淇鍓嶏紝voltage model 浣跨敤 per-die independent estimate锛屽洜姝や笉鍚?die 涓婂苟鍙?task 鐨勭數娴佷笉浼氬湪 shared supply path 涓彔鍔狅紝瀵艰嚧 serial 鍜?bandwidth_greedy 鐨?peak IR-drop 杩囦簬鎺ヨ繎銆備慨澶嶅悗锛宻hared-PDN mode 鑳戒綋鐜板苟琛?schedule 鐨勭灛鏃舵€荤數娴侀闄┿€俆hermal trace 宸叉寜 active task 鐨?die-level power 鏇存柊锛屼絾褰撳墠 per-die RC model 娌℃湁 die-to-die thermal coupling锛屽洜姝?clean case 鐨?peak temperature 宸紓浠嶇劧寰堝皬銆?
## Experiment 008: MVP Result Consolidation

Date:
2026-05-15

Commit:
TBD

Commands:

```bash
pytest
```

Purpose:
Consolidate the current MVP findings into RESULTS.md and link the summary from README.md.

Input result files:

```text
results/case_4die/scheduler_metrics_summary.csv
results/case_4die_stress/scheduler_metrics_summary.csv
```

Files added or updated:

```text
RESULTS.md
README.md
STATUS.md
TODO.md
EXPERIMENT_LOG.md
```

Clean 4-die MVP case key results:

```text
serial_ieee1838_style: TAT=0.0106, peak_ir_drop=0.034875, voltage_violation_count=0
bandwidth_greedy: TAT=0.0040, peak_ir_drop=0.0928125, voltage_violation_count=4
ptv_aware: TAT=0.0054, peak_ir_drop=0.0675, voltage_violation_count=0
```

Stress workload key results:

```text
serial_ieee1838_style: TAT=0.0454, peak_temperature=26.2233591261, peak_ir_drop=0.1125, temperature_violation_count=9, voltage_violation_count=0
bandwidth_greedy: TAT=0.0168, peak_temperature=26.4709087381, peak_ir_drop=0.571875, temperature_violation_count=48, voltage_violation_count=71
ptv_aware: TAT=0.0386, peak_temperature=25.8033739302, peak_ir_drop=0.159375, temperature_violation_count=0, voltage_violation_count=0
```

Result:
Passed.

Test result:
pytest: 31 passed, 1 warning

Notes:
This task only consolidated results and synchronized project state files. It did not change scheduler algorithms, the evaluator, or experiment parameters. RESULTS.md explicitly records that the stress workload is for mechanism validation, not a real benchmark.

## Experiment 009: FPP Lane Sweep

Date:
2026-05-15

Commit:
TBD

Commands:

```bash
pytest
python experiments/run_case_4die.py
python experiments/run_case_4die_stress.py
python experiments/sweep_fpp_lanes.py
```

Purpose:
Evaluate how FPP lane count affects serial, bandwidth-greedy, and PTV-aware scheduling on the 4-die stress workload.

Base config:

```text
configs/case_4die_stress.yaml
```

Sweep values:

```text
fpp_lanes = [1, 2, 3, 4, 6, 8]
```

Output files:

```text
results/sweeps/fpp_lanes/fpp_lane_sweep_summary.csv
results/sweeps/fpp_lanes/tat_vs_fpp_lanes.svg
results/sweeps/fpp_lanes/peak_ir_drop_vs_fpp_lanes.svg
results/sweeps/fpp_lanes/peak_temperature_vs_fpp_lanes.svg
results/sweeps/fpp_lanes/voltage_violations_vs_fpp_lanes.svg
results/sweeps/fpp_lanes/temperature_violations_vs_fpp_lanes.svg
```

Key observations:
- Serial TAT is insensitive to FPP lane count and remains 0.0454 s across the sweep.
- Bandwidth-greedy TAT decreases as FPP lanes increase, from 0.0318 s at 1 lane to 0.0066 s at 8 lanes.
- Bandwidth-greedy peak IR-drop increases as FPP lanes increase, from 0.490625 V at 1 lane to 1.003125 V at 8 lanes.
- Bandwidth-greedy violation counts are not strictly monotonic because higher lane counts change both instantaneous concurrency and total elapsed time. Voltage violations remain nonzero for all swept lane counts.
- PTV-aware keeps temperature_violation_count = 0 and voltage_violation_count = 0 for all swept lane counts.
- PTV-aware TAT improves from 0.0438 s at 1 lane to 0.0386 s at 2 lanes, then shows diminishing returns as physical constraints become binding.

Result:
Passed.

Test result:
pytest: 36 passed, 1 warning

Notes:
This experiment only changes the FPP lane count in the stress config copy. It does not modify scheduler algorithms, thermal limits, voltage limits, or workload tasks.

## Experiment 010: Voltage Limit Sweep

Date:
2026-05-15

Commit:
TBD

Commands:

```bash
pytest
python experiments/run_case_4die.py
python experiments/run_case_4die_stress.py
python experiments/sweep_fpp_lanes.py
python experiments/sweep_voltage_limits.py
```

Purpose:
Evaluate how the shared-PDN IR-drop limit affects serial, bandwidth-greedy, and PTV-aware scheduling on the 4-die stress workload.

Base config:

```text
configs/case_4die_stress.yaml
```

Sweep values:

```text
voltage.max_ir_drop_v = [0.10, 0.15, 0.20, 0.30, 0.50] V
```

Output files:

```text
results/sweeps/voltage_limits/voltage_limit_sweep_summary.csv
results/sweeps/voltage_limits/tat_vs_voltage_limit.svg
results/sweeps/voltage_limits/peak_ir_drop_vs_voltage_limit.svg
results/sweeps/voltage_limits/voltage_violations_vs_voltage_limit.svg
```

Key observations:
- Serial and bandwidth-greedy schedules do not change with voltage limit because these baselines do not use voltage constraints during scheduling.
- Bandwidth-greedy keeps TAT = 0.0168 s and peak_ir_drop = 0.571875 V across the sweep; voltage violations decrease as the limit is relaxed.
- PTV-aware increases TAT when the voltage limit is tighter and relaxes toward greedy as the voltage limit increases.
- At 0.10 V, the limit is too tight for some individual tasks, so PTV-aware still records voltage violations: 27 samples versus greedy's 86 samples. It also inserts 320 dummy cycles.
- For voltage limits 0.15 V and above, PTV-aware records voltage_violation_count = 0.
- PTV-aware voltage_violation_count is no greater than bandwidth-greedy for every swept limit.

Result:
Passed.

Test result:
pytest: 41 passed, 1 warning

Notes:
This experiment only changes `voltage.max_ir_drop_v` in a copied stress config. It does not modify scheduler algorithms, thermal limits, FPP lane count, or workload tasks.

## Experiment 011: Thermal Limit Sweep

Date:
2026-05-15

Commit:
TBD

Commands:

```bash
pytest
python experiments/run_case_4die.py
python experiments/run_case_4die_stress.py
python experiments/sweep_fpp_lanes.py
python experiments/sweep_voltage_limits.py
python experiments/sweep_thermal_limits.py
```

Purpose:
Evaluate how the thermal limit affects serial, bandwidth-greedy, and PTV-aware scheduling on the 4-die stress workload.

Base config:

```text
configs/case_4die_stress.yaml
```

Sweep values:

```text
thermal.max_temp_c = [25.5, 26.0, 26.5, 27.0, 28.0] C
```

Output files:

```text
results/sweeps/thermal_limits/thermal_limit_sweep_summary.csv
results/sweeps/thermal_limits/tat_vs_thermal_limit.svg
results/sweeps/thermal_limits/peak_temperature_vs_thermal_limit.svg
results/sweeps/thermal_limits/temperature_violations_vs_thermal_limit.svg
results/sweeps/thermal_limits/dummy_cycles_vs_thermal_limit.svg
```

Key observations:
- Serial and bandwidth-greedy schedules do not change with thermal limit because these baselines do not use thermal constraints during scheduling.
- Greedy temperature violations decrease as the limit is relaxed: 89 at 25.5 C, 74 at 26.0 C, and 0 at 26.5 C or higher.
- PTV-aware keeps temperature_violation_count = 0 for 26.0 C and above.
- The 25.5 C point is over-constrained: initial die temperatures are about 25.55 C, already above the limit. PTV-aware records 117 temperature-violation samples and inserts 63 dummy cycles.
- PTV-aware TAT is 0.0524 s at 25.5 C and 0.0386 s for 26.0 C and above.

Result:
Passed.

Test result:
pytest: 46 passed, 1 warning

Notes:
This experiment only changes `thermal.max_temp_c` in a copied stress config. It does not modify scheduler algorithms, voltage limits, FPP lane count, or workload tasks. The current thermal model is a simplified per-die RC model without die-to-die thermal coupling.

## Experiment 012: Richer Synthetic Workload and Workload Scale Sweep

Date:
2026-05-15

Commit:
TBD

Commands:

```bash
pytest
python experiments/run_case_4die.py
python experiments/run_case_4die_stress.py
python experiments/sweep_fpp_lanes.py
python experiments/sweep_voltage_limits.py
python experiments/sweep_thermal_limits.py
python experiments/sweep_workload_scale.py
```

Purpose:
Generate deterministic synthetic workloads at multiple die counts and task densities, then compare serial, bandwidth-greedy, and PTV-aware scheduling behavior as workload scale increases.

Generated workload dimensions:

```text
die_count = [4, 8, 12]
task_density = [small, medium, large]
```

Output files:

```text
results/sweeps/workload_scale/workload_scale_summary.csv
results/sweeps/workload_scale/tat_vs_workload_scale.svg
results/sweeps/workload_scale/peak_ir_drop_vs_workload_scale.svg
results/sweeps/workload_scale/peak_temperature_vs_workload_scale.svg
results/sweeps/workload_scale/voltage_violations_vs_workload_scale.svg
results/sweeps/workload_scale/temperature_violations_vs_workload_scale.svg
results/sweeps/workload_scale/task_count_vs_workload_scale.svg
```

Key observations:
- Task count increases with both die count and density: 4-small has 19 tasks, while 12-large has 142 tasks.
- Bandwidth-greedy is consistently fastest but has increasing voltage violations as workload scale grows. Greedy voltage violations increase from 18 for 4-small to 243 for 12-large.
- PTV-aware keeps voltage_violation_count = 0 and temperature_violation_count = 0 for every generated workload in this sweep.
- PTV-aware TAT is consistently below serial TAT and above greedy TAT.
- No over-constrained workload-scale point appears in the current sweep.
- Dummy cycles are not triggered in this sweep. Capture staggering is active for PTV-aware workloads.

Result:
Passed.

Test result:
pytest: 60 passed, 1 warning

Notes:
This experiment is synthetic mechanism validation only. It does not introduce benchmark-derived workloads, RTL mock validation, HotSpot, 3D-ICE, RedHawk, Voltus, or Tessent SSN.

## Experiment 013: Benchmark-derived Workload Schema and Example Adapter

Date:
2026-05-15

Commit:
TBD

Commands:

```bash
pytest
python experiments/run_case_4die.py
python experiments/run_case_4die_stress.py
python experiments/sweep_fpp_lanes.py
python experiments/sweep_voltage_limits.py
python experiments/sweep_thermal_limits.py
python experiments/sweep_workload_scale.py
python experiments/run_example_benchmark_workload.py
```

Purpose:
Validate a statistics-level benchmark-derived workload schema and a minimal adapter that converts benchmark statistics into scheduler-compatible abstract tasks.

Input files:

```text
benchmarks/schema.md
benchmarks/example_benchmark_stats.yaml
src/workload/benchmark_adapter.py
```

Output files:

```text
results/benchmarks/example/benchmark_task_summary.csv
results/benchmarks/example/serial_schedule.csv
results/benchmarks/example/greedy_schedule.csv
results/benchmarks/example/ptv_schedule.csv
results/benchmarks/example/scheduler_metrics_summary.csv
results/benchmarks/example/serial_gantt.svg
results/benchmarks/example/greedy_gantt.svg
results/benchmarks/example/ptv_gantt.svg
results/benchmarks/example/tat_comparison.svg
results/benchmarks/example/peak_ir_drop_comparison.svg
results/benchmarks/example/peak_temperature_comparison.svg
```

Key observations:
- The adapter generated 21 abstract tasks from the example statistics YAML.
- The generated workload contains scan shift, scan capture, BIST, instrument access, and DWR EXTEST tasks.
- Capture tasks use `is_capture_phase=True`.
- Scan durations are derived from scan-chain statistics, and DWR EXTEST durations are derived from interconnect DWR length.
- Serial, bandwidth-greedy, and PTV-aware schedulers all ran successfully on the generated workload.
- Example metrics: serial TAT = 0.065206 s, bandwidth_greedy TAT = 0.043492 s, ptv_aware TAT = 0.042852 s.
- Bandwidth-greedy records 26 voltage-violation samples in this example, while PTV-aware records 0.

Result:
Passed.

Test result:
pytest: 68 passed, 1 warning

Notes:
This experiment is schema validation only. It is not real benchmark validation, does not parse RTL, and does not introduce HotSpot, 3D-ICE, RedHawk, Voltus, Tessent SSN, or industrial signoff data.

## Design Note 016: B0 IEEE 1838 Layered Scheduler Spec

Date:
2026-05-16

Commit:
TBD

Type:
Design note, not an experiment.

Commands:

```bash
pytest
```

Purpose:
Freeze the completed A0 task-level PTV scheduling prototype and define the B-stage design direction for IEEE 1838-aware layered access scheduling.

Documents created:

```text
docs/DESIGN_SPEC_1838_LAYERED_SCHEDULER.md
docs/NEXT_PHASE_PLAN.md
```

Documents updated:

```text
README.md
STATUS.md
TODO.md
ROADMAP.md
DECISIONS.md
EXPERIMENT_LOG.md
```

Key decisions:
- A0 is task-level physical-aware scheduling and is no longer treated as the final architecture.
- B-stage work centers on IEEE 1838 access behavior, access path generation, layered task expansion, access time modeling, predictive scheduling, and asymmetric physical models.
- FPP is treated as optional data transport, not a universal control path.
- BIST local execution can release the PTAP control path after trigger in the next model.
- Future schedulers must distinguish access/config time, local execution time, data transfer time, capture time, readback time, and dummy cycle time.

Result:
Passed.

Test result:
pytest: 68 passed, 1 warning

## Design/Prototype Note 019: B1 AccessPath Model and Path Cost Estimator

Date:
2026-05-17

Commit:
TBD

Type:
Design/prototype note.

Commands:

```bash
pytest
python experiments/demo_access_path_generation.py
python experiments/run_case_4die.py
```

Purpose:
Implement the B1 access-path data model, access path generator, and MVP path timing estimator without changing scheduler or evaluator behavior.

Files added:

```text
src/access_path/__init__.py
src/access_path/model.py
src/access_path/generator.py
experiments/demo_access_path_generation.py
tests/test_access_path_generator.py
```

Output files:

```text
results/access_path/access_path_summary.csv
results/access_path/access_path_summary.md
```

Key observations:
- Basic access path estimated time increases from die0 to die3 because deeper access requires more STAP/3DCR path configuration bits.
- DWR access path adds wrapper configuration, serial shift, and readback overhead relative to the basic path.
- FPP data path includes `FPP_TRANSFER` for bulk data but still includes PTAP/STAP/FPP configuration overhead.

Result:
Completed for B1 AccessPath implementation. `pytest`, `demo_access_path_generation.py`, and `run_case_4die.py` completed successfully.

Test result:
pytest: 75 passed, 1 warning

Notes:
No scheduler, evaluator, benchmark, RTL parser, RTL mock, sweep, or industrial-tool integration was added in this task.

## Design Note 018: Frontier Idea Integration into B-stage Roadmap

Date:
2026-05-17

Commit:
TBD

Type:
Design note, not an experiment.

Commands:

```bash
pytest
```

Purpose:
Integrate selected frontier ideas into the B-stage roadmap before starting B1 AccessPath implementation.

Documents created:

```text
docs/FRONTIER_IDEA_INTEGRATION_PLAN.md
```

Documents updated:

```text
docs/DESIGN_SPEC_1838_LAYERED_SCHEDULER.md
docs/NEXT_PHASE_PLAN.md
README.md
STATUS.md
TODO.md
ROADMAP.md
DECISIONS.md
EXPERIMENT_LOG.md
```

Key planning additions:
- Interposer test-bus / BNH / MBB inspiration is recorded as future routing architecture work, not B1/B2 scope.
- UCIe-inspired throttle / emergency health events are abstracted only as future external health-event inputs, not as UCIe implementation.
- HBM-like vertical PDN risk motivates future PowerPillar-aware capture staggering.
- Package/substrate effects are represented only through future PackageProfile boundary conditions.
- SSN-inspired TAM abstraction is allowed only as future streaming-scan-inspired die-level TAM modeling, not as IEEE 1838 or Siemens SSN implementation.

Result:
Documentation planning only. No scheduler, evaluator, AccessPath code, RTL, SSN, UCIe, benchmark, or experiment was added.

Test result:
pytest: 68 passed, 1 warning


## Design Note 020: Repository State Consistency Fix

Date:
2026-05-17

Commit:
TBD

Type:
Design note, not an experiment.

Commands:

```bash
pytest
python experiments/demo_access_path_generation.py
python experiments/run_case_4die.py
python experiments/run_example_benchmark_workload.py
```

Purpose:
Audit and repair documentation that incorrectly described absent benchmark/audit artifacts as completed in the current checkout.

Repository audit:
- `benchmarks/realistic_uart_stats.yaml`: not present.
- `experiments/run_realistic_uart_workload.py`: not present.
- `experiments/audit_realistic_uart_schedule.py`: not present.
- `tests/test_realistic_uart_workload.py`: not present.
- `results/benchmarks/realistic_uart/`: not present.
- `experiments/audit_example_benchmark_schedule.py`: not present.
- `tests/test_example_benchmark_audit.py`: not present.
- `results/benchmarks/example/audit/`: not present.

State correction:
- Benchmark-derived workload schema and example adapter remain completed.
- Example benchmark workload runner, tests, and result directory remain valid.
- Realistic UART statistics case is moved back to future work.
- Example benchmark schedule audit is moved back to future work.
- No scheduler, evaluator, AccessPath code, benchmark implementation, RTL parser, RTL mock, or sweep was changed.

Result:
Documentation state was corrected. `pytest` and `run_case_4die.py` passed in the current follow-up run. `demo_access_path_generation.py` and `run_example_benchmark_workload.py` were blocked by write permission errors in existing `results/` subdirectories, so their outputs were not refreshed in this sandbox session.

Test result:
pytest: 81 passed, 1 warning


## Design/Prototype Note 021: B2 TestIntent to ExecutionPhase Layered Expander

Date:
2026-05-17

Commit:
TBD

Type:
Design/prototype note.

Commands:

```bash
pytest
python experiments/demo_access_path_generation.py
python experiments/demo_layered_task_expansion.py
python experiments/run_case_4die.py
python experiments/run_example_benchmark_workload.py
```

Purpose:
Implement the B2 TestIntent, ExecutionPhase, LayeredTask, and layered task expander MVP without changing scheduler or evaluator behavior.

Files added:

```text
src/layered/__init__.py
src/layered/intent.py
src/layered/phase.py
src/layered/expander.py
experiments/demo_layered_task_expansion.py
tests/test_layered_expander.py
```

Expected output files:

```text
results/layered_expansion/layered_task_summary.csv
results/layered_expansion/execution_phase_summary.csv
results/layered_expansion/layered_task_summary.md
```

Key observations:
- BIST expands into access, trigger, local run, re-access, and readback phases.
- `LOCAL_BIST_RUN` uses `uses_ptap=False`, so future phase schedulers can overlap local BIST execution with other die access phases.
- Internal scan expands into config, FPP shift-in, capture, FPP shift-out, and optional readback.
- DWR EXTEST expands into wrapper config, DWR shift-in, capture, and shift-out.
- Instrument access remains a simplified network access model with future room for SIB hierarchical or daisy-chain timing.

Result:
B2 layered expansion implementation and tests passed. `run_case_4die.py` also passed. `demo_layered_task_expansion.py` could not create `results/layered_expansion/` because the current sandbox denied write access to that results path. `demo_access_path_generation.py` and `run_example_benchmark_workload.py` were also blocked by write permission errors in existing results paths.

Test result:
pytest: 81 passed, 1 warning

## Design/Prototype Note 022: B2.5 Output Path Robustness Fix

Date:
2026-05-17

Commit:
TBD

Type:
Engineering robustness note.

Commands:

```bash
pytest
python experiments/demo_access_path_generation.py --output-dir tmp_access_path_out
python experiments/demo_layered_task_expansion.py --output-dir tmp_layered_out
python experiments/run_example_benchmark_workload.py --output-dir tmp_benchmark_out
```

Purpose:
Make B1/B2 demo scripts and the example benchmark runner write to configurable output directories so tests and sandboxed runs do not depend on fixed `results/` subdirectories being writable.

Files updated:

```text
experiments/demo_access_path_generation.py
experiments/demo_layered_task_expansion.py
experiments/run_example_benchmark_workload.py
tests/test_access_path_generator.py
tests/test_benchmark_adapter.py
README.md
STATUS.md
TODO.md
DECISIONS.md
EXPERIMENT_LOG.md
```

Behavior:
- `demo_access_path_generation.py` supports `--output-dir`, defaulting to `results/access_path/`.
- `demo_layered_task_expansion.py` supports `--output-dir`, defaulting to `results/layered_expansion/`.
- `run_example_benchmark_workload.py` supports `--output-dir`, defaulting to `results/benchmarks/example/`.
- Missing output directories are created automatically.
- Directory creation failures raise a clear error that includes the target path.
- Tests use pytest `tmp_path` for generated outputs.

Temporary output files generated:

```text
tmp_access_path_out/access_path_summary.csv
tmp_access_path_out/access_path_summary.md
tmp_layered_out/layered_task_summary.csv
tmp_layered_out/execution_phase_summary.csv
tmp_layered_out/layered_task_summary.md
tmp_benchmark_out/benchmark_task_summary.csv
tmp_benchmark_out/scheduler_metrics_summary.csv
tmp_benchmark_out/serial_schedule.csv
tmp_benchmark_out/greedy_schedule.csv
tmp_benchmark_out/ptv_schedule.csv
```

Additional benchmark plots were also generated under `tmp_benchmark_out/`.

Result:
Passed. The configurable output directory path works for all three scripts in the current sandbox.

Test result:
pytest: 81 passed, 1 warning

Notes:
This task did not modify scheduler core algorithms, the unified evaluator, AccessPath generation logic, or LayeredTask expansion logic. The warning remains the known `.pytest_cache` permission warning.

## Design/Prototype Note 023: B3.1 ExecutionPhase-Level Access-Time-Aware Scheduler

Date:
2026-05-17

Commit:
TBD

Type:
Design/prototype note.

Commands:

```bash
pytest tests/test_layered_scheduler.py
pytest
python experiments/demo_access_time_scheduler.py --output-dir tmp_access_time_scheduler_out
```

Purpose:
Implement the first B3 ExecutionPhase-level scheduler prototype without modifying existing A0 task-level schedulers, evaluator modules, AccessPath logic, or B2 layered expansion logic.

Files added:

```text
src/layered/scheduler.py
tests/test_layered_scheduler.py
experiments/demo_access_time_scheduler.py
```

Files updated:

```text
src/layered/__init__.py
STATUS.md
TODO.md
DECISIONS.md
EXPERIMENT_LOG.md
```

Implemented behavior:
- `ScheduledPhase` stores one `ExecutionPhase` with `start_time` and `end_time`.
- `LayeredScheduleResult` stores scheduled phases, total time, residual resource conflicts, and dependency violations.
- `AccessTimeAwareScheduler` implements deterministic earliest-start list scheduling.
- Stable input order is preserved when multiple phases can start at the same time.
- A phase can start only after all dependency phase IDs have completed.
- Missing dependency IDs raise `ValueError` with the missing ID.
- `uses_ptap=True` occupies a global PTAP resource.
- `uses_fpp=True` occupies FPP lane capacity using `phase.fpp_lanes`, defaulting to one lane when absent.
- `uses_dwr=True` occupies the named DWR segment, or a global DWR resource if no segment is provided.
- `is_capture_phase=True` occupies a global CAPTURE resource when `capture_exclusive=True`.
- `is_local_execution=True` does not automatically occupy PTAP.

Demo outputs:

```text
tmp_access_time_scheduler_out/phase_schedule.csv
tmp_access_time_scheduler_out/phase_schedule.md
```

Key validation observations:
- Pure dependency chains schedule serially.
- Independent local execution phases can overlap.
- PTAP phases serialize.
- BIST local execution can overlap with another PTAP config phase when `uses_ptap=False`.
- FPP lane capacity is respected.
- DWR conflicts are segment-specific.
- Result `total_time` equals the maximum scheduled phase end time.

Result:
Passed.

Test result:
`pytest tests/test_layered_scheduler.py`: 8 passed, 1 warning.
`pytest`: 89 passed, 1 warning.

Notes:
B3.1 is a first ExecutionPhase-level access-time-aware scheduling prototype. It is not predictive physical-aware scheduling, does not integrate thermal or voltage prediction, and is not a complete IEEE 1838 framework. Phase-level thermal / voltage prediction integration remains future B3.2/B3.3 work.
