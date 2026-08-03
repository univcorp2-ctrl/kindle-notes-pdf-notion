"""Typer command-line interface."""

from __future__ import annotations

import os
from pathlib import Path

import typer

from .notion import NotionClient
from .parsers import parse_path
from .pdf import generate_pdfs
from .state import SyncState

app = typer.Typer(
    no_args_is_help=True,
    help=(
        "Create PDFs from user-exported Kindle highlights/notes and optionally sync them to "
        "Notion. This tool does not access or convert ebook files."
    ),
)


def _load(input_path: Path):  # type: ignore[no-untyped-def]
    try:
        return parse_path(input_path)
    except (OSError, ValueError) as exc:
        raise typer.BadParameter(str(exc), param_hint="INPUT") from exc


def _credentials(token: str | None, data_source_id: str | None) -> tuple[str, str]:
    resolved_token = token or os.getenv("NOTION_TOKEN")
    resolved_source = data_source_id or os.getenv("NOTION_DATA_SOURCE_ID")
    if not resolved_token or not resolved_source:
        raise typer.BadParameter(
            "Set NOTION_TOKEN and NOTION_DATA_SOURCE_ID, or pass --token and --data-source-id"
        )
    return resolved_token, resolved_source


def _sync(
    input_path: Path,
    state_path: Path,
    dry_run: bool,
    token: str | None,
    data_source_id: str | None,
) -> None:
    result = _load(input_path)
    resolved_token, resolved_source = _credentials(token, data_source_id)
    state = SyncState.load(state_path)
    client = NotionClient(resolved_token, resolved_source)
    try:
        report = client.sync_books(result.books, state, dry_run=dry_run)
    finally:
        client.close()
    if not dry_run:
        state.save(state_path)
    typer.echo(
        "Notion: "
        f"created={report.created_pages}, existing={report.existing_pages}, "
        f"appended={report.appended_clippings}, skipped={report.skipped_clippings}, "
        f"planned={report.planned_clippings}"
    )


@app.command("inspect")
def inspect_command(
    input_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, metavar="INPUT"),
) -> None:
    """Inspect an export without writing files or contacting Notion."""

    result = _load(input_path)
    typer.echo(f"format: {result.input_format}")
    typer.echo(f"books: {len(result.books)}")
    typer.echo(f"clippings: {len(result.clippings)}")
    typer.echo(f"duplicates: {result.duplicate_count}")


@app.command("pdf")
def pdf_command(
    input_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, metavar="INPUT"),
    output: Path = typer.Option(Path("dist/kindle-notes.pdf"), "--output", "-o"),
    split: bool = typer.Option(False, "--split", help="Generate one PDF per book."),
) -> None:
    """Generate searchable PDF output."""

    result = _load(input_path)
    try:
        paths = generate_pdfs(result.books, output, split=split)
    except (OSError, ValueError) as exc:
        raise typer.BadParameter(str(exc), param_hint="--output") from exc
    for path in paths:
        typer.echo(str(path))


@app.command("notion")
def notion_command(
    input_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, metavar="INPUT"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Read Notion but perform no writes."),
    state: Path = typer.Option(Path(".kindle-notes-state.json"), "--state"),
    token: str | None = typer.Option(None, "--token", help="Defaults to NOTION_TOKEN.", hidden=True),
    data_source_id: str | None = typer.Option(
        None, "--data-source-id", help="Defaults to NOTION_DATA_SOURCE_ID."
    ),
) -> None:
    """Sync normalized notes to a Notion data source."""

    _sync(input_path, state, dry_run, token, data_source_id)


@app.command("run")
def run_command(
    input_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, metavar="INPUT"),
    output: Path = typer.Option(Path("dist/kindle-notes.pdf"), "--output", "-o"),
    split: bool = typer.Option(False, "--split"),
    sync_notion: bool = typer.Option(False, "--notion", help="Also sync to Notion."),
    dry_run: bool = typer.Option(False, "--dry-run"),
    state: Path = typer.Option(Path(".kindle-notes-state.json"), "--state"),
    token: str | None = typer.Option(None, "--token", hidden=True),
    data_source_id: str | None = typer.Option(None, "--data-source-id"),
) -> None:
    """Generate PDF and optionally sync the same normalized notes to Notion."""

    result = _load(input_path)
    paths = generate_pdfs(result.books, output, split=split)
    for path in paths:
        typer.echo(str(path))
    if sync_notion:
        _sync(input_path, state, dry_run, token, data_source_id)


if __name__ == "__main__":
    app()
