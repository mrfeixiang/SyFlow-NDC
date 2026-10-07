#!/usr/bin/env python3
"""Generate SyFlow NDC Go/No-Go workflow presentation with architecture diagrams.

Creates:
1. Agent architecture diagram (matplotlib → PNG)
2. Gate workflow diagram (matplotlib → PNG)
3. EGFRvIII pilot protocol diagram (matplotlib → PNG)
4. PowerPoint slides with all figures + GPU/API to-do list
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

OUT_DIR = Path(__file__).parent / "figures"
OUT_DIR.mkdir(exist_ok=True)

# ─── Color palette ───────────────────────────────────────────────────────────
C_BG = "#0F1419"
C_CARD = "#1A2332"
C_BORDER = "#2D3F54"
C_TEXT = "#E8ECF1"
C_SUBTEXT = "#8899AA"
C_CSO = "#6366F1"       # Indigo
C_TARGET = "#10B981"    # Emerald
C_NANO = "#F59E0B"      # Amber
C_DELIVERY = "#3B82F6"  # Blue
C_CONJ = "#EF4444"      # Red
C_TRANS = "#8B5CF6"      # Purple
C_REVIEW = "#EC4899"    # Pink
C_GO = "#10B981"
C_HOLD = "#F59E0B"
C_NOGO = "#EF4444"
C_GATE = "#1E40AF"
C_ARROW = "#64748B"


def draw_agent_architecture():
    """Draw the 8-agent orchestration architecture."""
    fig, ax = plt.subplots(1, 1, figsize=(16, 10), facecolor=C_BG)
    ax.set_facecolor(C_BG)
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 10)
    ax.axis("off")

    # Title
    ax.text(8, 9.6, "SyFlow NDC Agent Architecture", fontsize=22, fontweight="bold",
            color=C_TEXT, ha="center", va="center", fontfamily="sans-serif")
    ax.text(8, 9.2, "Provenance-first orchestration for nanobody-drug conjugate Go/No-Go decisions",
            fontsize=11, color=C_SUBTEXT, ha="center", va="center", fontfamily="sans-serif")

    def draw_box(x, y, w, h, label, sublabel, color, fontsize=11):
        box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1",
                             facecolor=color + "22", edgecolor=color, linewidth=2)
        ax.add_patch(box)
        ax.text(x + w / 2, y + h / 2 + 0.15, label, fontsize=fontsize, fontweight="bold",
                color=color, ha="center", va="center", fontfamily="sans-serif")
        ax.text(x + w / 2, y + h / 2 - 0.2, sublabel, fontsize=8,
                color=C_SUBTEXT, ha="center", va="center", fontfamily="sans-serif")

    # CSO at top
    draw_box(5.5, 7.5, 5, 1.2, "CSO — Chief Scientific Officer", "Orchestrator · No data tools · Sonnet 4.6", C_CSO, 13)

    # Data flow arrows from CSO
    for tx in [1.8, 4.6, 7.4, 10.2, 13.0]:
        ax.annotate("", xy=(tx + 1, 6.2), xytext=(8, 7.5),
                    arrowprops=dict(arrowstyle="-|>", color=C_ARROW, lw=1.5, connectionstyle="arc3,rad=0.0"))

    # 5 Specialists in middle row
    specs = [
        (0.3, 4.8, "Target &\nPatient", "G0 · Open Targets\nPubMed · ChEMBL", C_TARGET),
        (3.1, 4.8, "Nanobody &\nEpitope", "G1 · PubMed\nChEMBL · Scholar", C_NANO),
        (5.9, 4.8, "Delivery", "G2 · PubMed\nbioRxiv", C_DELIVERY),
        (8.7, 4.8, "Conjugation\n& Payload", "G3/G4 · ChEMBL\nPubMed", C_CONJ),
        (11.5, 4.8, "Translation\n& Safety", "G5 · Clinical Trials\nOpen Targets", C_TRANS),
    ]
    for x, y, label, sub, color in specs:
        draw_box(x, y, 2.6, 1.3, label, sub, color, 10)

    # Arrows from specialists to reviewer
    for x, _, _, _, _ in specs:
        ax.annotate("", xy=(8, 3.7), xytext=(x + 1.3, 4.8),
                    arrowprops=dict(arrowstyle="-|>", color=C_ARROW, lw=1.2, connectionstyle="arc3,rad=0.0"))

    # Scientific Reviewer
    draw_box(5.5, 2.4, 5, 1.2, "Scientific Reviewer & Gatekeeper",
             "Read-only · Claim-by-claim audit · Haiku 4.5", C_REVIEW, 12)

    # Feedback arrow from reviewer to CSO (routed to the right to avoid overlap)
    ax.annotate("", xy=(11.0, 8.1), xytext=(10.5, 3.6),
                arrowprops=dict(arrowstyle="-|>", color=C_REVIEW, lw=2,
                                connectionstyle="arc3,rad=-0.4", linestyle="--"))
    ax.text(14.2, 5.8, "Approve /\nRevise", fontsize=9, color=C_REVIEW,
            ha="center", va="center", fontfamily="sans-serif", style="italic")

    # Bottom: Provenance layer
    prov_box = FancyBboxPatch((1, 0.3), 14, 1.5, boxstyle="round,pad=0.1",
                               facecolor="#1E293B", edgecolor=C_BORDER, linewidth=1.5)
    ax.add_patch(prov_box)
    ax.text(8, 1.35, "Provenance Layer", fontsize=13, fontweight="bold",
            color=C_TEXT, ha="center", va="center", fontfamily="sans-serif")

    prov_items = [
        ("trace.jsonl", 3), ("MANIFEST.json", 6), ("claims.json", 9),
        ("plan.json (DAG)", 12),
    ]
    for label, px in prov_items:
        ax.text(px, 0.75, label, fontsize=9, color=C_SUBTEXT,
                ha="center", va="center", fontfamily="monospace",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="#0F1419", edgecolor=C_BORDER, linewidth=0.8))

    # Gate labels on specialist boxes
    gate_labels = [("G0", 1.6, 6.25, C_TARGET), ("G1", 4.4, 6.25, C_NANO),
                   ("G2", 7.2, 6.25, C_DELIVERY), ("G3/G4", 10.0, 6.25, C_CONJ),
                   ("G5", 12.8, 6.25, C_TRANS)]
    for gl, gx, gy, gc in gate_labels:
        ax.text(gx, gy, gl, fontsize=10, fontweight="bold", color=gc,
                ha="center", va="center", fontfamily="sans-serif",
                bbox=dict(boxstyle="round,pad=0.15", facecolor=gc + "33", edgecolor=gc, linewidth=1.2))

    fig.savefig(OUT_DIR / "agent_architecture.png", dpi=200, bbox_inches="tight",
                facecolor=C_BG, edgecolor="none")
    plt.close(fig)
    print(f"  ✓ {OUT_DIR / 'agent_architecture.png'}")


def draw_gate_workflow():
    """Draw the G0→G5 gate workflow with Go/Hold/No-Go decision points."""
    fig, ax = plt.subplots(1, 1, figsize=(16, 8), facecolor=C_BG)
    ax.set_facecolor(C_BG)
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 8)
    ax.axis("off")

    ax.text(8, 7.6, "SyFlow NDC Go/No-Go Gate Workflow", fontsize=20, fontweight="bold",
            color=C_TEXT, ha="center", va="center", fontfamily="sans-serif")

    gates = [
        ("G0", "Target", "Membrane protein?\nNormal-tissue window?", C_TARGET),
        ("G1", "VHH", "Live-cell binding?\nSelectivity confirmed?", C_NANO),
        ("G2", "Delivery", "Internalization?\nCorrect compartment?", C_DELIVERY),
        ("G3", "Product", "Reproducible NDC?\nStable, pure, defined?", C_CONJ),
        ("G4", "Function", "Antigen-dependent\nkilling? 4 controls?", "#F97316"),
        ("G5", "Translation", "Therapeutic window?\nKidney exposure OK?", C_TRANS),
    ]

    x_start = 0.8
    x_step = 2.5
    y_gate = 5.0
    y_decision = 2.5

    for i, (gid, name, criteria, color) in enumerate(gates):
        x = x_start + i * x_step

        # Gate box
        box = FancyBboxPatch((x, y_gate - 0.6), 2.0, 1.8, boxstyle="round,pad=0.1",
                             facecolor=color + "22", edgecolor=color, linewidth=2)
        ax.add_patch(box)
        ax.text(x + 1, y_gate + 0.65, gid, fontsize=14, fontweight="bold",
                color=color, ha="center", va="center", fontfamily="sans-serif")
        ax.text(x + 1, y_gate + 0.25, name, fontsize=10, fontweight="bold",
                color=C_TEXT, ha="center", va="center", fontfamily="sans-serif")
        ax.text(x + 1, y_gate - 0.25, criteria, fontsize=7.5,
                color=C_SUBTEXT, ha="center", va="center", fontfamily="sans-serif")

        # Arrow to next gate
        if i < len(gates) - 1:
            ax.annotate("", xy=(x + x_step, y_gate + 0.3), xytext=(x + 2.0, y_gate + 0.3),
                        arrowprops=dict(arrowstyle="-|>", color=C_GO, lw=2))
            ax.text(x + 2.0 + (x_step - 2.0) / 2, y_gate + 0.55, "Go", fontsize=8,
                    color=C_GO, ha="center", fontweight="bold", fontfamily="sans-serif")

        # Decision diamond area
        diamond_y = y_decision
        # Hold arrow (down-left)
        ax.annotate("", xy=(x + 0.3, diamond_y - 0.3), xytext=(x + 1, y_gate - 0.6),
                    arrowprops=dict(arrowstyle="-|>", color=C_HOLD, lw=1.5, linestyle="--"))
        ax.text(x + 0.3, diamond_y - 0.6, "Hold", fontsize=9, fontweight="bold",
                color=C_HOLD, ha="center", fontfamily="sans-serif",
                bbox=dict(boxstyle="round,pad=0.15", facecolor=C_HOLD + "22", edgecolor=C_HOLD, linewidth=1))
        ax.text(x + 0.3, diamond_y - 1.0, "Run next\nexperiment", fontsize=7,
                color=C_SUBTEXT, ha="center", fontfamily="sans-serif")

        # No-Go arrow (down-right)
        ax.annotate("", xy=(x + 1.7, diamond_y - 0.3), xytext=(x + 1, y_gate - 0.6),
                    arrowprops=dict(arrowstyle="-|>", color=C_NOGO, lw=1.5, linestyle="--"))
        ax.text(x + 1.7, diamond_y - 0.6, "No-Go", fontsize=9, fontweight="bold",
                color=C_NOGO, ha="center", fontfamily="sans-serif",
                bbox=dict(boxstyle="round,pad=0.15", facecolor=C_NOGO + "22", edgecolor=C_NOGO, linewidth=1))
        ax.text(x + 1.7, diamond_y - 1.0, "Stop or\nredesign", fontsize=7,
                color=C_SUBTEXT, ha="center", fontfamily="sans-serif")

    # Legend
    for lx, label, color in [(1, "Go → advance", C_GO), (4, "Hold → experiment", C_HOLD), (7.5, "No-Go → stop", C_NOGO)]:
        ax.text(lx, 0.4, "●", fontsize=14, color=color, ha="center", va="center")
        ax.text(lx + 0.3, 0.4, label, fontsize=10, color=C_TEXT, ha="left", va="center", fontfamily="sans-serif")

    ax.text(12, 0.4, "Thresholds set BEFORE each experiment", fontsize=9, color=C_SUBTEXT,
            ha="center", va="center", fontfamily="sans-serif", style="italic")

    fig.savefig(OUT_DIR / "gate_workflow.png", dpi=200, bbox_inches="tight",
                facecolor=C_BG, edgecolor="none")
    plt.close(fig)
    print(f"  ✓ {OUT_DIR / 'gate_workflow.png'}")


def draw_egfrviii_pilot():
    """Draw the EGFRvIII prospective pilot protocol."""
    fig, ax = plt.subplots(1, 1, figsize=(16, 9), facecolor=C_BG)
    ax.set_facecolor(C_BG)
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis("off")

    ax.text(8, 8.6, "EGFRvIII NDC Prospective Pilot", fontsize=20, fontweight="bold",
            color=C_TEXT, ha="center", va="center", fontfamily="sans-serif")
    ax.text(8, 8.2, "First closed-loop SyFlow validation cycle", fontsize=11,
            color=C_SUBTEXT, ha="center", va="center", fontfamily="sans-serif")

    steps = [
        ("Step 1", "Freeze Predictions", [
            "Lock binder rankings",
            "Record overturn assays",
            "Separate EGFRvIII from",
            "kinase-domain mutations",
        ], C_CSO, 2),
        ("Step 2", "Binding & Uptake", [
            "Flow cytometry cell panel:",
            "• U87-EGFRvIII (target+)",
            "• A431 (high WT EGFR)",
            "• CHO-K1 (target−)",
            "Internalization time course",
        ], C_NANO, 4.3),
        ("Step 3", "Conjugate Series", [
            "Sortase/SPAAC conjugation",
            "Each VHH + nonbinding ctrl",
            "Confirm DAR, free payload",
            "per batch before potency",
        ], C_CONJ, 6.6),
        ("Step 4", "DMTA Feedback", [
            "Which prediction survived?",
            "Which failed?",
            "Change VHH/linker/payload",
            "/format/population?",
            "→ First closed loop",
        ], C_DELIVERY, 8.9),
    ]

    y_top = 7.2
    box_h = 3.8
    box_w = 3.2

    for step_id, title, items, color, x in steps:
        # Step box
        box = FancyBboxPatch((x - 0.3, y_top - box_h), box_w, box_h,
                             boxstyle="round,pad=0.15",
                             facecolor=color + "15", edgecolor=color, linewidth=2)
        ax.add_patch(box)

        # Step number badge
        badge = FancyBboxPatch((x + box_w / 2 - 0.7, y_top - 0.15), 1.1, 0.45,
                               boxstyle="round,pad=0.08",
                               facecolor=color, edgecolor=color, linewidth=0)
        ax.add_patch(badge)
        ax.text(x + box_w / 2 - 0.15, y_top + 0.07, step_id, fontsize=10, fontweight="bold",
                color="white", ha="center", va="center", fontfamily="sans-serif")

        # Title
        ax.text(x + box_w / 2 - 0.15, y_top - 0.55, title, fontsize=12, fontweight="bold",
                color=color, ha="center", va="center", fontfamily="sans-serif")

        # Items
        for j, item in enumerate(items):
            ax.text(x + 0.1, y_top - 1.1 - j * 0.45, item, fontsize=8.5,
                    color=C_TEXT if not item.startswith("•") else C_SUBTEXT,
                    ha="left", va="center", fontfamily="sans-serif")

        # Arrow to next
        if x < 8:
            ax.annotate("", xy=(x + box_w + 0.05, y_top - box_h / 2),
                        xytext=(x + box_w - 0.35, y_top - box_h / 2),
                        arrowprops=dict(arrowstyle="-|>", color=C_ARROW, lw=2))

    # Cell panel box at bottom
    panel_box = FancyBboxPatch((1.5, 0.3), 13, 1.5, boxstyle="round,pad=0.1",
                                facecolor="#1E293B", edgecolor=C_BORDER, linewidth=1.5)
    ax.add_patch(panel_box)
    ax.text(8, 1.35, "Required Cell Panel", fontsize=12, fontweight="bold",
            color=C_TEXT, ha="center", va="center", fontfamily="sans-serif")

    cells = [
        ("U87-EGFRvIII", "Target+", C_GO),
        ("A431", "High WT", C_HOLD),
        ("U87 parental", "Moderate WT", C_HOLD),
        ("CHO-K1", "Target−", C_NOGO),
        ("GBM spheroids", "Patient-derived", C_CSO),
    ]
    for i, (name, role, color) in enumerate(cells):
        cx = 2.5 + i * 2.4
        ax.text(cx, 0.9, name, fontsize=9, fontweight="bold", color=color,
                ha="center", va="center", fontfamily="sans-serif")
        ax.text(cx, 0.55, role, fontsize=8, color=C_SUBTEXT,
                ha="center", va="center", fontfamily="sans-serif")

    # Success criteria at bottom
    ax.text(8, 2.15, "Judged by: correct No-Gos · informative next experiments · selective NDC activity",
            fontsize=10, color=C_SUBTEXT, ha="center", va="center", fontfamily="sans-serif", style="italic")

    fig.savefig(OUT_DIR / "egfrviii_pilot.png", dpi=200, bbox_inches="tight",
                facecolor=C_BG, edgecolor="none")
    plt.close(fig)
    print(f"  ✓ {OUT_DIR / 'egfrviii_pilot.png'}")


def draw_target_comparison():
    """Draw a 4-target comparison grid."""
    fig, ax = plt.subplots(1, 1, figsize=(16, 7), facecolor=C_BG)
    ax.set_facecolor(C_BG)
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 7)
    ax.axis("off")

    ax.text(8, 6.6, "SyFlow NDC Target Portfolio", fontsize=20, fontweight="bold",
            color=C_TEXT, ha="center", va="center", fontfamily="sans-serif")

    targets = [
        ("EGFRvIII", "Surface neoantigen", "GBM / NSCLC", "Direct NDC",
         "PILOT", C_GO, [
             "✓ Tumor-specific (Δexon 2-7)",
             "✓ Constitutive internalization",
             "✓ 34E5 reference VHH exists",
             "⚠ Live-cell selectivity unknown",
             "⚠ Heterogeneity & antigen loss",
         ]),
        ("TAK1", "Intracellular kinase", "AML / Pancreatic", "Indirect NDC",
         "ACTIVE", C_HOLD, [
             "○ TAK1 inhibitor as payload",
             "○ TROP2/CLDN18.2 as receptor",
             "⚠ Payload potency (~10 nM)",
             "⚠ Co-expression validation needed",
             "✓ TROP2-ADC clinical precedent",
         ]),
        ("RhoA", "Intracellular GTPase", "Gastric / PTCL", "Indirect NDC",
         "REFERENCE", C_HOLD, [
             "○ ROCK inhibitor payload",
             "○ EphA2/CXCR4 as receptor",
             "✓ Crystal structures (9VNG)",
             "✓ LigandMPNN designs exist",
             "⚠ Systemic ROCK inhibition risk",
         ]),
        ("PNPLA3", "Lipid droplet protein", "NASH / MAFLD", "Small molecule",
         "NO-GO for NDC", C_NOGO, [
             "✗ No extracellular domain",
             "✗ Not a membrane target",
             "✓ I148M variant validated",
             "✓ Nesso docking data exists",
             "→ GalNAc-siRNA competitors",
         ]),
    ]

    for i, (name, loc, indication, modality, status, color, items) in enumerate(targets):
        x = 0.5 + i * 3.9
        w, h = 3.5, 5.2

        box = FancyBboxPatch((x, 0.8), w, h, boxstyle="round,pad=0.12",
                             facecolor=color + "12", edgecolor=color, linewidth=2)
        ax.add_patch(box)

        # Status badge
        badge = FancyBboxPatch((x + w / 2 - 0.8, 5.7), 1.6, 0.35,
                               boxstyle="round,pad=0.06",
                               facecolor=color, edgecolor=color, linewidth=0)
        ax.add_patch(badge)
        ax.text(x + w / 2, 5.87, status, fontsize=8, fontweight="bold",
                color="white", ha="center", va="center", fontfamily="sans-serif")

        ax.text(x + w / 2, 5.35, name, fontsize=14, fontweight="bold",
                color=color, ha="center", va="center", fontfamily="sans-serif")
        ax.text(x + w / 2, 5.0, loc, fontsize=9, color=C_TEXT,
                ha="center", va="center", fontfamily="sans-serif")
        ax.text(x + w / 2, 4.7, indication, fontsize=8, color=C_SUBTEXT,
                ha="center", va="center", fontfamily="sans-serif")
        ax.text(x + w / 2, 4.35, modality, fontsize=9, fontweight="bold", color=C_TEXT,
                ha="center", va="center", fontfamily="sans-serif",
                bbox=dict(boxstyle="round,pad=0.12", facecolor="#0F1419", edgecolor=C_BORDER, linewidth=0.8))

        for j, item in enumerate(items):
            ic = C_GO if item.startswith("✓") else C_NOGO if item.startswith("✗") else C_HOLD if item.startswith("⚠") else C_SUBTEXT
            ax.text(x + 0.2, 3.7 - j * 0.5, item, fontsize=8, color=ic,
                    ha="left", va="center", fontfamily="sans-serif")

    fig.savefig(OUT_DIR / "target_portfolio.png", dpi=200, bbox_inches="tight",
                facecolor=C_BG, edgecolor="none")
    plt.close(fig)
    print(f"  ✓ {OUT_DIR / 'target_portfolio.png'}")


# ─── PowerPoint generation ───────────────────────────────────────────────────

def hex_to_rgb(hex_str):
    h = hex_str.lstrip("#")
    return RGBColor(int(h[:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def set_slide_bg(slide, hex_color):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = hex_to_rgb(hex_color)


def add_text_box(slide, left, top, width, height, text, font_size=18,
                 bold=False, color="#E8ECF1", alignment=PP_ALIGN.LEFT, font_name="Calibri"):
    txBox = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.bold = bold
    p.font.color.rgb = hex_to_rgb(color)
    p.font.name = font_name
    p.alignment = alignment
    return txBox


def add_bullet_slide(slide, items, start_top=2.0, font_size=14, color="#E8ECF1"):
    for i, item in enumerate(items):
        y = start_top + i * 0.45
        add_text_box(slide, 0.8, y, 8.5, 0.4, f"• {item}", font_size=font_size, color=color)


def create_ppt():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # ── Slide 1: Title ──
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    set_slide_bg(slide, C_BG)
    add_text_box(slide, 1, 1.5, 11, 1.5, "SyFlow NDC Go/No-Go Platform",
                 font_size=40, bold=True, color=C_CSO, alignment=PP_ALIGN.CENTER)
    add_text_box(slide, 1, 3.0, 11, 1, "Provenance-first decision framework for nanobody-drug conjugate development",
                 font_size=20, color=C_SUBTEXT, alignment=PP_ALIGN.CENTER)
    add_text_box(slide, 1, 4.2, 11, 0.5, "Adapted from Stanford Virtual Biotech review-and-audit pattern",
                 font_size=14, color=C_SUBTEXT, alignment=PP_ALIGN.CENTER)
    add_text_box(slide, 1, 5.5, 11, 0.5, "Targets: EGFRvIII (pilot) · TAK1 · RhoA · PNPLA3",
                 font_size=16, bold=True, color=C_TEXT, alignment=PP_ALIGN.CENTER)
    add_text_box(slide, 1, 6.2, 11, 0.5, "RTX 5080 GPU + Claude API · September 2026",
                 font_size=12, color=C_SUBTEXT, alignment=PP_ALIGN.CENTER)

    # ── Slide 2: Agent Architecture ──
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, C_BG)
    img_path = OUT_DIR / "agent_architecture.png"
    slide.shapes.add_picture(str(img_path), Inches(0.3), Inches(0.2), Inches(12.7), Inches(7.1))

    # ── Slide 3: Gate Workflow ──
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, C_BG)
    img_path = OUT_DIR / "gate_workflow.png"
    slide.shapes.add_picture(str(img_path), Inches(0.3), Inches(0.2), Inches(12.7), Inches(7.1))

    # ── Slide 4: Target Portfolio ──
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, C_BG)
    img_path = OUT_DIR / "target_portfolio.png"
    slide.shapes.add_picture(str(img_path), Inches(0.3), Inches(0.2), Inches(12.7), Inches(7.1))

    # ── Slide 5: EGFRvIII Pilot ──
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, C_BG)
    img_path = OUT_DIR / "egfrviii_pilot.png"
    slide.shapes.add_picture(str(img_path), Inches(0.3), Inches(0.2), Inches(12.7), Inches(7.1))

    # ── Slide 6: GPU vs API Execution Options ──
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, C_BG)
    add_text_box(slide, 0.5, 0.3, 12, 0.8, "SyFlow Nano: Execution Options",
                 font_size=28, bold=True, color=C_CSO, alignment=PP_ALIGN.LEFT)

    # Option A: Local GPU
    add_text_box(slide, 0.5, 1.2, 5.8, 0.5, "Option A: RTX 5080 (Local GPU)", font_size=18, bold=True, color=C_GO)
    gpu_items = [
        "RFdiffusion / RFOptimization binder generation (CUDA sm_120)",
        "LigandMPNN sequence design (existing rhoa_pipeline)",
        "Boltz-2 / Nesso structure prediction & docking",
        "GNINA molecular docking & rescoring",
        "ESMFold / ESM-2 sequence embeddings",
        "Local inference: ~16 GB VRAM, fits single-chain VHH models",
        "Batch processing: run overnight, feed results to SyFlow DMTA",
    ]
    for i, item in enumerate(gpu_items):
        add_text_box(slide, 0.8, 1.8 + i * 0.4, 5.5, 0.35, f"• {item}", font_size=11, color=C_TEXT)

    # Option B: Claude API
    add_text_box(slide, 6.8, 1.2, 5.8, 0.5, "Option B: Claude API (Agent Orchestration)", font_size=18, bold=True, color=C_NANO)
    api_items = [
        "CSO agent orchestration (Sonnet 4.6 — plan, dispatch, synthesize)",
        "Specialist agents: target, nanobody, delivery, conjugation, safety",
        "Scientific reviewer (Haiku 4.5 — cost-efficient QA)",
        "MCP data tools: Open Targets, PubMed, ChEMBL, Clinical Trials",
        "Evidence gathering, literature review, competitive intelligence",
        "Gate assessment: claim recording, provenance tracking, audit",
        "Closed-loop DMTA: prediction → experiment → feedback → next cycle",
    ]
    for i, item in enumerate(api_items):
        add_text_box(slide, 7.1, 1.8 + i * 0.4, 5.5, 0.35, f"• {item}", font_size=11, color=C_TEXT)

    # Combined workflow
    add_text_box(slide, 0.5, 5.2, 12, 0.5, "Combined Workflow: GPU generates candidates → API agents validate → GPU tests → API audits",
                 font_size=16, bold=True, color=C_DELIVERY, alignment=PP_ALIGN.CENTER)

    add_text_box(slide, 0.5, 5.8, 12, 1.2,
                 "GPU (SyFlow Nano): RFdiffusion designs VHH binders → LigandMPNN optimizes sequences → "
                 "Boltz-2 predicts structures → GNINA scores binding\n"
                 "API (SyFlow Agents): CSO reviews computational results → specialists gather literature/clinical evidence → "
                 "reviewer audits claims → gate decision recorded with provenance",
                 font_size=11, color=C_SUBTEXT)

    # ── Slide 7: To-Do List ──
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, C_BG)
    add_text_box(slide, 0.5, 0.3, 12, 0.8, "SyFlow Nano: Implementation To-Do List",
                 font_size=28, bold=True, color=C_CSO, alignment=PP_ALIGN.LEFT)

    # Phase 1
    add_text_box(slide, 0.5, 1.1, 6, 0.4, "Phase 1 — Infrastructure (Week 1)", font_size=16, bold=True, color=C_TARGET)
    p1 = [
        "☐ Set ANTHROPIC_API_KEY in .env",
        "☐ conda env create -f environment.yml",
        "☐ Verify RTX 5080 CUDA: torch.cuda.get_device_name(0)",
        "☐ Install RFdiffusion with sm_120 PyTorch nightly (cu128)",
        "☐ Run: python setup_mcp.py → mcp_config.json",
        "☐ Test: python run_syflow.py validate --target egfrviii",
    ]
    for i, item in enumerate(p1):
        add_text_box(slide, 0.7, 1.55 + i * 0.33, 5.5, 0.3, item, font_size=10, color=C_TEXT)

    # Phase 2
    add_text_box(slide, 0.5, 3.6, 6, 0.4, "Phase 2 — EGFRvIII Pilot (Weeks 2-4)", font_size=16, bold=True, color=C_NANO)
    p2 = [
        "☐ Run G0 gate: python run_syflow.py gate --target egfrviii --gate G0",
        "☐ GPU: RFdiffusion → generate EGFRvIII VHH candidates",
        "☐ GPU: LigandMPNN → optimize binder sequences",
        "☐ GPU: Boltz-2 → predict VHH-EGFRvIII complex structures",
        "☐ GPU: GNINA → score binding poses, rank candidates",
        "☐ Freeze predictions in SyFlow DMTA before experiments",
        "☐ API: Run full validation with Claude agents (all gates)",
        "☐ Compare agent predictions against 34E5 reference data",
    ]
    for i, item in enumerate(p2):
        add_text_box(slide, 0.7, 4.05 + i * 0.33, 5.8, 0.3, item, font_size=10, color=C_TEXT)

    # Phase 3
    add_text_box(slide, 6.8, 1.1, 6, 0.4, "Phase 3 — Multi-Target Expansion (Weeks 5-8)", font_size=16, bold=True, color=C_DELIVERY)
    p3 = [
        "☐ TAK1: Identify TROP2/CLDN18.2 VHH candidates (GPU)",
        "☐ TAK1: API agents assess indirect NDC feasibility",
        "☐ RhoA: Extend LigandMPNN designs to NDC context",
        "☐ RhoA: API agents evaluate EphA2/CXCR4 targeting",
        "☐ PNPLA3: Confirm No-Go for NDC (API gate assessment)",
        "☐ PNPLA3: Redirect to small molecule pipeline",
        "☐ Cross-target: Compare gate outcomes, calibrate thresholds",
    ]
    for i, item in enumerate(p3):
        add_text_box(slide, 7.0, 1.55 + i * 0.33, 5.8, 0.3, item, font_size=10, color=C_TEXT)

    # Phase 4
    add_text_box(slide, 6.8, 3.9, 6, 0.4, "Phase 4 — Closed-Loop DMTA (Weeks 9-12)", font_size=16, bold=True, color=C_TRANS)
    p4 = [
        "☐ Feed wet-lab results (if available) into SyFlow claims",
        "☐ Reviewer: which predictions survived / failed?",
        "☐ Update dossiers with measured data + ELN references",
        "☐ Re-run gate assessments with new evidence",
        "☐ Record first complete DMTA loop with audit trail",
        "☐ Retrospective: replay prior runs, score prediction accuracy",
        "☐ Publication: document decision framework and pilot results",
    ]
    for i, item in enumerate(p4):
        add_text_box(slide, 7.0, 4.35 + i * 0.33, 5.8, 0.3, item, font_size=10, color=C_TEXT)

    # GPU specs note
    add_text_box(slide, 0.5, 6.8, 12, 0.4,
                 "RTX 5080: 16 GB VRAM · sm_120 · PyTorch nightly cu128 · Sufficient for single-chain VHH design + docking · "
                 "Multi-chain complexes may need batch splitting",
                 font_size=9, color=C_SUBTEXT, alignment=PP_ALIGN.CENTER)

    # ── Slide 8: Key Decisions ──
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, C_BG)
    add_text_box(slide, 0.5, 0.3, 12, 0.8, "Key Design Decisions",
                 font_size=28, bold=True, color=C_CSO, alignment=PP_ALIGN.LEFT)

    decisions = [
        ("Evidence hierarchy, not agent count", "A model score cannot replace a missing assay. Gate thresholds set before experiments, not after.", C_TARGET),
        ("Correct No-Gos are successes", "PNPLA3 should fail at G0. ABT-414 teaches that WT EGFR cross-reactivity kills ADC programs.", C_NOGO),
        ("Provenance from execution, not self-report", "Trace-based attribution. Agents cannot misattribute their own work. SHA-256 manifest.", C_DELIVERY),
        ("GPU + API = closed loop", "GPU generates candidates (RFdiffusion → LigandMPNN → Boltz-2 → GNINA). API agents validate, audit, decide.", C_NANO),
        ("The unit of work is the dossier", "Indication × antigen × VHH × conjugation × linker-payload × batch. One decision per dossier.", C_CONJ),
        ("Reviewer cannot write, CSO cannot query", "Enforced separation. Reviewer is read-only. CSO delegates all analysis to specialists.", C_REVIEW),
    ]

    for i, (title, desc, color) in enumerate(decisions):
        y = 1.3 + i * 0.95
        add_text_box(slide, 0.8, y, 11, 0.35, title, font_size=15, bold=True, color=color)
        add_text_box(slide, 0.8, y + 0.35, 11, 0.35, desc, font_size=11, color=C_SUBTEXT)

    # Save
    ppt_path = Path(__file__).parent / "SyFlow_NDC_Workflow.pptx"
    prs.save(str(ppt_path))
    print(f"\n✓ Presentation saved: {ppt_path}")
    return ppt_path


# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Generating SyFlow NDC workflow figures...")
    draw_agent_architecture()
    draw_gate_workflow()
    draw_egfrviii_pilot()
    draw_target_comparison()
    print("\nGenerating PowerPoint presentation...")
    ppt_path = create_ppt()
    print(f"\nDone! Open: {ppt_path}")
