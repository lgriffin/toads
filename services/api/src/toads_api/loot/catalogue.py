"""The item catalogue officers search when they add an item to a night's loot list (docs/loot.md "Item data").

The data is LibItemDB's (MIT, `data/NOTICE`), turned into `data/items.tsv.gz` by `scripts/import_items.py`: WoW
Forever's items, with Classic's filling in the raid loot Forever's beta data lacks. It is read once, kept in memory
(about 24,000 items), and searched by name. No web framework or storage code.
"""

from __future__ import annotations

import gzip
from collections.abc import Iterable
from dataclasses import dataclass
from functools import cache
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data" / "items.tsv.gz"
SEARCH_LIMIT = 25
# Shorter than this matches too much to be useful ("a" is in most names).
MIN_QUERY = 2


@dataclass(frozen=True)
class CatalogueItem:
    id: int
    name: str
    # The game's quality: 0 poor, 1 common, 2 uncommon, 3 rare, 4 epic, 5 legendary, 6 artifact, 7 heirloom.
    quality: int
    item_level: int
    # The game's equip slot (INVTYPE_HEAD, ...); "" or INVTYPE_NON_EQUIP_IGNORE for an item nobody wears.
    slot: str
    # Which LibItemDB data named it: "Forever", or "Vanilla" (Classic) for an item Forever's beta data lacks.
    flavour: str = ""


def _fold(s: str) -> str:
    """A name as search compares it: case and the typographic apostrophe set aside."""
    return s.casefold().replace("\u2019", "'")


class ItemCatalogue:
    def __init__(self, items: Iterable[CatalogueItem], source: str = "") -> None:
        self._items = {i.id: i for i in items}
        self._folded = [(_fold(i.name), i) for i in self._items.values()]
        # Where the data came from, for docs and the API's answer: "LibItemDB ItemDB-v1.7.0, Forever enUS: ...".
        self.source = source

    def __len__(self) -> int:
        return len(self._items)

    def get(self, item_id: int) -> CatalogueItem | None:
        return self._items.get(item_id)

    def search(self, query: str, limit: int = SEARCH_LIMIT) -> list[CatalogueItem]:
        """Items whose name holds every word of `query`: whole-name matches first, then names that start with it, then
        the rest; within each, the best quality and highest item level first, so the big-ticket items lead."""
        q = " ".join(_fold(query).split())
        if len(q) < MIN_QUERY:
            return []
        words = q.split()
        hits: list[tuple[int, CatalogueItem]] = []
        for name, item in self._folded:
            if all(w in name for w in words):
                order = 0 if name == q else 1 if name.startswith(q) else 2 if q in name else 3
                hits.append((order, item))
        hits.sort(key=lambda h: (h[0], -h[1].quality, -h[1].item_level, h[1].name, h[1].id))
        return [item for _, item in hits[: max(0, limit)]]


def parse(lines: Iterable[str]) -> ItemCatalogue:
    """The catalogue from the TSV's lines: `#` comments (the first names the source), a header, then one item a line."""
    source = ""
    items = []
    header_seen = False
    for line in lines:
        line = line.rstrip("\n")
        if line.startswith("#"):
            source = source or line[1:].strip()
            continue
        if not header_seen:
            header_seen = True
            continue
        fields = line.split("\t")
        if len(fields) < 7:
            continue
        item_id, name, quality, _class, _subclass, slot, level = fields[:7]
        flavour = fields[7] if len(fields) > 7 else ""
        items.append(CatalogueItem(int(item_id), name, int(quality), int(level), slot, flavour))
    return ItemCatalogue(items, source)


@cache
def bundled() -> ItemCatalogue:
    """The catalogue that ships with the API, read on first use."""
    with gzip.open(DATA, "rt", encoding="utf-8") as f:
        return parse(f)
