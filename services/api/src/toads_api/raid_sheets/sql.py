"""SheetRepository over the hub database (hub_db.RaidSheetSnapshot)."""

from __future__ import annotations

from datetime import date

from hub_db import RaidSheetSnapshot
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from toads_api.raid_sheets.schemas import SheetKind, SheetSnapshot, SheetTable


def _to_schema(row: RaidSheetSnapshot) -> SheetSnapshot:
    return SheetSnapshot(
        id=row.id,
        kind=SheetKind(row.kind),
        spreadsheet_id=row.spreadsheet_id,
        tab=row.tab,
        raid_date=row.raid_date,
        raid_day=row.raid_day_id,
        content_digest=row.content_digest,
        fetched_at=row.fetched_at,
        table=SheetTable(tab=row.tab, headers=row.headers, rows=row.rows),
    )


class SqlSheetRepository:
    def __init__(self, db: sessionmaker[Session]) -> None:
        self.db = db

    def next_id(self) -> int:
        with self.db() as s:
            return int(s.scalar(select(func.coalesce(func.max(RaidSheetSnapshot.id), 0))) or 0) + 1

    def save(self, snapshot: SheetSnapshot) -> None:
        with self.db.begin() as s:
            s.merge(
                RaidSheetSnapshot(
                    id=snapshot.id,
                    kind=snapshot.kind.value,
                    spreadsheet_id=snapshot.spreadsheet_id,
                    tab=snapshot.tab,
                    raid_date=snapshot.raid_date,
                    raid_day_id=snapshot.raid_day,
                    content_digest=snapshot.content_digest,
                    fetched_at=snapshot.fetched_at,
                    headers=snapshot.table.headers,
                    rows=snapshot.table.rows,
                )
            )

    def get(self, snapshot_id: int) -> SheetSnapshot | None:
        with self.db() as s:
            row = s.get(RaidSheetSnapshot, snapshot_id)
            return _to_schema(row) if row is not None else None

    def latest(self, spreadsheet_id: str, tab: str) -> SheetSnapshot | None:
        q = (
            select(RaidSheetSnapshot)
            .where(RaidSheetSnapshot.spreadsheet_id == spreadsheet_id, RaidSheetSnapshot.tab == tab)
            .order_by(RaidSheetSnapshot.fetched_at.desc(), RaidSheetSnapshot.id.desc())
            .limit(1)
        )
        with self.db() as s:
            row = s.scalars(q).first()
            return _to_schema(row) if row is not None else None

    def for_raid(self, raid_day: str, raid_date: date) -> list[SheetSnapshot]:
        q = select(RaidSheetSnapshot).where(
            RaidSheetSnapshot.raid_day_id == raid_day, RaidSheetSnapshot.raid_date == raid_date
        )
        with self.db() as s:
            return [_to_schema(r) for r in s.scalars(q)]

    def raid_dates(self, raid_day: str | None, limit: int) -> list[tuple[str, date]]:
        q = (
            select(RaidSheetSnapshot.raid_day_id, RaidSheetSnapshot.raid_date)
            .where(RaidSheetSnapshot.raid_day_id.is_not(None), RaidSheetSnapshot.raid_date.is_not(None))
            .distinct()
            .order_by(RaidSheetSnapshot.raid_date.desc(), RaidSheetSnapshot.raid_day_id.desc())
            .limit(limit)
        )
        if raid_day is not None:
            q = q.where(RaidSheetSnapshot.raid_day_id == raid_day)
        with self.db() as s:
            return [(day, when) for day, when in s.execute(q) if day is not None and when is not None]
