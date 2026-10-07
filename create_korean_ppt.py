#!/usr/bin/env python3
"""Generate Korean-language SyFlow NDC Go/No-Go workflow presentation.

Creates an 8-slide widescreen (13.333 x 7.5 in) PowerPoint with dark background,
matching the visual style of the English version. All text content is in Korean.
Reuses existing figure PNGs for slides 2-5.
"""
from __future__ import annotations

from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

FIGURES_DIR = Path(__file__).parent / "figures"

# ─── Color palette ───────────────────────────────────────────────────────────
C_BG      = "#0F1419"
C_CARD    = "#1A2332"
C_BORDER  = "#2D3F54"
C_TEXT    = "#E8ECF1"
C_SUBTEXT = "#8899AA"
C_CSO     = "#6366F1"   # Indigo
C_TARGET  = "#10B981"   # Emerald / Green
C_NANO    = "#F59E0B"   # Amber
C_DELIVERY= "#3B82F6"   # Blue
C_CONJ    = "#EF4444"   # Red
C_TRANS   = "#8B5CF6"   # Purple
C_REVIEW  = "#EC4899"   # Pink
C_GO      = "#10B981"
C_HOLD    = "#F59E0B"
C_NOGO    = "#EF4444"

# Korean font: try Malgun Gothic first, fallback to Noto Sans CJK KR
KR_FONT = "Malgun Gothic"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def hex_to_rgb(hex_str: str) -> RGBColor:
    h = hex_str.lstrip("#")
    return RGBColor(int(h[:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def set_slide_bg(slide, hex_color: str):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = hex_to_rgb(hex_color)


def add_text_box(slide, left, top, width, height, text,
                 font_size=18, bold=False, color="#E8ECF1",
                 alignment=PP_ALIGN.LEFT, font_name=KR_FONT):
    txBox = slide.shapes.add_textbox(
        Inches(left), Inches(top), Inches(width), Inches(height)
    )
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


def add_rounded_rect(slide, left, top, width, height, fill_color, line_color=None):
    """Add a rounded rectangle shape with fill (and optional border)."""
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(left), Inches(top), Inches(width), Inches(height),
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = hex_to_rgb(fill_color)
    if line_color:
        shape.line.color.rgb = hex_to_rgb(line_color)
        shape.line.width = Pt(1.5)
    else:
        shape.line.fill.background()
    return shape


# ─── Slide builders ──────────────────────────────────────────────────────────

def slide_1_title(prs):
    """Slide 1 -- Title slide."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    set_slide_bg(slide, C_BG)

    add_text_box(slide, 1, 1.2, 11.333, 1.2,
                 "SyFlow NDC Go/No-Go \ud50c\ub7ab\ud3fc",
                 font_size=42, bold=True, color=C_CSO, alignment=PP_ALIGN.CENTER)

    add_text_box(slide, 1, 2.6, 11.333, 0.8,
                 "\ub098\ub178\ubc14\ub514 \uc57d\ubb3c \uc811\ud569\uccb4 \uac1c\ubc1c\uc744 \uc704\ud55c \ucd9c\ucc98\ucd94\uc801 \uae30\ubc18 \uc758\uc0ac\uacb0\uc815 \ud504\ub808\uc784\uc6cc\ud06c",
                 font_size=20, color=C_SUBTEXT, alignment=PP_ALIGN.CENTER)

    add_text_box(slide, 1, 3.6, 11.333, 0.6,
                 "\uc2a4\ud0e0\ud3ec\ub4dc Virtual Biotech\uc758 \uac80\ud1a0-\uac10\uc0ac \ud328\ud134 \uc801\uc6a9",
                 font_size=14, color=C_SUBTEXT, alignment=PP_ALIGN.CENTER)

    add_text_box(slide, 1, 4.8, 11.333, 0.6,
                 "\ud0c0\uac9f: EGFRvIII (\ud30c\uc77c\ub7ff) \xb7 TAK1 \xb7 RhoA \xb7 PNPLA3",
                 font_size=16, bold=True, color=C_TEXT, alignment=PP_ALIGN.CENTER)

    add_text_box(slide, 1, 5.8, 11.333, 0.5,
                 "RTX 5080 GPU + Claude API \xb7 2026\ub144 10\uc6d4",
                 font_size=12, color=C_SUBTEXT, alignment=PP_ALIGN.CENTER)


def slide_2_agent_arch(prs):
    """Slide 2 -- Agent Architecture (figure)."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, C_BG)

    # Slide title
    add_text_box(slide, 0.5, 0.15, 12, 0.5,
                 "\uc5d0\uc774\uc804\ud2b8 \uc544\ud0a4\ud14d\ucc98",
                 font_size=14, bold=True, color=C_CSO, alignment=PP_ALIGN.LEFT)

    img_path = FIGURES_DIR / "agent_architecture.png"
    slide.shapes.add_picture(str(img_path), Inches(0.3), Inches(0.5), Inches(12.7), Inches(6.8))


def slide_3_gate_workflow(prs):
    """Slide 3 -- Gate Workflow (figure)."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, C_BG)

    add_text_box(slide, 0.5, 0.15, 12, 0.5,
                 "\uac8c\uc774\ud2b8 \uc6cc\ud06c\ud50c\ub85c\uc6b0",
                 font_size=14, bold=True, color=C_CSO, alignment=PP_ALIGN.LEFT)

    img_path = FIGURES_DIR / "gate_workflow.png"
    slide.shapes.add_picture(str(img_path), Inches(0.3), Inches(0.5), Inches(12.7), Inches(6.8))


def slide_4_target_portfolio(prs):
    """Slide 4 -- Target Portfolio (figure)."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, C_BG)

    add_text_box(slide, 0.5, 0.15, 12, 0.5,
                 "\ud0c0\uac9f \ud3ec\ud2b8\ud3f4\ub9ac\uc624",
                 font_size=14, bold=True, color=C_CSO, alignment=PP_ALIGN.LEFT)

    img_path = FIGURES_DIR / "target_portfolio.png"
    slide.shapes.add_picture(str(img_path), Inches(0.3), Inches(0.5), Inches(12.7), Inches(6.8))


def slide_5_egfrviii_pilot(prs):
    """Slide 5 -- EGFRvIII Pilot (figure)."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, C_BG)

    add_text_box(slide, 0.5, 0.15, 12, 0.5,
                 "EGFRvIII \ud30c\uc77c\ub7ff \ud504\ub85c\ud1a0\ucf5c",
                 font_size=14, bold=True, color=C_CSO, alignment=PP_ALIGN.LEFT)

    img_path = FIGURES_DIR / "egfrviii_pilot.png"
    slide.shapes.add_picture(str(img_path), Inches(0.3), Inches(0.5), Inches(12.7), Inches(6.8))


def slide_6_gpu_api(prs):
    """Slide 6 -- GPU vs API execution options (Korean)."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, C_BG)

    add_text_box(slide, 0.5, 0.2, 12, 0.7,
                 "GPU vs API \uc2e4\ud589 \uc635\uc158",
                 font_size=28, bold=True, color=C_CSO, alignment=PP_ALIGN.LEFT)

    # --- Option A: Local GPU ---
    add_rounded_rect(slide, 0.4, 1.1, 6.1, 3.5, "#10B98108", C_GO)
    add_text_box(slide, 0.5, 1.15, 5.8, 0.45,
                 "\uc635\uc158 A: RTX 5080 (\ub85c\ucee8 GPU)",
                 font_size=17, bold=True, color=C_GO)

    gpu_items = [
        "RFdiffusion / RFOptimization \ubc14\uc778\ub354 \uc0dd\uc131 (CUDA sm_120)",
        "LigandMPNN \uc2dc\ud000\uc2a4 \uc124\uacc4 (\uae30\uc874 rhoa_pipeline)",
        "Boltz-2 / Nesso \uad6c\uc870 \uc608\uce21 \ubc0f \ub3c4\ud0b9",
        "GNINA \ubd84\uc790 \ub3c4\ud0b9 \ubc0f \uc7ac\uc2a4\ucf54\uc5b4\ub9c1",
        "ESMFold / ESM-2 \uc2dc\ud000\uc2a4 \uc784\ubca0\ub529",
        "\ub85c\ucee8 \ucd94\ub860: ~16 GB VRAM, \ub2e8\uc77c \uc0ac\uc2ac VHH \ubaa8\ub378 \uc801\ud569",
        "\ubc30\uce58 \ucc98\ub9ac: \uc57c\uac04 \uc2e4\ud589 \ud6c4 SyFlow DMTA\uc5d0 \uacb0\uacfc \uc804\ub2ec",
    ]
    for i, item in enumerate(gpu_items):
        add_text_box(slide, 0.7, 1.65 + i * 0.4, 5.6, 0.35,
                     f"\u2022 {item}", font_size=10, color=C_TEXT)

    # --- Option B: Claude API ---
    add_rounded_rect(slide, 6.8, 1.1, 6.1, 3.5, "#F59E0B08", C_NANO)
    add_text_box(slide, 6.9, 1.15, 5.8, 0.45,
                 "\uc635\uc158 B: Claude API (\uc5d0\uc774\uc804\ud2b8 \uc624\ucf00\uc2a4\ud2b8\ub808\uc774\uc158)",
                 font_size=17, bold=True, color=C_NANO)

    api_items = [
        "CSO \uc5d0\uc774\uc804\ud2b8 \uc624\ucf00\uc2a4\ud2b8\ub808\uc774\uc158 (Sonnet 4.6 \u2014 \uacc4\ud68d, \ubc30\uce58, \uc885\ud569)",
        "\uc804\ubb38\uac00 \uc5d0\uc774\uc804\ud2b8: \ud0c0\uac9f, \ub098\ub178\ubc14\ub514, \uc804\ub2ec, \uc811\ud569, \uc548\uc804\uc131",
        "\uacfc\ud559 \uc2ec\uc0ac\uad00 (Haiku 4.5 \u2014 \ube44\uc6a9 \ud6a8\uc728\uc801 QA)",
        "MCP \ub370\uc774\ud130 \ub3c4\uad6c: Open Targets, PubMed, ChEMBL, Clinical Trials",
        "\uc99d\uac70 \uc218\uc9d1, \ubb38\ud5cc \uac80\ud1a0, \uacbd\uc7c1 \uc815\ubcf4 \ubd84\uc11d",
        "\uac8c\uc774\ud2b8 \ud3c9\uac00: \uc8fc\uc7a5 \uae30\ub85d, \ucd9c\ucc98 \ucd94\uc801, \uac10\uc0ac",
        "\ud3d0\uc1c4\ud615 DMTA: \uc608\uce21 \u2192 \uc2e4\ud5d8 \u2192 \ud53c\ub4dc\ubc31 \u2192 \ub2e4\uc74c \uc0ac\uc774\ud074",
    ]
    for i, item in enumerate(api_items):
        add_text_box(slide, 7.1, 1.65 + i * 0.4, 5.6, 0.35,
                     f"\u2022 {item}", font_size=10, color=C_TEXT)

    # --- Combined workflow ---
    add_rounded_rect(slide, 0.4, 4.85, 12.5, 0.55, "#3B82F618", C_DELIVERY)
    add_text_box(slide, 0.5, 4.9, 12.3, 0.45,
                 "\ud1b5\ud569 \uc6cc\ud06c\ud50c\ub85c\uc6b0: GPU\uac00 \ud6c4\ubcf4\ubb3c\uc9c8 \uc0dd\uc131 \u2192 API \uc5d0\uc774\uc804\ud2b8\uac00 \uac80\uc99d \u2192 GPU \ud14c\uc2a4\ud2b8 \u2192 API \uac10\uc0ac",
                 font_size=15, bold=True, color=C_DELIVERY, alignment=PP_ALIGN.CENTER)

    # GPU detail line
    add_text_box(slide, 0.5, 5.55, 12.3, 0.4,
                 "GPU (SyFlow Nano): RFdiffusion\uc774 VHH \ubc14\uc778\ub354 \uc124\uacc4 \u2192 LigandMPNN\uc774 \uc2dc\ud000\uc2a4 \ucd5c\uc801\ud654 \u2192 "
                 "Boltz-2\uac00 \uad6c\uc870 \uc608\uce21 \u2192 GNINA\uac00 \uacb0\ud569 \uc2a4\ucf54\uc5b4\ub9c1",
                 font_size=10, color=C_SUBTEXT, alignment=PP_ALIGN.CENTER)

    # API detail line
    add_text_box(slide, 0.5, 5.95, 12.3, 0.4,
                 "API (SyFlow Agents): CSO\uac00 \uacc4\uc0b0 \uacb0\uacfc \uac80\ud1a0 \u2192 \uc804\ubb38\uac00\uac00 \ubb38\ud5cc/\uc784\uc0c1 \uc99d\uac70 \uc218\uc9d1 \u2192 "
                 "\uc2ec\uc0ac\uad00\uc774 \uc8fc\uc7a5 \uac10\uc0ac \u2192 \ucd9c\ucc98\ucd94\uc801\uacfc \ud568\uaed8 \uac8c\uc774\ud2b8 \uacb0\uc815 \uae30\ub85d",
                 font_size=10, color=C_SUBTEXT, alignment=PP_ALIGN.CENTER)


def slide_7_todo(prs):
    """Slide 7 -- To-Do List in Korean."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, C_BG)

    add_text_box(slide, 0.5, 0.15, 12, 0.6,
                 "\ud560 \uc77c \ubaa9\ub85d",
                 font_size=28, bold=True, color=C_CSO, alignment=PP_ALIGN.LEFT)

    # ── Phase 1 ──
    add_text_box(slide, 0.4, 0.85, 6.0, 0.35,
                 "1\ub2e8\uacc4 \u2014 \uc778\ud504\ub77c \uad6c\ucd95 (1\uc8fc\ucc28)",
                 font_size=14, bold=True, color=C_TARGET)
    p1 = [
        "\u2610 .env\uc5d0 ANTHROPIC_API_KEY \uc124\uc815",
        "\u2610 conda env create -f environment.yml",
        "\u2610 RTX 5080 CUDA \ud655\uc778: torch.cuda.get_device_name(0)",
        "\u2610 sm_120 PyTorch nightly (cu128)\ub85c RFdiffusion \uc124\uce58",
        "\u2610 \uc2e4\ud589: python setup_mcp.py \u2192 mcp_config.json",
        "\u2610 \ud14c\uc2a4\ud2b8: python run_syflow.py validate --target egfrviii",
    ]
    for i, item in enumerate(p1):
        add_text_box(slide, 0.6, 1.22 + i * 0.3, 5.8, 0.28, item, font_size=9, color=C_TEXT)

    # ── Phase 2 ──
    add_text_box(slide, 0.4, 3.1, 6.0, 0.35,
                 "2\ub2e8\uacc4 \u2014 EGFRvIII \ud30c\uc77c\ub7ff (2-4\uc8fc\ucc28)",
                 font_size=14, bold=True, color=C_NANO)
    p2 = [
        "\u2610 G0 \uac8c\uc774\ud2b8 \uc2e4\ud589: python run_syflow.py gate --target egfrviii --gate G0",
        "\u2610 GPU: RFdiffusion \u2192 EGFRvIII VHH \ud6c4\ubcf4\ubb3c\uc9c8 \uc0dd\uc131",
        "\u2610 GPU: LigandMPNN \u2192 \ubc14\uc778\ub354 \uc2dc\ud000\uc2a4 \ucd5c\uc801\ud654",
        "\u2610 GPU: Boltz-2 \u2192 VHH-EGFRvIII \ubcf5\ud569\uccb4 \uad6c\uc870 \uc608\uce21",
        "\u2610 GPU: GNINA \u2192 \uacb0\ud569 \ud3ec\uc988 \uc2a4\ucf54\uc5b4\ub9c1, \ud6c4\ubcf4\ubb3c\uc9c8 \uc21c\uc704",
        "\u2610 \uc2e4\ud5d8 \uc804 SyFlow DMTA\uc5d0 \uc608\uce21 \ub3d9\uacb0",
        "\u2610 API: Claude \uc5d0\uc774\uc804\ud2b8\ub85c \uc804\uccb4 \uac80\uc99d \uc2e4\ud589 (\uc804\uccb4 \uac8c\uc774\ud2b8)",
        "\u2610 \uc5d0\uc774\uc804\ud2b8 \uc608\uce21\uacfc 34E5 \ucc38\uc870 \ub370\uc774\ud130 \ube44\uad50",
    ]
    for i, item in enumerate(p2):
        add_text_box(slide, 0.6, 3.47 + i * 0.3, 5.8, 0.28, item, font_size=9, color=C_TEXT)

    # ── Phase 3 ──
    add_text_box(slide, 6.8, 0.85, 6.0, 0.35,
                 "3\ub2e8\uacc4 \u2014 \ub2e4\uc911 \ud0c0\uac9f \ud655\uc7a5 (5-8\uc8fc\ucc28)",
                 font_size=14, bold=True, color=C_DELIVERY)
    p3 = [
        "\u2610 TAK1: TROP2/CLDN18.2 VHH \ud6c4\ubcf4\ubb3c\uc9c8 \ud0d0\uc0c9 (GPU)",
        "\u2610 TAK1: API \uc5d0\uc774\uc804\ud2b8\ub85c \uac04\uc811 NDC \uac00\ub2a5\uc131 \ud3c9\uac00",
        "\u2610 RhoA: LigandMPNN \uc124\uacc4\ub97c NDC \ub9e5\ub77d\uc73c\ub85c \ud655\uc7a5",
        "\u2610 RhoA: API \uc5d0\uc774\uc804\ud2b8\ub85c EphA2/CXCR4 \ud0c0\uac9f\ud305 \ud3c9\uac00",
        "\u2610 PNPLA3: NDC\uc5d0 \ub300\ud55c No-Go \ud655\uc778 (API \uac8c\uc774\ud2b8 \ud3c9\uac00)",
        "\u2610 PNPLA3: \uc800\ubd84\uc790 \ud30c\uc774\ud504\ub77c\uc778\uc73c\ub85c \uc804\ud658",
        "\u2610 \uad50\ucc28 \ud0c0\uac9f: \uac8c\uc774\ud2b8 \uacb0\uacfc \ube44\uad50, \uc784\uacc4\uac12 \ubcf4\uc815",
    ]
    for i, item in enumerate(p3):
        add_text_box(slide, 7.0, 1.22 + i * 0.3, 5.8, 0.28, item, font_size=9, color=C_TEXT)

    # ── Phase 4 ──
    add_text_box(slide, 6.8, 3.35, 6.0, 0.35,
                 "4\ub2e8\uacc4 \u2014 \ud3d0\uc1c4\ud615 DMTA (9-12\uc8fc\ucc28)",
                 font_size=14, bold=True, color=C_TRANS)
    p4 = [
        "\u2610 \uc2b5\uc2dd \uc2e4\ud5d8 \uacb0\uacfc\ub97c SyFlow \uc8fc\uc7a5\uc5d0 \uc785\ub825",
        "\u2610 \uc2ec\uc0ac\uad00: \uc5b4\ub5a4 \uc608\uce21\uc774 \uc0dd\uc874/\uc2e4\ud328\ud588\ub294\uac00?",
        "\u2610 \uce21\uc815 \ub370\uc774\ud130 + ELN \ucc38\uc870\ub85c \ub3c4\uc2dc\uc5d0 \uc5c5\ub370\uc774\ud2b8",
        "\u2610 \uc0c8\ub85c\uc6b4 \uc99d\uac70\ub85c \uac8c\uc774\ud2b8 \ud3c9\uac00 \uc7ac\uc2e4\ud589",
        "\u2610 \uac10\uc0ac \ucd94\uc801\uacfc \ud568\uaed8 \uccab \ubc88\uc9f8 \uc644\uc804\ud55c DMTA \ub8e8\ud504 \uae30\ub85d",
        "\u2610 \ud68c\uace0: \uc774\uc804 \uc2e4\ud589 \uc7ac\uc0dd, \uc608\uce21 \uc815\ud655\ub3c4 \ud3c9\uac00",
        "\u2610 \ucd9c\ud310: \uc758\uc0ac\uacb0\uc815 \ud504\ub808\uc784\uc6cc\ud06c \ubc0f \ud30c\uc77c\ub7ff \uacb0\uacfc \ubb38\uc11c\ud654",
    ]
    for i, item in enumerate(p4):
        add_text_box(slide, 7.0, 3.72 + i * 0.3, 5.8, 0.28, item, font_size=9, color=C_TEXT)

    # Bottom GPU note
    add_text_box(slide, 0.3, 6.7, 12.7, 0.4,
                 "RTX 5080: 16 GB VRAM \xb7 sm_120 \xb7 PyTorch nightly cu128 \xb7 "
                 "\ub2e8\uc77c \uc0ac\uc2ac VHH \uc124\uacc4 + \ub3c4\ud0b9\uc5d0 \ucda9\ubd84 \xb7 "
                 "\ub2e4\uc911 \uc0ac\uc2ac \ubcf5\ud569\uccb4\ub294 \ubc30\uce58 \ubd84\ud560 \ud544\uc694",
                 font_size=9, color=C_SUBTEXT, alignment=PP_ALIGN.CENTER)


def slide_8_key_decisions(prs):
    """Slide 8 -- Key Design Decisions in Korean."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, C_BG)

    add_text_box(slide, 0.5, 0.2, 12, 0.7,
                 "\ud575\uc2ec \uc124\uacc4 \uacb0\uc815",
                 font_size=28, bold=True, color=C_CSO, alignment=PP_ALIGN.LEFT)

    decisions = [
        ("\uc99d\uac70 \uacc4\uce35\uc774 \uc5d0\uc774\uc804\ud2b8 \uc218\ubcf4\ub2e4 \uc911\uc694\ud558\ub2e4",
         "\ubaa8\ub378 \uc810\uc218\ub294 \uc2e4\ud5d8\uc744 \ub300\uccb4\ud560 \uc218 \uc5c6\ub2e4. \uac8c\uc774\ud2b8 \uc784\uacc4\uac12\uc740 \uc2e4\ud5d8 \uc804\uc5d0 \uc124\uc815\ud55c\ub2e4.",
         C_TARGET),
        ("\uc62c\ubc14\ub978 No-Go\ub3c4 \uc131\uacf5\uc774\ub2e4",
         "PNPLA3\uc740 G0\uc5d0\uc11c \uc2e4\ud328\ud574\uc57c \ud55c\ub2e4. ABT-414\ub294 WT EGFR \uad50\ucc28\ubc18\uc751\uc774 ADC \ud504\ub85c\uadf8\ub7a8\uc744 \uc8fd\uc778\ub2e4\ub294 \uac83\uc744 \uac00\ub974\uccd0\uc900\ub2e4.",
         C_NOGO),
        ("\ucd9c\ucc98\ucd94\uc801\uc740 \uc2e4\ud589 \uae30\ub85d\uc5d0\uc11c, \uc790\uae30\ubcf4\uace0\uac00 \uc544\ub2cc",
         "\ud2b8\ub808\uc774\uc2a4 \uae30\ubc18 \uadc0\uc18d. \uc5d0\uc774\uc804\ud2b8\ub294 \uc790\uc2e0\uc758 \uc791\uc5c5\uc744 \uc798\ubabb \uadc0\uc18d\ud560 \uc218 \uc5c6\ub2e4. SHA-256 \ub9e4\ub2c8\ud398\uc2a4\ud2b8.",
         C_DELIVERY),
        ("GPU + API = \ud3d0\uc1c4\ud615 \ub8e8\ud504",
         "GPU\uac00 \ud6c4\ubcf4\ubb3c\uc9c8\uc744 \uc0dd\uc131\ud558\uace0 (RFdiffusion \u2192 LigandMPNN \u2192 Boltz-2 \u2192 GNINA), API \uc5d0\uc774\uc804\ud2b8\uac00 \uac80\uc99d, \uac10\uc0ac, \uacb0\uc815\ud55c\ub2e4.",
         C_NANO),
        ("\uc791\uc5c5\uc758 \ub2e8\uc704\ub294 \ub3c4\uc2dc\uc5d0\uc774\ub2e4",
         "\uc801\uc751\uc99d \xd7 \ud56d\uc6d0 \xd7 VHH \xd7 \uc811\ud569 \xd7 \ub9c1\ucee4-\ud398\uc774\ub85c\ub4dc \xd7 \ubc30\uce58. \ub3c4\uc2dc\uc5d0\ub2f9 \ud558\ub098\uc758 \uacb0\uc815.",
         C_CONJ),
        ("\uc2ec\uc0ac\uad00\uc740 \uc4f8 \uc218 \uc5c6\uace0, CSO\ub294 \ucffc\ub9ac\ud560 \uc218 \uc5c6\ub2e4",
         "\uac15\uc81c \ubd84\ub9ac. \uc2ec\uc0ac\uad00\uc740 \uc77d\uae30 \uc804\uc6a9. CSO\ub294 \ubaa8\ub4e0 \ubd84\uc11d\uc744 \uc804\ubb38\uac00\uc5d0\uac8c \uc704\uc784\ud55c\ub2e4.",
         C_REVIEW),
    ]

    for i, (title, desc, color) in enumerate(decisions):
        y = 1.15 + i * 1.0
        # Color accent bar
        add_rounded_rect(slide, 0.5, y, 0.08, 0.7, color)
        add_text_box(slide, 0.8, y, 11.5, 0.4, title,
                     font_size=16, bold=True, color=color)
        add_text_box(slide, 0.8, y + 0.4, 11.5, 0.4, desc,
                     font_size=11, color=C_SUBTEXT)


# ─── Main ────────────────────────────────────────────────────────────────────

def create_korean_ppt():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    print("Building Korean PPT slides...")
    slide_1_title(prs)
    print("  [1/8] Title slide")
    slide_2_agent_arch(prs)
    print("  [2/8] Agent Architecture")
    slide_3_gate_workflow(prs)
    print("  [3/8] Gate Workflow")
    slide_4_target_portfolio(prs)
    print("  [4/8] Target Portfolio")
    slide_5_egfrviii_pilot(prs)
    print("  [5/8] EGFRvIII Pilot")
    slide_6_gpu_api(prs)
    print("  [6/8] GPU vs API Options")
    slide_7_todo(prs)
    print("  [7/8] To-Do List")
    slide_8_key_decisions(prs)
    print("  [8/8] Key Design Decisions")

    out_path = Path(__file__).parent / "SyFlow_NDC_Workflow_KR.pptx"
    prs.save(str(out_path))
    print(f"\nSaved: {out_path}")
    return out_path


if __name__ == "__main__":
    create_korean_ppt()
