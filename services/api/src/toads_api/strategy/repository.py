"""Where strategy docs and nights' raids live. StrategyService only talks to the StrategyRepository protocol; the
hub-db backed implementation is `sql.SqlStrategyRepository`."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True)
class StrategyDoc:
    """A Google Doc pinned to a raid, for one raid night (`raid_day`) or for every night (None)."""

    id: int
    raid: str
    raid_day: str | None
    title: str
    url: str
    created_by: int | None
    created_at: datetime


class StrategyRepository(Protocol):
    def docs(self) -> list[StrategyDoc]:
        """Every doc, newest first."""
        ...

    def pin(
        self, raid: str, raid_day: str | None, title: str, url: str, by: int, keep: int, through: str | None = None
    ) -> StrategyDoc:
        """Pin a doc to `raid` for `raid_day` (None: every night), replacing the one pinned there. Each raid and night
        keeps only its `keep` newest docs. A doc for one night also adds the raid to the end of that night's raids, if
        missing, in the same write. `through`: the night the officer acted through, for the audit log."""
        ...

    def remove(
        self, doc_id: int, by: int, nights: frozenset[str | None] | None = None, through: str | None = None
    ) -> bool:
        """Take a doc down. With `nights`, only a doc pinned for one of them (None standing for every night)."""
        ...

    def night_raids(self) -> dict[str, list[str]]:
        """The raids each raid day is running, in order, by raid day; a day that has not said is left out."""
        ...

    def set_night_raids(self, raid_day: str, raids: list[str], by: int) -> None:
        """Say which raids `raid_day` is running, in order; an empty list clears them."""
        ...


@dataclass
class InMemoryStrategyRepository:
    """For service tests."""

    rows: list[StrategyDoc] = field(default_factory=list)
    nights: dict[str, list[str]] = field(default_factory=dict)
    next_id: int = 1

    def docs(self) -> list[StrategyDoc]:
        return sorted(self.rows, key=lambda d: -d.id)

    def pin(
        self, raid: str, raid_day: str | None, title: str, url: str, by: int, keep: int, through: str | None = None
    ) -> StrategyDoc:
        if raid_day is not None and raid not in self.nights.get(raid_day, []):
            self.nights[raid_day] = [*self.nights.get(raid_day, []), raid]
        doc = StrategyDoc(self.next_id, raid, raid_day, title, url, by, datetime.now(UTC))
        self.next_id += 1
        self.rows.append(doc)
        kept = [d.id for d in self.docs() if (d.raid, d.raid_day) == (raid, raid_day)][:keep]
        self.rows = [d for d in self.rows if (d.raid, d.raid_day) != (raid, raid_day) or d.id in kept]
        return doc

    def remove(
        self, doc_id: int, by: int, nights: frozenset[str | None] | None = None, through: str | None = None
    ) -> bool:
        before = len(self.rows)
        self.rows = [d for d in self.rows if d.id != doc_id or (nights is not None and d.raid_day not in nights)]
        return len(self.rows) < before

    def night_raids(self) -> dict[str, list[str]]:
        return {day: list(raids) for day, raids in self.nights.items() if raids}

    def set_night_raids(self, raid_day: str, raids: list[str], by: int) -> None:
        self.nights[raid_day] = list(raids)
