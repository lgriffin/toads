"""Role badges (docs/role-badges.md).

- GET    /api/me/role-badges                                  the badges the caller's Discord roles earn
- GET    /api/admin/role-badges                               the catalogue, every tie, and the server's roles
- POST   /api/admin/role-badges                               tie a badge to a Discord role (super admins)
- DELETE /api/admin/role-badges/{discord_role_id}/{badge_id}  untie it

Discord role ids travel as strings: they exceed JavaScript's safe integers.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated

import anyio
import structlog
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from toads_api.discord_api import DiscordError, GuildRole
from toads_api.rbac import Permission, Principal
from toads_api.rbac.deps import get_services, require
from toads_api.role_badges.catalog import ROLE_BADGES, RoleBadge
from toads_api.role_badges.service import LinkView, RoleBadgeError, RoleBadgeService
from toads_api.services import Services

log = structlog.get_logger(__name__)
router = APIRouter(tags=["role-badges"])


def get_role_badges(request: Request) -> RoleBadgeService:
    return get_services(request).role_badges


RoleBadges = Annotated[RoleBadgeService, Depends(get_role_badges)]
Hub = Annotated[Services, Depends(get_services)]
SignedIn = Annotated[Principal, Depends(require(Permission.VIEW_GUILD_RAIDS))]
SuperAdmin = Annotated[Principal, Depends(require(Permission.MANAGE_ROLE_BADGES))]
# Discord snowflakes fit a signed 64-bit column (BigInteger); anything else names no role.
ROLE_ID = r"^[0-9]{1,19}$"
MAX_ROLE_ID = 2**63 - 1


class BadgeOut(BaseModel):
    id: str
    name: str
    file: str


class LinkOut(BaseModel):
    discord_role_id: str
    role_name: str
    badge: BadgeOut
    added_at: datetime


class RoleOut(BaseModel):
    id: str
    name: str
    # "#rrggbb", or None for a role without a colour.
    colour: str | None


class RoleBadgesAdmin(BaseModel):
    badges: list[BadgeOut]
    links: list[LinkOut]
    # The server's roles a member can hold, top of Discord's list first; None when Discord is not answering.
    roles: list[RoleOut] | None


class LinkIn(BaseModel):
    discord_role_id: str = Field(pattern=ROLE_ID)
    badge_id: str = Field(min_length=1, max_length=48)


def _badge(b: RoleBadge) -> BadgeOut:
    return BadgeOut(id=b.id, name=b.name, file=b.file)


def _link(v: LinkView) -> LinkOut:
    return LinkOut(
        discord_role_id=str(v.discord_role_id), role_name=v.role_name, badge=_badge(v.badge), added_at=v.added_at
    )


def _role(r: GuildRole) -> RoleOut:
    return RoleOut(id=str(r.id), name=r.name, colour=f"#{r.colour:06x}" if r.colour else None)


async def _member_roles(services: Services) -> list[GuildRole]:
    """Roles a member can be given: not @everyone (its id is the server's) and not a bot's or integration's own."""
    roles = await services.discord.guild_roles()
    return [r for r in roles if r.id != services.settings.discord_guild_id and not r.managed]


def _refused(exc: RoleBadgeError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.message)


@router.get("/api/me/role-badges")
async def my_role_badges(principal: SignedIn, badges: RoleBadges) -> list[BadgeOut]:
    return [_badge(b) for b in await anyio.to_thread.run_sync(badges.earned, principal.discord_role_ids)]


@router.get("/api/admin/role-badges")
async def role_badges_admin(principal: SuperAdmin, badges: RoleBadges, services: Hub) -> RoleBadgesAdmin:
    try:
        roles: list[RoleOut] | None = [_role(r) for r in await _member_roles(services)]
    except DiscordError:
        log.warning("role_badges.discord_unavailable")
        roles = None
    links = await anyio.to_thread.run_sync(badges.links)
    return RoleBadgesAdmin(
        badges=[_badge(b) for b in ROLE_BADGES.values()], links=[_link(v) for v in links], roles=roles
    )


@router.post("/api/admin/role-badges", status_code=status.HTTP_201_CREATED)
async def tie_role_badge(body: LinkIn, principal: SuperAdmin, badges: RoleBadges, services: Hub) -> LinkOut:
    role_id = int(body.discord_role_id)
    if role_id > MAX_ROLE_ID:
        raise HTTPException(422, detail="That role is not in the Toads server")
    try:
        roles = {r.id: r for r in await _member_roles(services)}
    except DiscordError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Discord is unavailable") from None
    role = roles.get(role_id)
    if role is None:
        raise HTTPException(422, detail="That role is not in the Toads server")
    try:
        view = await anyio.to_thread.run_sync(
            lambda: badges.tie(role_id, role.name, body.badge_id, principal.member_id)
        )
    except RoleBadgeError as exc:
        raise _refused(exc) from None
    log.info("role_badge.tied", by=principal.member_id, role=role_id, badge=body.badge_id)
    return _link(view)


@router.delete("/api/admin/role-badges/{discord_role_id}/{badge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def untie_role_badge(discord_role_id: str, badge_id: str, principal: SuperAdmin, badges: RoleBadges) -> Response:
    if not re.fullmatch(ROLE_ID, discord_role_id) or int(discord_role_id) > MAX_ROLE_ID:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="That role does not earn that badge")
    try:
        await anyio.to_thread.run_sync(badges.untie, int(discord_role_id), badge_id, principal.member_id)
    except RoleBadgeError as exc:
        raise _refused(exc) from None
    log.info("role_badge.untied", by=principal.member_id, role=discord_role_id, badge=badge_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def include_role_badges(app: FastAPI) -> None:
    app.include_router(router)
