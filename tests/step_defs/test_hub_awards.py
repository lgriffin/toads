"""REQ-HUB-AWARD-*: members' Discord usernames, the awards officers give them (docs/awards.md) and the badges super
admins tie to Discord roles (docs/role-badges.md).

Thin steps over the `hub` fixture (root conftest.py): the real API wired to the fake Discord server.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from hub_db import AuditEntry, DiscordRoleBadge, Member, MemberAward
from pytest_bdd import given, parsers, scenarios, then, when
from sqlalchemy import select
from toads_api.testing.fake_discord import FakeUser

from conftest import Hub, make_settings

FEATURES = Path(__file__).resolve().parents[1] / "features"
scenarios(str(FEATURES / "hub_award.feature"))


@pytest.fixture
def people() -> dict[str, Any]:
    return {}


def _member_id(hub: Hub, sid: str) -> int:
    return int(hub.get("/api/session", sid).json()["member_id"])


@given(parsers.parse('a raider who goes by the nickname "{nick}"'))
def a_raider(hub: Hub, people: dict[str, Any], nick: str) -> None:
    people["raider"] = hub.user(("wed", "raider"), nick=nick)


@given("a global officer")
def a_global_officer(hub: Hub, people: dict[str, Any]) -> None:
    people["officer"] = hub.login(hub.user(("global", "officer")))


@given("a Wednesday officer")
def a_day_officer(hub: Hub, people: dict[str, Any]) -> None:
    people["day_officer"] = hub.login(hub.user(("wed", "officer")))


def _raider_sid(hub: Hub, people: dict[str, Any]) -> str:
    if "raider_sid" not in people:
        people["raider_sid"] = hub.login(people["raider"])
    sid: str = people["raider_sid"]
    return sid


@when("they sign in")
def they_sign_in(hub: Hub, people: dict[str, Any]) -> None:
    _raider_sid(hub, people)


def _give(hub: Hub, people: dict[str, Any], who: str, award_id: str, period: str | None = None) -> Any:
    target = _member_id(hub, _raider_sid(hub, people))
    body: dict[str, Any] = {"member_id": target, "award_id": award_id}
    if period is not None:
        body["period"] = period
    r = hub.post("/api/admin/awards", people[who], body)
    people["last"] = r
    return r


@when(parsers.parse('the global officer gives the raider the "{award_id}" award'))
def officer_gives(hub: Hub, people: dict[str, Any], award_id: str) -> None:
    assert _give(hub, people, "officer", award_id).status_code == 201


@when(parsers.parse('the Wednesday officer tries to give the raider the "{award_id}" award'))
def day_officer_tries(hub: Hub, people: dict[str, Any], award_id: str) -> None:
    _give(hub, people, "day_officer", award_id)


@when(parsers.parse('the global officer gives the raider Raider of the Month for "{first}" and for "{second}"'))
def officer_gives_monthly(hub: Hub, people: dict[str, Any], first: str, second: str) -> None:
    for month in (first, second):
        assert _give(hub, people, "officer", "raider-of-the-month", month).status_code == 201


@when("the global officer takes it back")
def officer_takes_back(hub: Hub, people: dict[str, Any]) -> None:
    award = people["last"].json()
    assert hub.delete(f"/api/admin/awards/{award['id']}", people["officer"]).status_code == 204


@then(parsers.parse('their session reports their Discord username and the nickname "{nick}"'))
def session_reports(hub: Hub, people: dict[str, Any], nick: str) -> None:
    raider: FakeUser = people["raider"]
    s = hub.get("/api/session", _raider_sid(hub, people)).json()
    assert (s["display_name"], s["discord_username"]) == (nick, raider.username)


@then("their member row holds their Discord username")
def row_holds_username(hub: Hub, people: dict[str, Any]) -> None:
    raider: FakeUser = people["raider"]
    with hub.db() as db:
        row = db.scalars(select(Member).where(Member.discord_user_id == raider.user_id)).one()
    assert row.discord_username == raider.username


@then(parsers.parse('the raider sees "{name}" among their awards'))
def raider_sees(hub: Hub, people: dict[str, Any], name: str) -> None:
    assert name in [a["name"] for a in hub.get("/api/me/awards", _raider_sid(hub, people)).json()]


@then(parsers.parse('the guild\'s awards include "{name}" for "{member}"'))
def wall_includes(hub: Hub, people: dict[str, Any], name: str, member: str) -> None:
    wall = hub.get("/api/awards", people["officer"]).json()
    assert (name, member) in [(a["name"], a["member_name"]) for a in wall]


@then(parsers.parse('the audit log records "{action}"'))
def audit_records(hub: Hub, action: str) -> None:
    with hub.db() as db:
        assert action in [e.action for e in db.scalars(select(AuditEntry))]


@then("the request is refused as forbidden")
def refused_forbidden(people: dict[str, Any]) -> None:
    assert people["last"].status_code == 403


@then("no award is stored")
def nothing_stored(hub: Hub) -> None:
    with hub.db() as db:
        assert db.scalars(select(MemberAward)).all() == []


@then("the raider holds Raider of the Month twice")
def holds_twice(hub: Hub, people: dict[str, Any]) -> None:
    mine = hub.get("/api/me/awards", _raider_sid(hub, people)).json()
    assert sorted(a["period"] for a in mine if a["award_id"] == "raider-of-the-month") == ["2026-09", "2026-10"]


@then(parsers.parse('giving it again for "{month}" is refused as a duplicate'))
def duplicate_refused(hub: Hub, people: dict[str, Any], month: str) -> None:
    assert _give(hub, people, "officer", "raider-of-the-month", month).status_code == 409


@then("giving it with no month is refused")
def no_month_refused(hub: Hub, people: dict[str, Any]) -> None:
    assert _give(hub, people, "officer", "raider-of-the-month").status_code == 422


@when(parsers.parse('the global officer names the raider Sunder King for "{first}" and for "{second}"'))
def officer_gives_weekly(hub: Hub, people: dict[str, Any], first: str, second: str) -> None:
    for week in (first, second):
        assert _give(hub, people, "officer", "sunder-king", week).status_code == 201


@then("the raider holds Sunder King twice")
def holds_weekly_twice(hub: Hub, people: dict[str, Any]) -> None:
    mine = hub.get("/api/me/awards", _raider_sid(hub, people)).json()
    held = [(a["kind"], a["period"]) for a in mine if a["award_id"] == "sunder-king"]
    assert sorted(held) == [("honour", "2026-W43"), ("honour", "2026-W44")]


@then(parsers.parse('naming them Sunder King again for "{week}" is refused as a duplicate'))
def weekly_duplicate_refused(hub: Hub, people: dict[str, Any], week: str) -> None:
    assert _give(hub, people, "officer", "sunder-king", week).status_code == 409


@then("naming them Sunder King with no week is refused")
def no_week_refused(hub: Hub, people: dict[str, Any]) -> None:
    assert _give(hub, people, "officer", "sunder-king").status_code == 422


@then("the raider holds no awards")
def holds_none(hub: Hub, people: dict[str, Any]) -> None:
    assert hub.get("/api/me/awards", _raider_sid(hub, people)).json() == []


# ---------------------------------------------------------------- role badges


@given(parsers.parse('a Discord role named "{name}"'))
def a_discord_role(hub: Hub, people: dict[str, Any], name: str) -> None:
    role_id = 7000 + len(hub.fake.role_names)
    hub.fake.guild_roles.add(role_id)
    hub.fake.role_names[role_id] = name
    people.setdefault("roles", {})[name] = role_id


@given(parsers.parse('a raider who holds the "{name}" role'))
def a_raider_with_role(hub: Hub, people: dict[str, Any], name: str) -> None:
    people["raider"] = hub.user(("wed", "raider"), nick="Hopscotch")
    people["raider"].roles.add(people["roles"][name])


@given(parsers.parse('a member who holds only the "{name}" role'))
def a_member_with_role(hub: Hub, people: dict[str, Any], name: str) -> None:
    people["raider"] = hub.user(nick="Lilypadma")
    people["raider"].roles.add(people["roles"][name])


@then(parsers.parse('the member is on the "{day}" raid team'))
def on_team(hub: Hub, people: dict[str, Any], day: str) -> None:
    assert people["last"].status_code == 201, people["last"].text
    assert hub.get("/api/session", _raider_sid(hub, people)).json()["raid_days"] == [day]


@then("the member can tell Thursday's officers they will miss a night")
def reports_thursday(hub: Hub, people: dict[str, Any]) -> None:
    # The hub's clock stands in mid-January 1970; the 15th was a Thursday.
    body = {"first_date": "1970-01-15", "note": "Working late."}
    r = hub.post("/api/days/thu/absences", _raider_sid(hub, people), body)
    assert r.status_code == 201, r.text


@then(parsers.parse('the member runs the "{day}" raid night'))
def runs_night(hub: Hub, people: dict[str, Any], day: str) -> None:
    assert people["last"].status_code == 201, people["last"].text
    assert hub.get("/api/session", _raider_sid(hub, people)).json()["officer_days"] == [day]


@then("the member can open Thursday's officer board but not Wednesday's")
def opens_thursday_board(hub: Hub, people: dict[str, Any]) -> None:
    assert hub.get("/api/days/thu/board", _raider_sid(hub, people)).status_code == 200
    assert hub.get("/api/days/wed/board", _raider_sid(hub, people)).status_code == 403


@then("the member runs no raid night")
def runs_no_night(hub: Hub, people: dict[str, Any]) -> None:
    assert hub.get("/api/session", _raider_sid(hub, people)).json()["officer_days"] == []


@then("the member is on no raid team")
def on_no_team(hub: Hub, people: dict[str, Any]) -> None:
    assert hub.get("/api/session", _raider_sid(hub, people)).json()["raid_days"] == []


@given("a super admin")
def a_super_admin(hub: Hub, people: dict[str, Any]) -> None:
    user = hub.user()
    hub.services.settings = make_settings(super_admin_ids=str(user.user_id))
    people["admin"] = hub.login(user)


def _tie(hub: Hub, people: dict[str, Any], who: str, badge_id: str, role_id: int) -> None:
    body = {"discord_role_id": str(role_id), "badge_id": badge_id}
    people["last"] = hub.post("/api/admin/role-badges", people[who], body)


@when(parsers.parse('the super admin ties the "{badge_id}" badge to the "{name}" role'))
def admin_ties(hub: Hub, people: dict[str, Any], badge_id: str, name: str) -> None:
    _tie(hub, people, "admin", badge_id, people["roles"][name])


@when(parsers.parse('the super admin ties the "{badge_id}" badge to a role the server does not have'))
def admin_ties_unknown_role(hub: Hub, people: dict[str, Any], badge_id: str) -> None:
    _tie(hub, people, "admin", badge_id, 999_999)


@when(parsers.parse('the global officer tries to tie the "{badge_id}" badge to the "{name}" role'))
def officer_ties(hub: Hub, people: dict[str, Any], badge_id: str, name: str) -> None:
    _tie(hub, people, "officer", badge_id, people["roles"][name])


@when(parsers.parse('the super admin unties the "{badge_id}" badge from the "{name}" role'))
def admin_unties(hub: Hub, people: dict[str, Any], badge_id: str, name: str) -> None:
    r = hub.delete(f"/api/admin/role-badges/{people['roles'][name]}/{badge_id}", people["admin"])
    assert r.status_code == 204, r.text


@then(parsers.parse('the raider sees the "{name}" badge among their role badges'))
def raider_sees_role_badge(hub: Hub, people: dict[str, Any], name: str) -> None:
    assert people["last"].status_code == 201, people["last"].text
    assert name in [b["name"] for b in hub.get("/api/me/role-badges", _raider_sid(hub, people)).json()]


@then("the raider has no role badges")
def raider_has_no_role_badges(hub: Hub, people: dict[str, Any]) -> None:
    assert hub.get("/api/me/role-badges", _raider_sid(hub, people)).json() == []


@then("the request is refused as invalid")
def refused_invalid(people: dict[str, Any]) -> None:
    assert people["last"].status_code == 422, people["last"].text


@then("no role badge is stored")
def no_role_badge(hub: Hub) -> None:
    with hub.db() as db:
        assert db.scalars(select(DiscordRoleBadge)).all() == []


WEB = Path(__file__).resolve().parents[2] / "apps" / "web" / "src"


@given("the member's own page", target_fixture="me_page")
def me_page() -> dict[str, str]:
    return {
        name: (WEB / path).read_text(encoding="utf-8")
        for name, path in (
            ("layout", "routes/+layout.svelte"),
            ("page", "routes/me/+page.svelte"),
            ("card", "lib/components/AwardsCard.svelte"),
        )
    }


@then("its heading wears the same toads as the hub home's greeting")
def me_heading(me_page: dict[str, str]) -> None:
    # The layout loads the facts once (session, awards, role badges) and hands /me the same object the greeting uses.
    assert "setMe(() => me);" in me_page["layout"]
    # The preview is the same page answered from sample data, so it wears them too.
    assert "<h1>Me <MemberToads {...facts} size={40} /></h1>" in me_page["page"]


@then('its "Your toads" card shows each of those toads as a badge ahead of the awards')
def me_card(me_page: dict[str, str]) -> None:
    assert "<AwardsCard {awards} {toads} />" in me_page["page"]
    card = me_page["card"]
    assert card.index("{#each worn as t (t.id)}") < card.index("{#each awards as a (a.id)}")
