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
