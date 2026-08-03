"""Parser for Kindle notebook HTML exports."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

from ..models import Clipping
from .clippings import _extract_added_at, _parse_kind

_PAGE_RE = re.compile(r"(?:page|ページ)\s*([0-9]+)", re.IGNORECASE)
_LOCATION_RE = re.compile(
    r"(?:location|位置\s*(?:no\.?|no．)?|位置no\.?)\s*([0-9]+(?:\s*[-–]\s*[0-9]+)?)",
    re.IGNORECASE,
)


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _first_text(soup: BeautifulSoup, selectors: tuple[str, ...]) -> str:
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            text = _clean(node.get_text(" ", strip=True))
            if text:
                return text
    return ""


def _heading_for(node: Tag) -> str:
    heading = node.find_previous(
        class_=re.compile(r"(?:note|highlight|annotation).*heading", re.IGNORECASE)
    )
    if isinstance(heading, Tag):
        return _clean(heading.get_text(" ", strip=True))
    parent = node.parent
    if isinstance(parent, Tag):
        data_meta = parent.get("data-metadata") or parent.get("data-location")
        if isinstance(data_meta, str):
            return _clean(data_meta)
    return ""


def parse_html_export(content: str) -> list[Clipping]:
    """Parse a Kindle notebook HTML export with resilient selector fallbacks."""

    soup = BeautifulSoup(content, "html.parser")
    title = _first_text(soup, (".bookTitle", ".book-title", "[data-book-title]", "h1"))
    author = _first_text(soup, (".authors", ".author", ".bookAuthor", "[data-author]"))
    if author.casefold().startswith("by "):
        author = author[3:].strip()

    selectors = (
        ".noteText",
        ".highlightText",
        ".annotationText",
        "[data-highlight-text]",
        ".kindle-highlight",
    )
    nodes: list[Tag] = []
    for selector in selectors:
        nodes.extend(node for node in soup.select(selector) if isinstance(node, Tag))
    if not nodes:
        nodes = [node for node in soup.select("blockquote") if isinstance(node, Tag)]

    parsed: list[Clipping] = []
    seen_nodes: set[int] = set()
    for node in nodes:
        if id(node) in seen_nodes:
            continue
        seen_nodes.add(id(node))
        text = _clean(node.get_text("\n", strip=True))
        if not text:
            continue
        meta = _heading_for(node)
        page_match = _PAGE_RE.search(meta)
        location_match = _LOCATION_RE.search(meta)
        node_title = node.get("data-book-title")
        node_author = node.get("data-author")
        clipping_title = str(node_title).strip() if node_title else title
        clipping_author = str(node_author).strip() if node_author else author
        if not clipping_title:
            clipping_title = "Untitled Kindle export"
        location = None
        if location_match:
            location = re.sub(r"\s+", "", location_match.group(1)).replace("–", "-")
        parsed.append(
            Clipping(
                title=clipping_title,
                author=clipping_author,
                kind=_parse_kind(meta),
                text=text,
                page=page_match.group(1) if page_match else None,
                location=location,
                added_at=_extract_added_at(meta),
                source="kindle_html",
            )
        )
    return parsed
