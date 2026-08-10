"""Visual theme for the OPC UA drafts overview deck.

Colours, fonts and geometry live here so ``build_deck.py`` stays about structure.
Nothing in this module reads the content YAML.
"""

from __future__ import annotations

from dataclasses import dataclass

from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

SLIDE_WIDTH = Inches(13.333)
SLIDE_HEIGHT = Inches(7.5)

BLUE_DEEP = RGBColor(0x00, 0x2B, 0x49)
BLUE = RGBColor(0x00, 0x5A, 0x9C)
BLUE_LIGHT = RGBColor(0x4A, 0x90, 0xC2)
BLUE_PALE = RGBColor(0xE8, 0xF1, 0xF8)
ACCENT = RGBColor(0xF2, 0x99, 0x00)
ACCENT_DARK = RGBColor(0xB8, 0x73, 0x00)
GREY_TEXT = RGBColor(0x33, 0x3B, 0x44)
GREY_MUTED = RGBColor(0x6B, 0x74, 0x80)
GREY_RULE = RGBColor(0xD5, 0xDB, 0xE1)
GREY_PANEL = RGBColor(0xF4, 0xF6, 0xF8)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GREEN = RGBColor(0x2E, 0x7D, 0x4F)
RED = RGBColor(0xB3, 0x2D, 0x2D)

FONT_HEAD = "Segoe UI Semibold"
FONT_BODY = "Segoe UI"
FONT_MONO = "Consolas"

MARGIN_L = Inches(0.75)
MARGIN_R = Inches(0.75)
CONTENT_W = SLIDE_WIDTH - MARGIN_L - MARGIN_R
TITLE_TOP = Inches(0.45)
TITLE_H = Inches(0.80)
KICKER_TOP = Inches(1.22)
KICKER_H = Inches(0.34)
BODY_TOP = Inches(1.74)
BODY_H = Inches(5.00)
FOOTER_TOP = Inches(6.90)
FOOTER_H = Inches(0.36)

SIZE_TITLE = Pt(30)
SIZE_KICKER = Pt(13)
SIZE_BULLET_1 = Pt(17)
SIZE_BULLET_2 = Pt(14)
SIZE_BULLET_3 = Pt(12)
SIZE_TABLE = Pt(11)
SIZE_FOOTER = Pt(9)
SIZE_CODE = Pt(12)

BULLET_SIZES = {0: SIZE_BULLET_1, 1: SIZE_BULLET_2, 2: SIZE_BULLET_3}
BULLET_INDENT = {0: Inches(0.0), 1: Inches(0.32), 2: Inches(0.64)}
BULLET_MARKS = {0: "\u25a0", 1: "\u2013", 2: "\u00b7"}

DISCLAIMER = (
    "Working draft \u2014 not normative, not endorsed by the OPC Foundation. "
    "Namespace URIs and NodeIds are provisional."
)


@dataclass(frozen=True)
class SectionStyle:
    """
    Per-tree accent so a viewer can tell the trees apart at a glance.
    """

    key: str
    label: str
    color: RGBColor


SECTIONS: dict[str, SectionStyle] = {
    "front": SectionStyle("front", "Overview", BLUE_DEEP),
    "core": SectionStyle("core", "core \u2014 additions to the base namespace", BLUE),
    "cloud": SectionStyle(
        "cloud", "cloud \u2014 the Server's cloud-facing surface", RGBColor(0x1C, 0x6E, 0x8C)
    ),
    "metaverse": SectionStyle(
        "metaverse",
        "metaverse \u2014 worlds, perception, robot control",
        RGBColor(0x5B, 0x3E, 0x96),
    ),
    "wot": SectionStyle("wot", "wot \u2014 Web of Things", RGBColor(0x0B, 0x6E, 0x5E)),
    "companion": SectionStyle(
        "companion", "companion \u2014 domain specifications", RGBColor(0x8C, 0x4A, 0x1C)
    ),
    "stack": SectionStyle(
        "stack", "the reference implementation", RGBColor(0x1F, 0x4E, 0x79)
    ),
    "close": SectionStyle("close", "Where this goes next", BLUE_DEEP),
}

STATUS_COLORS = {
    "draft": BLUE,
    "review": ACCENT_DARK,
    "proposed": RGBColor(0x5B, 0x3E, 0x96),
}

DEMO_STATE_COLORS = {
    "master": GREEN,
    "branch": ACCENT_DARK,
    "walkthrough": GREY_MUTED,
}


def section_style(key: str) -> SectionStyle:
    """
    Resolve a section key to its style, falling back to the front-matter style.
    """
    return SECTIONS.get(key, SECTIONS["front"])
