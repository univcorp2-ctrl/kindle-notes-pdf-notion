"""Stable fingerprints for de-duplicating clippings."""

from __future__ import annotations

import hashlib
import json
import re

from .models import Clipping


def _normalize(value: str | None) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", value).strip().casefold()


def clipping_fingerprint(clipping: Clipping) -> str:
    """Return a stable SHA-256 identity for a clipping."""

    payload = {
        "title": _normalize(clipping.title),
        "author": _normalize(clipping.author),
        "kind": _normalize(clipping.kind),
        "text": _normalize(clipping.text),
        "page": _normalize(clipping.page),
        "location": _normalize(clipping.location),
        "added_at": _normalize(clipping.added_at),
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
