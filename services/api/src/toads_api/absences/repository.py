"""Where absences live. AbsenceService only talks to the AbsenceRepository protocol; the hub-db backed implementation
is `sql.SqlAbsenceRepository`."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime
from typing import Protocol


@dataclass(frozen=True)
class AbsenceRecord:
    id: int
    member_id: int
    raid_day: str
    first_date: date
    last_date: date
    note: str | None
    created_at: datetime


class AbsenceRepository(Protocol):
    def for_member(self, member_id: int, since: date) -> list[AbsenceRecord]: ...
    def for_day(self, raid_day: str, since: date) -> list[AbsenceRecord]: ...
    def get(self, absence_id: int) -> AbsenceRecord | None: ...
    def add(self, member_id: int, raid_day: str, first: date, last: date, note: str | None) -> AbsenceRecord: ...
    def change(self, absence_id: int, first: date, last: date, note: str | None) -> AbsenceRecord | None: ...
    def remove(self, absence_id: int) -> bool: ...


def _upcoming(rows: list[AbsenceRecord], since: date) -> list[AbsenceRecord]:
    return sorted((r for r in rows if r.last_date >= since), key=lambda r: (r.first_date, r.id))


@dataclass
class InMemoryAbsenceRepository:
    """For service tests."""

    rows: dict[int, AbsenceRecord] = field(default_factory=dict)

    def for_member(self, member_id: int, since: date) -> list[AbsenceRecord]:
        return _upcoming([r for r in self.rows.values() if r.member_id == member_id], since)

    def for_day(self, raid_day: str, since: date) -> list[AbsenceRecord]:
        return _upcoming([r for r in self.rows.values() if r.raid_day == raid_day], since)

    def get(self, absence_id: int) -> AbsenceRecord | None:
        return self.rows.get(absence_id)

    def add(self, member_id: int, raid_day: str, first: date, last: date, note: str | None) -> AbsenceRecord:
        row = AbsenceRecord(max(self.rows, default=0) + 1, member_id, raid_day, first, last, note, datetime.now(UTC))
        self.rows[row.id] = row
        return row

    def change(self, absence_id: int, first: date, last: date, note: str | None) -> AbsenceRecord | None:
        row = self.rows.get(absence_id)
        if row is None:
            return None
        self.rows[absence_id] = replace(row, first_date=first, last_date=last, note=note)
        return self.rows[absence_id]

    def remove(self, absence_id: int) -> bool:
        return self.rows.pop(absence_id, None) is not None
