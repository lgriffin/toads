"""Rules for the officers' loot lists. No RBAC, web framework or storage imports: the routes decide who may call (the
raid day's officers) and the repository decides where lists live.

A night's loot list holds the big-ticket items its officers track. Each item has a line of the night's members ranked
1st, 2nd, 3rd...: the first one in line without the item gets the next drop, and officers mark each one received.
"""

from __future__ import annotations

from collections.abc import Callable, Collection, Iterable
from dataclasses import dataclass
from datetime import datetime

from toads_api.loot.catalogue import CatalogueItem, ItemCatalogue
from toads_api.loot.repository import LootEntry, LootRepository

# A list is for the items that need deciding, not every drop: past this, officers take finished items off first.
ITEM_LIMIT = 100
LINE_LIMIT = 10
NOTE_LIMIT = 500


class LootError(Exception):
    """A request the rules refuse. `status` is the HTTP code the adapter should answer with."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


@dataclass(frozen=True)
class RecipientView:
    member_id: int
    rank: int
    # The member's shown name; "" when they are no longer a member of the hub.
    name: str
    received_at: datetime | None
    # First in line without the item: the one who gets the next drop.
    next_up: bool


@dataclass(frozen=True)
class LootView:
    entry: LootEntry
    # The catalogue's facts on the item (quality, item level, slot); None if a newer catalogue dropped it.
    item: CatalogueItem | None
    recipients: list[RecipientView]


class LootService:
    def __init__(
        self,
        repo: LootRepository,
        catalogue: Callable[[], ItemCatalogue],
        shown_names: Callable[[Iterable[int]], dict[int, str]],
        roster: Callable[[str], Collection[int]],
        clock: Callable[[], datetime],
    ) -> None:
        self.repo = repo
        self._catalogue = catalogue
        self._shown_names = shown_names
        self._roster = roster
        self._clock = clock

    @property
    def catalogue(self) -> ItemCatalogue:
        return self._catalogue()

    def search(self, query: str, limit: int) -> list[CatalogueItem]:
        return self.catalogue.search(query, limit)

    def _views(self, entries: list[LootEntry]) -> list[LootView]:
        names = self._shown_names({r.member_id for e in entries for r in e.recipients})
        catalogue = self.catalogue
        views = []
        for e in entries:
            waiting = [r for r in e.recipients if r.received_at is None]
            first = min(waiting, key=lambda r: r.rank).member_id if waiting else None
            line = [
                RecipientView(r.member_id, r.rank, names.get(r.member_id, ""), r.received_at, r.member_id == first)
                for r in sorted(e.recipients, key=lambda r: r.rank)
            ]
            views.append(LootView(e, catalogue.get(e.item_id), line))
        return views

    def _view(self, entry: LootEntry | None) -> LootView:
        if entry is None:
            raise LootError("That item is not on this night's loot list", status=404)
        return self._views([entry])[0]

    def loot(self, raid_day: str) -> list[LootView]:
        return self._views(self.repo.entries(raid_day))

    def _note(self, note: str) -> str:
        note = note.strip()
        if len(note) > NOTE_LIMIT:
            raise LootError(f"Keep the note to {NOTE_LIMIT} characters", status=422)
        return note

    def add(self, raid_day: str, *, item_id: int, by: int, note: str = "") -> LootView:
        """Put a catalogue item on the night's list, by its canonical name, with nobody in line yet."""
        item = self.catalogue.get(item_id)
        if item is None:
            raise LootError("No item has that id; search for it by name", status=422)
        note = self._note(note)
        if len(self.repo.entries(raid_day)) >= ITEM_LIMIT:
            raise LootError(f"A loot list holds {ITEM_LIMIT} items; take finished ones off first", status=409)
        entry = self.repo.add(raid_day, item.id, item.name, note, by, self._clock())
        if entry is None:
            raise LootError(f"{item.name} is already on this night's loot list", status=409)
        return self._view(entry)

    def set_note(self, raid_day: str, entry_id: int, *, note: str, by: int) -> LootView:
        return self._view(self.repo.set_note(raid_day, entry_id, self._note(note), by, self._clock()))

    def set_line(self, raid_day: str, entry_id: int, *, member_ids: list[int], by: int) -> LootView:
        """Rank exactly these members for the item, first to last. Each must be on the night's roster, unless they
        were in line already (someone who left the night keeps their place until an officer takes them off)."""
        entry = self.repo.entry(raid_day, entry_id)
        if entry is None:
            raise LootError("That item is not on this night's loot list", status=404)
        if len(set(member_ids)) != len(member_ids):
            raise LootError("Someone is in line twice", status=422)
        if len(member_ids) > LINE_LIMIT:
            raise LootError(f"Keep the line to {LINE_LIMIT} people", status=422)
        already = {r.member_id for r in entry.recipients}
        new = [m for m in member_ids if m not in already]
        if new:
            roster = set(self._roster(raid_day))
            if any(m not in roster for m in new):
                raise LootError("Only members of this night's raid group can be put in line", status=422)
        return self._view(self.repo.set_line(raid_day, entry_id, member_ids, by, self._clock()))

    def mark(self, raid_day: str, entry_id: int, member_id: int, *, received: bool, by: int) -> LootView:
        if self.repo.entry(raid_day, entry_id) is None:
            raise LootError("That item is not on this night's loot list", status=404)
        at = self._clock() if received else None
        entry = self.repo.mark(raid_day, entry_id, member_id, at, by)
        if entry is None:
            raise LootError("That member is not in line for this item", status=404)
        return self._view(entry)

    def remove(self, raid_day: str, entry_id: int, by: int) -> None:
        if not self.repo.remove(raid_day, entry_id, by):
            raise LootError("That item is not on this night's loot list", status=404)
