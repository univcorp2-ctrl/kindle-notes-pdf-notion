from pathlib import Path

from kindle_notes_pdf_notion.models import Book, Clipping
from kindle_notes_pdf_notion.pdf import generate_pdfs


def _books() -> list[Book]:
    return [
        Book(
            title="架空の本",
            author="山田 太郎",
            clippings=[
                Clipping(
                    title="架空の本",
                    author="山田 太郎",
                    text="検索可能な日本語テスト文章です。",
                    page="1",
                    location="10-11",
                    added_at="2024-01-01",
                )
            ],
        )
    ]


def test_generate_combined_pdf(tmp_path: Path) -> None:
    output = tmp_path / "notes.pdf"
    generated = generate_pdfs(_books(), output)
    assert generated == [output]
    data = output.read_bytes()
    assert data.startswith(b"%PDF")
    assert len(data) > 1000


def test_generate_split_pdf(tmp_path: Path) -> None:
    generated = generate_pdfs(_books(), tmp_path / "notes.pdf", split=True)
    assert len(generated) == 1
    assert generated[0].exists()
    assert "架空の本" in generated[0].name


def test_empty_books_rejected(tmp_path: Path) -> None:
    try:
        generate_pdfs([], tmp_path / "none.pdf")
    except ValueError as exc:
        assert "No clippings" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
