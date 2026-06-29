from __future__ import annotations

"""Figure 10 - Framework Overview (corrected v4 model).

Updated for the corrected IEEE 1838 model:
  - Two transport resources: TAP (mandatory, every die) and FPP (optional, Clause 7, some dies)
  - Task types: INTEST, EXTEST, BIST, IJTAG (all mandatory, all equal)
  - BIST is NOT a transport alternative -- it's a task with low transport overhead
  - Scheduling is about TAP time-multiplexing + FPP data offload + thermal constraints

Output: results/figures/v4_final/fig10_framework.png
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

OUTPUT_DIR = "results/figures/v4_final"
OUTPUT_PATH = "results/figures/v4_final/fig10_framework.png"

# Colour palette
COLORS = {
    "input":        "#d5d5d5",
    "m1_model":     "#4e79a7",
    "m2m3_recipe":  "#59a14f",
    "m4m6_sched":   "#f28e2b",
    "m7m12_eval":   "#8d62c8",
    "arrow":        "#555555",
    "online_tag":   "#d62728",
    "offline_tag":  "#888888",
    "lit_tag":      "#7f7f7f",
    "box_edge":     "#444444",
    "text_dark":    "#222222",
    "text_light":   "#ffffff",
    "tap_color":    "#1f77b4",
    "fpp_color":    "#ff7f0e",
    "bist_color":   "#2ca02c",
}

BLOCK_LABELS = {
    "input":    "INPUT:\nTest Case Definition",
    "m1":       "M1: IEEE 1838\nComputable System Model",
    "m2m3":     "M2-M3: Task-Based Recipe\nGeneration + Pareto Pruning",
    "m4m6":     "M4-M6: Constraint-Based\nJoint Scheduling",
    "m7m12b":   "M7-M12b: Evaluation\n& Validation",
}

BADGES = {
    "input":    [],
    "m1":       ["Offline"],
    "m2m3":     ["Offline"],
    "m4m6":     ["Online"],
    "m7m12b":   ["Offline (post-hoc)", "Online (M7 in-loop)"],
}

LIT_ANNOTATIONS = {
    "m2m3":   "cf. Patmanathan 2024\n(Pareto cubes)",
    "m4m6":   "cf. Habiby 2022\n(PBO)",
}


def _draw_rounded_box(ax, x0, y0, w, h, facecolor, edgecolor, linewidth=1.5,
                      radius=0.18, zorder=0.5):
    box = mpatches.FancyBboxPatch(
        (x0, y0), w, h,
        boxstyle=mpatches.BoxStyle("Round", pad=radius),
        facecolor=facecolor,
        edgecolor=edgecolor,
        linewidth=linewidth,
        zorder=zorder,
    )
    ax.add_patch(box)


def _draw_arrow(ax, x0, y0, x1, y1, color=COLORS["arrow"], lw=2.5):
    ax.annotate(
        "", xy=(x1, y1), xytext=(x0, y0),
        arrowprops=dict(arrowstyle="->", color=color, lw=lw,
                       connectionstyle="arc3,rad=0"),
    )


def _badge(ax, x, y, text, is_online=False):
    tag_color = COLORS["online_tag"] if is_online else COLORS["offline_tag"]
    box = mpatches.FancyBboxPatch(
        (x, y), len(text) * 0.09 + 0.18, 0.18,
        boxstyle=mpatches.BoxStyle("Round", pad=0.06),
        facecolor=tag_color,
        edgecolor="none",
        alpha=0.85,
        zorder=1.5,
    )
    ax.add_patch(box)
    ax.text(
        x + (len(text) * 0.09 + 0.18) / 2, y + 0.09,
        text, ha="center", va="center", fontsize=5.5, fontweight="bold",
        color="white",
    )


def _lit_callout(ax, x, y, text):
    ax.text(
        x, y, text,
        fontsize=5.5, style="italic", color=COLORS["lit_tag"],
        ha="left", va="top",
        bbox=dict(boxstyle="round,pad=0.2", facecolor="#f8f8f8",
                  edgecolor="#cccccc", alpha=0.85),
    )


def _block_header(ax, x0, y0, w, h, color, title, body_lines, badge_specs,
                  lit_text=None):
    _draw_rounded_box(ax, x0, y0, w, h, color, COLORS["box_edge"], radius=0.25)
    text_color = COLORS["text_light"] if color not in (COLORS["input"],) else COLORS["text_dark"]

    ax.text(x0 + 0.2, y0 + h - 0.28, title, fontsize=9, fontweight="bold",
            color=text_color, ha="left", va="top")

    y_cursor = y0 + h - 0.55
    for line in body_lines:
        ax.text(x0 + 0.28, y_cursor, line, fontsize=6.2, color=text_color,
                ha="left", va="top")
        y_cursor -= 0.20

    badge_x = x0 + w - 1.1
    badge_y = y0 + h - 0.20
    for idx, (btext, is_online) in enumerate(badge_specs):
        _badge(ax, badge_x, badge_y - idx * 0.22, btext, is_online=is_online)

    if lit_text:
        _lit_callout(ax, x0 + w + 0.15, y0 + h - 0.05, lit_text)


def _draw_resource_legend(ax, x, y, w, h):
    """Draw a small resource legend showing TAP/FPP/BIST in the M4-M6 block area."""
    items = [
        ("TAP (serial, mandatory)", COLORS["tap_color"]),
        ("FPP (parallel, optional)", COLORS["fpp_color"]),
        ("BIST engine (per-die)", COLORS["bist_color"]),
    ]
    ax.text(x + w / 2, y + h + 0.15, "Resources:", fontsize=6.5, fontweight="bold",
            color="#333333", ha="center")
    for i, (label, clr) in enumerate(items):
        iy = y + h - 0.25 - i * 0.25
        ax.add_patch(mpatches.Rectangle((x + 0.1, iy), 0.3, 0.15, facecolor=clr,
                                         edgecolor="#666666", linewidth=0.5))
        ax.text(x + 0.5, iy + 0.075, label, fontsize=5.5, color="#333333",
                ha="left", va="center")


def _draw_clause7_note(ax, x, y, w):
    """Add Clause 7 FPP note."""
    ax.text(x + w / 2, y,
            "FPP is optional per IEEE 1838-2019 Clause 7. Not every die has FPP hardware.\n"
            "Our model: only some dies have FPP lanes; scheduling adapts to actual hardware availability.",
            fontsize=6.5, style="italic", color=COLORS["lit_tag"],
            ha="center", va="top",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#fff8e1",
                      edgecolor="#ffcc80", alpha=0.9))


def _draw_bist_note(ax, x, y, w):
    """Add BIST correction note."""
    ax.text(x + w / 2, y,
            "IMPORTANT: BIST is NOT a transport alternative. It is a task type with low TAP overhead.\n"
            "BIST runs locally on dedicated engines; TAP is only needed for config + result readout.\n"
            "Different dies' BIST engines can operate simultaneously while TAP serves other tasks.",
            fontsize=6.5, style="italic", color="#cc3333",
            ha="center", va="top",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#fff5f5",
                      edgecolor="#ef9a9a", alpha=0.9))


def build_figure():
    configure_matplotlib()

    fig, ax = plt.subplots(figsize=(16, 12))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 13.5)
    ax.axis("off")

    box_w = 11.0
    box_x = (14 - box_w) / 2
    arrow_h = 0.30

    blocks = []
    y = 12.0

    # --- INPUT ---
    h_input = 1.2
    y -= h_input
    blocks.append(("input", box_x, y, box_w, h_input))
    y -= arrow_h

    # --- M1 ---
    h_m1 = 2.2
    y -= h_m1
    blocks.append(("m1", box_x, y, box_w, h_m1))
    y -= arrow_h

    # --- M2-M3 ---
    h_m2m3 = 2.2
    y -= h_m2m3
    blocks.append(("m2m3", box_x, y, box_w, h_m2m3))
    y -= arrow_h

    # --- M4-M6 ---
    h_m4m6 = 2.8
    y -= h_m4m6
    blocks.append(("m4m6", box_x, y, box_w, h_m4m6))
    y -= arrow_h

    # --- M7-M12b ---
    h_m7m12b = 2.0
    y -= h_m7m12b
    blocks.append(("m7m12b", box_x, y, box_w, h_m7m12b))

    # Block content definitions -- UPDATED for v4 corrected model
    content = {
        "input": {
            "title": BLOCK_LABELS["input"],
            "body": [
                "ITC'02 SoC Benchmarks (d695, p22810, p34392, p93791)",
                "IEEE 1838 Die Stack Topology (2.5D / 3D / 5.5D)",
                "Per-die IEEE 1838 access resources (STAP, DWR, FPP hardware)",
            ],
            "badges": BADGES["input"],
        },
        "m1": {
            "title": BLOCK_LABELS["m1"],
            "body": [
                "PTAP master (on primary die) + N STAP slaves (per-die chain)",
                "TRANSPORT: TAP (mandatory, every die) + FPP (optional, Clause 7, selected dies)",
                "TASK TYPES: INTEST (scan), EXTEST (interconnect), BIST (memory/logic), IJTAG (instruments)",
                "ALL task types are mandatory, all treated equally in scheduling",
                "Per-die BIST engines: capacity=1, can run independently across dies",
                "Thermal RC model, power profiles, DWR conflict groups",
            ],
            "badges": BADGES["m1"],
        },
        "m2m3": {
            "title": BLOCK_LABELS["m2m3"],
            "body": [
                "Each test_object declares: mandatory test_types + transport_options",
                "Recipe generator produces phase-level (CONFIG + EXEC + READOUT) variants",
                "Phase: transport mode (TAP serial vs FPP parallel), data size, timing",
                "BIST phases: CONFIG (TAP) + EXEC_BIST (local, no TAP) + READOUT (TAP)",
                "7-dimension Pareto dominance pruning (time, power, energy, etc.)",
                "Output: RecipeRow list (~50-200 candidate recipes per task)",
            ],
            "badges": BADGES["m2m3"],
            "lit": LIT_ANNOTATIONS["m2m3"],
        },
        "m4m6": {
            "title": BLOCK_LABELS["m4m6"],
            "body": [
                "SCHEDULING = TAP time-multiplexing + FPP data offload + thermal constraints",
                "M4: Thermal-risk-first greedy scheduler (fast baseline, sequential assignment)",
                "M5: CP-SAT constraint programming (OR-Tools) -- exact/feasible solver",
                "M6: ALNS metaheuristic (large-scale extension prototype)",
                "",
                "CONSTRAINTS:",
                "  TAP: NoOverlap on serial path (one task uses TAP at a time)",
                "  FPP: Cumulative (lanes per channel), only dies with FPP hardware",
                "  BIST: per-engine capacity=1, engine released during local EXEC phase",
                "  Power: system peak power limit, per-die PDN",
                "  Thermal: RC proxy (M7 in-loop) avoiding concurrent high-power dies",
            ],
            "badges": BADGES["m4m6"],
            "lit": LIT_ANNOTATIONS["m4m6"],
        },
        "m7m12b": {
            "title": BLOCK_LABELS["m7m12b"],
            "body": [
                "M7:  First-order RC thermal proxy (fast, used in scheduler loop)",
                "M8:  Multi-baseline comparison (serial, fixed-fastest, TAM-like)",
                "M12b: HotSpot 6.0 offline thermal validation (representative subset)",
                "Output: comparison tables + thermal validation report + schedule visualizations",
            ],
            "badges": BADGES["m7m12b"],
        },
    }

    color_key = {
        "input":  COLORS["input"],
        "m1":     COLORS["m1_model"],
        "m2m3":   COLORS["m2m3_recipe"],
        "m4m6":   COLORS["m4m6_sched"],
        "m7m12b": COLORS["m7m12_eval"],
    }

    for i, (bid, bx, by, bw, bh) in enumerate(blocks):
        info = content[bid]
        lit = info.get("lit", None)
        _block_header(ax, bx, by, bw, bh, color=color_key[bid],
                      title=info["title"], body_lines=info["body"],
                      badge_specs=[(b, ("Online" in b and "Offline" not in b))
                                   for b in info["badges"]],
                      lit_text=lit)
        if i < len(blocks) - 1:
            _, next_bx, next_by, _, next_bh = blocks[i + 1]
            arrow_x = 14 / 2
            _draw_arrow(ax, arrow_x, by, arrow_x, next_by + next_bh,
                        color=COLORS["arrow"], lw=2.8)

    # Clause 7 note (bottom-left)
    _draw_clause7_note(ax, 0.5, 0.35, 6.0)

    # BIST correction note (bottom-center)
    _draw_bist_note(ax, 6.5, 0.35, 6.0)

    # Fig title
    fig.suptitle("Fig. 10  Method Overview -- IEEE 1838 Test Access Scheduling Framework (v4 Corrected Model)",
                 y=0.995, fontsize=17, fontweight="bold")

    # Legend
    legend_items = [
        ("Input",        COLORS["input"]),
        ("M1  Model",    COLORS["m1_model"]),
        ("M2-M3  Recipe", COLORS["m2m3_recipe"]),
        ("M4-M6  Scheduling", COLORS["m4m6_sched"]),
        ("M7-M12b  Evaluation", COLORS["m7m12_eval"]),
    ]
    legend_x = box_x + box_w - 3.5
    legend_y = 2.5
    for j, (lbl, clr) in enumerate(legend_items):
        ly = legend_y - j * 0.35
        _draw_rounded_box(ax, legend_x, ly, 0.35, 0.20, facecolor=clr,
                         edgecolor=COLORS["box_edge"], linewidth=0.8, radius=0.08)
        ax.text(legend_x + 0.45, ly + 0.10, lbl, fontsize=7,
                color=COLORS["text_dark"], ha="left", va="center")

    # Badge legend
    badge_lg_y = legend_y - len(legend_items) * 0.35 - 0.4
    _badge(ax, legend_x, badge_lg_y, "Online", is_online=True)
    ax.text(legend_x + 0.7, badge_lg_y + 0.09, "Online (in scheduler loop)",
            fontsize=6, color=COLORS["text_dark"], ha="left", va="center")
    _badge(ax, legend_x, badge_lg_y - 0.28, "Offline", is_online=False)
    ax.text(legend_x + 0.7, badge_lg_y - 0.28 + 0.09, "Offline (post-hoc validation)",
            fontsize=6, color=COLORS["text_dark"], ha="left", va="center")

    # Resource legend (transport resources label)
    ax.text(legend_x, badge_lg_y - 0.7, "Transport:\n  TAP (mandatory)\n  FPP (optional, Clause 7)",
            fontsize=6, color=COLORS["lit_tag"], ha="left", va="top", style="italic")

    fig.tight_layout(rect=[0, 0.02, 1, 0.97])
    return fig


def configure_matplotlib():
    available = {font.name for font in fm.fontManager.ttflist}
    candidates = ["DejaVu Sans", "Arial Unicode MS",
                  "Microsoft YaHei", "SimHei", "Noto Sans CJK SC"]
    chosen = next((font for font in candidates if font in available), "sans-serif")
    plt.rcParams.update({"font.family": chosen, "axes.unicode_minus": False})


def main():
    output_dir = PROJECT_ROOT / OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    fig = build_figure()

    output_path = PROJECT_ROOT / OUTPUT_PATH
    fig.savefig(output_path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Figure 10 saved to: {output_path}")


if __name__ == "__main__":
    main()
