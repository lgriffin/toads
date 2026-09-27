"""Turning a session cookie into a Principal, re-reading Discord roles when they go stale (REQ-HUB-RBAC-002)."""

from __future__ import annotations

from dataclasses import replace

import structlog

from toads_api.discord_api import DiscordAuthError, GuildMember
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
