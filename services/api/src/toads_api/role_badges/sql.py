"""RoleBadgeRepository over hub-db. Tying a badge to a role and untying it are super admin actions, so each is
written to the audit log in the same transaction."""

from __future__ import annotations

from hub_db import DiscordRoleBadge
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from toads_api import audit
from toads_api.role_badges.repository import DuplicateLinkError, RoleBadgeLink


def _link(row: DiscordRoleBadge) -> RoleBadgeLink:
    return RoleBadgeLink(
        discord_role_id=row.discord_role_id,
        badge_id=row.badge_id,
        role_name=row.role_name,
        added_by=row.added_by,
        added_at=row.added_at,
    )


def _target(discord_role_id: int, badge_id: str) -> str:
    return f"discord_role:{discord_role_id} badge:{badge_id}"


class SqlRoleBadgeRepository:
    def __init__(self, db: sessionmaker[Session]) -> None:
        self._db = db

    def links(self) -> list[RoleBadgeLink]:
        with self._db() as db:
            return [_link(r) for r in db.scalars(select(DiscordRoleBadge).order_by(DiscordRoleBadge.id))]

    def add(self, discord_role_id: int, badge_id: str, role_name: str, by: int) -> RoleBadgeLink:
        try:
            with self._db.begin() as db:
                row = DiscordRoleBadge(
                    discord_role_id=discord_role_id, badge_id=badge_id, role_name=role_name, added_by=by
                )
                db.add(row)
                db.flush()
                audit.record(
                    db, actor=by, action="role_badge.add", target=_target(discord_role_id, badge_id), raid_day=None
                )
                return _link(row)
        except IntegrityError:
            raise DuplicateLinkError from None

    def remove(self, discord_role_id: int, badge_id: str, by: int) -> bool:
        query = select(DiscordRoleBadge).where(
            DiscordRoleBadge.discord_role_id == discord_role_id, DiscordRoleBadge.badge_id == badge_id
        )
        with self._db.begin() as db:
            row = db.scalars(query).first()
            if row is None:
                return False
            audit.record(
                db, actor=by, action="role_badge.remove", target=_target(discord_role_id, badge_id), raid_day=None
            )
            db.delete(row)
            return True
