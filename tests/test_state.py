import json
from pathlib import Path

from kindle_notes_pdf_notion.state import SyncState


def test_state_round_trip_and_seen(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    state = SyncState()
    state.mark_many("source", "page", ["b", "a"])
    state.save(path)

    loaded = SyncState.load(path)
    assert loaded.seen("source", "page", "a")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["sources"]["source"]["page"] == ["a", "b"]


def test_missing_state_is_empty(tmp_path: Path) -> None:
    state = SyncState.load(tmp_path / "missing.json")
    assert not state.seen("source", "page", "fingerprint")


def test_invalid_state_rejected(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{broken", encoding="utf-8")
    try:
        SyncState.load(path)
    except ValueError as exc:
        assert "Invalid sync state" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
