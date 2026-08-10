"""Structural checks on the generated deck.

There is no headless renderer in this repository, so overflow is estimated rather
than observed: for every text-bearing shape the checker measures how much text was
asked to fit and compares it against the space available.

    python decks/check_layout.py                  # check the default deck
    python decks/check_layout.py --deck other.pptx
    python decks/check_layout.py --strict         # non-zero exit on any finding

Findings are advisory. A slide flagged here is worth opening; a slide not flagged
is not guaranteed perfect.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from pptx import Presentation
from pptx.util import Emu, Pt

DEFAULT_DECK = Path(__file__).parent / "OPC-UA-Drafts-Overview.pptx"

# Segoe UI averages a little under 0.5 em per character across mixed-case prose.
AVG_CHAR_EM = 0.50
LINE_SPACING = 1.18
EMU_PER_PT = 12700


def shape_text_height(shape) -> float:
    """
    Estimate, in points, the height the text in ``shape`` needs at its own font sizes.
    """
    frame = shape.text_frame
    width_pt = (
        shape.width - frame.margin_left - frame.margin_right
    ) / EMU_PER_PT
    if width_pt <= 0:
        return 0.0
    total = (frame.margin_top + frame.margin_bottom) / EMU_PER_PT
    for para in frame.paragraphs:
        text = "".join(run.text for run in para.runs)
        size = max(
            [run.font.size.pt for run in para.runs if run.font.size is not None] or [18.0]
        )
        indent = 0.0
        p_pr = para._p.find("{http://schemas.openxmlformats.org/drawingml/2006/main}pPr")
        if p_pr is not None and p_pr.get("marL"):
            indent = int(p_pr.get("marL")) / EMU_PER_PT
        usable = max(width_pt - indent, size)
        chars_per_line = max(usable / (size * AVG_CHAR_EM), 1.0)
        lines = max(math.ceil(len(text) / chars_per_line), 1)
        spacing = para.line_spacing if isinstance(para.line_spacing, float) else LINE_SPACING
        total += lines * size * max(spacing, 1.0)
        if para.space_before is not None:
            total += para.space_before.pt
        if para.space_after is not None:
            total += para.space_after.pt
    return total


def check(deck_path: Path) -> list[str]:
    """
    Walk every slide and report shapes that overflow, sit off-slide, or run empty.
    """
    prs = Presentation(deck_path)
    width = prs.slide_width
    height = prs.slide_height
    findings: list[str] = []

    for index, slide in enumerate(prs.slides, start=1):
        title = ""
        for shape in slide.shapes:
            if shape.has_text_frame and shape.text_frame.text.strip():
                title = shape.text_frame.text.strip().split("\n")[0][:60]
                break

        for shape in slide.shapes:
            if shape.left is None or shape.top is None:
                continue
            if (
                shape.left < Emu(-1000)
                or shape.top < Emu(-1000)
                or shape.left + shape.width > width + Emu(1000)
                or shape.top + shape.height > height + Emu(1000)
            ):
                findings.append(
                    f"slide {index} ({title}): shape '{shape.shape_type}' extends past the slide"
                )
            if not shape.has_text_frame:
                continue
            text = shape.text_frame.text
            if not text.strip():
                continue
            needed = shape_text_height(shape)
            available = shape.height / EMU_PER_PT
            if needed > available * 1.06:
                findings.append(
                    f"slide {index} ({title}): text needs ~{needed:.0f}pt in a "
                    f"{available:.0f}pt box \u2014 {int(needed / available * 100)}% full"
                )

        if slide.has_notes_slide:
            notes = slide.notes_slide.notes_text_frame.text.strip()
            if notes and len(notes) < 120:
                findings.append(f"slide {index} ({title}): speaker notes are very short")

    for index, slide in enumerate(prs.slides, start=1):
        tables = [s for s in slide.shapes if s.has_table]
        for shape in tables:
            table = shape.table
            for r_index, row in enumerate(table.rows):
                for c_index, cell in enumerate(row.cells):
                    text = cell.text_frame.text
                    col_w = table.columns[c_index].width / EMU_PER_PT
                    size = 11.0
                    for para in cell.text_frame.paragraphs:
                        for run in para.runs:
                            if run.font.size is not None:
                                size = run.font.size.pt
                    chars_per_line = max(col_w / (size * AVG_CHAR_EM), 1.0)
                    lines = math.ceil(len(text) / chars_per_line)
                    if lines > 2:
                        findings.append(
                            f"slide {index}: table cell r{r_index}c{c_index} wraps to "
                            f"~{lines} lines \u2014 shorten it"
                        )
    return findings


def main(argv: list[str] | None = None) -> int:
    """
    Command-line entry point.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deck", type=Path, default=DEFAULT_DECK)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)

    if not args.deck.exists():
        print(f"{args.deck} does not exist \u2014 run build_deck.py first")
        return 1

    findings = check(args.deck)
    for finding in findings:
        print(finding)

    prs = Presentation(args.deck)
    print(f"\n{len(prs.slides)} slides, {len(findings)} findings")
    return 1 if (args.strict and findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
