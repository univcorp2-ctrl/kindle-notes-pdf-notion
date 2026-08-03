# Contributing

Thank you for improving `kindle-notes-pdf-notion`.

## Development

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
make check
```

## Pull requests

- Add tests for parser samples or behavior changes.
- Use synthetic text only. Do not submit excerpts from copyrighted books.
- Do not add ebook decryption, account scraping, or book-file conversion features.
- Keep network access limited to explicit Notion synchronization.
- Update `CHANGELOG.md` for user-visible changes.

## New export formats

Place sanitized, fully synthetic fixtures in `examples/` or construct them inside tests. Document the exact application/device and language format in `docs/FORMAT_SUPPORT.md`.
