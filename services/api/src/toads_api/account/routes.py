"""A member's own settings. Every route acts on the caller's own member id, taken from the session, never from the
request; any signed-in member may use them.

- GET    /api/me/settings   the name shown for them, the names they may choose, and whether their own key is saved
- PUT    /api/me/name       choose the Discord name or one of their approved characters
- PUT    /api/me/wcl-key    save their own Warcraft Logs client id and secret (write-only)
- DELETE /api/me/wcl-key    forget it; their requests go back to the guild key
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

import anyio
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from toads_api.account.service import AccountError, AccountService, AccountSettings, NameSource
from toads_api.rbac import Permission, Principal
from toads_api.rbac.deps import get_services, require

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/me", tags=["account"])


def get_account(request: Request) -> AccountService:
    return get_services(request).account


Account = Annotated[AccountService, Depends(get_account)]
SignedIn = Annotated[Principal, Depends(require(Permission.VIEW_GUILD_RAIDS))]


class NameOptionOut(BaseModel):
    source: NameSource
    name: str
    character_id: int | None


class WclKeyOut(BaseModel):
    """Never the key itself: which key is saved and whether Warcraft Logs accepted it last time."""

    client_id_hint: str
    status: str
    updated_at: datetime
    checked_at: datetime | None


class SettingsOut(BaseModel):
    shown_name: str
    name_source: NameSource
    name_character_id: int | None
    name_options: list[NameOptionOut]
    wcl_key: WclKeyOut | None
    # Which key the member's Warcraft Logs requests use right now.
    wcl_key_in_use: str


class NameIn(BaseModel):
    source: NameSource
    character_id: int | None = Field(default=None, gt=0)


class WclKeyIn(BaseModel):
    client_id: str = Field(min_length=1, max_length=200)
    client_secret: str = Field(min_length=1, max_length=400)


def _out(s: AccountSettings) -> SettingsOut:
    own = s.wcl_key is not None and s.wcl_key.status != "rejected"
    return SettingsOut(
        shown_name=s.shown_name,
        name_source=s.name_source,
        name_character_id=s.name_character_id,
        name_options=[NameOptionOut(source=o.source, name=o.name, character_id=o.character_id) for o in s.name_options],
        wcl_key=None
        if s.wcl_key is None
        else WclKeyOut(
            client_id_hint=s.wcl_key.client_id_hint,
            status=s.wcl_key.status,
            updated_at=s.wcl_key.updated_at,
            checked_at=s.wcl_key.checked_at,
        ),
        wcl_key_in_use="own" if own else "guild",
    )


def _refused(exc: AccountError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.message)


@router.get("/settings")
async def get_settings(principal: SignedIn, account: Account) -> SettingsOut:
    try:
        return _out(await anyio.to_thread.run_sync(account.settings, principal.member_id))
    except AccountError as exc:
        raise _refused(exc) from None


@router.put("/name")
async def choose_name(body: NameIn, principal: SignedIn, account: Account) -> SettingsOut:
    try:
        s = await anyio.to_thread.run_sync(account.choose_name, principal.member_id, body.source, body.character_id)
    except AccountError as exc:
        raise _refused(exc) from None
    return _out(s)


@router.put("/wcl-key")
async def save_wcl_key(body: WclKeyIn, principal: SignedIn, account: Account) -> SettingsOut:
    try:
        s = await anyio.to_thread.run_sync(
            account.save_wcl_key, principal.member_id, body.client_id, body.client_secret
        )
    except AccountError as exc:
        raise _refused(exc) from None
    # The member id and nothing else: never the id, secret or hint.
    log.info("account.wcl_key_saved", member_id=principal.member_id)
    return _out(s)


@router.delete("/wcl-key")
async def remove_wcl_key(principal: SignedIn, account: Account) -> SettingsOut:
    try:
        s = await anyio.to_thread.run_sync(account.remove_wcl_key, principal.member_id)
    except AccountError as exc:
        raise _refused(exc) from None
    log.info("account.wcl_key_removed", member_id=principal.member_id)
    return _out(s)
