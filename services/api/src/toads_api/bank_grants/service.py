"""Rules for bank grants and officer tokens. No RBAC, web framework or storage imports: the routes decide who may call
(super admins grant and mint; the global tier lists grants; any member redeems), the RBAC layer decides what a grant
opens, and the repository decides where grants and tokens live."""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from toads_api.bank_grants.repository import (
    BankGrantRecord,
    BankGrantRepository,
    NewGrant,
    NewToken,
    Redeemer,
    TokenRecord,
)

# The hub permissions a grant may carry, by value (toads_api.rbac.permissions.GRANTABLE; the matrix test keeps the
# two equal): importing bank snapshots, and running the request queue.
GRANTABLE = ("import_bank_snapshot", "manage_bank")
NAME_LIMIT = 100
NOTE_LIMIT = 100
# Officer tokens: how long one lasts and how often it may be redeemed, by default and at most.
DEFAULT_DAYS = 7
MAX_DAYS = 30
MAX_USES = 25
# Minted tokens start with this, so one pasted in the wrong place is recognisable.
MINTED_PREFIX = "toads-bank-"
# Every refused redemption says the same, so a guess learns nothing about which tokens exist.
REFUSED = "That token is not valid. Ask a super admin for a new one."


class GrantError(Exception):
    """A request the rules refuse. `status` is the HTTP code the adapter should answer with."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


@dataclass(frozen=True)
class Minted:
    """A new officer token: `token` is shown once, here, and never stored."""

    token: str
    record: TokenRecord


def hash_token(token: str) -> str:
    return hashlib.sha256(token.strip().encode()).hexdigest()


def _utc_now() -> datetime:
    return datetime.now(UTC)


class BankGrantService:
    def __init__(
        self, repo: BankGrantRepository, day_ids: Iterable[str], clock: Callable[[], datetime] = _utc_now
    ) -> None:
        self._repo = repo
        self._days = frozenset(day_ids)
        self._clock = clock

    # ------------------------------------------------------------------ grants

    def all_grants(self) -> list[BankGrantRecord]:
        return self._repo.all()

    def held_by(self, discord_user_id: int) -> frozenset[tuple[str, str | None]]:
        """What a member holds right now. A grant for a raid day the config no longer has opens nothing."""
        return frozenset(
            (permission, day)
            for permission, day in self._repo.held_by(discord_user_id)
            if permission in GRANTABLE and (day is None or day in self._days)
        )

    def _check(self, permissions: Iterable[str], raid_day: str | None) -> None:
        if any(p not in GRANTABLE for p in permissions):
            raise GrantError(f"Only {', '.join(GRANTABLE)} can be granted", 422)
        if raid_day is not None and raid_day not in self._days:
            raise GrantError("Unknown raid day", 422)

    def grant(
        self, discord_user_id: int, display_name: str, permission: str, raid_day: str | None, granted_by: int
    ) -> tuple[BankGrantRecord, bool]:
        """Grant one bank permission on one raid day's banks (None: every bank). Granting what is already held
        returns the existing grant; True when the grant is new."""
        self._check([permission], raid_day)
        if discord_user_id <= 0:
            raise GrantError("That is not a Discord user id", 422)
        name = display_name.strip()[:NAME_LIMIT] or str(discord_user_id)
        return self._repo.add(NewGrant(discord_user_id, name, permission, raid_day, granted_by))

    def revoke(self, grant_id: int, revoked_by: int) -> BankGrantRecord:
        removed = self._repo.remove(grant_id, revoked_by)
        if removed is None:
            raise GrantError("No such grant", 404)
        return removed

    # ------------------------------------------------------------------ tokens

    def mint(
        self,
        permissions: Iterable[str],
        raid_day: str | None,
        minted_by: int,
        *,
        days: int = DEFAULT_DAYS,
        max_uses: int = 1,
        note: str = "",
    ) -> Minted:
        """A token naming bank permissions (and a raid day, or every bank) that whoever redeems it receives. It lasts
        `days` and may be redeemed `max_uses` times (once by default)."""
        wanted = tuple(sorted(set(permissions)))
        if not wanted:
            raise GrantError("Name at least one permission", 422)
        self._check(wanted, raid_day)
        if not 1 <= days <= MAX_DAYS:
            raise GrantError(f"A token lasts 1 to {MAX_DAYS} days", 422)
        if not 1 <= max_uses <= MAX_USES:
            raise GrantError(f"A token may be redeemed 1 to {MAX_USES} times", 422)
        token = MINTED_PREFIX + secrets.token_urlsafe(32)
        now = self._clock()
        record = self._repo.add_token(
            NewToken(
                token_hash=hash_token(token),
                permissions=wanted,
                raid_day=raid_day,
                note=note.strip()[:NOTE_LIMIT],
                minted_by=minted_by,
                minted_at=now,
                expires_at=now + timedelta(days=days),
                max_uses=max_uses,
            )
        )
        return Minted(token, record)

    def tokens(self) -> list[TokenRecord]:
        return self._repo.tokens()

    def now(self) -> datetime:
        return self._clock()

    def revoke_token(self, token_id: int, revoked_by: int) -> TokenRecord:
        """Only a token that could still be redeemed can be revoked; grants already given from it stay."""
        record = self._repo.token(token_id)
        if record is None:
            raise GrantError("No such token", 404)
        now = self._clock()
        if not record.usable(now):
            raise GrantError(f"That token is already {record.status(now)}", 409)
        self._repo.revoke_token(token_id, now, revoked_by)
        return record

    def redeem(self, token: str, redeemer: Redeemer) -> tuple[TokenRecord, list[BankGrantRecord]]:
        """Give the redeemer the grants a token names. A missing, wrong, expired, used-up or revoked token all get the
        same answer."""
        if not 8 <= len(token.strip()) <= 200:
            raise GrantError(REFUSED, 400)
        redeemed = self._repo.redeem(hash_token(token), self._clock(), redeemer)
        if redeemed is None:
            raise GrantError(REFUSED, 400)
        return redeemed
