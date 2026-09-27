"""Raid sheet rules: which raid a sheet tab belongs to, when a download is new content, what a raid shows.

Who may ask is decided before this, in the routes. Scopes are passed in as raid day ids, never as a Principal.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Literal

from toads_api.raid_sheets.config import RaidSheetsConfig, SheetSource
from toads_api.raid_sheets.dates import raid_date_of
from toads_api.raid_sheets.repository import SheetRepository
from toads_api.raid_sheets.schemas import (
    ImportResult,
    NewSnapshot,
    RaidSheets,
    SheetImport,
    SheetKind,
    SheetLink,
    SheetSnapshot,
    SheetTable,
)
from toads_api.raid_sheets.summary import RaidHeadline, RaidSummary, summarise
from toads_api.raid_sheets.tabs import keeps, redact, report_code


class RaidSheetError(Exception):
    status_code = 400


class NotFound(RaidSheetError):
    status_code = 404


class ImportConflict(RaidSheetError):
    """Other imports kept changing the same tab while this one tried to add its version."""

    status_code = 409


class UnknownSource(RaidSheetError):
    """Only configured spreadsheets are accepted, so a leaked service token cannot plant arbitrary tables."""

    status_code = 422


# How often to re-read a tab's latest version after losing a race with a concurrent import.
_ATTEMPTS = 5
# A sheet with no dates (RPB) joins a raid only when it was downloaded within this long after the raid.
FOLLOW_WINDOW = timedelta(days=7)


@dataclass(frozen=True)
class _Link:
    raid_date: date | None
    raid_day: str | None
    report_code: str | None


def _within_window(raid_date: date, fetched_at: datetime) -> bool:
    return raid_date <= fetched_at.date() <= raid_date + FOLLOW_WINDOW


def _redacted(table: SheetTable) -> SheetTable:
    return SheetTable(
        tab=table.tab,
        headers=[redact(c) for c in table.headers],
        rows=[[redact(c) for c in row] for row in table.rows],
    )


def _grid(snap: SheetSnapshot) -> list[list[str]]:
    return [snap.table.headers, *snap.table.rows]


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
        """Keep each tab whose content changed since its last snapshot, linked to the raid it describes.

        Setup tabs are dropped and webhooks or e-mails blanked before anything is stored. The report code is read
        from the whole download first, since it sits on the Instructions tab that is then dropped."""
        source = self.config.source(imp.spreadsheet_id)
        if source is None:
            raise UnknownSource("spreadsheet is not a configured raid sheet")
        code = report_code(c for t in imp.tables for row in [t.headers, *t.rows] for c in row)
        result = ImportResult()
        new_raids: set[tuple[date, str]] = set()
        for table in imp.tables:
            if not keeps(table.tab, source.tabs):
                result.skipped.append(table.tab)
                continue
            clean = _redacted(table)
            digest = content_digest(clean)
            link = self._link_for(source, imp, clean, digest, code)
            outcome = self._store(source, imp, clean, digest, link)
            getattr(result, outcome).append(table.tab)
            if outcome == "stored" and link.raid_date is not None and link.raid_day is not None:
                new_raids.add((link.raid_date, link.raid_day))
        for raid_date, raid_day in sorted(new_raids):
            self._attach_followers(source, raid_date, raid_day, code)
        return result

    def _link_for(
        self, source: SheetSource, imp: SheetImport, table: SheetTable, digest: str, code: str | None
    ) -> _Link:
        raid_date = raid_date_of(table.tab, [table.headers, *table.rows])
        if raid_date is not None:
            return _Link(raid_date, self.raid_day_for(source, raid_date), code)
        if source.follows is None:
            return _Link(None, None, code)
        latest = self.repo.latest(imp.spreadsheet_id, table.tab)
        if latest is not None and latest.content_digest == digest:
            return _Link(latest.raid_date, latest.raid_day, latest.report_code)
        target = self.repo.latest_linked(source.follows)
        if (
            target is not None
            and target.raid_date is not None
            and target.raid_day is not None
            and _within_window(target.raid_date, imp.fetched_at)
            and not self._has_tab(target.raid_day, target.raid_date, imp.spreadsheet_id, table.tab)
        ):
            return _Link(target.raid_date, target.raid_day, target.report_code or code)
        return _Link(None, None, code)

    def _has_tab(self, raid_day: str, raid_date: date, spreadsheet_id: str, tab: str) -> bool:
        return any(s.spreadsheet_id == spreadsheet_id and s.tab == tab for s in self.repo.for_raid(raid_day, raid_date))

    def _attach_followers(self, source: SheetSource, raid_date: date, raid_day: str, code: str | None) -> None:
        """A new raid from `source`: undated tabs of the sheets that follow it, downloaded in the week after the raid
        and not yet on it, join it. This covers an RPB regenerated before its CBA."""
        on_raid = {(s.spreadsheet_id, s.tab) for s in self.repo.for_raid(raid_day, raid_date)}
        for follower in self.config.sources:
            if follower.follows != source.kind:
                continue
            for snap in self.repo.latest_versions(follower.spreadsheet_id):
                if (
                    snap.raid_date is None
                    and (snap.spreadsheet_id, snap.tab) not in on_raid
                    and _within_window(raid_date, snap.fetched_at)
                ):
                    self.repo.link(snap.id, raid_date, raid_day, code)

    def _store(
        self,
        source: SheetSource,
        imp: SheetImport,
        table: SheetTable,
        digest: str,
        link: _Link,
    ) -> Literal["stored", "unchanged", "undated"]:
        """Add the next version of a tab unless it matches the latest one. Retries when a concurrent import
        takes the version number first, so the same change is never kept twice."""
        for _ in range(_ATTEMPTS):
            latest = self.repo.latest(imp.spreadsheet_id, table.tab)
            if latest is not None and (
                latest.content_digest,
                latest.raid_date,
                latest.raid_day,
                latest.report_code,
            ) == (digest, link.raid_date, link.raid_day, link.report_code):
                return "unchanged"
            stored = self.repo.insert(
                NewSnapshot(
                    kind=source.kind,
                    spreadsheet_id=imp.spreadsheet_id,
                    tab=table.tab,
                    raid_date=link.raid_date,
                    raid_day=link.raid_day,
                    content_digest=digest,
                    fetched_at=imp.fetched_at,
                    table=table,
                    report_code=link.report_code,
                    version=latest.version + 1 if latest is not None else 1,
                )
            )
            if stored is not None:
                return "stored" if link.raid_day is not None else "undated"
        raise ImportConflict(f"tab {table.tab!r} kept changing during import; try again")

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
            if key not in newest or s.version > newest[key].version:
                newest[key] = s
        return sorted(newest.values(), key=lambda s: (s.kind.value, s.tab))

    def for_raid(self, raid_day: str, raid_date: date) -> RaidSheets:
        snaps = self._current(self.repo.for_raid(raid_day, raid_date))
        return RaidSheets(
            raid_day=raid_day,
            raid_date=raid_date,
            report_code=next((s.report_code for s in snaps if s.report_code), None),
            sheets=[self._link(s) for s in snaps],
        )

    def summary(self, raid_day: str, raid_date: date) -> RaidSummary:
        """The raid's totals and per-player lines, read from its newest CBA and RPB tabs."""
        snaps = self._current(self.repo.for_raid(raid_day, raid_date))
        by_kind = {kind: {s.tab.strip().lower(): _grid(s) for s in snaps if s.kind == kind} for kind in SheetKind}
        return summarise(
            raid_day,
            raid_date.isoformat(),
            cba=by_kind[SheetKind.CBA],
            rpb=by_kind[SheetKind.RPB],
            report_code=next((s.report_code for s in snaps if s.report_code), None),
        )

    def trend(self, raid_day: str | None = None, limit: int = 12) -> list[RaidHeadline]:
        """Each recent raid's totals, newest first: the home page's week-by-week view."""
        return [self.summary(day, when).headline for day, when in self.repo.raid_dates(raid_day, limit)]

    def recent(self, raid_day: str | None = None, limit: int = 8) -> list[RaidSheets]:
        """The latest raids that have sheets, newest first: what the home page lists."""
        return [self.for_raid(day, when) for day, when in self.repo.raid_dates(raid_day, limit)]

    def snapshot(self, raid_day: str, snapshot_id: int) -> SheetSnapshot:
        """A tab's rows. Scoped to the raid day in the path so ids do not leak across days."""
        snap = self.repo.get(snapshot_id)
        if snap is None or snap.raid_day != raid_day:
            raise NotFound("no such sheet")
        return snap
