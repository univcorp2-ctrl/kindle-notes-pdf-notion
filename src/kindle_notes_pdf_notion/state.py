"""Atomic local state used to prevent duplicate Notion writes."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class SyncState:
    """Fingerprints already appended to Notion, grouped by source and page."""

    sources: dict[str, dict[str, set[str]]] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> SyncState:
        """Load state from disk, returning an empty state when absent."""

        if not path.exists():
            return cls()
        try:
            payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
            raw_sources = payload.get("sources", {})
            sources = {
                str(source_id): {
                    str(page_id): set(map(str, fingerprints))
                    for page_id, fingerprints in pages.items()
                }
                for source_id, pages in raw_sources.items()
            }
            return cls(sources=sources)
        except (json.JSONDecodeError, AttributeError, TypeError) as exc:
            raise ValueError(f"Invalid sync state file: {path}") from exc

    def seen(self, data_source_id: str, page_id: str, fingerprint: str) -> bool:
        """Return whether a fingerprint has already been synced."""

        return fingerprint in self.sources.get(data_source_id, {}).get(page_id, set())

    def mark_many(self, data_source_id: str, page_id: str, fingerprints: list[str]) -> None:
        """Mark fingerprints as synced."""

        pages = self.sources.setdefault(data_source_id, {})
        pages.setdefault(page_id, set()).update(fingerprints)

    def save(self, path: Path) -> None:
        """Atomically persist state in deterministic JSON form."""

        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "sources": {
                source_id: {
                    page_id: sorted(fingerprints)
                    for page_id, fingerprints in sorted(pages.items())
                }
                for source_id, pages in sorted(self.sources.items())
            },
        }
        handle, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as temporary:
                json.dump(payload, temporary, ensure_ascii=False, indent=2, sort_keys=True)
                temporary.write("\n")
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_name, path)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)
