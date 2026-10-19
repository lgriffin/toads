"""REQ-HUB-AWARD-*: members' Discord usernames and the awards officers give them (docs/awards.md).

Thin steps over the `hub` fixture (root conftest.py): the real API wired to the fake Discord server.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from hub_db import AuditEntry, Member, MemberAward
from pytest_bdd import given, parsers, scenarios, then, when
from sqlalchemy import select
from toads_api.testing.fake_discord import FakeUser

from conftest import Hub

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


@then("the raider holds no awards")
def holds_none(hub: Hub, people: dict[str, Any]) -> None:
    assert hub.get("/api/me/awards", _raider_sid(hub, people)).json() == []
