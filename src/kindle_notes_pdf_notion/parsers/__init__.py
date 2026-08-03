"""Input detection, parsing, grouping, and de-duplication."""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

from ..fingerprints import clipping_fingerprint
from ..models import Book, Clipping, ParseResult
from .clippings import parse_clippings
from .html_export import parse_html_export


def read_text(path: Path) -> str:
    """Read a Kindle export using common encodings without silent corruption."""

    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "shift_jis"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Unsupported text encoding: {path}")


def detect_format(content: str, suffix: str = "") -> str:
    """Detect a supported export format from extension and content."""

    lowered = content.lstrip().casefold()
    suffix = suffix.casefold()
    if suffix in {".html", ".htm"} or lowered.startswith("<!doctype html") or "<html" in lowered:
        return "kindle_html"
    if "==========" in content:
        return "my_clippings"
    raise ValueError("Input is not a supported My Clippings.txt or Kindle HTML export")


def _deduplicate(clippings: list[Clipping]) -> tuple[list[Clipping], int]:
    unique: list[Clipping] = []
    seen: set[str] = set()
    duplicates = 0
    for clipping in clippings:
        fingerprint = clipping_fingerprint(clipping)
        if fingerprint in seen:
            duplicates += 1
            continue
        seen.add(fingerprint)
        unique.append(clipping)
    return unique, duplicates


def _group_books(clippings: list[Clipping]) -> list[Book]:
    grouped: OrderedDict[tuple[str, str], Book] = OrderedDict()
    for clipping in clippings:
        key = (clipping.title.casefold(), clipping.author.casefold())
        book = grouped.setdefault(key, Book(title=clipping.title, author=clipping.author))
        book.clippings.append(clipping)
    return list(grouped.values())


def parse_content(content: str, suffix: str = "") -> ParseResult:
    """Parse in-memory export content."""

    input_format = detect_format(content, suffix)
    parsed = parse_html_export(content) if input_format == "kindle_html" else parse_clippings(content)
    unique, duplicate_count = _deduplicate(parsed)
    return ParseResult(
        input_format=input_format,
        books=_group_books(unique),
        clippings=unique,
        duplicate_count=duplicate_count,
    )


def parse_path(path: Path) -> ParseResult:
    """Read and parse an export file."""

    return parse_content(read_text(path), path.suffix)


__all__ = ["detect_format", "parse_content", "parse_path", "read_text"]
