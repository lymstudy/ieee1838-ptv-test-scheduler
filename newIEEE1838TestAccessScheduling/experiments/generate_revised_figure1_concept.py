"""Generate revised Figure 1 -- IEEE 1838 Test Access Architecture concept diagram.

This script produces a publication-quality 3-panel conceptual figure explaining WHY
test access scheduling is a hard problem for 3D stacked ICs under IEEE 1838.

Transport resources (2):
  - TAP (Test Access Port) -- serial chain present on every die, shared bottleneck
  - FPP (Flexible Parallel Port) -- optional parallel lanes on some dies (IEEE 1838 Clause 7)

Task types (3):
  - INTEST  -- internal scan test, needs continuous TAP or FPP
  - BIST    -- built-in self-test, needs TAP only for config/readback; releases TAP during execution
  - EXTEST  -- interconnect test, needs TAP + DWR wrapper cells on both connected dies

Panel (a): Physical 3D stack cross-section with PTAP/STAP serial chain and FPP lanes
Panel (b): Per-die task selection -- multiple test tasks per die with resource signatures
Panel (c): Scheduling timeline showing TAP time-multiplexing and BIST window exploitation

Output: results/figures/v4_final/fig1_concept.png
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, FancyArrowPatch, BoxStyle
import numpy as np


# ---------------------------------------------------------------------------
# Colours (consistent with the project palette)
# ---------------------------------------------------------------------------

COLOR_TAP_SERIAL = "#8d62c8"       # purple -- PTAP/STAP serial chain
COLOR_FPP = "#f28e2b"              # orange -- FPP parallel lanes
COLOR_BIST = "#59a14f"             # green  -- BIST engine / local execution
COLOR_DIE_BASE = "#d6dce4"         # light blue-gray for die silicon
COLOR_DIE_DARK = "#b0b9c8"         # slightly darker for die outlines
COLOR_PCB = "#8b7355"              # brown-ish for PCB substrate
COLOR_INTERPOSER = "#a0a0a0"       # gray for silicon interposer
COLOR_TEXT_DARK = "#2a2a2a"        # near-black for main text
COLOR_TEXT_MUTED = "#555555"       # gray for secondary labels
COLOR_BG = "#fafafa"               # figure background
COLOR_TASK_INTEST = "#4c78a8"      # blue for INTEST
COLOR_TASK_BIST = "#59a14f"        # green for BIST
COLOR_TASK_EXTEST = "#e45756"      # red for EXTEST
COLOR_HIGHLIGHT = "#fff2cc"        # pale yellow for highlights


# ---------------------------------------------------------------------------
# Font configuration
# ---------------------------------------------------------------------------


def configure_matplotlib() -> None:
    available = {font.name for font in fm.fontManager.ttflist}
    candidates = [
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    chosen = next((font for font in candidates if font in available), "DejaVu Sans")
    plt.rcParams.update(
        {
            "font.family": chosen,
            "axes.unicode_minus": False,
            "figure.facecolor": COLOR_BG,
            "axes.facecolor": "white",
        }
    )


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------


def rounded_box(ax, x, y, w, h, facecolor, edgecolor="#666666",
                linewidth=1.2, alpha=1.0, zorder=2, pad=4.0):
    """Draw a rounded-corner box using FancyBboxPatch (publication style)."""
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=BoxStyle("Round", pad=pad),
        facecolor=facecolor,
        edgecolor=edgecolor,
        linewidth=linewidth,
        alpha=alpha,
        zorder=zorder,
    )
    ax.add_patch(box)
    return box


def vertical_arrow(ax, x, y_start, y_end, color=COLOR_TAP_SERIAL, lw=1.5):
    """Draw a solid vertical arrow."""
    arrow = FancyArrowPatch(
        (x, y_start), (x, y_end),
        arrowstyle="->",
        color=color,
        linewidth=lw,
        zorder=5,
    )
    ax.add_patch(arrow)
    return arrow


def dashed_arrow_v(ax, x, y_start, y_end, color="#888888", lw=1.0):
    """Draw a dashed vertical arrow for conceptual linking."""
    arrow = FancyArrowPatch(
        (x, y_start), (x, y_end),
        arrowstyle="->",
        linestyle="--",
        color=color,
        linewidth=lw,
        zorder=5,
    )
    ax.add_patch(arrow)
    return arrow


def resource_segment_bar(ax, x, y, total_w, segments, label=""):
    """Draw a horizontal resource-usage bar with colored segments.

    Parameters
    ----------
    segments : list of (label, fraction, color)
    """
    bar_h = 0.26
    bg = Rectangle((x, y), total_w, bar_h, facecolor="#e0e0e0",
                   edgecolor="#aaaaaa", linewidth=0.5, zorder=2)
    ax.add_patch(bg)

    cur_x = x
    for seg_label, frac, color in segments:
        seg_w = total_w * frac
        seg = Rectangle((cur_x, y), seg_w, bar_h, facecolor=color,
                        edgecolor="#999999", linewidth=0.4, alpha=0.85, zorder=3)
        ax.add_patch(seg)
        if seg_w > 0.5:
            ax.text(cur_x + seg_w / 2, y + bar_h / 2, seg_label,
                    ha="center", va="center", fontsize=5.8, color="white",
                    fontweight="bold", zorder=4)
        cur_x += seg_w

    if label:
        ax.text(x - 0.15, y + bar_h / 2, label, ha="right", va="center",
                fontsize=6.5, color=COLOR_TEXT_MUTED, fontstyle="italic")


# ---------------------------------------------------------------------------
# Panel (a): 3D Stack Cross-Section
# ---------------------------------------------------------------------------


def draw_panel_a_stack(ax):
    """Draw the physical 3D/2.5D chip cross-section with test access architecture."""

    # Layout constants
    die_w = 14.0
    die_h = 3.0
    die_x = 4.0
    interposer_h = 1.6
    pcb_h = 1.8
    gap = 0.6
    n_dies = 4

    pcb_y = 1.0
    interposer_y = pcb_y + pcb_h
    die_y_start = interposer_y + interposer_h + gap

    # --- PCB ---
    rounded_box(ax, die_x - 3.0, pcb_y, die_w + 6.0, pcb_h,
                facecolor=COLOR_PCB, edgecolor="#5a4a34", alpha=0.55)
    ax.text(die_x + die_w / 2, pcb_y + pcb_h / 2, "PCB / Test Pins",
            ha="center", va="center", fontsize=9, fontstyle="italic",
            color="white", fontweight="bold")

    # --- Interposer ---
    rounded_box(ax, die_x - 1.5, interposer_y, die_w + 3.0, interposer_h,
                facecolor=COLOR_INTERPOSER, edgecolor="#707070", alpha=0.5)
    ax.text(die_x + die_w / 2, interposer_y + interposer_h / 2,
            "Silicon Interposer (2.5D)",
            ha="center", va="center", fontsize=8.5, fontstyle="italic",
            color="white", fontweight="bold")

    # --- PTAP on interposer (centre, towards left) ---
    ptap_w, ptap_h = 2.2, 0.85
    ptap_x = die_x + 0.8
    ptap_y = interposer_y + interposer_h / 2 - ptap_h / 2
    rounded_box(ax, ptap_x, ptap_y, ptap_w, ptap_h,
                facecolor=COLOR_TAP_SERIAL, edgecolor="#6d42a8", alpha=0.9, pad=3.0)
    ax.text(ptap_x + ptap_w / 2, ptap_y + ptap_h / 2, "PTAP",
            ha="center", va="center", fontsize=8, color="white", fontweight="bold")

    # --- Stacked dies ---
    die_labels = ["Die 3 (Top)", "Die 2", "Die 1", "Die 0 (Bottom)"]
    die_colors = ["#c3cddb", "#bcc6d4", "#b5bfcd", "#aeb8c6"]

    for i in range(n_dies):
        dy = die_y_start + i * (die_h + gap)
        rounded_box(ax, die_x, dy, die_w, die_h,
                    facecolor=die_colors[i], edgecolor=COLOR_DIE_DARK, alpha=0.9)
        ax.text(die_x + die_w / 2, dy + die_h / 2, die_labels[i],
                ha="center", va="center", fontsize=10, fontweight="bold",
                color=COLOR_TEXT_DARK)

    # --- STAP blocks inside each die (left edge) ---
    stap_w, stap_h = 1.1, 0.85
    stap_x = die_x + 0.5
    for i in range(n_dies):
        dy = die_y_start + i * (die_h + gap) + (die_h - stap_h) / 2
        rounded_box(ax, stap_x, dy, stap_w, stap_h,
                    facecolor=COLOR_TAP_SERIAL, edgecolor="#6d42a8", alpha=0.8, pad=2.5)
        ax.text(stap_x + stap_w / 2, dy + stap_h / 2, "STAP",
                ha="center", va="center", fontsize=6.5, color="white", fontweight="bold")

    # --- Serial TAP chain arrows (vertical, PTAP -> STAP Die0 -> ... -> STAP Die3) ---
    arrow_x = stap_x + stap_w / 2

    # PTAP top
    ptap_top = ptap_y + ptap_h
    # STAP Die0 bottom
    stap0_bottom = die_y_start + 0 * (die_h + gap) + (die_h - stap_h) / 2
    vertical_arrow(ax, arrow_x, ptap_top, stap0_bottom, color=COLOR_TAP_SERIAL, lw=1.8)

    # Between each pair of STAPs
    for i in range(n_dies - 1):
        stap_bottom_top = die_y_start + i * (die_h + gap) + (die_h - stap_h) / 2 + stap_h
        stap_top_bottom = die_y_start + (i + 1) * (die_h + gap) + (die_h - stap_h) / 2
        vertical_arrow(ax, arrow_x, stap_bottom_top, stap_top_bottom,
                       color=COLOR_TAP_SERIAL, lw=1.8)

    # --- Label the serial chain ---
    chain_label_x = stap_x + stap_w + 0.8
    # Centre of the die stack
    chain_label_y = die_y_start + die_h / 2 + 1.5 * (die_h + gap)
    ax.text(chain_label_x, chain_label_y,
            "PTAP/STAP Serial Chain\n(shared bottleneck)",
            fontsize=8.5, color=COLOR_TAP_SERIAL, fontweight="bold",
            ha="left", va="center",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                      edgecolor=COLOR_TAP_SERIAL, alpha=0.85))

    # --- Shared BIST engine inside Die 1 ---
    bist_x = die_x + die_w - 3.6
    bist_w, bist_h = 3.2, 1.35
    bist_y = die_y_start + 1 * (die_h + gap) + (die_h - bist_h) / 2
    rounded_box(ax, bist_x, bist_y, bist_w, bist_h,
                facecolor=COLOR_BIST, edgecolor="#3a7a30", alpha=0.88)
    ax.text(bist_x + bist_w / 2, bist_y + bist_h / 2,
            "Shared BIST\nEngine",
            ha="center", va="center", fontsize=7.5, color="white", fontweight="bold")

    # Dashed arrow from BIST to TAP chain (conceptual link)
    dashed_arrow_v(ax, bist_x, bist_y + bist_h / 2,
                   die_y_start + 1 * (die_h + gap) + die_h / 2,
                   color=COLOR_BIST, lw=1.3)

    # --- FPP Lanes on right side of stack ---
    fpp_start_x = die_x + die_w + 1.5
    fpp_lane_w = 0.9
    fpp_gap_x = 0.3
    n_fpp = 4

    fpp_bottom = die_y_start + 0.4
    fpp_top = die_y_start + (n_dies - 1) * (die_h + gap) + die_h - 0.4

    for lane_i in range(n_fpp):
        lx = fpp_start_x + lane_i * (fpp_lane_w + fpp_gap_x)
        lane = Rectangle((lx, fpp_bottom), fpp_lane_w, fpp_top - fpp_bottom,
                         facecolor=COLOR_FPP, edgecolor=COLOR_FPP,
                         alpha=0.6, zorder=2)
        ax.add_patch(lane)

        # Small connector circles at each die level
        for d in range(n_dies):
            dy = die_y_start + d * (die_h + gap) + die_h / 2
            ax.plot(lx + fpp_lane_w / 2, dy, 'o',
                    color=COLOR_FPP, markersize=4.5, zorder=3, markeredgewidth=0.5,
                    markeredgecolor="#c07020")

    # FPP label
    fpp_centre_x = fpp_start_x + (n_fpp * (fpp_lane_w + fpp_gap_x) - fpp_gap_x) / 2
    ax.text(fpp_centre_x, fpp_top + 0.8,
            "FPP Lanes\n(optional, IEEE 1838\nClause 7)",
            fontsize=8.5, color=COLOR_FPP, fontweight="bold",
            ha="center", va="bottom",
            bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                      edgecolor=COLOR_FPP, alpha=0.85))

    # --- TSV pillar icons far right ---
    tsv_x = fpp_start_x + n_fpp * (fpp_lane_w + fpp_gap_x) + 1.0
    for d in range(n_dies):
        dy = die_y_start + d * (die_h + gap) + die_h - 1.0
        pillar = Rectangle((tsv_x, dy), 0.35, 0.7, facecolor="#d4a843",
                           edgecolor="#8b7332", linewidth=0.5, zorder=2)
        ax.add_patch(pillar)
    ax.text(tsv_x + 0.35 / 2, fpp_top + 0.8, "TSV\npillars",
            fontsize=7, color="#8b7332", ha="center", va="bottom",
            fontstyle="italic")

    # --- Panel label ---
    ax.text(0.02, 0.98, "(a) 3D/2.5D Stack Cross-Section with IEEE 1838 Test Access",
            transform=ax.transAxes, fontsize=11, fontweight="bold",
            color=COLOR_TEXT_DARK, ha="left", va="top")

    # --- Layout ---
    right_margin = tsv_x + 2.0
    top_margin = fpp_top + 3.0
    ax.set_xlim(0, right_margin)
    ax.set_ylim(0, top_margin)
    ax.set_aspect("equal")
    ax.axis("off")


# ---------------------------------------------------------------------------
# Panel (b): Task Selection Problem
# ---------------------------------------------------------------------------


def draw_panel_b_tasks(ax):
    """Show the task selection problem: 3 task types per die with different resource signatures."""

    box_w = 8.0
    box_h = 2.2
    box_x = 5.5
    gap_y = 0.6

    # ---- INTEST ----
    intest_y = 14.0
    rounded_box(ax, box_x, intest_y, box_w, box_h,
                facecolor="white", edgecolor=COLOR_TASK_INTEST, linewidth=2.0, alpha=0.97)
    ax.text(box_x + 0.3, intest_y + box_h - 0.35,
            "INTEST  —  Internal Scan Test",
            fontsize=10.5, fontweight="bold", color=COLOR_TASK_INTEST,
            ha="left", va="top")
    ax.text(box_x + 0.3, intest_y + 0.5,
            "TAP for configuration  +  TAP (or FPP) for scan data transfer",
            fontsize=8.5, color=COLOR_TEXT_MUTED, ha="left", va="center")
    # resource bar
    resource_segment_bar(ax, box_x + 0.3, intest_y + 0.95, box_w - 0.8,
                         [("TAP Config", 0.18, COLOR_TAP_SERIAL),
                          ("Scan Data (TAP or FPP)", 0.45, COLOR_TAP_SERIAL),
                          ("TAP Read", 0.18, COLOR_TAP_SERIAL)],
                         label="TAP: continuous")

    # ---- BIST ----
    bist_y = intest_y - box_h - gap_y
    rounded_box(ax, box_x, bist_y, box_w, box_h,
                facecolor="white", edgecolor=COLOR_TASK_BIST, linewidth=2.0, alpha=0.97)
    ax.text(box_x + 0.3, bist_y + box_h - 0.35,
            "BIST  —  Built-In Self-Test",
            fontsize=10.5, fontweight="bold", color=COLOR_TASK_BIST,
            ha="left", va="top")
    ax.text(box_x + 0.3, bist_y + 0.5,
            "TAP for config only; then BIST engine runs locally independently",
            fontsize=8.5, color=COLOR_TEXT_MUTED, ha="left", va="center")

    resource_segment_bar(ax, box_x + 0.3, bist_y + 0.95, box_w - 0.8,
                         [("TAP\nConfig", 0.12, COLOR_TAP_SERIAL),
                          ("BIST runs locally (frees TAP!)", 0.38, COLOR_BIST),
                          ("TAP\nReadback", 0.12, COLOR_TAP_SERIAL)],
                         label="TAP: intermittent")

    # Highlight callout
    callout_x = box_x + 0.3 + (box_w - 0.8) * 0.18
    callout_w = (box_w - 0.8) * 0.38
    callout_y = bist_y + 1.10
    ax.text(callout_x + callout_w / 2, callout_y,
            "TAP RELEASED\n  during BIST\nexecution",
            ha="center", va="center", fontsize=7.2, fontweight="bold",
            color="#2a6b1a",
            bbox=dict(boxstyle="round,pad=0.35", facecolor=COLOR_HIGHLIGHT,
                      edgecolor=COLOR_BIST, alpha=0.92, linewidth=1.5),
            zorder=10)

    # ---- EXTEST ----
    extest_y = bist_y - box_h - gap_y
    rounded_box(ax, box_x, extest_y, box_w, box_h,
                facecolor="white", edgecolor=COLOR_TASK_EXTEST, linewidth=2.0, alpha=0.97)
    ax.text(box_x + 0.3, extest_y + box_h - 0.35,
            "EXTEST  —  Interconnect Test",
            fontsize=10.5, fontweight="bold", color=COLOR_TASK_EXTEST,
            ha="left", va="top")
    ax.text(box_x + 0.3, extest_y + 0.5,
            "TAP for config + DWR wrapper cells on both connected dies simultaneously",
            fontsize=8.5, color=COLOR_TEXT_MUTED, ha="left", va="center")

    resource_segment_bar(ax, box_x + 0.3, extest_y + 0.95, box_w - 0.8,
                         [("TAP Config", 0.14, COLOR_TAP_SERIAL),
                          ("Die0 DWR active", 0.20, COLOR_TASK_EXTEST),
                          ("Die1 DWR active", 0.20, COLOR_TASK_EXTEST),
                          ("TAP Read", 0.14, COLOR_TAP_SERIAL)],
                         label="Needs both dies")

    # ---- "per die" header ----
    ax.text(box_x + box_w / 2, intest_y + box_h + 0.7,
            "Example: Die 1  —  multiple test tasks compete for shared resources",
            fontsize=10.5, fontweight="bold", color=COLOR_TEXT_DARK,
            ha="center", va="bottom",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="#eeeeee",
                      edgecolor="#bbbbbb", alpha=0.8))

    # ---- Legend ----
    leg_x = 0.8
    leg_y = 14.5
    leg_items = [
        ("TAP / Serial path", COLOR_TAP_SERIAL),
        ("BIST local", COLOR_BIST),
        ("DWR (Wrapper)", COLOR_TASK_EXTEST),
        ("FPP Lanes", COLOR_FPP),
    ]
    for idx, (lbl, clr) in enumerate(leg_items):
        ly = leg_y - idx * 0.55
        rect = Rectangle((leg_x, ly), 0.7, 0.35, facecolor=clr,
                         edgecolor="#999999", linewidth=0.5, zorder=3)
        ax.add_patch(rect)
        ax.text(leg_x + 0.9, ly + 0.18, lbl, fontsize=8.2,
                color=COLOR_TEXT_MUTED, ha="left", va="center")

    # ---- Panel label ----
    ax.text(0.02, 0.98, "(b) Per-Die Task Selection: Resource Signatures",
            transform=ax.transAxes, fontsize=11, fontweight="bold",
            color=COLOR_TEXT_DARK, ha="left", va="top")

    ax.set_xlim(0, box_x + box_w + 1.5)
    ax.set_ylim(0, intest_y + box_h + 2.2)
    ax.set_aspect("equal")
    ax.axis("off")


# ---------------------------------------------------------------------------
# Panel (c): Scheduling Timeline
# ---------------------------------------------------------------------------


def draw_panel_c_timeline(ax):
    """Draw a simplified Gantt-like timeline showing TAP time-multiplexing."""

    t_start = 4.5          # x offset for the Gantt area
    t_total = 12.0         # width of the time axis
    lane_h = 0.85
    lane_gap = 0.55

    y_tap = 2.0 + 3 * (lane_h + lane_gap)
    y_fpp = 2.0 + 2 * (lane_h + lane_gap)
    y_bist = 2.0 + lane_h + lane_gap
    y_die = 2.0

    # ---- Lane backgrounds and labels ----
    lanes = [
        (y_tap, "Serial TAP\n(bottleneck)", COLOR_TAP_SERIAL),
        (y_fpp, "FPP Lanes\n(optional)", COLOR_FPP),
        (y_bist, "Shared BIST\nEngine", COLOR_BIST),
        (y_die, "Die Activity\n(Die0..Die3)", "#999999"),
    ]
    for ly, ltxt, lc in lanes:
        bg = Rectangle((t_start, ly), t_total, lane_h,
                       facecolor="white", edgecolor=lc, linewidth=1.8,
                       alpha=0.96, zorder=1)
        ax.add_patch(bg)
        ax.text(t_start - 0.25, ly + lane_h / 2, ltxt,
                ha="right", va="center", fontsize=8, fontweight="bold", color=lc)

    # ---- Time axis ticks ----
    ax.hlines(y_tap - 0.30, t_start, t_start + t_total,
              color="#aaaaaa", linewidth=0.8)
    for ti in np.arange(0, t_total + 0.01, 2.0):
        ax.vlines(t_start + ti, y_tap - 0.45, y_tap - 0.15,
                  color="#aaaaaa", linewidth=0.6)
        ax.text(t_start + ti, y_tap - 0.65, f"t={int(ti)}",
                ha="center", va="top", fontsize=6, color="#888888")

    # ---- Block drawing helper ----
    def blk(x0, w, y, color, txt="", ec=None):
        if ec is None:
            ec = color
        r = Rectangle((t_start + x0, y + 0.07), w, lane_h - 0.14,
                      facecolor=color, edgecolor=ec, linewidth=0.5,
                      alpha=0.82, zorder=5)
        ax.add_patch(r)
        if txt and w > 0.3:
            ax.text(t_start + x0 + w / 2, y + lane_h / 2,
                    txt, ha="center", va="center", fontsize=5.8,
                    color="white", fontweight="bold", zorder=6)
        return r

    # ---- TAP lane: time-multiplexed usage across dies ----
    tap_schedule = [
        (0.0,  1.0,  "D0 cfg"),
        (1.0,  0.8,  "D2 cfg"),
        (1.8,  0.6,  "D0 rd"),
        (2.4,  0.7,  "D3 cfg"),
        (3.1,  1.1,  "D1 cfg"),
        (4.2,  0.6,  "D2 rd"),
        (4.8,  0.7,  "D1 rd"),
        (5.5,  0.8,  "D3 rd"),
        (7.5,  0.8,  "D0 cfg"),
        (8.3,  0.7,  "D0 rd"),
    ]
    for x0, w, txt in tap_schedule:
        blk(x0, w, y_tap, COLOR_TAP_SERIAL, txt)

    # ---- BIST lane: runs fill the gaps ----
    bist_schedule = [
        (0.2,  2.7,  "D0 BIST executing"),
        (3.2,  3.8,  "D1 BIST executing"),
        (7.7,  2.0,  "D2 BIST executing"),
    ]
    for x0, w, txt in bist_schedule:
        blk(x0, w, y_bist, COLOR_BIST, txt)

    # ---- FPP lane: parallel data offloading ----
    fpp_schedule = [
        (0.1,  0.9,  "D2 cfg+FPP"),
        (3.3,  1.3,  "D3 FPP\ndata"),
        (5.0,  2.0,  "D0 FPP\ndata"),
    ]
    for x0, w, txt in fpp_schedule:
        blk(x0, w, y_fpp, COLOR_FPP, txt)

    # ---- Die activity lane ----
    die_schedule = [
        (0.0,  3.2,  "Die0"),
        (3.1,  1.7,  "Die1"),
        (1.0,  3.9,  "Die2"),
        (2.4,  1.8,  "Die3"),
        (7.5,  2.0,  "Die0"),
    ]
    die_clrs = ["#c3cddb", "#b9c2d0", "#aeb8c6", "#a3aebc", "#c3cddb"]
    for (x0, w, txt), dc in zip(die_schedule, die_clrs):
        blk(x0, w, y_die, dc, txt, ec=COLOR_DIE_DARK)

    # ---- Free window annotations ----
    win_color = "#d64040"

    # Window around t=1.8 (gap between D0 rd and D3 cfg on TAP)
    ax.annotate(
        "",
        xy=(t_start + 2.2,  y_tap + lane_h + 0.6),
        xytext=(t_start + 1.6, y_tap + lane_h + 0.15),
        arrowprops=dict(arrowstyle="->", color=win_color, lw=1.5),
    )
    ax.text(t_start + 3.0, y_tap + lane_h + 0.5,
            "Free TAP\nwindow",
            fontsize=7.5, color=win_color, fontweight="bold",
            ha="left", va="center")

    # Window around t=4.2 (gap)
    ax.annotate(
        "",
        xy=(t_start + 4.7,  y_tap + lane_h + 0.6),
        xytext=(t_start + 4.2, y_tap + lane_h + 0.15),
        arrowprops=dict(arrowstyle="->", color=win_color, lw=1.5),
    )

    # ---- Dashed lines: BIST -> TAP gap conceptual link ----
    dashed_arrow_v(ax, t_start + 2.0, y_bist + lane_h, y_tap,
                   color=COLOR_BIST, lw=1.2)
    dashed_arrow_v(ax, t_start + 5.0, y_bist + lane_h, y_tap,
                   color=COLOR_BIST, lw=1.2)

    # ---- Key insight box ----
    insight = ("Key Insight: TAP Time-Multiplexing\n"
               "BIST execution frees the serial TAP;\n"
               "concurrent BIST + TAP operations\n"
               "dramatically reduce total test time.")
    ax.text(t_start + t_total / 2, y_fpp + lane_h + 2.0,
            insight,
            ha="center", va="bottom", fontsize=9, fontweight="bold",
            color="#c0392b",
            bbox=dict(boxstyle="round,pad=0.55", facecolor="#fff5f5",
                      edgecolor=win_color, alpha=0.93),
            zorder=10)

    # ---- Panel label ----
    ax.text(0.02, 0.98,
            "(c) Schedule Timeline: TAP Time-Multiplexing with BIST Window Exploitation",
            transform=ax.transAxes, fontsize=11, fontweight="bold",
            color=COLOR_TEXT_DARK, ha="left", va="top")

    ax.set_xlim(0, t_start + t_total + 1.5)
    ax.set_ylim(0, y_tap + lane_h + 4.0)
    ax.set_aspect("equal")
    ax.axis("off")


# ---------------------------------------------------------------------------
# Main figure assembly
# ---------------------------------------------------------------------------


def main() -> None:
    configure_matplotlib()

    figure_dir = Path("results/figures/v4_final")
    figure_dir.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(16, 5.5), dpi=200)

    # GridSpec: 3 columns with width ratios that give each panel adequate space
    gs = fig.add_gridspec(1, 3, width_ratios=[1.15, 0.95, 1.05],
                          wspace=0.06, left=0.025, right=0.985,
                          top=0.88, bottom=0.06)

    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[0, 2])

    draw_panel_a_stack(ax_a)
    draw_panel_b_tasks(ax_b)
    draw_panel_c_timeline(ax_c)

    # ---- Overall figure title ----
    fig.suptitle(
        "Fig. 1  IEEE 1838 Test Access Architecture and the Scheduling Challenge",
        fontsize=14, fontweight="bold", color=COLOR_TEXT_DARK,
        x=0.5, y=0.985,
    )

    # ---- Footer ----
    fig.text(
        0.5, 0.012,
        "Transport resources: TAP (serial, every die) and FPP (parallel, optional). "
        "BIST is a task type that releases TAP during execution, enabling concurrent test scheduling.",
        ha="center", va="bottom", fontsize=7.2, color=COLOR_TEXT_MUTED, fontstyle="italic",
    )

    output_path = figure_dir / "fig1_concept.png"
    fig.savefig(output_path, dpi=200, bbox_inches="tight", facecolor=COLOR_BG)
    plt.close(fig)

    print(f"Figure saved to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
