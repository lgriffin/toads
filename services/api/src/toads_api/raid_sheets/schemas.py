"""Shapes for the raid sheet routes. Every list and string has a cap: the tables arrive from a spreadsheet."""

from __future__ import annotations

import enum
from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

DayId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9_-]{1,32}$")]
# Google spreadsheet ids are URL-safe base64, 44 characters today; allow some slack either way.
SpreadsheetId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{20,64}$")]
Cell = Annotated[str, StringConstraints(max_length=500)]
TabName = Annotated[str, StringConstraints(min_length=1, max_length=100)]

MAX_COLUMNS = 100
MAX_ROWS = 2000


class SheetKind(enum.StrEnum):
    CBA = "cba"
    RPB = "rpb"


class SheetTable(BaseModel):
    """One tab as the worker read it: the first non-empty row as headers, then the data rows, all as text."""

    tab: TabName
    headers: list[Cell] = Field(max_length=MAX_COLUMNS)
    rows: list[Annotated[list[Cell], Field(max_length=MAX_COLUMNS)]] = Field(max_length=MAX_ROWS)


class SheetImport(BaseModel):
    """What the worker posts after downloading one spreadsheet."""

    spreadsheet_id: SpreadsheetId
    fetched_at: datetime
    tables: list[SheetTable] = Field(max_length=100)


class ImportResult(BaseModel):
    stored: list[str] = []  # tabs with new content, saved as a new snapshot
    unchanged: list[str] = []  # tabs identical to their latest snapshot
    undated: list[str] = []  # tabs with no raid date to link them by; kept, but on no raid


class NewSnapshot(BaseModel):
    """A tab's content as the service decided to keep it; the repository assigns its id."""

    kind: SheetKind
    spreadsheet_id: str
    tab: str
    raid_date: date | None
    raid_day: str | None
    content_digest: str
    fetched_at: datetime
    table: SheetTable
    # 1 for a tab's first snapshot, then +1 per change. Unique per tab, so two imports cannot both add version n.
    version: int = Field(ge=1)


class SheetSnapshot(NewSnapshot):
    id: int


class SheetLink(BaseModel):
    """A sheet tab attached to a raid, without its rows."""

    snapshot_id: int
    kind: SheetKind
    title: str
    tab: str
    url: str
    fetched_at: datetime


class RaidSheets(BaseModel):
    raid_day: str
    raid_date: date
    sheets: list[SheetLink]
