"""Which spreadsheets to import and how they map to raid days: configuration, not code."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel

from toads_api.raid_sheets.schemas import DayId, SheetKind, SpreadsheetId


class SheetSource(BaseModel):
    kind: SheetKind
    spreadsheet_id: SpreadsheetId
    title: str = ""
    # Set when a spreadsheet only ever covers one raid day. Otherwise the day is the one whose weekday
    # matches the tab's date.
    raid_day: DayId | None = None
    # Tab names to keep (shell patterns, any case). Left out, every tab but the templates' setup tabs is kept.
    tabs: list[str] | None = None
    # For a sheet with no dates in it (RPB): new content joins the raid of the latest sheet of this kind, when that
    # raid was in the week before the download and has no copy of the tab yet.
    follows: SheetKind | None = None

    @property
    def url(self) -> str:
        return f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}/edit"

    @property
    def label(self) -> str:
        return self.title or self.kind.value.upper()


class RaidSheetsConfig(BaseModel):
    sources: list[SheetSource] = []
    # Weekday (0 = Monday) per raid day id. Days left out fall back to the weekday named in the raid day's name.
    weekdays: dict[DayId, int] = {}

    @classmethod
    def load(cls, path: Path) -> RaidSheetsConfig:
        if not path.exists():
            return cls()
        return cls.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")) or {})

    def source(self, spreadsheet_id: str) -> SheetSource | None:
        return next((s for s in self.sources if s.spreadsheet_id == spreadsheet_id), None)
