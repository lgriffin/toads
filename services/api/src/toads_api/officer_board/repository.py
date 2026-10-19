"""Where board cards live. OfficerBoardService only talks to the BoardRepository protocol; the hub-db backed
implementation is `sql.SqlBoardRepository`."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime
from typing import Protocol


@dataclass(frozen=True)
class CardFields:
    """What an officer writes on a card."""

    title: str
    notes: str = ""
    assignee_member_id: int | None = None
    due_on: date | None = None


@dataclass(frozen=True)
class Card:
    id: int
    raid_day: str
    lane: str
    position: int
    fields: CardFields
    created_by: int | None
    created_at: datetime
    updated_at: datetime


class BoardRepository(Protocol):
    def cards(self, raid_day: str) -> list[Card]:
        """Every card on the day's board, by lane, then position."""
        ...

    def add(self, raid_day: str, lane: str, fields: CardFields, by: int) -> Card:
        """A new card at the bottom of `lane`."""
        ...

    def edit(self, raid_day: str, card_id: int, fields: CardFields, by: int) -> Card | None: ...

    def arrange(self, raid_day: str, card_id: int, lanes: dict[str, list[int]], by: int) -> bool:
        """Put every card named in `lanes` in that lane at its index there; `card_id` is the card that moved."""
        ...

    def remove(self, raid_day: str, card_id: int, by: int) -> bool: ...


@dataclass
class InMemoryBoardRepository:
    """For service tests."""

    rows: list[Card] = field(default_factory=list)
    next_id: int = 1

    def cards(self, raid_day: str) -> list[Card]:
        return sorted((c for c in self.rows if c.raid_day == raid_day), key=lambda c: (c.lane, c.position, c.id))

    def add(self, raid_day: str, lane: str, fields: CardFields, by: int) -> Card:
        position = sum(1 for c in self.rows if c.raid_day == raid_day and c.lane == lane)
        now = datetime.now(UTC)
        card = Card(self.next_id, raid_day, lane, position, fields, by, now, now)
        self.next_id += 1
        self.rows.append(card)
        return card

    def _index(self, raid_day: str, card_id: int) -> int | None:
        return next((i for i, c in enumerate(self.rows) if (c.raid_day, c.id) == (raid_day, card_id)), None)

    def edit(self, raid_day: str, card_id: int, fields: CardFields, by: int) -> Card | None:
        i = self._index(raid_day, card_id)
        if i is None:
            return None
        self.rows[i] = replace(self.rows[i], fields=fields, updated_at=datetime.now(UTC))
        return self.rows[i]

    def arrange(self, raid_day: str, card_id: int, lanes: dict[str, list[int]], by: int) -> bool:
        if self._index(raid_day, card_id) is None:
            return False
        for lane, ids in lanes.items():
            for position, cid in enumerate(ids):
                i = self._index(raid_day, cid)
                if i is not None:
                    stamp = datetime.now(UTC) if cid == card_id else self.rows[i].updated_at
                    self.rows[i] = replace(self.rows[i], lane=lane, position=position, updated_at=stamp)
        return True

    def remove(self, raid_day: str, card_id: int, by: int) -> bool:
        i = self._index(raid_day, card_id)
        if i is None:
            return False
        del self.rows[i]
        return True
