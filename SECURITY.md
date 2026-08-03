# Security Policy

## Supported versions

The latest `main` branch and the latest tagged release receive security fixes.

## Reporting

Please open a private GitHub security advisory for vulnerabilities. Do not include Notion tokens, personal highlights, generated PDFs, or real book excerpts in reports.

## Secret handling

- Use `NOTION_TOKEN` through environment variables or a secret manager.
- Never commit `.env`, generated PDFs, or `.kindle-notes-state.json`.
- The CLI does not print tokens.
- Rotate the Notion token if it may have been exposed.

## Scope

This project processes user-exported notes. Features that obtain ebook content, bypass access controls, or scrape user accounts are intentionally out of scope.
