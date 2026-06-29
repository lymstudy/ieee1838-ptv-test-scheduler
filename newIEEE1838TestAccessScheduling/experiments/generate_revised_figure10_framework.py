from __future__ import annotations

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
import numpy as np

FIGURE_DIR = "results/figures/revised"
FIGURE_PATH = "results/figures/revised/fig10_framework_overview.png"

# ---------------------------------------------------------------------------
# Colour palette – one colour per major block
# ---------------------------------------------------------------------------
COLORS = {
    "input":       "#d5d5d5",   # light gray
    "m1_model":    "#4e79a7",   # blue
    "m2m3_recipe": "#59a14f",   # green
    "m4m6_sched":  "#f28e2b",   # orange
    "m7m12_eval":  "#8d62c8",   # purple
    "arrow":       "#555555",
    "online_tag":  "#d62728",
    "offline_tag": "#888888",
    "lit_tag":     "#7f7f7f",
    "box_edge":    "#444444",
    "text_dark":   "#222222",
    "text_light":  "#ffffff",
}

# Title abbreviations and corresponding full labels
BLOCK_LABELS = {
    "input":    "INPUT:\nTest Case Definition",
    "m1":       "M1: IEEE 1838\nComputable System Model",
    "m2m3":     "M2–M3: Test Access Recipe\nGeneration + Pareto Pruning",
    "m4m6":     "M4–M6: Constraint-Based\nScheduling",
    "m7m12b":   "M7–M12b: Evaluation\n& Validation",
}

# Badges per block
BADGES = {
    "input":    [],
    "m1":       ["Offline"],
    "m2m3":     ["Offline"],
    "m4m6":     ["Online"],
    "m7m12b":   ["Offline (post-hoc)", "Online (M7 in-loop)"],
}

# Literature annotations
LIT_ANNOTATIONS = {
    "m2m3":   "cf. Patmanathan 2024\n(Pareto cubes)",
    "m4m6":   "cf. Habiby 2022\n(PBO)",
}


def _draw_rounded_box(ax, x0, y0, w, h, facecolor, edgecolor, linewidth=1.5,
                      radius=0.18, zorder=0.5):
    """Draw a rounded-rectangle using FancyBboxPatch."""
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
    """Draw a simple downward arrow."""
    ax.annotate(
        "", xy=(x1, y1), xytext=(x0, y0),
        arrowprops=dict(
            arrowstyle="->", color=color, lw=lw,
            connectionstyle="arc3,rad=0",
        ),
    )


def _badge(ax, x, y, text, is_online=False):
    """Add a small rounded tag / badge."""
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
    """Literature reference callout in small italic gray."""
    ax.text(
        x, y, text,
        fontsize=5.5, style="italic", color=COLORS["lit_tag"],
        ha="left", va="top",
        bbox=dict(
            boxstyle="round,pad=0.2",
            facecolor="#f8f8f8",
            edgecolor="#cccccc",
            alpha=0.85,
        ),
    )


def _block_header(ax, x0, y0, w, h, color, title, body_lines, badge_specs,
                  lit_text=None):
    """
    Draw one major pipeline block.
    - title: title string inside the block
    - body_lines: list of bullet strings
    - badge_specs: list of (text, is_online)
    - lit_text: optional literature callout text
    """
    _draw_rounded_box(ax, x0, y0, w, h, color, COLORS["box_edge"], radius=0.25)

    # Determine text colour based on background luminance
    text_color = COLORS["text_light"] if color not in (COLORS["input"],) else COLORS["text_dark"]

    # Title – bold, inside the box, top-left
    ax.text(
        x0 + 0.2, y0 + h - 0.28, title,
        fontsize=9, fontweight="bold", color=text_color,
        ha="left", va="top",
    )

    # Body lines – smaller font, below title
    y_cursor = y0 + h - 0.55
    for line in body_lines:
        ax.text(
            x0 + 0.28, y_cursor, line,
            fontsize=6.2, color=text_color, ha="left", va="top",
        )
        y_cursor -= 0.20

    # Badges – top-right corner of the block
    badge_x = x0 + w - 1.1
    badge_y = y0 + h - 0.20
    for idx, (btext, is_online) in enumerate(badge_specs):
        _badge(ax, badge_x, badge_y - idx * 0.22, btext, is_online=is_online)

    # Literature annotation
    if lit_text:
        _lit_callout(ax, x0 + w + 0.15, y0 + h - 0.05, lit_text)


def build_figure():
    """Build Figure 10 – Method Overview Framework Diagram."""

    configure_matplotlib()

    # Figure dimensions
    fig, ax = plt.subplots(figsize=(15, 10))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 12.5)
    ax.axis("off")

    # -----------------------------------------------------------------------
    # Block geometry: (x, y, w, h) – stacked vertically, centred
    # -----------------------------------------------------------------------
    box_w = 11.0
    box_x = (14 - box_w) / 2  # centred in 14-wide canvas
    arrow_h = 0.30

    blocks = []
    y = 10.6

    # --- INPUT ---
    h_input = 1.15
    y -= h_input
    blocks.append(("input", box_x, y, box_w, h_input))
    y -= arrow_h

    # --- M1 ---
    h_m1 = 2.0
    y -= h_m1
    blocks.append(("m1", box_x, y, box_w, h_m1))
    y -= arrow_h

    # --- M2-M3 ---
    h_m2m3 = 2.0
    y -= h_m2m3
    blocks.append(("m2m3", box_x, y, box_w, h_m2m3))
    y -= arrow_h

    # --- M4-M6 ---
    h_m4m6 = 2.3
    y -= h_m4m6
    blocks.append(("m4m6", box_x, y, box_w, h_m4m6))
    y -= arrow_h

    # --- M7-M12b ---
    h_m7m12b = 2.0
    y -= h_m7m12b
    blocks.append(("m7m12b", box_x, y, box_w, h_m7m12b))

    # -----------------------------------------------------------------------
    # Block content definitions
    # -----------------------------------------------------------------------
    content = {
        "input": {
            "title": BLOCK_LABELS["input"],
            "body": [
                "ITC’02 SoC Benchmarks  (d695, p22810, p34392, p93791)",
                "IEEE 1838 Die Stack Topology  (2.5D Interposer / 3D Stack / 5.5D Multi-tower)",
            ],
            "badges": BADGES["input"],
        },
        "m1": {
            "title": BLOCK_LABELS["m1"],
            "body": [
                "PTAP / STAP serial chain,  DWR segments,  BIST engines,  FPP channels",
                "Resource limits,  power profiles,  thermal RC parameters",
                "Output:  SystemModel JSON",
            ],
            "badges": BADGES["m1"],
        },
        "m2m3": {
            "title": BLOCK_LABELS["m2m3"],
            "body": [
                "S (serial),  B (BIST),  F (FPP),  H (hybrid),  I (interconnect) recipes",
                "Each recipe:  phase-level resource signature + timing",
                "7-dimension Pareto dominance pruning",
                "Output:  RecipeRow list  (∼50–200 candidate recipes per case)",
            ],
            "badges": BADGES["m2m3"],
            "lit": LIT_ANNOTATIONS["m2m3"],
        },
        "m4m6": {
            "title": BLOCK_LABELS["m4m6"],
            "body": [
                "M4:  Thermal-risk-first greedy scheduler  (baseline)",
                "M5:  CP-SAT constraint programming  (OR-Tools)  — exact / feasible solver",
                "M6:  ALNS metaheuristic  (extension prototype)",
                "Constraints:  serial TAP (NoOverlap),  FPP lanes (Cumulative),",
                "              DWR conflict groups,  BIST engines,  power,  thermal",
                "Output:  ScheduledPhase list  +  makespan",
            ],
            "badges": BADGES["m4m6"],
            "lit": LIT_ANNOTATIONS["m4m6"],
        },
        "m7m12b": {
            "title": BLOCK_LABELS["m7m12b"],
            "body": [
                "M7:   First-order RC thermal proxy  (fast, in-loop)",
                "M8:   Multi-baseline comparison  (serial, fixed-path, TAM-like, etc.)",
                "M12b: HotSpot 6.0 offline thermal validation  (representative subset)",
                "Output:  comparison tables  +  thermal validation report",
            ],
            "badges": BADGES["m7m12b"],
        },
    }

    # -----------------------------------------------------------------------
    # Draw blocks and arrows
    # -----------------------------------------------------------------------
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
        _block_header(
            ax, bx, by, bw, bh,
            color=color_key[bid],
            title=info["title"],
            body_lines=info["body"],
            badge_specs=[(b, ("Online" in b and "Offline" not in b)) for b in info["badges"]],
            lit_text=lit,
        )
        # Draw arrow from bottom of this block to top of the next block
        if i < len(blocks) - 1:
            _, next_bx, next_by, _, next_bh = blocks[i + 1]
            arrow_x = 14 / 2
            _draw_arrow(ax, arrow_x, by, arrow_x, next_by + next_bh,
                        color=COLORS["arrow"], lw=2.8)

    # -----------------------------------------------------------------------
    # Bottom annotation (FPP clause note)
    # -----------------------------------------------------------------------
    ax.text(
        14 / 2, 0.15,
        "FPP is an optional component defined in IEEE 1838-2019 Clause 7",
        fontsize=8, style="italic", color=COLORS["lit_tag"],
        ha="center", va="bottom",
    )

    # -----------------------------------------------------------------------
    # Title
    # -----------------------------------------------------------------------
    fig.suptitle(
        "Fig. 10  Method Overview — Test Access Scheduling Framework",
        y=0.995, fontsize=17, fontweight="bold",
    )

    # -----------------------------------------------------------------------
    # Legend for colour coding (bottom-right)
    # -----------------------------------------------------------------------
    legend_items = [
        ("Input",        COLORS["input"]),
        ("M1  Model",    COLORS["m1_model"]),
        ("M2–M3  Recipe",  COLORS["m2m3_recipe"]),
        ("M4–M6  Scheduling", COLORS["m4m6_sched"]),
        ("M7–M12b  Evaluation", COLORS["m7m12_eval"]),
    ]
    legend_y = 2.0
    legend_x = box_x + box_w - 3.2
    for j, (lbl, clr) in enumerate(legend_items):
        ly = legend_y - j * 0.35
        _draw_rounded_box(
            ax, legend_x, ly, 0.35, 0.20,
            facecolor=clr, edgecolor=COLORS["box_edge"],
            linewidth=0.8, radius=0.08, zorder=0.6,
        )
        ax.text(
            legend_x + 0.45, ly + 0.10, lbl,
            fontsize=7, color=COLORS["text_dark"], ha="left", va="center",
        )

    # Badge legend
    badge_lg_y = legend_y - len(legend_items) * 0.35 - 0.4
    _badge(ax, legend_x, badge_lg_y, "Online", is_online=True)
    ax.text(legend_x + 0.7, badge_lg_y + 0.09,
            "Online (in scheduler loop)", fontsize=6.5, color=COLORS["text_dark"],
            ha="left", va="center")
    _badge(ax, legend_x, badge_lg_y - 0.28, "Offline", is_online=False)
    ax.text(legend_x + 0.7, badge_lg_y - 0.28 + 0.09,
            "Offline (post-hoc validation)", fontsize=6.5, color=COLORS["text_dark"],
            ha="left", va="center")

    fig.tight_layout(rect=[0, 0.02, 1, 0.97])

    return fig


def configure_matplotlib():
    available = {font.name for font in fm.fontManager.ttflist}
    # Prefer DejaVu Sans for broad glyph coverage (tildes, unicode symbols)
    candidates = ["DejaVu Sans", "Arial Unicode MS",
                  "Microsoft YaHei", "SimHei", "Noto Sans CJK SC"]
    chosen = next((font for font in candidates if font in available), "sans-serif")
    plt.rcParams.update({
        "font.family": chosen,
        "axes.unicode_minus": False,
    })


def main():
    figure_dir = PROJECT_ROOT / FIGURE_DIR
    figure_dir.mkdir(parents=True, exist_ok=True)

    fig = build_figure()

    output_path = PROJECT_ROOT / FIGURE_PATH
    fig.savefig(output_path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Figure saved to: {output_path}")


if __name__ == "__main__":
    main()
