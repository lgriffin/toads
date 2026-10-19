"""LogRepository over hub-db."""

from __future__ import annotations

from typing import Any

from hub_db import LogIndex, LogRaid
from hub_db.logs import INDEX_ROW
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, defer, sessionmaker

from toads_api.logs.repository import RaidLine, Saved, StoredIndex, StoredRaid


def _line(row: LogRaid) -> RaidLine:
    return RaidLine(
        row.report_id, row.raid_date, row.weekday, dict(row.summary), row.page_version, row.want_hash, row.page_hash
    )


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
                    LogRaid.report_id,
                    LogRaid.raid_date,
                    LogRaid.weekday,
                    LogRaid.summary,
                    LogRaid.page_version,
                    LogRaid.want_hash,
                    LogRaid.page_hash,
                ).order_by(LogRaid.raid_date.desc())
            )
            return [
                RaidLine(r.report_id, r.raid_date, r.weekday, dict(r.summary), r.page_version, r.want_hash, r.page_hash)
                for r in rows
            ]

    def raid(self, report_id: str) -> StoredRaid | None:
        with self._db() as db:
            row = db.get(LogRaid, report_id)
            return None if row is None else StoredRaid(_line(row), None if row.page is None else dict(row.page))

    def replace_index(self, generated_at: str, bosses: list[dict[str, Any]], raids: list[RaidLine]) -> bool:
        with self._db.begin() as db:
            # The index row's lock makes the newer-list check and the replacement one step for overlapping workers.
            index = db.scalars(select(LogIndex).where(LogIndex.id == INDEX_ROW).with_for_update()).first()
            if index is None:
                db.add(LogIndex(id=INDEX_ROW, generated_at=generated_at, bosses=bosses))
            elif generated_at < index.generated_at:
                return False
            else:
                index.generated_at, index.bosses = generated_at, bosses
            keep = [r.report_id for r in raids]
            db.execute(delete(LogRaid).where(LogRaid.report_id.not_in(keep)))
            # The list's columns only: the analyses stay in the database.
            held = {
                row.report_id: row
                for row in db.scalars(select(LogRaid).options(defer(LogRaid.page)).where(LogRaid.report_id.in_(keep)))
            }
            for r in raids:
                row = held.get(r.report_id)
                if row is None:
                    db.add(
                        LogRaid(
                            report_id=r.report_id,
                            raid_date=r.raid_date,
                            weekday=r.weekday,
                            summary=r.summary,
                            want_hash=r.want_hash,
                        )
                    )
                    continue
                row.raid_date, row.weekday, row.summary = r.raid_date, r.weekday, r.summary
                if r.want_hash is not None:
                    row.want_hash = r.want_hash
            return True

    def save_page(self, report_id: str, version: int, page: dict[str, Any], page_hash: str) -> Saved:
        with self._db.begin() as db:
            row = db.get(LogRaid, report_id, with_for_update=True)
            if row is None:
                return "unlisted"
            if row.want_hash is not None and row.want_hash != page_hash:
                return "superseded"
            row.page, row.page_version, row.page_hash = page, version, page_hash
            return "saved"
