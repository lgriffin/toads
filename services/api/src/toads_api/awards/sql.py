"""AwardRepository over hub-db. Giving and taking back an award are officer actions, so each is written to the audit
log in the same transaction."""

from __future__ import annotations

from collections.abc import Iterable

from hub_db import Member, MemberAward
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from toads_api import audit
from toads_api.awards.repository import AwardRecord, DuplicateAwardError


def _record(row: MemberAward) -> AwardRecord:
    return AwardRecord(
        id=row.id,
        member_id=row.member_id,
        award_id=row.award_id,
        period=row.period,
        note=row.note,
        awarded_by=row.awarded_by,
        awarded_at=row.awarded_at,
    )


def _target(row: MemberAward) -> str:
    return f"member:{row.member_id} award:{row.award_id}" + (f" {row.period}" if row.period else "")


class SqlAwardRepository:
    def __init__(self, db: sessionmaker[Session]) -> None:
        self._db = db

    def member_exists(self, member_id: int) -> bool:
        with self._db() as db:
            return db.get(Member, member_id) is not None

    def awards(self, member_ids: Iterable[int] | None = None) -> list[AwardRecord]:
        query = select(MemberAward).order_by(MemberAward.id)
        if member_ids is not None:
            query = query.where(MemberAward.member_id.in_(list(member_ids)))
        with self._db() as db:
            return [_record(r) for r in db.scalars(query)]

    def add(self, member_id: int, award_id: str, period: str, note: str | None, by: int) -> AwardRecord:
        try:
            with self._db.begin() as db:
                row = MemberAward(member_id=member_id, award_id=award_id, period=period, note=note, awarded_by=by)
                db.add(row)
                db.flush()
                audit.record(db, actor=by, action="award.give", target=_target(row), raid_day=None, detail=note)
                return _record(row)
        except IntegrityError:
            raise DuplicateAwardError from None

    def remove(self, award_row_id: int, by: int) -> bool:
        with self._db.begin() as db:
            row = db.get(MemberAward, award_row_id)
            if row is None:
                return False
            audit.record(db, actor=by, action="award.take_back", target=_target(row), raid_day=None)
            db.delete(row)
            return True
