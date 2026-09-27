"""Where sheet snapshots live. RaidSheetService only talks to this protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Protocol

from toads_api.raid_sheets.schemas import NewSnapshot, SheetKind, SheetSnapshot


class SheetRepository(Protocol):
    def insert(self, snapshot: NewSnapshot) -> SheetSnapshot | None:
        """Store the snapshot with a new id, or return None when the tab already has `snapshot.version`
        (another import got there first). Atomic: the store enforces one row per (spreadsheet, tab, version)."""
        ...

    def get(self, snapshot_id: int) -> SheetSnapshot | None: ...
    def latest(self, spreadsheet_id: str, tab: str) -> SheetSnapshot | None: ...
    def for_raid(self, raid_day: str, raid_date: date) -> list[SheetSnapshot]: ...
    def raid_dates(self, raid_day: str | None, limit: int) -> list[tuple[str, date]]: ...

    def latest_linked(self, kind: SheetKind) -> SheetSnapshot | None:
        """The snapshot of this kind on the newest raid (latest raid date, then latest download)."""
        ...

    def latest_versions(self, spreadsheet_id: str) -> list[SheetSnapshot]:
        """The newest version of each tab of one spreadsheet."""
        ...

    def link(self, snapshot_id: int, raid_date: date, raid_day: str, report_code: str | None) -> None:
        """Attach a stored snapshot to a raid (an undated RPB tab, once its CBA names the raid)."""
        ...


@dataclass
class InMemorySheetRepository:
    """Process-local, for tests and local dev. Not durable across restarts."""

    snapshots: dict[int, SheetSnapshot] = field(default_factory=dict)

    def insert(self, snapshot: NewSnapshot) -> SheetSnapshot | None:
        key = (snapshot.spreadsheet_id, snapshot.tab, snapshot.version)
        if any((s.spreadsheet_id, s.tab, s.version) == key for s in self.snapshots.values()):
            return None
        stored = SheetSnapshot(id=max(self.snapshots, default=0) + 1, **snapshot.model_dump())
        self.snapshots[stored.id] = stored
        return stored

    def get(self, snapshot_id: int) -> SheetSnapshot | None:
        return self.snapshots.get(snapshot_id)

    def latest(self, spreadsheet_id: str, tab: str) -> SheetSnapshot | None:
        same = [s for s in self.snapshots.values() if s.spreadsheet_id == spreadsheet_id and s.tab == tab]
        return max(same, key=lambda s: s.version, default=None)

    def for_raid(self, raid_day: str, raid_date: date) -> list[SheetSnapshot]:
        return [s for s in self.snapshots.values() if s.raid_day == raid_day and s.raid_date == raid_date]

    def raid_dates(self, raid_day: str | None, limit: int) -> list[tuple[str, date]]:
        keys: set[tuple[str, date]] = set()
        for s in self.snapshots.values():
            if s.raid_day is not None and s.raid_date is not None and raid_day in (None, s.raid_day):
                keys.add((s.raid_day, s.raid_date))
        return sorted(keys, key=lambda k: (k[1], k[0]), reverse=True)[:limit]

    def latest_linked(self, kind: SheetKind) -> SheetSnapshot | None:
        linked = [s for s in self.snapshots.values() if s.kind == kind and s.raid_day is not None]
        return max(linked, key=lambda s: (s.raid_date or date.min, s.fetched_at, s.id), default=None)

    def latest_versions(self, spreadsheet_id: str) -> list[SheetSnapshot]:
        newest: dict[str, SheetSnapshot] = {}
        for s in self.snapshots.values():
            if s.spreadsheet_id == spreadsheet_id and (s.tab not in newest or s.version > newest[s.tab].version):
                newest[s.tab] = s
        return list(newest.values())

    def link(self, snapshot_id: int, raid_date: date, raid_day: str, report_code: str | None) -> None:
        snap = self.snapshots[snapshot_id]
        self.snapshots[snapshot_id] = snap.model_copy(
            update={"raid_date": raid_date, "raid_day": raid_day, "report_code": report_code}
        )
