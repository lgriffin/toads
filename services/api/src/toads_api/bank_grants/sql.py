"""BankGrantRepository over hub-db. Granting, revoking, minting, revoking a token and redeeming one are written to the
audit log in the same transaction. Officer tokens are stored as SHA-256 hashes only."""

from __future__ import annotations

import hmac
from datetime import UTC, datetime

from hub_db import EVERY_DAY, BankGrant, BankGrantToken, Member
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from toads_api import audit
from toads_api.bank_grants.repository import BankGrantRecord, NewGrant, NewToken, Redeemer, TokenRecord


def _day_in(day: str | None) -> str:
    return EVERY_DAY if day is None else day


def _day_out(day: str) -> str | None:
    return None if day == EVERY_DAY else day


def _aware(at: datetime) -> datetime:
    """SQLite hands back naive datetimes; every time stored here is UTC."""
    return at if at.tzinfo is not None else at.replace(tzinfo=UTC)


def _target(row: BankGrant) -> str:
    return f"bank grant {row.id}: {row.permission} for discord user {row.discord_user_id}"


def _name(db: Session, member_id: int | None) -> str | None:
    member = db.get(Member, member_id) if member_id is not None else None
    return member.display_name if member else None


def _grant(row: BankGrant, granted_by_name: str | None) -> BankGrantRecord:
    return BankGrantRecord(
        id=row.id,
        discord_user_id=row.discord_user_id,
        display_name=row.display_name,
        permission=row.permission,
        raid_day=_day_out(row.raid_day),
        granted_by=row.granted_by,
        granted_by_name=granted_by_name,
        granted_at=_aware(row.granted_at),
    )


def _token(row: BankGrantToken, minted_by_name: str | None) -> TokenRecord:
    return TokenRecord(
        id=row.id,
        permissions=tuple(row.permissions),
        raid_day=_day_out(row.raid_day),
        note=row.note,
        minted_by=row.minted_by,
        minted_by_name=minted_by_name,
        minted_at=_aware(row.minted_at),
        expires_at=_aware(row.expires_at),
        max_uses=row.max_uses,
        uses=row.uses,
        used_by=row.used_by,
        used_at=None if row.used_at is None else _aware(row.used_at),
        revoked_at=None if row.revoked_at is None else _aware(row.revoked_at),
    )


def _existing(db: Session, grant: NewGrant) -> BankGrant | None:
    return db.scalar(
        select(BankGrant).where(
            BankGrant.discord_user_id == grant.discord_user_id,
            BankGrant.permission == grant.permission,
            BankGrant.raid_day == _day_in(grant.raid_day),
        )
    )


class SqlBankGrantRepository:
    def __init__(self, db: sessionmaker[Session]) -> None:
        self._db = db

    # ------------------------------------------------------------------ grants

    def all(self) -> list[BankGrantRecord]:
        with self._db() as db:
            rows = db.execute(
                select(BankGrant, Member.display_name)
                .outerjoin(Member, Member.id == BankGrant.granted_by)
                .order_by(BankGrant.id)
            ).all()
            return [_grant(row, name) for row, name in rows]

    def held_by(self, discord_user_id: int) -> list[tuple[str, str | None]]:
        with self._db() as db:
            rows = db.execute(
                select(BankGrant.permission, BankGrant.raid_day).where(BankGrant.discord_user_id == discord_user_id)
            ).all()
            return [(permission, _day_out(day)) for permission, day in rows]

    @staticmethod
    def _add(db: Session, grant: NewGrant, *, audited: bool) -> tuple[BankGrant, bool]:
        """Inside the caller's transaction. A concurrent insert of the same grant fails the unique constraint at
        flush and rolls the whole transaction back; the callers then try once more and find the row."""
        existing = _existing(db, grant)
        if existing is not None:
            return existing, False
        row = BankGrant(
            discord_user_id=grant.discord_user_id,
            display_name=grant.display_name,
            permission=grant.permission,
            raid_day=_day_in(grant.raid_day),
            granted_by=grant.granted_by,
        )
        db.add(row)
        db.flush()
        if audited and grant.granted_by is not None:
            audit.record(db, actor=grant.granted_by, action="bank.grant", target=_target(row), raid_day=grant.raid_day)
        return row, True

    def add(self, grant: NewGrant) -> tuple[BankGrantRecord, bool]:
        for attempt in range(2):
            try:
                with self._db.begin() as db:
                    row, created = self._add(db, grant, audited=True)
                    return _grant(row, _name(db, row.granted_by)), created
            except IntegrityError:
                if attempt:
                    raise
        raise AssertionError("unreachable")

    def remove(self, grant_id: int, revoked_by: int) -> BankGrantRecord | None:
        with self._db.begin() as db:
            row = db.get(BankGrant, grant_id)
            if row is None:
                return None
            record = _grant(row, _name(db, row.granted_by))
            audit.record(db, actor=revoked_by, action="bank.revoke", target=_target(row), raid_day=record.raid_day)
            db.delete(row)
            return record

    # ------------------------------------------------------------------ tokens

    def add_token(self, token: NewToken) -> TokenRecord:
        with self._db.begin() as db:
            row = BankGrantToken(
                token_hash=token.token_hash,
                permissions=list(token.permissions),
                raid_day=_day_in(token.raid_day),
                note=token.note,
                minted_by=token.minted_by,
                minted_at=token.minted_at,
                expires_at=token.expires_at,
                max_uses=token.max_uses,
                uses=0,
            )
            db.add(row)
            db.flush()
            audit.record(
                db,
                actor=token.minted_by,
                action="bank.token_minted",
                target=f"bank token {row.id}",
                raid_day=token.raid_day,
                detail=",".join(token.permissions),
            )
            return _token(row, _name(db, row.minted_by))

    def tokens(self) -> list[TokenRecord]:
        with self._db() as db:
            rows = db.execute(
                select(BankGrantToken, Member.display_name)
                .outerjoin(Member, Member.id == BankGrantToken.minted_by)
                .order_by(BankGrantToken.id.desc())
            ).all()
            return [_token(row, name) for row, name in rows]

    def token(self, token_id: int) -> TokenRecord | None:
        with self._db() as db:
            row = db.get(BankGrantToken, token_id)
            return None if row is None else _token(row, _name(db, row.minted_by))

    def revoke_token(self, token_id: int, at: datetime, revoked_by: int) -> None:
        with self._db.begin() as db:
            row = db.get(BankGrantToken, token_id, with_for_update=True)
            if row is None or row.revoked_at is not None:
                return
            row.revoked_at = at
            audit.record(
                db,
                actor=revoked_by,
                action="bank.token_revoked",
                target=f"bank token {row.id}",
                raid_day=_day_out(row.raid_day),
            )

    def redeem(
        self, token_hash: str, now: datetime, redeemer: Redeemer
    ) -> tuple[TokenRecord, list[BankGrantRecord]] | None:
        for attempt in range(2):
            try:
                return self._redeem(token_hash, now, redeemer)
            except IntegrityError:
                # The redeemer was granted the same thing concurrently; nothing was spent, so try once more.
                if attempt:
                    raise
        raise AssertionError("unreachable")

    def _redeem(
        self, token_hash: str, now: datetime, redeemer: Redeemer
    ) -> tuple[TokenRecord, list[BankGrantRecord]] | None:
        with self._db.begin() as db:
            row = db.scalar(select(BankGrantToken).where(BankGrantToken.token_hash == token_hash).with_for_update())
            if row is None or not hmac.compare_digest(row.token_hash, token_hash):
                return None
            if not _token(row, None).usable(now):
                return None
            row.uses += 1
            row.used_by = redeemer.discord_user_id
            row.used_at = now
            day = _day_out(row.raid_day)
            grants: list[BankGrantRecord] = []
            for permission in row.permissions:
                grant = NewGrant(redeemer.discord_user_id, redeemer.display_name, permission, day, row.minted_by)
                granted, _ = self._add(db, grant, audited=False)
                grants.append(_grant(granted, _name(db, granted.granted_by)))
            audit.record(
                db,
                actor=redeemer.member_id,
                action="bank.token_redeemed",
                target=f"bank token {row.id}",
                raid_day=day,
                detail=", ".join(f"bank grant {g.id}: {g.permission}" for g in grants),
            )
            return _token(row, _name(db, row.minted_by)), grants
