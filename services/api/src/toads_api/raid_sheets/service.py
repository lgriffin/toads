"""Raid sheet rules: which raid a sheet tab belongs to, when a download is new content, what a raid shows.

Who may ask is decided before this, in the routes. Scopes are passed in as raid day ids, never as a Principal.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

from toads_api.raid_sheets.config import RaidSheetsConfig, SheetSource
from toads_api.raid_sheets.dates import raid_date_of
from toads_api.raid_sheets.repository import SheetRepository
from toads_api.raid_sheets.schemas import (
    ImportResult,
    RaidSheets,
    SheetImport,
    SheetLink,
    SheetSnapshot,
    SheetTable,
)


class RaidSheetError(Exception):
    status_code = 400


class NotFound(RaidSheetError):
    status_code = 404


class UnknownSource(RaidSheetError):
    """Only configured spreadsheets are accepted, so a leaked service token cannot plant arbitrary tables."""

    status_code = 422


def content_digest(table: SheetTable) -> str:
    blob = json.dumps([table.headers, table.rows], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


@dataclass
class RaidSheetService:
    repo: SheetRepository
    config: RaidSheetsConfig
    # Raid day id -> weekday (0 = Monday), for days that raid on a fixed weekday.
    weekdays: Mapping[str, int]

    def raid_day_for(self, source: SheetSource, raid_date: date) -> str | None:
        if source.raid_day is not None:
            return source.raid_day
        days = [d for d, weekday in self.weekdays.items() if weekday == raid_date.weekday()]
        return days[0] if len(days) == 1 else None

    def record_import(self, imp: SheetImport) -> ImportResult:
        """Keep each tab whose content changed since its last snapshot, linked to the raid its date names."""
        source = self.config.source(imp.spreadsheet_id)
        if source is None:
            raise UnknownSource("spreadsheet is not a configured raid sheet")
        result = ImportResult()
        for table in imp.tables:
            digest = content_digest(table)
            raid_date = raid_date_of(table.tab, [table.headers, *table.rows])
            raid_day = self.raid_day_for(source, raid_date) if raid_date is not None else None
            latest = self.repo.latest(imp.spreadsheet_id, table.tab)
            if (
                latest is not None
                and latest.content_digest == digest
                and (latest.raid_date, latest.raid_day) == (raid_date, raid_day)
            ):
                result.unchanged.append(table.tab)
                continue
            self.repo.save(
                SheetSnapshot(
                    id=self.repo.next_id(),
                    kind=source.kind,
                    spreadsheet_id=imp.spreadsheet_id,
                    tab=table.tab,
                    raid_date=raid_date,
                    raid_day=raid_day,
                    content_digest=digest,
                    fetched_at=imp.fetched_at,
                    table=table,
                )
            )
            (result.stored if raid_day is not None else result.undated).append(table.tab)
        return result

    def _link(self, snap: SheetSnapshot) -> SheetLink:
        source = self.config.source(snap.spreadsheet_id)
        return SheetLink(
            snapshot_id=snap.id,
            kind=snap.kind,
            title=source.label if source else snap.kind.value.upper(),
            tab=snap.tab,
            url=source.url if source else f"https://docs.google.com/spreadsheets/d/{snap.spreadsheet_id}/edit",
            fetched_at=snap.fetched_at,
        )

    def _current(self, snaps: list[SheetSnapshot]) -> list[SheetSnapshot]:
        """The newest snapshot of each tab; older ones stay stored as history."""
        newest: dict[tuple[str, str], SheetSnapshot] = {}
        for s in snaps:
            key = (s.spreadsheet_id, s.tab)
            if key not in newest or (s.fetched_at, s.id) > (newest[key].fetched_at, newest[key].id):
                newest[key] = s
        return sorted(newest.values(), key=lambda s: (s.kind.value, s.tab))

    def for_raid(self, raid_day: str, raid_date: date) -> RaidSheets:
        snaps = self._current(self.repo.for_raid(raid_day, raid_date))
        return RaidSheets(raid_day=raid_day, raid_date=raid_date, sheets=[self._link(s) for s in snaps])

    def recent(self, raid_day: str | None = None, limit: int = 8) -> list[RaidSheets]:
        """The latest raids that have sheets, newest first: what the home page lists."""
        return [self.for_raid(day, when) for day, when in self.repo.raid_dates(raid_day, limit)]

    def snapshot(self, raid_day: str, snapshot_id: int) -> SheetSnapshot:
        """A tab's rows. Scoped to the raid day in the path so ids do not leak across days."""
        snap = self.repo.get(snapshot_id)
        if snap is None or snap.raid_day != raid_day:
            raise NotFound("no such sheet")
        return snap
