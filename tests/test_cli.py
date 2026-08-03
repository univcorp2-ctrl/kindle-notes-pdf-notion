from pathlib import Path

from typer.testing import CliRunner

from kindle_notes_pdf_notion.cli import app


runner = CliRunner()


def _sample(path: Path) -> None:
    path.write_text(
        """Synthetic Book (Example Author)
- Your Highlight on page 1 | Location 1-2 | Added on 2024-01-01
Synthetic content.
==========
""",
        encoding="utf-8",
    )


def test_inspect_command(tmp_path: Path) -> None:
    path = tmp_path / "My Clippings.txt"
    _sample(path)
    result = runner.invoke(app, ["inspect", str(path)])
    assert result.exit_code == 0
    assert "books: 1" in result.stdout
    assert "clippings: 1" in result.stdout


def test_pdf_command(tmp_path: Path) -> None:
    path = tmp_path / "My Clippings.txt"
    output = tmp_path / "out.pdf"
    _sample(path)
    result = runner.invoke(app, ["pdf", str(path), "--output", str(output)])
    assert result.exit_code == 0
    assert output.read_bytes().startswith(b"%PDF")


def test_notion_requires_credentials(tmp_path: Path) -> None:
    path = tmp_path / "My Clippings.txt"
    _sample(path)
    result = runner.invoke(app, ["notion", str(path)], env={})
    assert result.exit_code != 0
    assert "NOTION_TOKEN" in result.output
