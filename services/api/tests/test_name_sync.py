"""Discord names follow the member onto the hub (REQ-HUB-AUTH-004): the session's role refresh and the officers'
roster sync both store what Discord says now."""

from __future__ import annotations

from hub_db import Member
from sqlalchemy import select
from toads_api.identity import sync_raid_rosters

from conftest import Hub


def _row(hub: Hub, user_id: int) -> tuple[str, str]:
    with hub.db() as db:
        row = db.scalars(select(Member).where(Member.discord_user_id == user_id)).one()
        return row.display_name, row.discord_username


def test_a_rename_reaches_the_member_row_on_the_role_refresh(hub: Hub) -> None:
    user = hub.user(("wed", "raider"), nick="Before")
    sid = hub.login(user)
    user.nick, user.username = "After", "after_handle"
    hub.pass_time(hub.services.settings.role_refresh_seconds)
    session = hub.get("/api/session", sid).json()
    assert (session["display_name"], session["discord_username"]) == ("After", "after_handle")
    assert _row(hub, user.user_id) == ("After", "after_handle")


def test_no_rename_before_the_refresh_is_due(hub: Hub) -> None:
    user = hub.user(("wed", "raider"), nick="Before")
    sid = hub.login(user)
    user.nick = "After"
    hub.pass_time(hub.services.settings.role_refresh_seconds - 1)
    assert hub.get("/api/session", sid).json()["display_name"] == "Before"


def test_a_member_who_left_keeps_their_last_name(hub: Hub) -> None:
    user = hub.user(("wed", "raider"), nick="Stayed")
    sid = hub.login(user)
    user.nick, user.in_guild = "Gone", False
    hub.pass_time(hub.services.settings.role_refresh_seconds)
    assert hub.get("/api/session", sid).status_code == 401
    assert _row(hub, user.user_id) == ("Stayed", user.username)


def test_the_roster_sync_renames_members_without_a_raid_night(hub: Hub) -> None:
    raider = hub.user(("wed", "raider"), nick="Raider")
    visitor = hub.user(nick="Visitor")
    hub.login(raider)
    hub.login(visitor)
    raider.nick, visitor.nick = "Raider Renamed", "Visitor Renamed"
    members = hub.client.portal.call(hub.services.discord.guild_members)
    assert sync_raid_rosters(hub.services, members) == 1
    assert _row(hub, raider.user_id)[0] == "Raider Renamed"
    assert _row(hub, visitor.user_id)[0] == "Visitor Renamed"
