"""Turning a session cookie into a Principal, re-reading Discord roles when they go stale (REQ-HUB-RBAC-002), and
the members a bot acts for."""

from __future__ import annotations

import json
from collections.abc import Collection, Iterable
from dataclasses import replace
from datetime import UTC, datetime

import anyio
import structlog
from hub_db import Member
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

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
        # Off the old nights' rosters straight away: a member who left the server never signs in again.
        await anyio.to_thread.run_sync(
            record_raid_days, services, data.member_id, () if member is None else member.role_ids
        )
        await services.sessions.delete(session_id)
        log.info("session.ended_on_refresh", member_id=data.member_id, left_server=member is None)
        return None
    updated = replace(
        data,
        role_ids=sorted(member.role_ids),
        display_name=member.server_name,
        discord_username=member.username,
        refreshed_at=services.clock(),
    )
    await services.sessions.save(session_id, updated)
    await anyio.to_thread.run_sync(record_raid_days, services, data.member_id, member.role_ids)
    return updated


def raid_days_of(services: Services, role_ids: Collection[int]) -> list[str]:
    """The raid days a member's Discord roles put them on, in config order."""
    return list(services.principal_for(0, role_ids).day_roles)


def record_raid_days(services: Services, member_id: int, role_ids: Collection[int]) -> None:
    """Keep the member row's raid days in step with their roles, for the comp builder's roster (docs/comps.md)."""
    days = raid_days_of(services, role_ids)
    with services.db.begin() as db:
        row = db.get(Member, member_id)
        if row is not None and row.raid_days != days:
            row.raid_days = days


def upsert_member(services: Services, member: GuildMember, *, signing_in: bool = False) -> int:
    """The hub member row for a Discord member, created on first sight; returns its id. `signing_in` stamps the
    sign-in, which tells the comp builder the member has used the hub (docs/comps.md)."""
    # Read before the write opens: the night badges' roles come from the database too.
    days = raid_days_of(services, member.role_ids)
    with services.db.begin() as db:
        row = db.scalar(select(Member).where(Member.discord_user_id == member.user_id))
        if row is None:
            row = Member(
                discord_user_id=member.user_id, display_name=member.server_name, discord_username=member.username
            )
            db.add(row)
            db.flush()
        else:
            row.display_name = member.server_name
            row.discord_username = member.username
        row.raid_days = days
        if signing_in:
            row.signed_in_at = datetime.fromtimestamp(services.clock(), UTC)
        return row.id


def member_ids_for(services: Services, members: Iterable[GuildMember]) -> dict[int, int]:
    """The hub member id of each Discord member, by Discord user id, creating the rows of those the hub has not met
    (without a sign-in), as an import that names people before they sign in needs."""
    return {m.user_id: upsert_member(services, m) for m in members}


ROSTERS_SYNCED_KEY = "comps:rosters:synced"


def sync_raid_rosters(services: Services, members: Iterable[GuildMember]) -> int:
    """Put every Discord member holding a raid night's roles on that night's comp roster, signed in or not, and take
    everyone else off; `members` is the whole server. Returns how many hold a night. The rows it creates carry no
    sign-in, so the comp builder marks them (docs/comps.md). Never a source of permissions."""
    holders: dict[int, tuple[GuildMember, list[str]]] = {}
    # The same reading of roles as a sign-in, badge ties included. Each reading queries the ties, and most members
    # share a handful of role sets, so each set is read once.
    nights_of: dict[frozenset[int], list[str]] = {}
    for m in members:
        if m.role_ids not in nights_of:
            nights_of[m.role_ids] = raid_days_of(services, m.role_ids)
        if days := nights_of[m.role_ids]:
            holders[m.user_id] = (m, days)
    with services.db.begin() as db:
        rows = {r.discord_user_id: r for r in db.scalars(select(Member))}
        for user_id, row in rows.items():
            if user_id not in holders and row.raid_days:
                row.raid_days = []
        for user_id, (m, days) in holders.items():
            known = rows.get(user_id)
            if known is None:
                db.add(
                    Member(
                        discord_user_id=user_id, display_name=m.server_name, discord_username=m.username, raid_days=days
                    )
                )
                continue
            known.display_name, known.discord_username = m.server_name, m.username
            if known.raid_days != days:
                known.raid_days = days
    return len(holders)


async def refresh_raid_rosters(services: Services) -> None:
    """Re-read the server's raid-role holders with the Toad Bot's token, at most once per `role_refresh_seconds`
    across the hub. If Discord does not answer, the rosters stay as last read and the next request tries again."""
    if not await services.redis.set(ROSTERS_SYNCED_KEY, "1", nx=True, ex=services.settings.role_refresh_seconds):
        return
    try:
        members = await services.discord.guild_members()
    except DiscordError:
        await services.redis.delete(ROSTERS_SYNCED_KEY)
        log.warning("comps.rosters_unavailable")
        return
    try:
        holders = await anyio.to_thread.run_sync(sync_raid_rosters, services, members)
    except SQLAlchemyError:
        # Such as a sign-in creating the same new member mid-sync: serve the stored rosters and let the next one retry.
        await services.redis.delete(ROSTERS_SYNCED_KEY)
        log.exception("comps.rosters_sync_failed")
        return
    log.info("comps.rosters_synced", members=len(members), holders=holders)


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
        username = str(seen.get("username", ""))
    except (ValueError, TypeError, KeyError):
        return None
    return await anyio.to_thread.run_sync(services.principal_for, member_id, role_ids, name, discord_user_id, username)


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
    seen = {
        "member_id": member_id,
        "role_ids": sorted(member.role_ids),
        "name": member.server_name,
        "username": member.username,
    }
    await services.redis.set(_acting_key(discord_user_id), json.dumps(seen), ex=services.settings.role_refresh_seconds)
    return await anyio.to_thread.run_sync(
        services.principal_for, member_id, set(member.role_ids), member.server_name, member.user_id, member.username
    )
