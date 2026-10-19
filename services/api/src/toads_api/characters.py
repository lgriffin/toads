"""Where the API looks up characters seen in the guild's logs.

Characters belong to wcl-store (lgriffin/warcraftlogs_project), whose tables the worker keeps in the hub
database beside hub-db's (toads_worker.store). Only the worker imports the analyzer, so `SqlCharacters`
reads wcl-store's `characters` table by name, read-only; tests use `InMemoryCharacters`.
The claim flow resolves names server-side only: a client-sent name would let anyone auto-approve a
claim on someone else's character by sending their own nickname (REQ-HUB-CLAIM-001).
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import Column, Integer, MetaData, Table, Text, case, func, inspect, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.sql import Select

# Most names a search answers with; members narrow it by typing more.
SEARCH_LIMIT = 20
# Shortest query that searches: one letter would list half the guild.
MIN_QUERY = 2


@dataclass(frozen=True)
class Character:
    id: int
    name: str
    player_class: str


class CharacterDirectory(Protocol):
    def name_of(self, character_id: int) -> str | None: ...

    def search(self, query: str) -> list[Character]:
        """Characters whose name contains `query` (case-insensitive), names starting with it first; empty for a query
        shorter than MIN_QUERY."""
        ...


def _fold(s: str) -> str:
    return unicodedata.normalize("NFKC", s).strip().casefold()


def _ranked(found: list[Character], query: str) -> list[Character]:
    q = _fold(query)
    return sorted(found, key=lambda c: (not _fold(c.name).startswith(q), _fold(c.name)))[:SEARCH_LIMIT]


class InMemoryCharacters:
    def __init__(self, names: dict[int, str] | None = None, classes: dict[int, str] | None = None) -> None:
        self.names: dict[int, str] = dict(names or {})
        self.classes: dict[int, str] = dict(classes or {})

    def name_of(self, character_id: int) -> str | None:
        return self.names.get(character_id)

    def search(self, query: str) -> list[Character]:
        q = _fold(query)
        if len(q) < MIN_QUERY:
            return []
        found = [Character(cid, n, self.classes.get(cid, "")) for cid, n in self.names.items() if q in _fold(n)]
        return _ranked(found, query)


# wcl-store's table as far as the claim flow needs it (wcl_store.postgres.schema.characters). Never created from here.
_characters = Table(
    "characters",
    MetaData(),
    Column("id", Integer, primary_key=True),
    Column("name", Text, nullable=False),
    Column("player_class", Text, nullable=False),
)


class SqlCharacters:
    """wcl-store's characters in the hub database. Before the worker's first run the table is missing, and the
    directory reads as empty rather than failing; any other database error still raises."""

    def __init__(self, db: sessionmaker[Session]) -> None:
        self._db = db

    def _rows(self, stmt: Select[tuple[int, str, str]]) -> list[Character]:
        try:
            with self._db() as db:
                return [Character(r.id, r.name, r.player_class) for r in db.execute(stmt)]
        except DBAPIError:
            with self._db() as db:
                if inspect(db.connection()).has_table(_characters.name):
                    raise
            return []

    def name_of(self, character_id: int) -> str | None:
        cols = (_characters.c.id, _characters.c.name, _characters.c.player_class)
        found = self._rows(select(*cols).where(_characters.c.id == character_id))
        return found[0].name if found else None

    def search(self, query: str) -> list[Character]:
        q = query.strip()
        if len(_fold(q)) < MIN_QUERY:
            return []
        # NFKC on the query folds full-width input; stored names are WoW names, which have no width forms.
        escaped = unicodedata.normalize("NFKC", q).lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        lower = func.lower(_characters.c.name)
        stmt = (
            select(_characters.c.id, _characters.c.name, _characters.c.player_class)
            .where(lower.like(f"%{escaped}%", escape="\\"))
            .order_by(case((lower.like(f"{escaped}%", escape="\\"), 0), else_=1), lower)
            .limit(SEARCH_LIMIT)
        )
        return _ranked(self._rows(stmt), q)
