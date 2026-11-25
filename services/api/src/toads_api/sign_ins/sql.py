"""SignInRepository over hub-db. Reading the audit is not itself audited: it changes nothing."""

from __future__ import annotations

from datetime import UTC, datetime

from hub_db import Member, SignIn
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from toads_api.sign_ins.repository import MemberRecord, SignInRecord


def _aware(at: datetime) -> datetime:
    # SQLite hands back naive datetimes; every stored time is UTC.
    return at if at.tzinfo is not None else at.replace(tzinfo=UTC)


class SqlSignInRepository:
    def __init__(self, db: sessionmaker[Session]) -> None:
        self._db = db

    def between(self, start: datetime, end: datetime) -> list[SignInRecord]:
        # Compare in UTC, as every sign-in is stored: SQLite keeps no offset, so a local bound would be read as UTC.
        start, end = start.astimezone(UTC), end.astimezone(UTC)
        query = select(SignIn).where(SignIn.at >= start, SignIn.at < end).order_by(SignIn.at, SignIn.id)
        with self._db() as db:
            return [SignInRecord(r.member_id, _aware(r.at), tuple(r.raid_days or ())) for r in db.scalars(query)]

    def members(self) -> list[MemberRecord]:
        query = select(Member.id, Member.raid_days, Member.signed_in_at)
        with self._db() as db:
            return [
                MemberRecord(member_id, tuple(days or ()), None if at is None else _aware(at))
                for member_id, days, at in db.execute(query)
            ]
