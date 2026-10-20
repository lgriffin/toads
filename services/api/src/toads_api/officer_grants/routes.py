"""Officer grants (docs/admin.md "Officer grants"). Super admins alone; there is no route that makes anyone a super
admin.

- GET    /api/admin/officer-grants                   every officer grant, and the raid days one can cover
- GET    /api/admin/officer-grants/discord-members   members of the Toads Discord whose name starts with `q`
- POST   /api/admin/officer-grants                   make a Discord member an officer of a raid day, or global officer
- DELETE /api/admin/officer-grants/{grant_id}        revoke it; it stops working on the member's next call

Discord user ids travel as strings: they exceed JavaScript's safe integers.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

import anyio
import structlog
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Path, Query, Response, status
from pydantic import BaseModel, Field

from toads_api.discord_api import DiscordError, GuildMember
from toads_api.officer_grants.repository import OfficerGrantRecord
from toads_api.officer_grants.service import OfficerGrantError, OfficerGrantService
from toads_api.rbac.deps import get_services, require
from toads_api.rbac.permissions import Permission, Principal
from toads_api.services import Services

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/admin/officer-grants", tags=["super admins"])

Live = Annotated[Services, Depends(get_services)]
SuperAdmin = Annotated[Principal, Depends(require(Permission.MANAGE_OFFICER_GRANTS))]


def grants_of(live: Live) -> OfficerGrantService:
    return live.officer_grants


Grants = Annotated[OfficerGrantService, Depends(grants_of)]


class OfficerGrantIn(BaseModel):
    discord_user_id: str = Field(pattern=r"^[1-9]\d{0,19}$")
    # None: a global officer, on every raid day.
    raid_day: str | None = Field(default=None, pattern=r"^[a-z0-9_-]{1,32}$")


class OfficerGrantOut(BaseModel):
    id: int
    discord_user_id: str
    username: str
    display_name: str
    raid_day: str | None
    granted_by_name: str | None
    granted_at: datetime


class RaidDayOut(BaseModel):
    id: str
    name: str


class OfficerGrantsOut(BaseModel):
    grants: list[OfficerGrantOut]
    # The raid days a grant can cover, in config order.
    raid_days: list[RaidDayOut]


class DiscordMemberOut(BaseModel):
    discord_user_id: str
    username: str
    display_name: str


def _grant(g: OfficerGrantRecord) -> OfficerGrantOut:
    return OfficerGrantOut(
        id=g.id,
        discord_user_id=str(g.discord_user_id),
        username=g.username,
        display_name=g.display_name,
        raid_day=g.raid_day,
        granted_by_name=g.granted_by_name,
        granted_at=g.granted_at,
    )


def _member(m: GuildMember) -> DiscordMemberOut:
    return DiscordMemberOut(discord_user_id=str(m.user_id), username=m.username, display_name=m.server_name)


def _discord_down() -> HTTPException:
    return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Discord is not answering; try again shortly")


@router.get("")
async def list_officer_grants(_: SuperAdmin, grants: Grants, live: Live) -> OfficerGrantsOut:
    records = await anyio.to_thread.run_sync(grants.all_grants)
    return OfficerGrantsOut(
        grants=[_grant(g) for g in records],
        raid_days=[RaidDayOut(id=d.id, name=d.name) for d in live.raid_days.raid_days],
    )


@router.get("/discord-members")
async def find_discord_members(
    q: Annotated[str, Query(min_length=1, max_length=32)], _: SuperAdmin, live: Live
) -> list[DiscordMemberOut]:
    try:
        found = await live.discord.search_members(q.strip(), limit=10)
    except DiscordError:
        raise _discord_down() from None
    return [_member(m) for m in found]


@router.post("", status_code=status.HTTP_201_CREATED)
async def grant_officer(
    body: OfficerGrantIn, response: Response, principal: SuperAdmin, grants: Grants, live: Live
) -> OfficerGrantOut:
    """Only someone in the Toads server can be granted; their names are kept for the list."""
    try:
        member = await live.discord.guild_member(int(body.discord_user_id))
    except DiscordError:
        raise _discord_down() from None
    if member is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="They are not in the Toads Discord")
    try:
        record, created = await anyio.to_thread.run_sync(
            grants.grant, member.user_id, member.username, member.server_name, body.raid_day, principal.member_id
        )
    except OfficerGrantError as exc:
        raise HTTPException(exc.status, detail=exc.message) from None
    if not created:
        response.status_code = status.HTTP_200_OK
    log.info("officer.grant", grant_id=record.id, raid_day=record.raid_day, new=created)
    return _grant(record)


@router.delete("/{grant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_officer(grant_id: Annotated[int, Path(ge=1)], principal: SuperAdmin, grants: Grants) -> Response:
    try:
        record = await anyio.to_thread.run_sync(grants.revoke, grant_id, principal.member_id)
    except OfficerGrantError as exc:
        raise HTTPException(exc.status, detail=exc.message) from None
    log.info("officer.revoke", grant_id=record.id, raid_day=record.raid_day)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def include_officer_grants(app: FastAPI) -> None:
    app.include_router(router)
