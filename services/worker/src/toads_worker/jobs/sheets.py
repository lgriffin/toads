"""Import adapter for the guild's CBA and RPB Google Sheets (read-only; nothing is written back).

Downloads each configured spreadsheet as .xlsx through Google's export link, reads every tab into plain text
tables and posts them to the hub API with the service token. Linking a tab to its raid, and deciding whether it
changed, are the API's RaidSheetService rules; this module only fetches and reads.
"""

from __future__ import annotations

import io
from collections.abc import Iterable, Iterator
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import Any

import httpx
import yaml
from openpyxl import load_workbook

from toads_worker.settings import Settings

EXPORT_URL = "https://docs.google.com/spreadsheets/d/{id}/export?format=xlsx"
# Same caps as the API's SheetImport schema, applied here so an oversized tab is trimmed rather than refused.
MAX_BYTES = 20 * 1024 * 1024
MAX_TABS = 100
MAX_COLUMNS = 100
MAX_ROWS = 2000
MAX_CELL = 500


class SheetUnavailableError(RuntimeError):
    """Google answered with something other than a spreadsheet: usually the sheet is not shared by link."""


def spreadsheet_ids(config_path: Path) -> list[str]:
    """The configured spreadsheets. The API checks each id again against its own copy of the config."""
    if not config_path.exists():
        return []
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return [str(s["spreadsheet_id"]) for s in data.get("sources", [])]


def cell_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        text = value.date().isoformat() if value.time() == time(0) else value.isoformat(sep=" ")
    elif isinstance(value, date):
        text = value.isoformat()
    elif isinstance(value, float) and value.is_integer():
        text = str(int(value))
    else:
        text = str(value).strip()
    return text[:MAX_CELL]


def _trimmed(values: Iterable[Any]) -> list[str]:
    row = [cell_text(v) for v in values][:MAX_COLUMNS]
    while row and not row[-1]:
        row.pop()
    return row


def read_tables(xlsx: bytes) -> Iterator[dict[str, Any]]:
    """Every tab as {tab, headers, rows}: the first non-empty row is the header, empty rows are dropped."""
    book = load_workbook(io.BytesIO(xlsx), read_only=True, data_only=True)
    try:
        for sheet in book.worksheets[:MAX_TABS]:
            rows = (r for r in (_trimmed(v) for v in sheet.iter_rows(values_only=True)) if r)
            headers = next(rows, None)
            if headers is None:
                continue
            body = [r for _, r in zip(range(MAX_ROWS), rows, strict=False)]
            yield {"tab": sheet.title[:100], "headers": headers, "rows": body}
    finally:
        book.close()


def download(http: httpx.Client, spreadsheet_id: str) -> bytes:
    with http.stream("GET", EXPORT_URL.format(id=spreadsheet_id), follow_redirects=True) as r:
        r.raise_for_status()
        if "spreadsheetml" not in r.headers.get("content-type", ""):
            raise SheetUnavailableError(f"spreadsheet {spreadsheet_id} is not shared as 'Anyone with the link'")
        data = bytearray()
        for chunk in r.iter_bytes():
            data += chunk
            if len(data) > MAX_BYTES:
                raise SheetUnavailableError(f"spreadsheet {spreadsheet_id} is larger than {MAX_BYTES} bytes")
    return bytes(data)


def import_raid_sheets(
    settings: Settings | None = None,
    *,
    google: httpx.Client | None = None,
    hub: httpx.Client | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Download every configured sheet and hand it to the hub. Returns the hub's result per spreadsheet."""
    settings = settings or Settings()
    token = settings.hub_service_token.get_secret_value()
    if not token:
        raise RuntimeError("TOADS_HUB_SERVICE_TOKEN is not set")
    google = google or httpx.Client(timeout=30.0)
    hub = hub or httpx.Client(base_url=settings.hub_api_url, timeout=30.0)
    fetched_at = (now or datetime.now(UTC)).isoformat()
    results: dict[str, Any] = {}
    for sid in spreadsheet_ids(settings.raid_sheets_config):
        body = {"spreadsheet_id": sid, "fetched_at": fetched_at, "tables": list(read_tables(download(google, sid)))}
        r = hub.post("/api/worker/raid-sheets", json=body, headers={"Authorization": f"Bearer {token}"})
        r.raise_for_status()
        results[sid] = r.json()
    return results
