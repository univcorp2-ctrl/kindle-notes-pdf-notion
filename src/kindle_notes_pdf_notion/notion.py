"""Notion data-source synchronization using the current REST API."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable

import httpx

from .fingerprints import clipping_fingerprint
from .models import Book, Clipping
from .state import SyncState

NOTION_VERSION = "2026-03-11"


class NotionAPIError(RuntimeError):
    """A sanitized Notion API error that never includes credentials."""


@dataclass(slots=True)
class SyncReport:
    """Summary of a Notion synchronization run."""

    created_pages: int = 0
    existing_pages: int = 0
    appended_clippings: int = 0
    skipped_clippings: int = 0
    planned_clippings: int = 0


def _chunks(values: list[dict[str, Any]], size: int) -> Iterable[list[dict[str, Any]]]:
    for index in range(0, len(values), size):
        yield values[index : index + size]


def _property_type(value: dict[str, Any]) -> str:
    explicit = value.get("type")
    if isinstance(explicit, str):
        return explicit
    for candidate in ("title", "rich_text", "number", "select", "date"):
        if candidate in value:
            return candidate
    return ""


def detect_title_property(schema: dict[str, Any]) -> str:
    """Find the title property name in a retrieved data-source schema."""

    properties = schema.get("properties")
    if not isinstance(properties, dict):
        raise NotionAPIError("Notion data source has no properties schema")
    for name, value in properties.items():
        if isinstance(value, dict) and _property_type(value) == "title":
            return str(name)
    raise NotionAPIError("Notion data source has no title property")


def _text_value(content: str) -> list[dict[str, Any]]:
    return [{"type": "text", "text": {"content": content[:2000]}}]


def _iso_date(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", value)
    if not match:
        return None
    year, month, day = map(int, match.groups())
    return f"{year:04d}-{month:02d}-{day:02d}"


def build_page_properties(
    book: Book, schema: dict[str, Any], title_property: str
) -> dict[str, Any]:
    """Build properties while gracefully supporting a title-only data source."""

    properties_schema = schema.get("properties", {})
    result: dict[str, Any] = {title_property: {"title": _text_value(book.title)}}
    latest = next(
        (
            date
            for date in reversed([_iso_date(item.added_at) for item in book.clippings])
            if date
        ),
        None,
    )
    for name, definition in properties_schema.items():
        if name == title_property or not isinstance(definition, dict):
            continue
        normalized = str(name).casefold().replace(" ", "")
        kind = _property_type(definition)
        if normalized in {"author", "著者"} and book.author and kind == "rich_text":
            result[name] = {"rich_text": _text_value(book.author)}
        elif normalized in {"highlightcount", "clippingcount", "件数"} and kind == "number":
            result[name] = {"number": len(book.clippings)}
        elif normalized in {"source", "ソース"}:
            source = book.clippings[0].source if book.clippings else "kindle_export"
            if kind == "select":
                result[name] = {"select": {"name": source}}
            elif kind == "rich_text":
                result[name] = {"rich_text": _text_value(source)}
        elif normalized in {"latesthighlight", "latestdate", "最新日"} and latest and kind == "date":
            result[name] = {"date": {"start": latest}}
    return result


def _clipping_blocks(clipping: Clipping) -> list[dict[str, Any]]:
    metadata = [clipping.kind.capitalize()]
    if clipping.page:
        metadata.append(f"p. {clipping.page}")
    if clipping.location:
        metadata.append(f"loc. {clipping.location}")
    if clipping.added_at:
        metadata.append(clipping.added_at)
    blocks: list[dict[str, Any]] = [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": _text_value(" | ".join(metadata)),
                "color": "gray",
            },
        }
    ]
    text = clipping.text or "(no text)"
    for start in range(0, len(text), 1900):
        blocks.append(
            {
                "object": "block",
                "type": "quote",
                "quote": {"rich_text": _text_value(text[start : start + 1900])},
            }
        )
    return blocks


class NotionClient:
    """Small Notion REST client with bounded retry behavior."""

    def __init__(
        self,
        token: str,
        data_source_id: str,
        *,
        client: httpx.Client | None = None,
        max_retries: int = 3,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if not token or not data_source_id:
            raise ValueError("NOTION_TOKEN and NOTION_DATA_SOURCE_ID are required")
        self.data_source_id = data_source_id
        self.max_retries = max_retries
        self.sleeper = sleeper
        self._owns_client = client is None
        self.http = client or httpx.Client(
            base_url="https://api.notion.com",
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            },
        )

    def close(self) -> None:
        """Close an internally-created HTTP client."""

        if self._owns_client:
            self.http.close()

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        for attempt in range(self.max_retries + 1):
            response = self.http.request(method, path, json=payload)
            transient = response.status_code == 429 or response.status_code >= 500
            if transient and attempt < self.max_retries:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else min(0.5 * (2**attempt), 4.0)
                self.sleeper(delay)
                continue
            if response.is_error:
                try:
                    message = str(response.json().get("message", "request failed"))
                except (ValueError, AttributeError):
                    message = "request failed"
                raise NotionAPIError(f"Notion API returned HTTP {response.status_code}: {message}")
            data = response.json()
            if not isinstance(data, dict):
                raise NotionAPIError("Notion API returned an unexpected response")
            return data
        raise NotionAPIError("Notion API retry limit exceeded")

    def retrieve_schema(self) -> dict[str, Any]:
        return self._request("GET", f"/v1/data_sources/{self.data_source_id}")

    def find_book_page(self, title: str, title_property: str) -> str | None:
        response = self._request(
            "POST",
            f"/v1/data_sources/{self.data_source_id}/query",
            {"filter": {"property": title_property, "title": {"equals": title}}, "page_size": 1},
        )
        results = response.get("results", [])
        if isinstance(results, list) and results and isinstance(results[0], dict):
            page_id = results[0].get("id")
            return str(page_id) if page_id else None
        return None

    def create_book_page(
        self, book: Book, schema: dict[str, Any], title_property: str
    ) -> str:
        response = self._request(
            "POST",
            "/v1/pages",
            {
                "parent": {
                    "type": "data_source_id",
                    "data_source_id": self.data_source_id,
                },
                "properties": build_page_properties(book, schema, title_property),
            },
        )
        page_id = response.get("id")
        if not page_id:
            raise NotionAPIError("Notion did not return a page ID")
        return str(page_id)

    def append_clippings(self, page_id: str, clippings: list[Clipping]) -> None:
        blocks = [block for clipping in clippings for block in _clipping_blocks(clipping)]
        for batch in _chunks(blocks, 90):
            self._request("PATCH", f"/v1/blocks/{page_id}/children", {"children": batch})

    def sync_books(self, books: list[Book], state: SyncState, dry_run: bool = False) -> SyncReport:
        """Upsert book pages and append only clippings absent from local state."""

        report = SyncReport()
        schema = self.retrieve_schema()
        title_property = detect_title_property(schema)
        for book in books:
            page_id = self.find_book_page(book.title, title_property)
            if page_id:
                report.existing_pages += 1
            elif dry_run:
                page_id = f"dry-run:{book.title}"
            else:
                page_id = self.create_book_page(book, schema, title_property)
                report.created_pages += 1

            fingerprints = [clipping_fingerprint(clipping) for clipping in book.clippings]
            fresh = [
                clipping
                for clipping, fingerprint in zip(book.clippings, fingerprints, strict=True)
                if not state.seen(self.data_source_id, page_id, fingerprint)
            ]
            report.skipped_clippings += len(book.clippings) - len(fresh)
            if dry_run:
                report.planned_clippings += len(fresh)
                continue
            if fresh:
                self.append_clippings(page_id, fresh)
                fresh_fingerprints = [clipping_fingerprint(clipping) for clipping in fresh]
                state.mark_many(self.data_source_id, page_id, fresh_fingerprints)
                report.appended_clippings += len(fresh)
        return report
