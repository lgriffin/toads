"""Turning a session cookie into a Principal, re-reading Discord roles when they go stale (REQ-HUB-RBAC-002), and
the members a bot acts for."""

from __future__ import annotations

import json
from dataclasses import replace

import anyio
import structlog
from hub_db import Member
from sqlalchemy import select

from toads_api.discord_api import DiscordAuthError, DiscordError, GuildMember
from toads_api.rbac.permissions import Principal
from toads_api.services import Services
from toads_api.sessions import SessionData

log = structlog.get_logger(__name__)


class DiscordUnavailableError(Exception):
    """Roles are due for a refresh but Discord did not answer; we fail closed rather than trust stale roles."""


def roles_removed(services: Services, old: SessionData, member: GuildMember) -> bool:
    """True when the member lost any role the raid-day config maps to a hub role."""
    lost = set(old.role_ids) - member.role_ids
    return bool(lost & services.raid_days.all_role_ids())


async def refresh(services: Services, session_id: str, data: SessionData) -> SessionData | None:
    """Re-read the member's roles. Returns the updated session, or None after ending it.

    A removed mapped role, leaving the server or a revoked token ends the session: the member signs in
    again and gets a principal built from scratch. Added roles simply take effect.
    """
    try:
        member = await services.discord.current_member(data.access_token)
    except DiscordAuthError:
        member = None
    except Exception as exc:
        raise DiscordUnavailableError from exc
    if member is None or roles_removed(services, data, member):
        await services.sessions.delete(session_id)
        log.info("session.ended_on_refresh", member_id=data.member_id, left_server=member is None)
        return None
    updated = replace(
        data,
        role_ids=sorted(member.role_ids),
        display_name=member.server_name,
        refreshed_at=services.clock(),
    )
    await services.sessions.save(session_id, updated)
    return updated


def upsert_member(services: Services, member: GuildMember) -> int:
    """The hub member row for a Discord member, created on first sight; returns its id."""
    with services.db.begin() as db:
        row = db.scalar(select(Member).where(Member.discord_user_id == member.user_id))
        if row is None:
            row = Member(discord_user_id=member.user_id, display_name=member.server_name)
            db.add(row)
            db.flush()
        else:
            row.display_name = member.server_name
        return row.id


class NotAMemberError(Exception):
    """The Discord user a bot acts for is not in the Toads server."""


def _acting_key(discord_user_id: int) -> str:
    return f"acting:member:{discord_user_id}"


async def _cached_acting(services: Services, discord_user_id: int) -> Principal | None:
    raw = await services.redis.get(_acting_key(discord_user_id))
    if raw is None:
        return None
    try:
        seen = json.loads(raw)
        member_id, role_ids, name = int(seen["member_id"]), {int(r) for r in seen["role_ids"]}, str(seen["name"])
    except (ValueError, TypeError, KeyError):
        return None
    return services.raid_days.principal_for(member_id, role_ids, name, discord_user_id)


async def acting_principal(services: Services, discord_user_id: int) -> Principal:
    """The Principal of the Discord member a bot acts for (docs/bank.md). Roles come straight from Discord with the
    hub's bot token, never from the bot, so the bot can only act as a member with that member's own powers.

    What Discord said is kept in Redis for `role_refresh_seconds`, the same staleness a signed-in session is allowed
    (REQ-HUB-RBAC-002), so a busy bot neither runs into Discord's rate limits nor rewrites the member row per call.
    Someone not in the server is never remembered: they are asked about again next time."""
    cached = await _cached_acting(services, discord_user_id)
    if cached is not None:
        return cached
    try:
        member = await services.discord.guild_member(discord_user_id)
    except DiscordError as exc:
        raise DiscordUnavailableError from exc
    if member is None:
        raise NotAMemberError
    member_id = await anyio.to_thread.run_sync(upsert_member, services, member)
    seen = {"member_id": member_id, "role_ids": sorted(member.role_ids), "name": member.server_name}
    await services.redis.set(_acting_key(discord_user_id), json.dumps(seen), ex=services.settings.role_refresh_seconds)
    return services.raid_days.principal_for(member_id, set(member.role_ids), member.server_name, member.user_id)
