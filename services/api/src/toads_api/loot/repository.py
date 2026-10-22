"""Where loot lists live. LootService only talks to the LootRepository protocol; the hub-db backed implementation is
`sql.SqlLootRepository`."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class InLine:
    """A member in line for an item: rank 1 is first. `received_at` is set once they have it."""

    member_id: int
    rank: int
    received_at: datetime | None = None


@dataclass(frozen=True)
class LootEntry:
    id: int
    raid_day: str
    item_id: int
    item_name: str
    note: str
    # By rank.
    recipients: tuple[InLine, ...]
    created_by: int | None
    created_at: datetime
    updated_at: datetime


class LootRepository(Protocol):
    def entries(self, raid_day: str) -> list[LootEntry]:
        """Every item on the day's loot list, in the order they were added."""
        ...

    def entry(self, raid_day: str, entry_id: int) -> LootEntry | None: ...

    def add(self, raid_day: str, item_id: int, item_name: str, note: str, by: int, at: datetime) -> LootEntry | None:
        """A new item at the bottom of the list; None when the day's list already holds that item."""
        ...

    def set_note(self, raid_day: str, entry_id: int, note: str, by: int, at: datetime) -> LootEntry | None: ...

    def set_line(self, raid_day: str, entry_id: int, member_ids: list[int], by: int, at: datetime) -> LootEntry | None:
        """Put exactly `member_ids` in line, ranked in that order. A member who stays keeps their received mark."""
        ...

    def mark(
        self, raid_day: str, entry_id: int, member_id: int, received: bool, by: int, at: datetime
    ) -> LootEntry | None:
        """Mark one member received at `at`, or clear the mark; either way the item counts as updated at `at`. None
        when the item is gone or the member is not in its line."""
        ...

    def remove(self, raid_day: str, entry_id: int, by: int) -> bool: ...


@dataclass
class InMemoryLootRepository:
    """For service tests."""

    rows: list[LootEntry] = field(default_factory=list)
    next_id: int = 1

    def entries(self, raid_day: str) -> list[LootEntry]:
        return [e for e in self.rows if e.raid_day == raid_day]

    def entry(self, raid_day: str, entry_id: int) -> LootEntry | None:
        return next((e for e in self.rows if (e.raid_day, e.id) == (raid_day, entry_id)), None)

    def _put(self, new: LootEntry) -> LootEntry:
        self.rows = [new if e.id == new.id else e for e in self.rows]
        return new

    def add(self, raid_day: str, item_id: int, item_name: str, note: str, by: int, at: datetime) -> LootEntry | None:
        if any(e.item_id == item_id for e in self.entries(raid_day)):
            return None
        entry = LootEntry(self.next_id, raid_day, item_id, item_name, note, (), by, at, at)
        self.next_id += 1
        self.rows.append(entry)
        return entry

    def set_note(self, raid_day: str, entry_id: int, note: str, by: int, at: datetime) -> LootEntry | None:
        e = self.entry(raid_day, entry_id)
        return None if e is None else self._put(replace(e, note=note, updated_at=at))

    def set_line(self, raid_day: str, entry_id: int, member_ids: list[int], by: int, at: datetime) -> LootEntry | None:
        e = self.entry(raid_day, entry_id)
        if e is None:
            return None
        had = {r.member_id: r.received_at for r in e.recipients}
        line = tuple(InLine(m, rank, had.get(m)) for rank, m in enumerate(member_ids, start=1))
        return self._put(replace(e, recipients=line, updated_at=at))

    def mark(
        self, raid_day: str, entry_id: int, member_id: int, received: bool, by: int, at: datetime
    ) -> LootEntry | None:
        e = self.entry(raid_day, entry_id)
        if e is None or all(r.member_id != member_id for r in e.recipients):
            return None
        stamp = at if received else None
        line = tuple(replace(r, received_at=stamp) if r.member_id == member_id else r for r in e.recipients)
        return self._put(replace(e, recipients=line, updated_at=at))

    def remove(self, raid_day: str, entry_id: int, by: int) -> bool:
        before = len(self.rows)
        self.rows = [e for e in self.rows if (e.raid_day, e.id) != (raid_day, entry_id)]
        return len(self.rows) < before
