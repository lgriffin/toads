"""Where awards live. AwardService only talks to the AwardRepository protocol; the hub-db backed implementation is
`sql.SqlAwardRepository`."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True)
class AwardRecord:
    id: int
    member_id: int
    award_id: str
    # "YYYY-MM" for a monthly award, "" otherwise.
    period: str
    note: str | None
    awarded_by: int | None
    awarded_at: datetime


class DuplicateAwardError(Exception):
    """The member already holds this award (for this month, when it is a monthly one)."""


class AwardRepository(Protocol):
    def member_exists(self, member_id: int) -> bool: ...
    def awards(self, member_ids: Iterable[int] | None = None) -> list[AwardRecord]: ...
    def add(self, member_id: int, award_id: str, period: str, note: str | None, by: int) -> AwardRecord: ...
    def remove(self, award_row_id: int, by: int) -> bool: ...


@dataclass
class InMemoryAwardRepository:
    """For service tests."""

    members: set[int] = field(default_factory=set)
    rows: dict[int, AwardRecord] = field(default_factory=dict)

    def member_exists(self, member_id: int) -> bool:
        return member_id in self.members

    def awards(self, member_ids: Iterable[int] | None = None) -> list[AwardRecord]:
        wanted = None if member_ids is None else set(member_ids)
        return [r for _, r in sorted(self.rows.items()) if wanted is None or r.member_id in wanted]

    def add(self, member_id: int, award_id: str, period: str, note: str | None, by: int) -> AwardRecord:
        if any((r.member_id, r.award_id, r.period) == (member_id, award_id, period) for r in self.rows.values()):
            raise DuplicateAwardError
        row = AwardRecord(max(self.rows, default=0) + 1, member_id, award_id, period, note, by, datetime.now(UTC))
        self.rows[row.id] = row
        return row

    def remove(self, award_row_id: int, by: int) -> bool:
        return self.rows.pop(award_row_id, None) is not None
