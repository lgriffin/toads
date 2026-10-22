"""StrategyRepository over hub-db. Every change is an officer's action, so each is written to the audit log in the
same transaction."""

from __future__ import annotations

from hub_db import NightDoc
from hub_db import StrategyDoc as StrategyDocRow
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from toads_api import audit
from toads_api.strategy.repository import Removed, StrategyDoc


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

    def remove(self, doc_id: int, by: int, through: str | None = None, nights: frozenset[str] | None = None) -> Removed:
        with self._db.begin() as db:
            # Locked, so a night pinning it meanwhile waits on its foreign key and then leaves it out; a pin already
            # saved is seen below.
            row = db.scalar(select(StrategyDocRow).where(StrategyDocRow.id == doc_id).with_for_update())
            if row is None:
                return "missing"
            if nights is not None:
                pinning = db.scalars(select(NightDoc.raid_day_id).where(NightDoc.doc_id == doc_id))
                if any(day not in nights for day in pinning):
                    return "pinned"
            target = f"strategy_doc:{doc_id}"
            audit.record(db, actor=by, action="strategy.remove", target=target, raid_day=through, detail=row.raid)
            # Not left to ON DELETE CASCADE alone: SQLite only honours it with foreign keys switched on.
            db.execute(delete(NightDoc).where(NightDoc.doc_id == doc_id))
            db.delete(row)
            return "removed"

    def night_docs(self) -> dict[str, list[int]]:
        query = select(NightDoc).order_by(NightDoc.raid_day_id, NightDoc.position, NightDoc.doc_id)
        out: dict[str, list[int]] = {}
        with self._db() as db:
            for r in db.scalars(query):
                out.setdefault(r.raid_day_id, []).append(r.doc_id)
        return out

    def set_night_docs(self, raid_day: str, doc_ids: list[int], by: int) -> None:
        # Two saves can collide on the primary key where Postgres's lock is not taken, or a doc taken down meanwhile can
        # fail the foreign key: try once more over the other write, which leaves that doc out.
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
            # A doc taken down since the service checked the list is left out rather than failing the save.
            known = set(db.scalars(select(StrategyDocRow.id).where(StrategyDocRow.id.in_(doc_ids))))
            doc_ids = [d for d in doc_ids if d in known]
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
