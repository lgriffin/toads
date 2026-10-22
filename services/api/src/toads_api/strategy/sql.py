"""StrategyRepository over hub-db. Every change is an officer's action, so each is written to the audit log in the
same transaction."""

from __future__ import annotations

from datetime import UTC, datetime

from hub_db import NightRaid
from hub_db import StrategyDoc as StrategyDocRow
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from toads_api import audit
from toads_api.strategy.repository import StrategyDoc


def _doc(row: StrategyDocRow) -> StrategyDoc:
    return StrategyDoc(row.id, row.raid, row.title, row.url, row.created_by, row.created_at)


class SqlStrategyRepository:
    def __init__(self, db: sessionmaker[Session]) -> None:
        self._db = db

    def docs(self) -> list[StrategyDoc]:
        with self._db() as db:
            return [_doc(r) for r in db.scalars(select(StrategyDocRow).order_by(StrategyDocRow.id.desc()))]

    def pin(self, raid: str, title: str, url: str, by: int, keep: int, raid_day: str | None = None) -> StrategyDoc:
        with self._db.begin() as db:
            row = StrategyDocRow(raid=raid, title=title, url=url, created_by=by)
            db.add(row)
            db.flush()
            older = select(StrategyDocRow.id).where(StrategyDocRow.raid == raid).order_by(StrategyDocRow.id.desc())
            stale = list(db.scalars(older.offset(keep)))
            if stale:
                db.execute(delete(StrategyDocRow).where(StrategyDocRow.id.in_(stale)))
            audit.record(
                db, actor=by, action="strategy.pin", target=f"strategy_doc:{row.id}", raid_day=raid_day, detail=raid
            )
            return _doc(row)

    def remove(self, doc_id: int, by: int, raid_day: str | None = None) -> bool:
        with self._db.begin() as db:
            row = db.get(StrategyDocRow, doc_id)
            if row is None:
                return False
            audit.record(
                db,
                actor=by,
                action="strategy.remove",
                target=f"strategy_doc:{doc_id}",
                raid_day=raid_day,
                detail=row.raid,
            )
            db.delete(row)
            return True

    def night_raids(self) -> dict[str, str]:
        with self._db() as db:
            return {r.raid_day_id: r.raid for r in db.scalars(select(NightRaid))}

    def set_night_raid(self, raid_day: str, raid: str | None, by: int) -> None:
        with self._db.begin() as db:
            row = db.get(NightRaid, raid_day)
            if raid is None:
                if row is not None:
                    db.delete(row)
            elif row is None:
                db.add(NightRaid(raid_day_id=raid_day, raid=raid, set_by=by))
            else:
                row.raid = raid
                row.set_by = by
                row.set_at = datetime.now(UTC)
            audit.record(
                db, actor=by, action="strategy.night", target=f"night_raid:{raid_day}", raid_day=raid_day, detail=raid
            )
