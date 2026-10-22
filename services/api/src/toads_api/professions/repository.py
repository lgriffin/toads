"""Where professions and crafter designations live. ProfessionService only talks to the ProfessionRepository protocol;
the hub-db backed implementation is `sql.SqlProfessionRepository`."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True)
class ProfessionRecord:
    member_id: int
    profession: str
    skill: int | None = None
    specialisation: str | None = None


@dataclass(frozen=True)
class CrafterRecord:
    profession: str
    member_id: int
    note: str | None
    designated_by: int | None
    designated_at: datetime


class ProfessionRepository(Protocol):
    def professions(self, member_ids: Iterable[int] | None = None) -> list[ProfessionRecord]:
        """Every listed profession of these members (everyone's when None), by member then profession."""
        ...

    def set_professions(self, member_id: int, records: list[ProfessionRecord]) -> list[str]:
        """Replace a member's professions, dropping any crafter designation for a profession they no longer list.
        Returns the professions whose designation went."""
        ...

    def crafters(self, member_ids: Iterable[int] | None = None) -> list[CrafterRecord]: ...
    def designate(
        self, profession: str, member_id: int, note: str | None, by: int, raid_day: str | None
    ) -> CrafterRecord:
        """Name a member a guild crafter for a profession, or change the note of one already named; audited."""
        ...

    def undesignate(self, profession: str, member_id: int, by: int, raid_day: str | None) -> bool:
        """Audited. False when they were not named for it."""
        ...

    def members_on(self, raid_day: str) -> list[int]:
        """Members whose Discord roles put them on this raid day, as last read from Discord."""
        ...


@dataclass
class InMemoryProfessionRepository:
    """For service tests."""

    rows: dict[int, list[ProfessionRecord]] = field(default_factory=dict)
    named: dict[tuple[str, int], CrafterRecord] = field(default_factory=dict)
    raid_days: dict[int, list[str]] = field(default_factory=dict)

    def professions(self, member_ids: Iterable[int] | None = None) -> list[ProfessionRecord]:
        wanted = None if member_ids is None else set(member_ids)
        return [
            r
            for m, rows in sorted(self.rows.items())
            if wanted is None or m in wanted
            for r in sorted(rows, key=lambda r: r.profession)
        ]

    def set_professions(self, member_id: int, records: list[ProfessionRecord]) -> list[str]:
        self.rows[member_id] = list(records)
        kept = {r.profession for r in records}
        gone = sorted(p for p, m in self.named if m == member_id and p not in kept)
        for p in gone:
            del self.named[(p, member_id)]
        return gone

    def crafters(self, member_ids: Iterable[int] | None = None) -> list[CrafterRecord]:
        wanted = None if member_ids is None else set(member_ids)
        return [r for _, r in sorted(self.named.items()) if wanted is None or r.member_id in wanted]

    def designate(
        self, profession: str, member_id: int, note: str | None, by: int, raid_day: str | None
    ) -> CrafterRecord:
        row = CrafterRecord(profession, member_id, note, by, datetime.now(UTC))
        self.named[(profession, member_id)] = row
        return row

    def undesignate(self, profession: str, member_id: int, by: int, raid_day: str | None) -> bool:
        return self.named.pop((profession, member_id), None) is not None

    def members_on(self, raid_day: str) -> list[int]:
        return sorted(m for m, days in self.raid_days.items() if raid_day in days)
