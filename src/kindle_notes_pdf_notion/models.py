"""Typed domain models for exported reading notes."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Clipping:
    """A single exported highlight, note, or bookmark."""

    title: str
    author: str = ""
    kind: str = "highlight"
    text: str = ""
    page: str | None = None
    location: str | None = None
    added_at: str | None = None
    source: str = "unknown"


@dataclass(slots=True)
class Book:
    """A book and its normalized clippings."""

    title: str
    author: str = ""
    clippings: list[Clipping] = field(default_factory=list)


@dataclass(slots=True)
class ParseResult:
    """Parsed input together with format and duplicate statistics."""

    input_format: str
    books: list[Book]
    clippings: list[Clipping]
    duplicate_count: int = 0
