"""Where specs and comps live. CompService only talks to the CompRepository protocol; the hub-db backed
implementation is `sql.SqlCompRepository`."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True)
class SpecRecord:
    member_id: int
    wow_class: str
    primary: str
    secondary: str | None


@dataclass(frozen=True)
class Seat:
    spec: str
    member_id: int | None = None


@dataclass(frozen=True)
class CompRecord:
    id: int
    raid_day: str
    name: str
    size: int
    # One per raid seat, in group order; None is an empty seat.
    slots: list[Seat | None]
    updated_by: int | None
    updated_at: datetime


class DuplicateCompError(Exception):
    """The raid day already has a comp by that name."""


class CompRepository(Protocol):
    def specs(self, member_ids: Iterable[int] | None = None) -> list[SpecRecord]: ...
    def set_specs(self, record: SpecRecord) -> None: ...
    def clear_specs(self, member_id: int) -> bool: ...

    def members_on(self, raid_day: str) -> list[int]:
        """Members whose Discord roles put them on this raid day when they last signed in."""
        ...

    def comps(self, raid_day: str) -> list[CompRecord]: ...
    def save_comp(
        self, raid_day: str, comp_id: int | None, name: str, size: int, slots: list[Seat | None], by: int
    ) -> CompRecord | None:
        """Create (comp_id None) or replace a comp; None when comp_id names no comp of this raid day."""
        ...

    def delete_comp(self, raid_day: str, comp_id: int, by: int) -> bool: ...


@dataclass
class InMemoryCompRepository:
    """For service tests."""

    spec_rows: dict[int, SpecRecord] = field(default_factory=dict)
    raid_days: dict[int, list[str]] = field(default_factory=dict)
    comp_rows: dict[int, CompRecord] = field(default_factory=dict)

    def specs(self, member_ids: Iterable[int] | None = None) -> list[SpecRecord]:
        wanted = None if member_ids is None else set(member_ids)
        return [r for i, r in sorted(self.spec_rows.items()) if wanted is None or i in wanted]

    def set_specs(self, record: SpecRecord) -> None:
        self.spec_rows[record.member_id] = record

    def clear_specs(self, member_id: int) -> bool:
        return self.spec_rows.pop(member_id, None) is not None

    def members_on(self, raid_day: str) -> list[int]:
        return sorted(m for m, days in self.raid_days.items() if raid_day in days)

    def comps(self, raid_day: str) -> list[CompRecord]:
        return [c for c in self.comp_rows.values() if c.raid_day == raid_day]

    def save_comp(
        self, raid_day: str, comp_id: int | None, name: str, size: int, slots: list[Seat | None], by: int
    ) -> CompRecord | None:
        if any(c.raid_day == raid_day and c.name == name and c.id != comp_id for c in self.comp_rows.values()):
            raise DuplicateCompError
        now = datetime.now(UTC)
        if comp_id is None:
            comp_id = max(self.comp_rows, default=0) + 1
            row = CompRecord(comp_id, raid_day, name, size, list(slots), by, now)
        else:
            old = self.comp_rows.get(comp_id)
            if old is None or old.raid_day != raid_day:
                return None
            row = replace(old, name=name, size=size, slots=list(slots), updated_by=by, updated_at=now)
        self.comp_rows[comp_id] = row
        return row

    def delete_comp(self, raid_day: str, comp_id: int, by: int) -> bool:
        row = self.comp_rows.get(comp_id)
        if row is None or row.raid_day != raid_day:
            return False
        del self.comp_rows[comp_id]
        return True
