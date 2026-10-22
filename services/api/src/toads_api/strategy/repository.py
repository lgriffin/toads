"""Where strategy docs and nights' pins live. StrategyService only talks to the StrategyRepository protocol; the hub-db
backed implementation is `sql.SqlStrategyRepository`."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True)
class StrategyDoc:
    """A Google Doc added to a raid."""

    id: int
    raid: str
    title: str
    url: str
    created_by: int | None
    created_at: datetime


class StrategyRepository(Protocol):
    def docs(self) -> list[StrategyDoc]:
        """Every doc, newest first."""
        ...

    def add(self, raid: str, title: str, url: str, by: int, through: str | None = None) -> StrategyDoc:
        """Add a doc to `raid`. `through`: the night the officer acted through, for the audit log."""
        ...

    def remove(self, doc_id: int, by: int, through: str | None = None) -> bool:
        """Take a doc down, and off every night that pinned it."""
        ...

    def night_docs(self) -> dict[str, list[int]]:
        """The docs each raid day pins for its raiders, in order, by raid day; a day that pins none is left out."""
        ...

    def set_night_docs(self, raid_day: str, doc_ids: list[int], by: int) -> None:
        """Say which docs `raid_day` pins for its raiders, in order; an empty list clears them."""
        ...


@dataclass
class InMemoryStrategyRepository:
    """For service tests."""

    rows: list[StrategyDoc] = field(default_factory=list)
    nights: dict[str, list[int]] = field(default_factory=dict)
    next_id: int = 1

    def docs(self) -> list[StrategyDoc]:
        return sorted(self.rows, key=lambda d: -d.id)

    def add(self, raid: str, title: str, url: str, by: int, through: str | None = None) -> StrategyDoc:
        doc = StrategyDoc(self.next_id, raid, title, url, by, datetime.now(UTC))
        self.next_id += 1
        self.rows.append(doc)
        return doc

    def remove(self, doc_id: int, by: int, through: str | None = None) -> bool:
        before = len(self.rows)
        self.rows = [d for d in self.rows if d.id != doc_id]
        self.nights = {day: [i for i in ids if i != doc_id] for day, ids in self.nights.items()}
        return len(self.rows) < before

    def night_docs(self) -> dict[str, list[int]]:
        return {day: list(ids) for day, ids in self.nights.items() if ids}

    def set_night_docs(self, raid_day: str, doc_ids: list[int], by: int) -> None:
        self.nights[raid_day] = list(doc_ids)
