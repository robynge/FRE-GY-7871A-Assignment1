"""Write a report once and get both a PDF and a Markdown file.

Every call appends to two streams at the same time, so the two files cannot
drift apart. Numbers are formatted by `report_math.format_number`, which keeps
small estimates readable instead of rounding them to zero.
"""
from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    CondPageBreak, Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
    TableStyle,
)

from .report_math import format_number, formula_image

ACCENT = colors.HexColor("#8264FF")
INK = colors.HexColor("#0A0A23")
MUTED = colors.HexColor("#676777")
TINT = colors.HexColor("#F0ECFF")
STRIPE = colors.HexColor("#FAF9FE")
PAGE_WIDTH = A4[0] - 80


class Report:
    """A document being written to a PDF story and a Markdown buffer at once."""

    def __init__(self, title: str, subtitle: str = "", running_head: str = ""):
        self.title = title
        self.running_head = running_head or title
        self.story: list = []
        self.md: list[str] = [f"# {title}\n"]
        self._figures: list[tuple[str, Path]] = []
        self._caption_pending = False
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle("Body9", fontName="Helvetica", fontSize=9, leading=12.5,
                                  spaceAfter=7, textColor=INK))
        styles.add(ParagraphStyle("Note8", fontName="Helvetica", fontSize=8, leading=10.3,
                                  spaceAfter=6, textColor=MUTED))
        styles.add(ParagraphStyle("Bullet9", fontName="Helvetica", fontSize=9, leading=12.5,
                                  spaceAfter=4, leftIndent=12, bulletIndent=2, textColor=INK))
        styles.add(ParagraphStyle("Cell", fontName="Helvetica", fontSize=7.3, leading=9,
                                  textColor=INK))
        styles.add(ParagraphStyle("CellHead", fontName="Helvetica-Bold", fontSize=7.3,
                                  leading=9, textColor=INK))
        styles["Title"].fontSize = 18
        styles["Title"].leading = 22
        styles["Title"].textColor = INK
        styles["Heading1"].fontSize = 12.5
        styles["Heading1"].leading = 15
        styles["Heading1"].textColor = INK
        styles["Heading1"].spaceBefore = 12
        styles["Heading1"].keepWithNext = True
        styles["Heading2"].fontSize = 10.5
        styles["Heading2"].leading = 13
        styles["Heading2"].textColor = INK
        styles["Heading2"].keepWithNext = True
        self.styles = styles
        self.story.append(Paragraph(escape(title), styles["Title"]))
        if subtitle:
            self.story.append(Paragraph(escape(subtitle), styles["Note8"]))
            self.md.append(subtitle + "\n")

    # -- text ---------------------------------------------------------------
    def p(self, text: str) -> None:
        self.story.append(Paragraph(escape(text), self.styles["Body9"]))
        self.md.append(text.replace("$", r"\$") + "\n")

    def note(self, text: str) -> None:
        paragraph = Paragraph(escape(text), self.styles["Note8"])
        if self._caption_pending:
            image = self.story.pop(-2)  # the image, ahead of its spacer
            self.story.pop()
            self.story.extend([KeepTogether([image, paragraph]), Spacer(1, 6)])
            self._caption_pending = False
        else:
            self.story.append(paragraph)
        self.md.append(f"*{text}*\n".replace("$", r"\$"))

    def section(self, text: str) -> None:
        self.story.append(Paragraph(escape(text), self.styles["Heading1"]))
        self.md.append(f"## {text}\n")

    def sub(self, text: str) -> None:
        self.story.append(Paragraph(escape(text), self.styles["Heading2"]))
        self.md.append(f"### {text}\n")

    def bullets(self, items: list[str]) -> None:
        for item in items:
            self.story.append(Paragraph(escape(item), self.styles["Bullet9"], bulletText="•"))
            self.md.append(f"- {item}".replace("$", r"\$"))
        self.md.append("")
        self.story.append(Spacer(1, 5))

    def link(self, label: str, url: str) -> None:
        self.story.append(Paragraph(
            f'<link href="{escape(url, quote=True)}" color="#6542CE">{escape(label)}</link>',
            self.styles["Note8"]))
        self.md.append(f"[{label}]({url})\n")

    # -- blocks -------------------------------------------------------------
    def equation(self, *lines: str) -> None:
        for line in lines:
            self.story.extend([formula_image(line, PAGE_WIDTH), Spacer(1, 7)])
        body = (lines[0] if len(lines) == 1
                else "\\begin{aligned}\n" + "\\\\\n".join(lines) + "\n\\end{aligned}")
        self.md.append(f"$$\n{body}\n$$\n")

    def table(self, frame: pd.DataFrame, widths=None, keep_together=True) -> None:
        if frame is None or frame.empty:
            self.p("No observations for this sample.")
            return
        header = [Paragraph(escape(str(c)), self.styles["CellHead"]) for c in frame.columns]
        rows = [header] + [
            [Paragraph(format_number(value, target="pdf"), self.styles["Cell"])
             for value in record]
            for record in frame.itertuples(index=False, name=None)]
        table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), TINT),
            ("LINEBELOW", (0, 0), (-1, 0), .6, ACCENT),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, STRIPE])]))
        start = len(self.story)
        while start and isinstance(self.story[start - 1], Paragraph) \
                and self.story[start - 1].style.name in ("Heading2", "Note8"):
            start -= 1
        preceding, self.story[start:] = self.story[start:], []
        if keep_together and len(rows) <= 16:
            self.story.append(KeepTogether(preceding + [table]))
        else:
            for paragraph in preceding:  # the early break replaces keep-with-next
                paragraph.keepWithNext = 0
            self.story.extend([CondPageBreak(120)] + preceding + [table])
        self.story.append(Spacer(1, 7))
        self.md.append(frame.map(lambda v: format_number(v, target="markdown"))
                       .to_markdown(index=False, disable_numparse=True) + "\n")

    def figure(self, path: Path, alt: str, width: float = PAGE_WIDTH) -> None:
        image = Image(str(path))
        scale = width / image.imageWidth
        image.drawWidth, image.drawHeight = width, image.imageHeight * scale
        image.hAlign = "LEFT"
        self.story.extend([image, Spacer(1, 6)])
        self._caption_pending = True
        self._figures.append((alt, Path(path)))
        self.md.append(f"![{alt}]({{FIGURE_{len(self._figures) - 1}}})\n")

    def page_break(self) -> None:
        self.story.append(PageBreak())

    # -- output -------------------------------------------------------------
    def save(self, pdf_path: Path, markdown_path: Path) -> None:
        head, page_width = self.running_head, A4[0]

        def footer(canvas, doc):
            canvas.setFont("Helvetica", 7)
            canvas.setFillColor(MUTED)
            canvas.drawString(40, 22, head)
            canvas.drawRightString(page_width - 40, 22, str(doc.page))

        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        document = SimpleDocTemplate(str(pdf_path), pagesize=A4, leftMargin=40,
                                     rightMargin=40, topMargin=34, bottomMargin=35,
                                     title=self.title, author="")
        document.build(list(self.story), onFirstPage=footer, onLaterPages=footer)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        text = "\n".join(self.md)
        # Figures are referenced relative to the Markdown file so the document
        # can be moved without breaking every image.
        for index, (_, figure) in enumerate(self._figures):
            try:
                relative = figure.resolve().relative_to(markdown_path.resolve().parent)
            except ValueError:
                relative = figure
            text = text.replace(f"{{FIGURE_{index}}}", str(relative))
        markdown_path.write_text(text)
