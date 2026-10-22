"""StrategyRepository over hub-db. Every change is an officer's action, so each is written to the audit log in the
same transaction."""

from __future__ import annotations

from hub_db import NightRaid
from hub_db import StrategyDoc as StrategyDocRow
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from toads_api import audit
from toads_api.strategy.repository import StrategyDoc


def _doc(row: StrategyDocRow) -> StrategyDoc:
    return StrategyDoc(row.id, row.raid, row.raid_day_id, row.title, row.url, row.created_by, row.created_at)


def _where(raid: str, raid_day: str | None) -> str:
    """The audit detail for a doc: its raid and the night it is for."""
    return f"{raid} for {raid_day or 'every night'}"


def _lock_night(db: Session, raid_day: str) -> None:
    """Serialise changes to one night's raids until the transaction ends, so two officers' saves never interleave into
    a list neither sent. SQLite already runs one writer at a time; Postgres takes a transaction-scoped advisory lock."""
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": f"night_raid:{raid_day}"})


class SqlStrategyRepository:
    def __init__(self, db: sessionmaker[Session]) -> None:
        self._db = db

    def docs(self) -> list[StrategyDoc]:
        with self._db() as db:
            return [_doc(r) for r in db.scalars(select(StrategyDocRow).order_by(StrategyDocRow.id.desc()))]

    def pin(
        self, raid: str, raid_day: str | None, title: str, url: str, by: int, keep: int, through: str | None = None
    ) -> StrategyDoc:
        with self._db.begin() as db:
            if raid_day is not None:
                # In the same transaction as the doc, so a pinned night doc is never left off its night's Raid page.
                _lock_night(db, raid_day)
                if db.get(NightRaid, (raid_day, raid)) is None:
                    last = db.scalar(select(func.max(NightRaid.position)).where(NightRaid.raid_day_id == raid_day))
                    db.add(
                        NightRaid(raid_day_id=raid_day, raid=raid, position=0 if last is None else last + 1, set_by=by)
                    )
            row = StrategyDocRow(raid=raid, raid_day_id=raid_day, title=title, url=url, created_by=by)
            db.add(row)
            db.flush()
            older = (
                select(StrategyDocRow.id)
                .where(
                    StrategyDocRow.raid == raid,
                    StrategyDocRow.raid_day_id.is_(None)
                    if raid_day is None
                    else StrategyDocRow.raid_day_id == raid_day,
                )
                .order_by(StrategyDocRow.id.desc())
            )
            stale = list(db.scalars(older.offset(keep)))
            if stale:
                db.execute(delete(StrategyDocRow).where(StrategyDocRow.id.in_(stale)))
            audit.record(
                db,
                actor=by,
                action="strategy.pin",
                target=f"strategy_doc:{row.id}",
                raid_day=through,
                detail=_where(raid, raid_day),
            )
            return _doc(row)

    def remove(
        self, doc_id: int, by: int, nights: frozenset[str | None] | None = None, through: str | None = None
    ) -> bool:
        with self._db.begin() as db:
            row = db.get(StrategyDocRow, doc_id)
            if row is None or (nights is not None and row.raid_day_id not in nights):
                return False
            audit.record(
                db,
                actor=by,
                action="strategy.remove",
                target=f"strategy_doc:{doc_id}",
                raid_day=through,
                detail=_where(row.raid, row.raid_day_id),
            )
            db.delete(row)
            return True

    def night_raids(self) -> dict[str, list[str]]:
        query = select(NightRaid).order_by(NightRaid.raid_day_id, NightRaid.position, NightRaid.raid)
        out: dict[str, list[str]] = {}
        with self._db() as db:
            for r in db.scalars(query):
                out.setdefault(r.raid_day_id, []).append(r.raid)
        return out

    def set_night_raids(self, raid_day: str, raids: list[str], by: int) -> None:
        # Two officers saving a night's raids at once: the rows' primary key lets one write land, and the other tries
        # again over it, so the night ends up with one of the two lists, never a mix that fails.
        for attempt in range(2):
            try:
                self._set_night_raids(raid_day, raids, by)
                return
            except IntegrityError:
                if attempt == 1:
                    raise

    def _set_night_raids(self, raid_day: str, raids: list[str], by: int) -> None:
        with self._db.begin() as db:
            _lock_night(db, raid_day)
            db.execute(delete(NightRaid).where(NightRaid.raid_day_id == raid_day))
            db.add_all(NightRaid(raid_day_id=raid_day, raid=r, position=i, set_by=by) for i, r in enumerate(raids))
            db.flush()
            audit.record(
                db,
                actor=by,
                action="strategy.night",
                target=f"night_raid:{raid_day}",
                raid_day=raid_day,
                detail=",".join(raids) or None,
            )
