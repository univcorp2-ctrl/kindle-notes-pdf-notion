from pathlib import Path

from kindle_notes_pdf_notion.parsers import parse_content, parse_path

ENGLISH = """Example Book (Ada Reader)
- Your Highlight on page 12 | Location 100-102 | Added on Monday, January 1, 2024 10:00 AM
A useful synthetic highlight.
==========
Example Book (Ada Reader)
- Your Note on page 13 | Location 103 | Added on Tuesday, January 2, 2024 11:00 AM
A synthetic note.
==========
"""

JAPANESE = """架空の本 (山田 太郎)
- あなたのハイライト 位置No. 20-21 | 追加日: 2024年1月3日 水曜日
これはテスト用の架空の文章です。
==========
"""

HTML = """<!doctype html><html><body>
<h1 class="bookTitle">HTML Sample</h1>
<div class="authors">By Example Author</div>
<div class="noteHeading">Highlight on page 7 | Location 50-51 | Added on 2024-02-01</div>
<div class="noteText">A completely synthetic HTML highlight.</div>
</body></html>"""


def test_parse_english_clippings_and_deduplicate() -> None:
    result = parse_content(ENGLISH + ENGLISH)
    assert result.input_format == "my_clippings"
    assert len(result.books) == 1
    assert len(result.clippings) == 2
    assert result.duplicate_count == 2
    assert result.clippings[0].page == "12"
    assert result.clippings[0].location == "100-102"
    assert result.clippings[1].kind == "note"


def test_parse_japanese_clippings() -> None:
    result = parse_content(JAPANESE)
    assert result.books[0].title == "架空の本"
    assert result.books[0].author == "山田 太郎"
    assert result.clippings[0].location == "20-21"
    assert result.clippings[0].kind == "highlight"


def test_parse_html_export() -> None:
    result = parse_content(HTML, ".html")
    clipping = result.clippings[0]
    assert result.input_format == "kindle_html"
    assert clipping.title == "HTML Sample"
    assert clipping.author == "Example Author"
    assert clipping.page == "7"
    assert clipping.text == "A completely synthetic HTML highlight."


def test_parse_path_utf8_sig(tmp_path: Path) -> None:
    path = tmp_path / "My Clippings.txt"
    path.write_bytes(("\ufeff" + JAPANESE).encode("utf-8"))
    assert parse_path(path).books[0].title == "架空の本"


def test_unsupported_input() -> None:
    try:
        parse_content("not a Kindle export")
    except ValueError as exc:
        assert "supported" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
