"""OfficerGrantRepository over hub-db. Granting and revoking are super admin actions, so each is written to the audit
log in the same transaction."""

from __future__ import annotations

from datetime import UTC, datetime

from hub_db import EVERY_DAY, Member, OfficerGrant
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from toads_api import audit
from toads_api.officer_grants.repository import NewOfficerGrant, OfficerGrantRecord


def _day_in(day: str | None) -> str:
    return EVERY_DAY if day is None else day


def _day_out(day: str) -> str | None:
    return None if day == EVERY_DAY else day


def _aware(at: datetime) -> datetime:
    """SQLite hands back naive datetimes; every time stored here is UTC."""
    return at if at.tzinfo is not None else at.replace(tzinfo=UTC)


def _target(row: OfficerGrant) -> str:
    scope = "global officer" if row.raid_day == EVERY_DAY else "officer"
    return f"officer grant {row.id}: {scope} for discord user {row.discord_user_id}"


def _record(row: OfficerGrant, granted_by_name: str | None) -> OfficerGrantRecord:
    return OfficerGrantRecord(
        id=row.id,
        discord_user_id=row.discord_user_id,
        username=row.username,
        display_name=row.display_name,
        raid_day=_day_out(row.raid_day),
        granted_by=row.granted_by,
        granted_by_name=granted_by_name,
        granted_at=_aware(row.granted_at),
    )


def _name(db: Session, member_id: int | None) -> str | None:
    member = db.get(Member, member_id) if member_id is not None else None
    return member.display_name if member else None


class SqlOfficerGrantRepository:
    def __init__(self, db: sessionmaker[Session]) -> None:
        self._db = db

    def all(self) -> list[OfficerGrantRecord]:
        with self._db() as db:
            rows = db.execute(
                select(OfficerGrant, Member.display_name)
                .outerjoin(Member, Member.id == OfficerGrant.granted_by)
                .order_by(OfficerGrant.id)
            ).all()
            return [_record(row, name) for row, name in rows]

    def held_by(self, discord_user_id: int) -> list[str | None]:
        with self._db() as db:
            days = db.scalars(select(OfficerGrant.raid_day).where(OfficerGrant.discord_user_id == discord_user_id))
            return [_day_out(d) for d in days]

    def _add(self, grant: NewOfficerGrant) -> tuple[OfficerGrantRecord, bool]:
        with self._db.begin() as db:
            existing = db.scalar(
                select(OfficerGrant).where(
                    OfficerGrant.discord_user_id == grant.discord_user_id,
                    OfficerGrant.raid_day == _day_in(grant.raid_day),
                )
            )
            if existing is not None:
                return _record(existing, _name(db, existing.granted_by)), False
            row = OfficerGrant(
                discord_user_id=grant.discord_user_id,
                username=grant.username,
                display_name=grant.display_name,
                raid_day=_day_in(grant.raid_day),
                granted_by=grant.granted_by,
            )
            db.add(row)
            db.flush()
            audit.record(
                db, actor=grant.granted_by, action="officer.grant", target=_target(row), raid_day=grant.raid_day
            )
            return _record(row, _name(db, row.granted_by)), True

    def add(self, grant: NewOfficerGrant) -> tuple[OfficerGrantRecord, bool]:
        try:
            return self._add(grant)
        except IntegrityError:
            # The same grant was made concurrently; the second try finds it.
            return self._add(grant)

    def remove(self, grant_id: int, revoked_by: int) -> OfficerGrantRecord | None:
        with self._db.begin() as db:
            row = db.get(OfficerGrant, grant_id)
            if row is None:
                return None
            record = _record(row, _name(db, row.granted_by))
            audit.record(db, actor=revoked_by, action="officer.revoke", target=_target(row), raid_day=record.raid_day)
            db.delete(row)
            return record
