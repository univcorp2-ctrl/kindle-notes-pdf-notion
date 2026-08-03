"""Searchable PDF generation for normalized reading notes."""

from __future__ import annotations

import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

from .models import Book, Clipping

_BODY_FONT = "HeiseiMin-W3"
_HEADING_FONT = "HeiseiKakuGo-W5"


def _register_fonts() -> None:
    for name in (_BODY_FONT, _HEADING_FONT):
        try:
            pdfmetrics.getFont(name)
        except KeyError:
            pdfmetrics.registerFont(UnicodeCIDFont(name))


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|\x00-\x1f]+", "-", value).strip(" .-")
    cleaned = re.sub(r"\s+", "-", cleaned)
    return cleaned[:80] or "untitled"


def _metadata_line(clipping: Clipping) -> str:
    parts = [clipping.kind.capitalize()]
    if clipping.page:
        parts.append(f"p. {clipping.page}")
    if clipping.location:
        parts.append(f"loc. {clipping.location}")
    if clipping.added_at:
        parts.append(clipping.added_at)
    return " | ".join(parts)


def _page_number(canvas: object, document: object) -> None:
    canvas.saveState()  # type: ignore[attr-defined]
    canvas.setFont(_BODY_FONT, 8)  # type: ignore[attr-defined]
    canvas.drawRightString(195 * mm, 10 * mm, str(document.page))  # type: ignore[attr-defined]
    canvas.restoreState()  # type: ignore[attr-defined]


def _build_one(books: list[Book], output: Path, title: str) -> None:
    _register_fonts()
    output.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "JapaneseTitle",
        parent=styles["Title"],
        fontName=_HEADING_FONT,
        fontSize=24,
        leading=32,
        alignment=TA_CENTER,
        spaceAfter=16,
    )
    heading_style = ParagraphStyle(
        "JapaneseHeading",
        parent=styles["Heading1"],
        fontName=_HEADING_FONT,
        fontSize=17,
        leading=23,
        spaceAfter=8,
    )
    subheading_style = ParagraphStyle(
        "JapaneseSubheading",
        parent=styles["Heading2"],
        fontName=_HEADING_FONT,
        fontSize=11,
        leading=16,
        textColor="#555555",
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "JapaneseBody",
        parent=styles["BodyText"],
        fontName=_BODY_FONT,
        fontSize=10.5,
        leading=17,
        spaceAfter=11,
    )
    meta_style = ParagraphStyle(
        "JapaneseMeta",
        parent=body_style,
        fontSize=8.5,
        leading=13,
        textColor="#666666",
        spaceAfter=4,
    )

    story: list[object] = [Spacer(1, 45 * mm), Paragraph(escape(title), title_style)]
    count = sum(len(book.clippings) for book in books)
    story.extend(
        [
            Paragraph(f"{len(books)} books / {count} clippings", subheading_style),
            PageBreak(),
            Paragraph("Book index / 書籍一覧", heading_style),
        ]
    )
    for index, book in enumerate(books, start=1):
        author = f" — {escape(book.author)}" if book.author else ""
        story.append(
            Paragraph(f"{index}. {escape(book.title)}{author} ({len(book.clippings)})", body_style)
        )
    story.append(PageBreak())

    for book_index, book in enumerate(books):
        story.append(Paragraph(escape(book.title), heading_style))
        if book.author:
            story.append(Paragraph(escape(book.author), subheading_style))
        story.append(Paragraph(f"{len(book.clippings)} clippings", meta_style))
        for clipping in book.clippings:
            story.append(Paragraph(escape(_metadata_line(clipping)), meta_style))
            body = escape(clipping.text or "(no text)").replace("\n", "<br/>")
            story.append(Paragraph(body, body_style))
        if book_index < len(books) - 1:
            story.append(PageBreak())

    document = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=title,
        author="kindle-notes-pdf-notion",
    )
    document.build(story, onFirstPage=_page_number, onLaterPages=_page_number)


def generate_pdfs(books: list[Book], output: Path, split: bool = False) -> list[Path]:
    """Generate one combined PDF or one PDF per book."""

    if not books:
        raise ValueError("No clippings were found; PDF was not generated")
    if not split:
        _build_one(books, output, "Kindle Notes / Kindle読書メモ")
        return [output]

    generated: list[Path] = []
    for book in books:
        target = output.with_name(f"{output.stem}-{_safe_filename(book.title)}{output.suffix or '.pdf'}")
        _build_one([book], target, book.title)
        generated.append(target)
    return generated
