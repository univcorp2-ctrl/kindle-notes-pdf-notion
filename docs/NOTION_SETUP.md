# Notion setup

## 1. Create a database

Create a Notion database for books. A title property is required; its visible name can be anything. Optional columns are described in the README.

## 2. Create an integration

Create an internal Notion integration in your workspace and grant read/update/insert content capabilities required for the target database. Copy the integration secret into a local secret manager or environment variable.

Do not paste the secret into source code, GitHub issues, generated PDFs, or state files.

## 3. Share the database

Open the database in Notion, choose the connections/integrations menu, and connect the integration. A valid token alone is not enough; the database must be shared with the integration.

## 4. Copy the Data Source ID

Notion databases can contain one or more data sources. Open the database settings, choose **Manage data sources**, open the desired data source menu, and select **Copy data source ID**.

This project uses the current Data Source API rather than the legacy database-query API.

## 5. Configure environment variables

```bash
export NOTION_TOKEN="secret_..."
export NOTION_DATA_SOURCE_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

PowerShell example:

```powershell
$env:NOTION_TOKEN = "secret_..."
$env:NOTION_DATA_SOURCE_ID = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

## 6. Verify with dry-run

```bash
kindle-notes notion "My Clippings.txt" --dry-run
```

Dry-run reads the schema and queries matching book pages, but it does not create pages, append blocks, or update the local state file.

## 7. Sync

```bash
kindle-notes notion "My Clippings.txt"
```

The local `.kindle-notes-state.json` records fingerprints appended to each Notion page. Back it up together with your workflow, but do not publish it if page IDs or reading data are sensitive.

## Troubleshooting

- **401**: token is missing, expired, or invalid.
- **403/404**: the integration is not connected to the original database/data source.
- **No title property**: add or retain a title column in the selected data source.
- **Duplicate blocks after deleting state**: restore the prior state or manually reconcile the Notion page. The CLI never deletes existing Notion content.
- **429**: the client observes `Retry-After` and retries a bounded number of times.
