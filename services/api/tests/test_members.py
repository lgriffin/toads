"""Members directory (REQ-HUB-PRIV-004) and the viewer's raid/officer days on /api/session (REQ-HUB-DAY-004)."""

from __future__ import annotations

import pytest

from conftest import Hub


def test_members_see_display_names_only(hub: Hub) -> None:
    hub.login(hub.user(("sun", "raider"), nick="Ribbit"))
    sid = hub.login(hub.user(("wed", "trial"), nick="Hopscotch"))
    rows = hub.get("/api/members", sid).json()
    assert [r["display_name"] for r in rows] == ["Hopscotch", "Ribbit"]
    assert all(r["discord_user_id"] is None for r in rows)


def test_plain_members_can_list(hub: Hub) -> None:
    sid = hub.login(hub.user(nick="Newt"))
    assert hub.get("/api/members", sid).status_code == 200


@pytest.mark.parametrize("roles", [(("wed", "officer"),), (("global", "officer"),)])
def test_officers_see_discord_ids_as_strings(hub: Hub, roles: tuple[tuple[str, str], ...]) -> None:
    officer = hub.user(*roles, nick="Boss")
    sid = hub.login(officer)
    [row] = hub.get("/api/members", sid).json()
    assert row["discord_user_id"] == str(officer.user_id)


def test_snowflakes_keep_full_precision(hub: Hub) -> None:
    officer = hub.user(("global", "officer"))
    hub.fake.users.pop(officer.user_id)
    officer.user_id = 1_234_567_890_123_456_789
    hub.fake.add_user(officer)
    sid = hub.login(officer)
    assert hub.get("/api/members", sid).json()[0]["discord_user_id"] == "1234567890123456789"


@pytest.mark.security
def test_signed_out_cannot_list_members(hub: Hub) -> None:
    assert hub.get("/api/members", None).status_code == 401


def test_session_lists_raid_and_officer_days(hub: Hub) -> None:
    sid = hub.login(hub.user(("sun", "officer"), ("wed", "raider")))
    info = hub.get("/api/session", sid).json()
    assert info["raid_days"] == ["wed", "sun"]  # config order
    assert info["officer_days"] == ["sun"]
    assert info["global_officer"] is False


def test_plain_member_has_no_days(hub: Hub) -> None:
    info = hub.get("/api/session", hub.login(hub.user())).json()
    assert (info["raid_days"], info["officer_days"]) == ([], [])


def test_global_officer_is_officer_everywhere(hub: Hub) -> None:
    info = hub.get("/api/session", hub.login(hub.user(("global", "officer"), ("wed", "trial")))).json()
    assert info["raid_days"] == ["wed"]
    assert info["officer_days"] == ["wed", "sun"]
    assert info["global_officer"] is True
