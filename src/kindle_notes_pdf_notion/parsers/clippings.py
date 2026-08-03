"""Parser for Kindle ``My Clippings.txt`` exports."""

from __future__ import annotations

import re

from ..models import Clipping

_SEPARATOR_RE = re.compile(r"^={8,}\s*$", re.MULTILINE)
_AUTHOR_RE = re.compile(r"^(?P<title>.*)\s+\((?P<author>[^()]*)\)\s*$")
_PAGE_RE = re.compile(r"(?:page|ページ)\s*([0-9]+)", re.IGNORECASE)
_LOCATION_RE = re.compile(
    r"(?:location|位置\s*(?:no\.?|no．)?|位置no\.?)\s*([0-9]+(?:\s*[-–]\s*[0-9]+)?)",
    re.IGNORECASE,
)


def _parse_header(line: str) -> tuple[str, str]:
    match = _AUTHOR_RE.match(line.strip())
    if not match:
        return line.strip(), ""
    return match.group("title").strip(), match.group("author").strip()


def _parse_kind(meta: str) -> str:
    lowered = meta.casefold()
    if "bookmark" in lowered or "ブックマーク" in meta:
        return "bookmark"
    if "note" in lowered or "メモ" in meta:
        return "note"
    if "highlight" in lowered or "ハイライト" in meta:
        return "highlight"
    return "clipping"


def _extract_added_at(meta: str) -> str | None:
    markers = ("added on", "added", "追加日", "作成日")
    lowered = meta.casefold()
    for marker in markers:
        index = lowered.find(marker.casefold())
        if index >= 0:
            value = meta[index + len(marker) :].lstrip(" :：-").strip()
            return value or None
    segments = [segment.strip() for segment in meta.split("|") if segment.strip()]
    if segments and re.search(r"\d{4}", segments[-1]):
        return segments[-1].lstrip("- ")
    return None


def parse_clippings(content: str) -> list[Clipping]:
    """Parse a ``My Clippings.txt`` string into normalized clippings."""

    parsed: list[Clipping] = []
    for raw_record in _SEPARATOR_RE.split(content.replace("\r\n", "\n")):
        lines = [line.rstrip() for line in raw_record.strip("\ufeff\n ").splitlines()]
        if len(lines) < 2:
            continue
        title, author = _parse_header(lines[0])
        meta = lines[1].strip()
        if not title or not meta.startswith("-"):
            continue
        text = "\n".join(lines[2:]).strip()
        page_match = _PAGE_RE.search(meta)
        location_match = _LOCATION_RE.search(meta)
        location = None
        if location_match:
            location = re.sub(r"\s+", "", location_match.group(1)).replace("–", "-")
        parsed.append(
            Clipping(
                title=title,
                author=author,
                kind=_parse_kind(meta),
                text=text,
                page=page_match.group(1) if page_match else None,
                location=location,
                added_at=_extract_added_at(meta),
                source="my_clippings",
            )
        )
    return parsed
