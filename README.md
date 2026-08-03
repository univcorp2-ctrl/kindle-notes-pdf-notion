# kindle-notes-pdf-notion

Kindleから**正規にエクスポートしたハイライト・メモ**を読み込み、検索可能なPDFを作成し、同じ内容をNotionへ同期するオープンソースCLIです。日本語と英語の `My Clippings.txt`、およびKindleの注釈HTMLエクスポートに対応します。

> [!IMPORTANT]
> このツールは電子書籍ファイルを読み取りません。DRM解除、AZW/KFXの復号・変換、Amazonアカウントのスクレイピング、購入書籍本文の抽出は行いません。ユーザー自身がエクスポートできるハイライト・メモ、またはユーザー所有／DRMフリー資料だけを扱ってください。

## 主な機能

- `My Clippings.txt` とKindle注釈HTMLを自動判定
- 日本語・英語の書名、著者、ハイライト／メモ、ページ、位置、日時を正規化
- SHA-256 fingerprintによる入力内・Notion同期時の重複防止
- 日本語CIDフォントを使った検索可能PDF（フォントファイル同梱なし）
- 統合PDF、または書籍別PDF
- Notion API `2026-03-11` のData Source APIに対応
- Notionのタイトル列を自動検出し、タイトル列だけのデータソースでも動作
- `--dry-run`、429/一時的5xxの再試行、atomicなローカルstate保存
- ローカル処理が基本。Notionコマンドを明示した場合以外は外部通信なし

## 必要環境

- Python 3.11以上
- PDF作成だけならNotionアカウントは不要
- Notion同期にはNotion Integration TokenとData Source IDが必要

## インストール

```bash
git clone https://github.com/univcorp2-ctrl/kindle-notes-pdf-notion.git
cd kindle-notes-pdf-notion
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e .
```

開発用依存も入れる場合:

```bash
pip install -e ".[dev]"
```

## クイックスタート

入力を確認します。

```bash
kindle-notes inspect "examples/My Clippings.txt"
```

統合PDFを作ります。

```bash
kindle-notes pdf "examples/My Clippings.txt" --output dist/kindle-notes.pdf
```

書籍ごとのPDFに分けます。

```bash
kindle-notes pdf "examples/My Clippings.txt" --output dist/kindle-notes.pdf --split
```

PDF作成とNotion同期を一度に実行します。

```bash
kindle-notes run "My Clippings.txt" \
  --output dist/kindle-notes.pdf \
  --notion
```

## Kindleから入力を用意する

### Kindle端末の `My Clippings.txt`

1. Kindle端末をUSBでPCへ接続します。
2. Kindle内の `documents/My Clippings.txt` をPCへコピーします。
3. コピーしたファイルを `kindle-notes` に渡します。

端末や言語設定によりメタデータ表現が異なるため、対応状況は [docs/FORMAT_SUPPORT.md](docs/FORMAT_SUPPORT.md) を確認してください。

### Kindleアプリの注釈HTML

Kindleアプリのノート／注釈画面から、アプリが提供するエクスポート機能でHTMLを保存または自分宛てに送信し、そのHTMLファイルを入力にします。書籍本体のファイルは使用しません。

## Notion連携

詳しい手順は [docs/NOTION_SETUP.md](docs/NOTION_SETUP.md) にあります。

1. Notionに読書メモ用データベースを作成します。タイトル列は必須です。
2. Notion Integrationを作成し、対象データベースへ接続します。
3. データベース設定の **Manage data sources** からData Source IDをコピーします。
4. 環境変数を設定します。

```bash
cp .env.example .env
export NOTION_TOKEN="secret_..."
export NOTION_DATA_SOURCE_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

`.env` は自動読込しません。シェル、OSの環境変数、または安全なSecret Managerから設定してください。CLI引数 `--token` もありますが、シェル履歴に残る可能性があるため環境変数を推奨します。

書込み前の確認:

```bash
kindle-notes notion "My Clippings.txt" --dry-run
```

実同期:

```bash
kindle-notes notion "My Clippings.txt"
```

### 対応するNotion列

タイトル列はschemaから自動検出します。次の列は存在し、かつ型が一致するときだけ設定します。

| 列名候補 | 型 | 値 |
|---|---|---|
| `Author` / `著者` | Rich text | 著者 |
| `Highlight Count` / `Clipping Count` / `件数` | Number | 件数 |
| `Source` / `ソース` | Select または Rich text | 入力形式 |
| `Latest Highlight` / `Latest Date` / `最新日` | Date | 最新日 |

タイトル列だけでも同期できます。

## 重複防止とstate

入力内の重複は、書名・著者・種別・本文・ページ・位置・日時から作るSHA-256 fingerprintで除外します。Notionへ追加済みのfingerprintは既定で `.kindle-notes-state.json` に保存します。

```bash
kindle-notes notion "My Clippings.txt" --state data/my-state.json
```

stateファイルを削除すると、ローカルの追加済み判定も失われます。Notion側の既存ブロックを自動削除・再構築はしません。

## コマンド

```text
kindle-notes inspect INPUT
kindle-notes pdf INPUT --output FILE [--split]
kindle-notes notion INPUT [--dry-run] [--state FILE]
kindle-notes run INPUT --output FILE [--split] [--notion] [--dry-run]
```

## プライバシーとセキュリティ

- PDF生成と `inspect` はローカルだけで完結します。
- Notion Tokenはログへ出力しません。
- Notion同期を明示した場合だけ `api.notion.com` へ接続します。
- `.env`、state、生成PDFには個人情報や引用が含まれる可能性があります。Gitへcommitしないでください。
- 不具合や脆弱性の報告方法は [SECURITY.md](SECURITY.md) を参照してください。

## 開発

```bash
make install
make check
make demo
```

個別実行:

```bash
ruff check .
mypy src
pytest
```

GitHub ActionsではPython 3.11、3.12、3.13でlint、型検査、テストを実行します。Codespacesまたはdevcontainerでも利用できます。

## 設計

```text
src/kindle_notes_pdf_notion/
├── parsers/          # My Clippings / HTML / 自動判定
├── models.py         # Book / Clipping / ParseResult
├── fingerprints.py   # SHA-256重複判定
├── pdf.py            # ReportLab PDF
├── notion.py         # Notion Data Source API
├── state.py          # atomic JSON state
└── cli.py            # Typer CLI
```

## 関連OSS

設計調査では次のプロジェクトを参考資料として確認しました。本リポジトリはコードをコピーしていない独立実装です。

- [arkalim/kindle-to-notion](https://github.com/arkalim/kindle-to-notion) — GPL-3.0
- [SenaThenu/kindle-clippings-to-notion](https://github.com/SenaThenu/kindle-clippings-to-notion) — MIT
- [watayu0828/book2notion](https://github.com/watayu0828/book2notion) — MIT
- [ganeshh123/notion-pdf-export](https://github.com/ganeshh123/notion-pdf-export) — MIT

## License

MIT License。詳細は [LICENSE](LICENSE) を参照してください。

---

## English

`kindle-notes-pdf-notion` turns user-exported Kindle highlights and notes (`My Clippings.txt` or notebook HTML) into searchable PDFs and can sync the same normalized notes to a Notion data source. It never accesses ebook files, removes access controls, converts purchased books, or scrapes Amazon accounts. See the Japanese sections above and `docs/` for setup details.
