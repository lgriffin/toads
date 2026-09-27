"""Where sheet snapshots live. RaidSheetService only talks to this protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Protocol

from toads_api.raid_sheets.schemas import NewSnapshot, SheetSnapshot


class SheetRepository(Protocol):
    def insert(self, snapshot: NewSnapshot) -> SheetSnapshot | None:
        """Store the snapshot with a new id, or return None when the tab already has `snapshot.version`
        (another import got there first). Atomic: the store enforces one row per (spreadsheet, tab, version)."""
        ...

    def get(self, snapshot_id: int) -> SheetSnapshot | None: ...
    def latest(self, spreadsheet_id: str, tab: str) -> SheetSnapshot | None: ...
    def for_raid(self, raid_day: str, raid_date: date) -> list[SheetSnapshot]: ...
    def raid_dates(self, raid_day: str | None, limit: int) -> list[tuple[str, date]]: ...


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
