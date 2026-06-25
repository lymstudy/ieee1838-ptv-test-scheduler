from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.generate_m14_experiment_chapter import read_csv, summarize_m10, summarize_m11, summarize_m12b


CAPTION_FIELDS = ["artifact_id", "artifact_type", "path", "caption", "paper_usage"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a Chinese experiment chapter draft from M10-M14 artifacts.")
    parser.add_argument("--m10-table", default="results/tables/m10_benchmark_sweep.csv")
    parser.add_argument("--m11-table", default="results/tables/m11_algorithm_comparison.csv")
    parser.add_argument("--m12b-table", default="results/tables/m12_hotspot_validation_summary.csv")
    parser.add_argument("--m13-index", default="results/tables/m13_figure_index.csv")
    parser.add_argument("--m16-index", default="results/tables/m16_figure_index.csv")
    parser.add_argument("--output", default="results/reports/m15_chinese_experiment_chapter_draft.md")
    parser.add_argument("--caption-output", default="results/tables/m15_caption_index.csv")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    m10 = summarize_m10(read_csv(Path(args.m10_table)))
    m11 = summarize_m11(read_csv(Path(args.m11_table)))
    m12b = summarize_m12b(read_csv(Path(args.m12b_table)))
    figure_index = Path(args.m16_index) if Path(args.m16_index).exists() else Path(args.m13_index)
    figure_rows = read_csv(figure_index)

    captions = build_caption_rows(figure_rows)
    write_chinese_chapter(Path(args.output), m10, m11, m12b, captions)
    write_caption_index(Path(args.caption_output), captions)
    print(f"output={args.output}")
    print(f"caption_output={args.caption_output}")


def build_caption_rows(figure_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    caption_by_id = {
        "m13_m10_speedup_nominal_lane8": (
            "图 1 不同规模与拓扑场景下 M4 贪心调度相对于纯串行 IEEE 1838 访问的加速比",
            "用于说明 benchmark 覆盖的规模变化和拓扑变化下，方法仍能带来稳定测试时间收益。",
        ),
        "m13_m11_algorithm_makespan": (
            "图 2 不同调度方法的平均归一化测试完成时间对比",
            "用于说明 M4/M5 方法相对于纯串行、固定最快路径和 TAM-like 基线的整体表现。",
        ),
        "m13_m12b_proxy_hotspot_peak_comparison": (
            "图 3 热代理模型与 HotSpot 离线验证得到的峰值温度对比",
            "用于说明热代理与 HotSpot 的趋势关系，避免声称二者数值完全等价。",
        ),
        "m13_hotspot_trace_heatmap_medium_3d_m4_greedy": (
            "图 4 中等规模 3D stack 场景下 M4 贪心调度的 HotSpot block-level 温度热图",
            "用于展示代表性调度结果中的热点位置和温度随时间变化趋势。",
        ),
        "m13_representative_m4_greedy_gantt": (
            "图 5 代表性 M4 贪心调度结果的甘特图",
            "用于说明生成的测试任务在时间轴上的排布方式以及并行访问效果。",
        ),
        "m16_ieee1838_resource_gantt_xlarge": (
            "图 1 xlarge 5.5D 场景下 IEEE 1838-aware 测试调度资源层甘特图",
            "用于展示 PTAP/STAP、FPP lane、DWR/scan 和目标测试事务在正式大规模 case 中的资源占用关系。",
        ),
        "m16_power_temperature_hotspot_composite": (
            "图 2 功耗曲线、温度曲线与 HotSpot 热点分布综合图",
            "用于展示调度方法对系统功耗、热代理温度趋势和 HotSpot block-level 热点分布的影响。",
        ),
        "m16_method_comparison_normalized": (
            "图 3 不同调度方法的多指标归一化对比",
            "用于说明测试时间收益、功耗/温度代价和 FPP 利用之间的权衡关系。",
        ),
        "m16_benchmark_coverage_matrix": (
            "图 4 benchmark 规模与拓扑覆盖矩阵",
            "用于直接说明正式实验覆盖 4/6/8/12 die、三类封装拓扑、目标数和 recipe 数，而不是早期小示例。",
        ),
    }
    rows = []
    for figure in figure_rows:
        caption, usage = caption_by_id.get(
            figure["figure_id"],
            (figure.get("title", figure["figure_id"]), figure.get("notes", "")),
        )
        rows.append(
            {
                "artifact_id": figure["figure_id"],
                "artifact_type": "figure",
                "path": figure["path"],
                "caption": caption,
                "paper_usage": usage,
            }
        )
    rows.extend(
        [
            {
                "artifact_id": "m10_benchmark_sweep",
                "artifact_type": "table",
                "path": "results/tables/m10_benchmark_sweep.csv",
                "caption": "表 1 M10 benchmark suite 的规模、拓扑和资源敏感性实验结果",
                "paper_usage": "用于支撑大规模覆盖实验和 M4 贪心调度的加速比分析。",
            },
            {
                "artifact_id": "m11_algorithm_comparison",
                "artifact_type": "table",
                "path": "results/tables/m11_algorithm_comparison.csv",
                "caption": "表 2 M11 不同基线与本文方法的调度结果对比",
                "paper_usage": "用于支撑算法对比和消融实验叙述。",
            },
            {
                "artifact_id": "m12b_hotspot_validation",
                "artifact_type": "table",
                "path": "results/tables/m12_hotspot_validation_summary.csv",
                "caption": "表 3 M12b 代表性调度结果的 HotSpot 离线验证结果",
                "paper_usage": "用于支撑热代理趋势验证和热模型局限性讨论。",
            },
        ]
    )
    return rows


def write_chinese_chapter(output_path: Path, m10: dict[str, Any], m11: dict[str, Any], m12b: dict[str, Any], captions: list[dict[str, str]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# M15 中文实验章节初稿",
        "",
        "## 1 实验设置",
        "",
        "本文实验基于前述 IEEE 1838 可计算模型和 Test Access Recipe 生成方法展开。实验目标不是仅验证单个手写示例，而是考察所提出的测试访问路径生成与协同调度方法在不同规模、不同先进封装拓扑以及不同调度策略下的表现。",
        f"M10 benchmark suite 共包含 {m10['case_count']} 个测试场景，覆盖 {len(m10['workloads'])} 个 ITC'02 派生 workload（{', '.join(m10['workloads'])}）、{len(m10['scales'])} 个规模等级（{', '.join(m10['scales'])}）以及 {len(m10['topologies'])} 类封装拓扑（{', '.join(m10['topologies'])}）。",
        f"M10 共生成 {m10['total_rows']} 行调度实验结果，其中 {m10['ok_rows']} 行成功得到合法调度。",
        "",
        f"在算法对比方面，M11 选取小规模和中等规模代表性场景，对 {m11['method_count']} 类方法进行比较，共得到 {m11['ok_rows']} 行成功结果，占全部 {m11['total_rows']} 行实验的主要部分。",
        "这些方法包括纯串行访问、固定最快路径、TAM-like 基线、低功耗优先策略、M4 贪心调度、M5 CP-SAT 精修以及受规模限制的 M6 ALNS 外层搜索。",
        "",
        f"热验证方面，M12b 对 {m12b['case_count']} 个代表性场景执行 HotSpot 离线验证，共得到 {m12b['ok_rows']} 行成功 HotSpot 输出。HotSpot 在本文中作为离线代表性验证工具使用，不嵌入主调度闭环。",
        "",
        "## 2 规模与拓扑覆盖实验",
        "",
        "M10 实验用于说明本文方法并不依赖某一个固定 3D stack 示例，而是可以迁移到 2.5D interposer、3D stack 和 5.5D multi-tower 三类结构。",
        f"在 nominal 功耗配置和 8 条 FPP lane 的设置下，M4 贪心调度相对于纯串行 IEEE 1838 访问的平均加速比为 {m10['nominal_lane8_avg_speedup']:.2f}x，平均归一化完成时间为 {m10['nominal_lane8_avg_norm']:.4f}。",
        "这一结果说明，在显式考虑串行访问、FPP lane、DWR segment 和功耗约束后，路径选择与调度协同仍然能够显著缩短测试完成时间。",
        "",
        "| 拓扑类型 | M4 结果行数 | 平均归一化完成时间 | 平均加速比 |",
        "| --- | ---: | ---: | ---: |",
    ]
    for stat in m10["topology_stats"]:
        lines.append(f"| {stat['topology']} | {stat['rows']} | {stat['avg_norm']:.4f} | {stat['avg_speedup']:.2f} |")

    lines.extend(["", "各规模下 M4 的最佳结果如下：", "", "| 规模 | 场景 | FPP lane 数 | 功耗配置 | 归一化完成时间 | 加速比 |", "| --- | --- | ---: | --- | ---: | ---: |"])
    for row in m10["best_by_scale"]:
        lines.append(
            f"| {row['scale']} | {row['case_id']} | {row['lane_count']} | {row['power_profile']} | "
            f"{float(row['normalized_makespan']):.4f} | {float(row['speedup_vs_serial']):.2f} |"
        )

    lines.extend(
        [
            "",
            "## 3 算法对比与消融分析",
            "",
            "M11 实验进一步比较不同调度策略的影响。纯串行方法保留 IEEE 1838 串行访问路径，但无法利用 FPP 和 BIST 并行性，因此作为最保守基线。固定最快路径和 TAM-like 方法能够降低测试时间，但它们弱化了 IEEE 1838 访问层级、配置开销和资源互斥的表达。本文的 M4/M5 方法在保留这些约束的同时进行 recipe 选择和时隙安排。",
            "",
            "| 方法 | 类型 | 成功行数 | 平均归一化完成时间 | 平均加速比 |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
    )
    for stat in m11["method_stats"]:
        lines.append(f"| {stat['method']} | {stat['family']} | {stat['rows']} | {stat['avg_norm']:.4f} | {stat['avg_speedup']:.2f} |")

    lines.extend(
        [
            "",
            "从结果看，M5 CP-SAT 精修在当前代表性场景中取得最低平均归一化完成时间。需要注意的是，CP-SAT 输出为满足约束的可行调度；除非求解器状态明确给出最优性证明，否则不应在论文中表述为全局最优。",
            "M6 ALNS 当前只在目标数不超过阈值的场景中运行，这是为了避免将算法对比实验变成不可控的长时间搜索。该部分更适合作为中大规模搜索框架的原型证据，而不是最终性能上界。",
            "",
            "## 4 热代理与 HotSpot 离线验证",
            "",
            "调度器内部使用快速热代理模型评估不同 recipe 和时隙安排的热风险。该模型适合在大量候选方案上快速比较趋势，但不应被描述为完整热仿真工具。",
            "为避免热结论只依赖代理模型，M12b 将代表性调度结果导出为 HotSpot 可读的 `.flp/.ptrace` 输入，并在 Linux/EDA VM 上执行离线 HotSpot 验证。",
            f"当前 HotSpot 峰值温度范围为 {m12b['hotspot_min']:.2f} C 到 {m12b['hotspot_max']:.2f} C。代理模型选出的最佳调度与 HotSpot 峰值温度排序在 {m12b['ranking_match_count']} / {len(m12b['ranking_matches'])} 个代表性场景中一致。",
            "",
            "| 场景 | 代理模型最佳调度 | HotSpot 最佳调度 | 排序是否一致 |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in m12b["ranking_matches"]:
        lines.append(f"| {item['case_id']} | {item['proxy_best']} | {item['hotspot_best']} | {item['match']} |")

    lines.extend(
        [
            "",
            "上述结果支持将热代理模型用于调度过程中的趋势引导，但不能说明代理模型与 HotSpot 在数值上完全等价。当前 HotSpot 输入仍是简化 block-level floorplan，因此论文中应将其表述为代表性离线验证，而不是工业级 signoff 热分析。",
            "",
            "## 5 图表安排",
            "",
            "本阶段整理的图表可以按以下方式放入论文实验章节：",
            "",
            "| 图表编号 | 建议标题 | 用途 |",
            "| --- | --- | --- |",
        ]
    )
    for row in captions:
        lines.append(f"| {row['artifact_id']} | {row['caption']} | {row['paper_usage']} |")

    lines.extend(
        [
            "",
            "## 6 局限性",
            "",
            "第一，benchmark workload 来自公开 ITC'02 信息并经过封装结构映射，仍然属于研究原型级输入，而不是某一真实工业芯片的完整 DFT 数据。",
            "第二，M10 用于覆盖规模和拓扑敏感性，因此只选择了少数方法进行大范围 sweep；更丰富的算法比较集中在 M11。",
            "第三，M11 当前主要覆盖 small 和 medium 场景，large/xlarge 场景下的 CP-SAT/ALNS 全量对比仍可作为后续补充。",
            "第四，HotSpot 验证只覆盖代表性 case，不应夸大为完整工业 3D 热仿真流程。",
            "",
            "## 7 本章小结",
            "",
            "实验结果表明，基于 Test Access Recipe 的 IEEE 1838-aware 路径生成与调度方法能够在保持访问路径和资源约束显式建模的同时，显著降低整体测试完成时间。",
            "M10 证明了该方法在 2.5D、3D 和 5.5D 场景中的可扩展性；M11 进一步说明 M4/M5 调度框架相对于纯串行和固定路径基线具有竞争力；M12b 则通过代表性 HotSpot 离线验证补充了热代理模型的可信度边界。",
            "因此，本文方法的主要价值不在于单一启发式规则，而在于将 IEEE 1838 访问路径生成、资源约束调度和电热风险评估组织到同一套可计算实验框架中。",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_caption_index(output_path: Path, rows: list[dict[str, str]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CAPTION_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
