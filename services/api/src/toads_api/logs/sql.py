"""LogRepository over hub-db."""

from __future__ import annotations

from typing import Any

from hub_db import LogIndex, LogRaid
from hub_db.logs import INDEX_ROW
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from toads_api.logs.repository import RaidLine, StoredIndex, StoredRaid


def _line(row: LogRaid) -> RaidLine:
    return RaidLine(row.report_id, row.raid_date, row.weekday, dict(row.summary), row.page_version)


class SqlLogRepository:
    def __init__(self, db: sessionmaker[Session]) -> None:
        self._db = db

    def index(self) -> StoredIndex | None:
        with self._db() as db:
            row = db.get(LogIndex, INDEX_ROW)
            return None if row is None else StoredIndex(row.generated_at, list(row.bosses))

    def raids(self) -> list[RaidLine]:
        with self._db() as db:
            # Only the list's columns: the analysis stays in the database.
            rows = db.execute(
                select(
                    LogRaid.report_id, LogRaid.raid_date, LogRaid.weekday, LogRaid.summary, LogRaid.page_version
                ).order_by(LogRaid.raid_date.desc())
            )
            return [RaidLine(r.report_id, r.raid_date, r.weekday, dict(r.summary), r.page_version) for r in rows]

    def raid(self, report_id: str) -> StoredRaid | None:
        with self._db() as db:
            row = db.get(LogRaid, report_id)
            return None if row is None else StoredRaid(_line(row), None if row.page is None else dict(row.page))

    def replace_index(self, generated_at: str, bosses: list[dict[str, Any]], raids: list[RaidLine]) -> None:
        with self._db.begin() as db:
            index = db.get(LogIndex, INDEX_ROW)
            if index is None:
                db.add(LogIndex(id=INDEX_ROW, generated_at=generated_at, bosses=bosses))
            else:
                index.generated_at, index.bosses = generated_at, bosses
            keep = [r.report_id for r in raids]
            db.execute(delete(LogRaid).where(LogRaid.report_id.not_in(keep)))
            held = {row.report_id: row for row in db.scalars(select(LogRaid).where(LogRaid.report_id.in_(keep)))}
            for r in raids:
                row = held.get(r.report_id)
                if row is None:
                    db.add(LogRaid(report_id=r.report_id, raid_date=r.raid_date, weekday=r.weekday, summary=r.summary))
                else:
                    row.raid_date, row.weekday, row.summary = r.raid_date, r.weekday, r.summary

    def save_page(self, report_id: str, version: int, page: dict[str, Any]) -> bool:
        with self._db.begin() as db:
            row = db.get(LogRaid, report_id)
            if row is None:
                return False
            row.page, row.page_version = page, version
            return True
