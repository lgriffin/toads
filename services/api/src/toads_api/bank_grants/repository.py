"""Where bank grants and officer tokens live. BankGrantService only talks to the BankGrantRepository protocol; the
hub-db backed implementation is `sql.SqlBankGrantRepository`."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True)
class NewGrant:
    discord_user_id: int
    display_name: str
    permission: str
    # None: every bank.
    raid_day: str | None
    # The member id of the super admin granting it, or of the one who minted the token it came from.
    granted_by: int | None


@dataclass(frozen=True)
class BankGrantRecord:
    id: int
    discord_user_id: int
    display_name: str
    permission: str
    raid_day: str | None
    granted_by: int | None
    granted_by_name: str | None
    granted_at: datetime


@dataclass(frozen=True)
class NewToken:
    token_hash: str
    permissions: tuple[str, ...]
    raid_day: str | None
    note: str
    minted_by: int
    minted_at: datetime
    expires_at: datetime
    max_uses: int


@dataclass(frozen=True)
class TokenRecord:
    """An officer token, never the token itself: its hash stays in the repository."""

    id: int
    permissions: tuple[str, ...]
    raid_day: str | None
    note: str
    minted_by: int | None
    minted_by_name: str | None
    minted_at: datetime
    expires_at: datetime
    max_uses: int
    uses: int
    used_by: int | None
    used_at: datetime | None
    revoked_at: datetime | None

    def status(self, now: datetime) -> str:
        if self.revoked_at is not None:
            return "revoked"
        if self.uses >= self.max_uses:
            return "used"
        if self.expires_at <= now:
            return "expired"
        return "active"

    def usable(self, now: datetime) -> bool:
        return self.status(now) == "active"


@dataclass(frozen=True)
class Redeemer:
    discord_user_id: int
    display_name: str
    # Their hub member id, for the audit log.
    member_id: int


class BankGrantRepository(Protocol):
    def all(self) -> list[BankGrantRecord]: ...
    def held_by(self, discord_user_id: int) -> list[tuple[str, str | None]]: ...

    def add(self, grant: NewGrant) -> tuple[BankGrantRecord, bool]:
        """Store a grant, or return the one already held for the same user, permission and raid day. True when new."""
        ...

    def remove(self, grant_id: int, revoked_by: int) -> BankGrantRecord | None:
        """Delete a grant; None when there is no such grant."""
        ...

    def add_token(self, token: NewToken) -> TokenRecord: ...
    def tokens(self) -> list[TokenRecord]: ...
    def token(self, token_id: int) -> TokenRecord | None: ...
    def revoke_token(self, token_id: int, at: datetime, revoked_by: int) -> None: ...

    def redeem(
        self, token_hash: str, now: datetime, redeemer: Redeemer
    ) -> tuple[TokenRecord, list[BankGrantRecord]] | None:
        """In one transaction: find the token by its hash and, if it is still usable at `now`, count the use and give
        the redeemer its grants. None when there is no such token or it is not usable."""
        ...


@dataclass
class InMemoryBankGrantRepository:
    """For service tests; never use it outside tests."""

    grants: dict[int, BankGrantRecord] = field(default_factory=dict)
    names: dict[int, str] = field(default_factory=dict)
    revoked: list[tuple[int, int]] = field(default_factory=list)
    minted: dict[int, tuple[str, TokenRecord]] = field(default_factory=dict)

    def all(self) -> list[BankGrantRecord]:
        return [self.grants[i] for i in sorted(self.grants)]

    def held_by(self, discord_user_id: int) -> list[tuple[str, str | None]]:
        return [(g.permission, g.raid_day) for g in self.all() if g.discord_user_id == discord_user_id]

    def add(self, grant: NewGrant) -> tuple[BankGrantRecord, bool]:
        for g in self.grants.values():
            if (g.discord_user_id, g.permission, g.raid_day) == (
                grant.discord_user_id,
                grant.permission,
                grant.raid_day,
            ):
                return g, False
        record = BankGrantRecord(
            id=max(self.grants, default=0) + 1,
            discord_user_id=grant.discord_user_id,
            display_name=grant.display_name,
            permission=grant.permission,
            raid_day=grant.raid_day,
            granted_by=grant.granted_by,
            granted_by_name=None if grant.granted_by is None else self.names.get(grant.granted_by),
            granted_at=datetime.now(UTC),
        )
        self.grants[record.id] = record
        return record, True

    def remove(self, grant_id: int, revoked_by: int) -> BankGrantRecord | None:
        record = self.grants.pop(grant_id, None)
        if record is not None:
            self.revoked.append((grant_id, revoked_by))
        return record

    def add_token(self, token: NewToken) -> TokenRecord:
        record = TokenRecord(
            id=max(self.minted, default=0) + 1,
            permissions=token.permissions,
            raid_day=token.raid_day,
            note=token.note,
            minted_by=token.minted_by,
            minted_by_name=self.names.get(token.minted_by),
            minted_at=token.minted_at,
            expires_at=token.expires_at,
            max_uses=token.max_uses,
            uses=0,
            used_by=None,
            used_at=None,
            revoked_at=None,
        )
        self.minted[record.id] = (token.token_hash, record)
        return record

    def tokens(self) -> list[TokenRecord]:
        return [self.minted[i][1] for i in sorted(self.minted)]

    def token(self, token_id: int) -> TokenRecord | None:
        entry = self.minted.get(token_id)
        return None if entry is None else entry[1]

    def revoke_token(self, token_id: int, at: datetime, revoked_by: int) -> None:
        digest, record = self.minted[token_id]
        self.minted[token_id] = (digest, replace(record, revoked_at=at))

    def redeem(
        self, token_hash: str, now: datetime, redeemer: Redeemer
    ) -> tuple[TokenRecord, list[BankGrantRecord]] | None:
        found = next(((d, r) for d, r in self.minted.values() if d == token_hash), None)
        if found is None or not found[1].usable(now):
            return None
        record = replace(found[1], uses=found[1].uses + 1, used_by=redeemer.discord_user_id, used_at=now)
        self.minted[record.id] = (token_hash, record)
        grants = [
            self.add(NewGrant(redeemer.discord_user_id, redeemer.display_name, p, record.raid_day, record.minted_by))[0]
            for p in record.permissions
        ]
        return record, grants
