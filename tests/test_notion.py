import json
from collections.abc import Callable

import httpx

from kindle_notes_pdf_notion.models import Book, Clipping
from kindle_notes_pdf_notion.notion import (
    NotionClient,
    build_page_properties,
    detect_title_property,
)
from kindle_notes_pdf_notion.state import SyncState

SCHEMA = {
    "object": "data_source",
    "id": "source-id",
    "properties": {
        "Name": {"id": "title", "type": "title", "title": {}},
        "Author": {"id": "a", "type": "rich_text", "rich_text": {}},
        "Highlight Count": {"id": "c", "type": "number", "number": {}},
        "Source": {"id": "s", "type": "select", "select": {}},
        "Latest Highlight": {"id": "d", "type": "date", "date": {}},
    },
}


def _book() -> Book:
    return Book(
        title="Synthetic Book",
        author="Test Author",
        clippings=[
            Clipping(
                title="Synthetic Book",
                author="Test Author",
                text="Synthetic highlight only.",
                page="3",
                added_at="2024-03-04",
                source="my_clippings",
            )
        ],
    )


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(
        base_url="https://api.notion.com",
        transport=httpx.MockTransport(handler),
    )


def test_detect_title_and_optional_properties() -> None:
    assert detect_title_property(SCHEMA) == "Name"
    properties = build_page_properties(_book(), SCHEMA, "Name")
    assert properties["Name"]["title"][0]["text"]["content"] == "Synthetic Book"
    assert properties["Author"]["rich_text"][0]["text"]["content"] == "Test Author"
    assert properties["Highlight Count"]["number"] == 1
    assert properties["Latest Highlight"]["date"]["start"] == "2024-03-04"


def test_sync_creates_page_appends_and_marks_state() -> None:
    requests: list[tuple[str, str, dict[str, object] | None]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content) if request.content else None
        requests.append((request.method, request.url.path, payload))
        if request.method == "GET":
            return httpx.Response(200, json=SCHEMA)
        if request.url.path.endswith("/query"):
            return httpx.Response(200, json={"results": []})
        if request.url.path == "/v1/pages":
            return httpx.Response(200, json={"id": "page-id"})
        if request.url.path == "/v1/blocks/page-id/children":
            return httpx.Response(200, json={"results": []})
        return httpx.Response(404, json={"message": "unexpected"})

    state = SyncState()
    api = NotionClient("secret-test", "source-id", client=_client(handler), sleeper=lambda _: None)
    report = api.sync_books([_book()], state)

    assert report.created_pages == 1
    assert report.appended_clippings == 1
    assert any(method == "PATCH" for method, _, _ in requests)
    page_payload = next(payload for method, path, payload in requests if path == "/v1/pages")
    assert page_payload is not None
    assert page_payload["parent"] == {
        "type": "data_source_id",
        "data_source_id": "source-id",
    }
    assert state.sources["source-id"]["page-id"]


def test_dry_run_never_writes() -> None:
    methods: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        methods.append(request.method)
        if request.method == "GET":
            return httpx.Response(200, json=SCHEMA)
        return httpx.Response(200, json={"results": [{"id": "existing-page"}]})

    api = NotionClient("secret-test", "source-id", client=_client(handler), sleeper=lambda _: None)
    report = api.sync_books([_book()], SyncState(), dry_run=True)
    assert report.existing_pages == 1
    assert report.planned_clippings == 1
    assert methods == ["GET", "POST"]


def test_retry_on_rate_limit() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "0"}, json={"message": "slow"})
        return httpx.Response(200, json=SCHEMA)

    api = NotionClient("secret-test", "source-id", client=_client(handler), sleeper=lambda _: None)
    assert api.retrieve_schema()["id"] == "source-id"
    assert calls == 2
