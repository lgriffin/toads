"""Where strategy docs and nights' raids live. StrategyService only talks to the StrategyRepository protocol; the
hub-db backed implementation is `sql.SqlStrategyRepository`."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True)
class StrategyDoc:
    """A Google Doc pinned to a raid."""

    id: int
    raid: str
    title: str
    url: str
    created_by: int | None
    created_at: datetime


class StrategyRepository(Protocol):
    def docs(self) -> list[StrategyDoc]:
        """Every raid's docs, newest first."""
        ...

    def pin(self, raid: str, title: str, url: str, by: int, keep: int, raid_day: str | None = None) -> StrategyDoc:
        """Pin a doc to `raid`, replacing its pinned doc. The raid keeps only its `keep` newest docs. `raid_day` is the
        night whose officer pinned it, for the audit log; None for the global tier."""
        ...

    def remove(self, doc_id: int, by: int, raid_day: str | None = None) -> bool: ...

    def night_raids(self) -> dict[str, str]:
        """The raid each raid day is running, by raid day; a day that has not said is left out."""
        ...

    def set_night_raid(self, raid_day: str, raid: str | None, by: int) -> None:
        """Say which raid `raid_day` is running; None clears it."""
        ...


@dataclass
class InMemoryStrategyRepository:
    """For service tests."""

    rows: list[StrategyDoc] = field(default_factory=list)
    nights: dict[str, str] = field(default_factory=dict)
    next_id: int = 1

    def docs(self) -> list[StrategyDoc]:
        return sorted(self.rows, key=lambda d: -d.id)

    def pin(self, raid: str, title: str, url: str, by: int, keep: int, raid_day: str | None = None) -> StrategyDoc:
        doc = StrategyDoc(self.next_id, raid, title, url, by, datetime.now(UTC))
        self.next_id += 1
        self.rows.append(doc)
        kept = [d.id for d in self.docs() if d.raid == raid][:keep]
        self.rows = [d for d in self.rows if d.raid != raid or d.id in kept]
        return doc

    def remove(self, doc_id: int, by: int, raid_day: str | None = None) -> bool:
        before = len(self.rows)
        self.rows = [d for d in self.rows if d.id != doc_id]
        return len(self.rows) < before

    def night_raids(self) -> dict[str, str]:
        return dict(self.nights)

    def set_night_raid(self, raid_day: str, raid: str | None, by: int) -> None:
        if raid is None:
            self.nights.pop(raid_day, None)
        else:
            self.nights[raid_day] = raid
