# Format support

## Supported inputs

### `My Clippings.txt`

Recognized structure:

```text
Book title (Author)
- metadata line
Exported highlight or note
==========
```

The parser recognizes common English and Japanese terms for highlights, notes, bookmarks, page numbers, location numbers, and added dates. Input is normalized to UTF-8 after trying UTF-8 BOM, UTF-8, CP1252, and Shift-JIS.

### Kindle notebook HTML

The HTML parser uses multiple class/attribute fallbacks commonly found in exported annotation pages, including `bookTitle`, `authors`, `noteHeading`, `noteText`, highlight/annotation variants, data attributes, and blockquote fallback.

Because Amazon can change export markup, sanitized synthetic samples are welcome through pull requests.

## Not supported

- Ebook files such as AZW, AZW3, KFX, MOBI, or EPUB as book-content input
- Decryption or access-control removal
- Amazon account login or web scraping
- Full-book reconstruction from highlights
- OCR of screenshots

## Privacy-safe bug reports

Replace real titles, authors, locations, dates, and text with synthetic values while preserving the exact separators, metadata labels, HTML tags, and class names needed to reproduce the parser issue.
