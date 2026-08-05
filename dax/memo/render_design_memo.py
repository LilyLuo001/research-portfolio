"""Render the approved DAX W1 Markdown memo to a reviewable PDF.

The renderer intentionally supports only the Markdown constructs used by the
memo. Keeping it local and deterministic makes the Gate-1 PDF reproducible.
"""

from __future__ import annotations

import argparse
import functools
import html
import pathlib
import re

from reportlab.lib import colors
from reportlab import rl_config
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_INPUT = HERE / "design_memo_v1.md"
DEFAULT_OUTPUT = HERE / "design_memo_v1.pdf"
FONT_DIR = pathlib.Path("/System/Library/Fonts/Supplemental")
LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")


def register_fonts() -> None:
    fonts = {
        "DAXArial": FONT_DIR / "Arial.ttf",
        "DAXArialBold": FONT_DIR / "Arial Bold.ttf",
        "DAXArialItalic": FONT_DIR / "Arial Italic.ttf",
        "DAXCourier": FONT_DIR / "Courier New.ttf",
    }
    for name, path in fonts.items():
        if not path.exists():
            raise FileNotFoundError(f"required PDF font not found: {path}")
        pdfmetrics.registerFont(TTFont(name, str(path)))
    pdfmetrics.registerFontFamily(
        "DAXArial",
        normal="DAXArial",
        bold="DAXArialBold",
        italic="DAXArialItalic",
        boldItalic="DAXArialBold",
    )


def inline_markup(value: str) -> str:
    """Convert the memo's inline Markdown subset to ReportLab markup."""
    placeholders: dict[str, str] = {}

    def stash(rendered: str) -> str:
        token = f"@@DAX{len(placeholders)}@@"
        placeholders[token] = rendered
        return token

    def link(match: re.Match[str]) -> str:
        label = html.escape(match.group(1))
        url = html.escape(match.group(2), quote=True)
        return stash(f'<link href="{url}" color="#1f5d99">{label}</link>')

    text = LINK_RE.sub(link, value)

    def code(match: re.Match[str]) -> str:
        return stash(f'<font name="DAXCourier">{html.escape(match.group(1))}</font>')

    text = re.sub(r"`([^`]+)`", code, text)
    text = html.escape(text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)
    for token, rendered in placeholders.items():
        text = text.replace(html.escape(token), rendered)
    return text


def make_styles():
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "DAXTitle",
            parent=base["Title"],
            fontName="DAXArialBold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#18324b"),
            alignment=TA_LEFT,
            spaceAfter=14,
        ),
        "h1": ParagraphStyle(
            "DAXH1",
            parent=base["Heading1"],
            fontName="DAXArialBold",
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#18324b"),
            spaceBefore=12,
            spaceAfter=6,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "DAXH2",
            parent=base["Heading2"],
            fontName="DAXArialBold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#285b7a"),
            spaceBefore=9,
            spaceAfter=4,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "DAXBody",
            parent=base["BodyText"],
            fontName="DAXArial",
            fontSize=8.2,
            leading=10.6,
            spaceAfter=5,
            textColor=colors.HexColor("#20262b"),
        ),
        "bullet": ParagraphStyle(
            "DAXBullet",
            parent=base["BodyText"],
            fontName="DAXArial",
            fontSize=8.2,
            leading=10.6,
            leftIndent=15,
            firstLineIndent=-9,
            spaceAfter=3,
        ),
        "numbered": ParagraphStyle(
            "DAXNumbered",
            parent=base["BodyText"],
            fontName="DAXArial",
            fontSize=8.2,
            leading=10.6,
            leftIndent=17,
            firstLineIndent=-12,
            spaceAfter=3,
        ),
        "table": ParagraphStyle(
            "DAXTable",
            parent=base["BodyText"],
            fontName="DAXArial",
            fontSize=6.3,
            leading=7.8,
            spaceAfter=0,
        ),
        "table_header": ParagraphStyle(
            "DAXTableHeader",
            parent=base["BodyText"],
            fontName="DAXArialBold",
            fontSize=6.3,
            leading=7.8,
            textColor=colors.white,
            alignment=TA_CENTER,
        ),
    }
    return styles


def is_table_separator(line: str) -> bool:
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def table_widths(rows: list[list[str]], total: float) -> list[float]:
    columns = max(len(row) for row in rows)
    scores = []
    for index in range(columns):
        lengths = [len(row[index]) if index < len(row) else 0 for row in rows]
        scores.append(max(7, min(34, max(lengths, default=7))))
    score_total = sum(scores)
    return [total * score / score_total for score in scores]


def build_story(markdown: str, styles, available_width: float):
    lines = markdown.splitlines()
    story = []
    paragraph: list[str] = []
    index = 0

    def flush_paragraph() -> None:
        if paragraph:
            story.append(Paragraph(inline_markup(" ".join(paragraph)), styles["body"]))
            paragraph.clear()

    while index < len(lines):
        raw = lines[index].rstrip()
        stripped = raw.strip()

        if not stripped:
            flush_paragraph()
            index += 1
            continue

        if stripped.startswith("|") and index + 1 < len(lines) and is_table_separator(lines[index + 1]):
            flush_paragraph()
            table_lines = [stripped]
            index += 2
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index].strip())
                index += 1
            raw_rows = [
                [cell.strip() for cell in line.strip("|").split("|")]
                for line in table_lines
            ]
            columns = max(len(row) for row in raw_rows)
            for row in raw_rows:
                row.extend([""] * (columns - len(row)))
            cells = []
            for row_index, row in enumerate(raw_rows):
                style = styles["table_header"] if row_index == 0 else styles["table"]
                cells.append([Paragraph(inline_markup(cell), style) for cell in row])
            table = Table(
                cells,
                colWidths=table_widths(raw_rows, available_width),
                repeatRows=1,
                hAlign="LEFT",
                splitByRow=1,
            )
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#285b7a")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#b8c4cc")),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f6f8")]),
                        ("LEFTPADDING", (0, 0), (-1, -1), 3),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ]
                )
            )
            story.extend([table, Spacer(1, 6)])
            continue

        heading = re.match(r"^(#{1,3})\s+(.+)$", stripped)
        if heading:
            flush_paragraph()
            level = len(heading.group(1))
            style = styles["title"] if level == 1 else styles["h1"] if level == 2 else styles["h2"]
            story.append(Paragraph(inline_markup(heading.group(2)), style))
            index += 1
            continue

        if stripped == "---":
            flush_paragraph()
            story.append(Spacer(1, 6))
            index += 1
            continue

        bullet = re.match(r"^-\s+(.+)$", stripped)
        numbered = re.match(r"^(\d+)\.\s+(.+)$", stripped)
        # A wrapped prose line can begin with a number (for example,
        # "10. Otherwise ..."). Treat it as a list item only when no paragraph
        # is currently being accumulated.
        if bullet or (numbered and not paragraph):
            flush_paragraph()
            if bullet:
                story.append(Paragraph(f"&#8226;&nbsp; {inline_markup(bullet.group(1))}", styles["bullet"]))
            else:
                story.append(
                    Paragraph(
                        f"{numbered.group(1)}.&nbsp; {inline_markup(numbered.group(2))}",
                        styles["numbered"],
                    )
                )
            index += 1
            continue

        paragraph.append(stripped)
        index += 1

    flush_paragraph()
    return story


def page_frame(canvas, document) -> None:
    canvas.saveState()
    width, height = letter
    canvas.setStrokeColor(colors.HexColor("#b8c4cc"))
    canvas.setLineWidth(0.4)
    canvas.line(0.65 * inch, 0.52 * inch, width - 0.65 * inch, 0.52 * inch)
    canvas.setFont("DAXArial", 7)
    canvas.setFillColor(colors.HexColor("#5c6870"))
    canvas.drawString(0.65 * inch, 0.34 * inch, "DAX design memo v1 - PI defaults approved; evidence pending")
    canvas.drawRightString(width - 0.65 * inch, 0.34 * inch, f"Page {document.page}")
    canvas.restoreState()


def render(source: pathlib.Path, output: pathlib.Path) -> None:
    rl_config.invariant = 1
    register_fonts()
    output.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(output),
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.62 * inch,
        bottomMargin=0.67 * inch,
        title="Dynamic AI Exposure (DAX): pre-registered design memo v1",
        author="DAX research team",
        subject="PI-approved design defaults; Gate-1 evidence pending",
    )
    styles = make_styles()
    story = build_story(source.read_text(encoding="utf-8"), styles, document.width)
    canvas_factory = functools.partial(pdfcanvas.Canvas, invariant=1)
    document.build(
        story,
        onFirstPage=page_frame,
        onLaterPages=page_frame,
        canvasmaker=canvas_factory,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=pathlib.Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=pathlib.Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    render(args.input, args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
