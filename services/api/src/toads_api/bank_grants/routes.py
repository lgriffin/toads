"""Bank grants and officer tokens (docs/bank.md "Grants", docs/admin.md).

- GET    /api/admin/bank/grants              every grant (the global tier)
- POST   /api/admin/bank/grants              grant one Discord user one bank permission (super admins)
- DELETE /api/admin/bank/grants/{grant_id}   revoke it; it stops working on the member's next call (super admins)
- GET    /api/admin/bank/tokens              every officer token, never the token itself (super admins)
- POST   /api/admin/bank/tokens              mint one; the answer is the only time the token is shown (super admins)
- DELETE /api/admin/bank/tokens/{token_id}   revoke one that could still be redeemed (super admins)
- POST   /api/bank/redeem                    redeem a token for the grants it names (any member; the bank bot may
                                             call it for the member who used /bank redeem)
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

import anyio
import structlog
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Path, Response, status
from pydantic import BaseModel, Field

from toads_api.bank_grants.repository import BankGrantRecord, Redeemer, TokenRecord
from toads_api.bank_grants.service import DEFAULT_DAYS, MAX_DAYS, MAX_USES, BankGrantService, GrantError
from toads_api.discord_api import DiscordError
from toads_api.rbac.deps import get_services, require
from toads_api.rbac.permissions import Permission, Principal
from toads_api.services import Services

log = structlog.get_logger(__name__)
grants_router = APIRouter(prefix="/api/admin/bank/grants", tags=["bank", "super admins"])
tokens_router = APIRouter(prefix="/api/admin/bank/tokens", tags=["bank", "super admins"])
redeem_router = APIRouter(prefix="/api/bank", tags=["bank"])

GrantablePermission = Literal["import_bank_snapshot", "manage_bank"]
Live = Annotated[Services, Depends(get_services)]
GlobalTier = Annotated[Principal, Depends(require(Permission.MANAGE_BANK))]
SuperAdmin = Annotated[Principal, Depends(require(Permission.MANAGE_GRANTS))]
Member = Annotated[Principal, Depends(require(Permission.VIEW_BANK))]

# Refused redemptions per member before they must wait (a token is 256 random bits; this keeps guessing noisy).
REDEEM_ATTEMPTS = 5
REDEEM_WINDOW_SECONDS = 15 * 60


def grants_of(live: Live) -> BankGrantService:
    return live.bank_grants


Grants = Annotated[BankGrantService, Depends(grants_of)]


class GrantIn(BaseModel):
    # A string: Discord ids do not fit in a JavaScript number.
    discord_user_id: str = Field(pattern=r"^[1-9]\d{0,19}$")
    permission: GrantablePermission
    # None: every bank.
    raid_day: str | None = Field(default=None, pattern=r"^[a-z0-9_-]{1,32}$")


class GrantOut(BaseModel):
    id: int
    discord_user_id: str
    display_name: str
    permission: str
    raid_day: str | None
    granted_by: int | None
    granted_by_name: str | None
    granted_at: datetime


class TokenIn(BaseModel):
    permissions: list[GrantablePermission] = Field(min_length=1, max_length=2)
    raid_day: str | None = Field(default=None, pattern=r"^[a-z0-9_-]{1,32}$")
    days: int = Field(default=DEFAULT_DAYS, ge=1, le=MAX_DAYS)
    max_uses: int = Field(default=1, ge=1, le=MAX_USES)
    note: str = Field(default="", max_length=100)


class TokenOut(BaseModel):
    id: int
    permissions: list[str]
    raid_day: str | None
    note: str
    minted_by: int | None
    minted_by_name: str | None
    minted_at: datetime
    expires_at: datetime
    max_uses: int
    uses: int
    used_by: str | None
    used_at: datetime | None
    revoked_at: datetime | None
    # active, used, expired or revoked
    status: str


class MintedOut(TokenOut):
    # Shown once, here; only its hash is kept.
    token: str


class RedeemIn(BaseModel):
    token: str = Field(min_length=1, max_length=200)


class RedeemedOut(BaseModel):
    token_id: int
    grants: list[GrantOut]


def _grant(g: BankGrantRecord) -> GrantOut:
    return GrantOut(
        id=g.id,
        discord_user_id=str(g.discord_user_id),
        display_name=g.display_name,
        permission=g.permission,
        raid_day=g.raid_day,
        granted_by=g.granted_by,
        granted_by_name=g.granted_by_name,
        granted_at=g.granted_at,
    )


def _token(t: TokenRecord, now: datetime) -> TokenOut:
    return TokenOut(
        id=t.id,
        permissions=list(t.permissions),
        raid_day=t.raid_day,
        note=t.note,
        minted_by=t.minted_by,
        minted_by_name=t.minted_by_name,
        minted_at=t.minted_at,
        expires_at=t.expires_at,
        max_uses=t.max_uses,
        uses=t.uses,
        used_by=None if t.used_by is None else str(t.used_by),
        used_at=t.used_at,
        revoked_at=t.revoked_at,
        status=t.status(now),
    )


def _refused(exc: GrantError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.message)


# ------------------------------------------------------------------ grants


@grants_router.get("")
async def list_grants(_: GlobalTier, grants: Grants) -> list[GrantOut]:
    return [_grant(g) for g in await anyio.to_thread.run_sync(grants.all_grants)]


@grants_router.post("", status_code=status.HTTP_201_CREATED)
async def grant(body: GrantIn, response: Response, principal: SuperAdmin, grants: Grants, live: Live) -> GrantOut:
    """Only someone in the Toads server can be granted anything; their server name is kept for the list."""
    user_id = int(body.discord_user_id)
    try:
        member = await live.discord.guild_member(user_id)
    except DiscordError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Discord is unavailable") from None
    if member is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="That Discord user is not in the Toads server")
    try:
        record, created = await anyio.to_thread.run_sync(
            grants.grant, user_id, member.server_name, body.permission, body.raid_day, principal.member_id
        )
    except GrantError as exc:
        raise _refused(exc) from None
    if not created:
        response.status_code = status.HTTP_200_OK
    log.info("bank.grant", grant_id=record.id, permission=record.permission, raid_day=record.raid_day, new=created)
    return _grant(record)


@grants_router.delete("/{grant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke(grant_id: Annotated[int, Path(ge=1)], principal: SuperAdmin, grants: Grants) -> Response:
    try:
        record = await anyio.to_thread.run_sync(grants.revoke, grant_id, principal.member_id)
    except GrantError as exc:
        raise _refused(exc) from None
    log.info("bank.revoke", grant_id=record.id, permission=record.permission, raid_day=record.raid_day)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ------------------------------------------------------------------ tokens


@tokens_router.get("")
async def list_tokens(_: SuperAdmin, grants: Grants) -> list[TokenOut]:
    now = grants.now()
    return [_token(t, now) for t in await anyio.to_thread.run_sync(grants.tokens)]


@tokens_router.post("", status_code=status.HTTP_201_CREATED)
async def mint(body: TokenIn, principal: SuperAdmin, grants: Grants) -> MintedOut:
    def work() -> MintedOut:
        minted = grants.mint(
            body.permissions,
            body.raid_day,
            principal.member_id,
            days=body.days,
            max_uses=body.max_uses,
            note=body.note,
        )
        return MintedOut(**_token(minted.record, grants.now()).model_dump(), token=minted.token)

    try:
        out = await anyio.to_thread.run_sync(work)
    except GrantError as exc:
        raise _refused(exc) from None
    # Never the token: its id and what it grants.
    log.info("bank.token_minted", token_id=out.id, permissions=out.permissions, raid_day=out.raid_day)
    return out


@tokens_router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_token(token_id: Annotated[int, Path(ge=1)], principal: SuperAdmin, grants: Grants) -> Response:
    try:
        await anyio.to_thread.run_sync(grants.revoke_token, token_id, principal.member_id)
    except GrantError as exc:
        raise _refused(exc) from None
    log.info("bank.token_revoked", token_id=token_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ------------------------------------------------------------------ redeem


@redeem_router.post("/redeem")
async def redeem(body: RedeemIn, principal: Member, grants: Grants, live: Live) -> RedeemedOut:
    """Every refusal reads the same, and a member who keeps getting it wrong must wait (REDEEM_ATTEMPTS per
    REDEEM_WINDOW_SECONDS). The bank bot calls this for the member who used /bank redeem."""
    if principal.discord_user_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Your hub session has no Discord identity; sign in again")
    failures = f"bank:redeem:failures:{principal.discord_user_id}"
    seen = await live.redis.get(failures)
    if seen is not None and int(seen) >= REDEEM_ATTEMPTS:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many tries; wait a while and try again")
    redeemer = Redeemer(principal.discord_user_id, principal.display_name, principal.member_id)
    try:
        token, granted = await anyio.to_thread.run_sync(grants.redeem, body.token, redeemer)
    except GrantError as exc:
        await live.redis.incr(failures)
        await live.redis.expire(failures, REDEEM_WINDOW_SECONDS)
        raise _refused(exc) from None
    log.info("bank.token_redeemed", token_id=token.id, grants=[g.id for g in granted])
    return RedeemedOut(token_id=token.id, grants=[_grant(g) for g in granted])


def include_bank_grants(app: FastAPI) -> None:
    for router in (grants_router, tokens_router, redeem_router):
        app.include_router(router)
