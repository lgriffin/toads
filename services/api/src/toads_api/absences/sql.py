"""AbsenceRepository over hub-db. Absences are a member's own word about their own nights, not officer actions, so
they are not written to the audit log."""

from __future__ import annotations

from datetime import date

from hub_db import MemberAbsence
from sqlalchemy import ColumnElement, select
from sqlalchemy.orm import Session, sessionmaker

from toads_api.absences.repository import AbsenceRecord


def _record(row: MemberAbsence) -> AbsenceRecord:
    return AbsenceRecord(
        id=row.id,
        member_id=row.member_id,
        raid_day=row.raid_day,
        first_date=row.first_date,
        last_date=row.last_date,
        note=row.note,
        created_at=row.created_at,
    )


class SqlAbsenceRepository:
    def __init__(self, db: sessionmaker[Session]) -> None:
        self._db = db

    def _upcoming(self, where: ColumnElement[bool], since: date) -> list[AbsenceRecord]:
        query = (
            select(MemberAbsence)
            .where(MemberAbsence.last_date >= since, where)
            .order_by(MemberAbsence.first_date, MemberAbsence.id)
        )
        with self._db() as db:
            return [_record(r) for r in db.scalars(query)]

    def for_member(self, member_id: int, since: date) -> list[AbsenceRecord]:
        return self._upcoming(MemberAbsence.member_id == member_id, since=since)

    def for_day(self, raid_day: str, since: date) -> list[AbsenceRecord]:
        return self._upcoming(MemberAbsence.raid_day == raid_day, since=since)

    def get(self, absence_id: int) -> AbsenceRecord | None:
        with self._db() as db:
            row = db.get(MemberAbsence, absence_id)
            return None if row is None else _record(row)

    def add(self, member_id: int, raid_day: str, first: date, last: date, note: str | None) -> AbsenceRecord:
        with self._db.begin() as db:
            row = MemberAbsence(member_id=member_id, raid_day=raid_day, first_date=first, last_date=last, note=note)
            db.add(row)
            db.flush()
            return _record(row)

    def remove(self, absence_id: int) -> bool:
        with self._db.begin() as db:
            row = db.get(MemberAbsence, absence_id)
            if row is None:
                return False
            db.delete(row)
            return True
