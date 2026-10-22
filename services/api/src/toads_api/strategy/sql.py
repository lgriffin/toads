"""StrategyRepository over hub-db. Every change is an officer's action, so each is written to the audit log in the
same transaction."""

from __future__ import annotations

from hub_db import NightDoc
from hub_db import StrategyDoc as StrategyDocRow
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from toads_api import audit
from toads_api.strategy.repository import StrategyDoc


def _doc(row: StrategyDocRow) -> StrategyDoc:
    return StrategyDoc(row.id, row.raid, row.title, row.url, row.created_by, row.created_at)


def _lock_night(db: Session, raid_day: str) -> None:
    """Serialise changes to one night's pins until the transaction ends, so two officers' saves never interleave into
    a list neither sent. SQLite already runs one writer at a time; Postgres takes a transaction-scoped advisory lock."""
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": f"night_strategy:{raid_day}"})


class SqlStrategyRepository:
    def __init__(self, db: sessionmaker[Session]) -> None:
        self._db = db

    def docs(self) -> list[StrategyDoc]:
        with self._db() as db:
            return [_doc(r) for r in db.scalars(select(StrategyDocRow).order_by(StrategyDocRow.id.desc()))]

    def add(self, raid: str, title: str, url: str, by: int, through: str | None = None) -> StrategyDoc:
        with self._db.begin() as db:
            row = StrategyDocRow(raid=raid, title=title, url=url, created_by=by)
            db.add(row)
            db.flush()
            audit.record(
                db, actor=by, action="strategy.add", target=f"strategy_doc:{row.id}", raid_day=through, detail=raid
            )
            return _doc(row)

    def remove(self, doc_id: int, by: int, through: str | None = None) -> bool:
        with self._db.begin() as db:
            row = db.get(StrategyDocRow, doc_id)
            if row is None:
                return False
            audit.record(
                db,
                actor=by,
                action="strategy.remove",
                target=f"strategy_doc:{doc_id}",
                raid_day=through,
                detail=row.raid,
            )
            # Not left to ON DELETE CASCADE alone: SQLite only honours it with foreign keys switched on.
            db.execute(delete(NightDoc).where(NightDoc.doc_id == doc_id))
            db.delete(row)
            return True

    def night_docs(self) -> dict[str, list[int]]:
        query = select(NightDoc).order_by(NightDoc.raid_day_id, NightDoc.position, NightDoc.doc_id)
        out: dict[str, list[int]] = {}
        with self._db() as db:
            for r in db.scalars(query):
                out.setdefault(r.raid_day_id, []).append(r.doc_id)
        return out

    def set_night_docs(self, raid_day: str, doc_ids: list[int], by: int) -> None:
        # A doc taken down while the night is being saved makes the insert fail its foreign key, or two saves collide on
        # the primary key where Postgres's lock is not taken: try once more over the other write.
        for attempt in range(2):
            try:
                self._set_night_docs(raid_day, doc_ids, by)
                return
            except IntegrityError:
                if attempt == 1:
                    raise

    def _set_night_docs(self, raid_day: str, doc_ids: list[int], by: int) -> None:
        with self._db.begin() as db:
            _lock_night(db, raid_day)
            db.execute(delete(NightDoc).where(NightDoc.raid_day_id == raid_day))
            db.add_all(NightDoc(raid_day_id=raid_day, doc_id=d, position=i, set_by=by) for i, d in enumerate(doc_ids))
            db.flush()
            audit.record(
                db,
                actor=by,
                action="strategy.night",
                target=f"night_strategy:{raid_day}",
                raid_day=raid_day,
                detail=",".join(map(str, doc_ids)) or None,
            )
