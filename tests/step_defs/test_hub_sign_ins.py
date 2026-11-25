"""REQ-HUB-SIGNIN-*: the officers' sign-in audit (docs/sign-ins.md).

Thin steps over the `hub` fixture (root conftest.py): the real API wired to the fake Discord server. Every sign-in goes
through the real /auth/callback.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from toads_api.discord_api import GuildMember
from toads_api.identity import upsert_member

from conftest import Hub

FEATURES = Path(__file__).resolve().parents[1] / "features"
scenarios(str(FEATURES / "hub_signin.feature"))

DAY_IDS = {"Wednesday": "wed", "Sunday": "sun"}


@pytest.fixture
def people() -> dict[str, Any]:
    return {}


def _noon(day: str) -> float:
    return datetime.combine(date.fromisoformat(day), datetime.min.time(), UTC).replace(hour=12).timestamp()


def _sign_in_on(hub: Hub, people: dict[str, Any], nick: str, day: str) -> str:
    today, hub.now = hub.now, _noon(day)
    session_id = hub.login(people[nick])
    hub.now = today
    return session_id


@given(parsers.parse('today is "{today}"'))
def today_is(hub: Hub, today: str) -> None:
    hub.now = _noon(today)


@given(parsers.parse("a {day} officer"))
def an_officer(hub: Hub, people: dict[str, Any], day: str) -> None:
    roles = ("global", "officer") if day == "global" else (DAY_IDS[day], "officer")
    people[day] = hub.login(hub.user(roles))


@given(parsers.parse('a Wednesday raider "{nick}" who signed in on "{day}"'))
def a_raider_signed_in(hub: Hub, people: dict[str, Any], nick: str, day: str) -> None:
    people[nick] = hub.user(("wed", "raider"), nick=nick)
    people["raider"] = _sign_in_on(hub, people, nick, day)


@given(parsers.parse('a Wednesday raider "{nick}" who has never signed in'))
def a_raider_never(hub: Hub, nick: str) -> None:
    # The hub meets them as the raid nights' roster sync does every Discord member on a night, without a sign-in.
    user = hub.user(("wed", "raider"), nick=nick)
    member = GuildMember(user.user_id, user.username, None, user.nick, frozenset(user.roles))
    upsert_member(hub.services, member)


@given(parsers.parse('a member on no raid night "{nick}" who signed in on "{day}"'))
def a_member_signed_in(hub: Hub, people: dict[str, Any], nick: str, day: str) -> None:
    people[nick] = hub.user(nick=nick)
    _sign_in_on(hub, people, nick, day)


@when(parsers.parse('"{nick}" signs in again on "{day}"'))
def signs_in_again(hub: Hub, people: dict[str, Any], nick: str, day: str) -> None:
    _sign_in_on(hub, people, nick, day)


def _audit(hub: Hub, sid: str, day: str | None, on: str | None = None) -> Any:
    path = "/api/admin/sign-ins" if day is None else f"/api/days/{day}/sign-ins"
    return hub.get(f"{path}?on={on}" if on else path, sid)


def _names(hub: Hub, sid: str, day: str | None, on: str | None = None) -> list[str]:
    r = _audit(hub, sid, day, on)
    assert r.status_code == 200, r.text
    return [s["member_name"] for s in r.json()["sign_ins"]]


@then(parsers.parse('the Wednesday officer sees "{nick}" among the sign-ins on "{on}"'))
def officer_sees(hub: Hub, people: dict[str, Any], nick: str, on: str) -> None:
    assert nick in _names(hub, people["Wednesday"], "wed", on)


@then(parsers.parse('the Wednesday officer sees "{nick}" last signed in on "{on}" and "{never}" never'))
def officer_sees_last(hub: Hub, people: dict[str, Any], nick: str, on: str, never: str) -> None:
    members = {
        m["member_name"]: m["last_signed_in_at"] for m in _audit(hub, people["Wednesday"], "wed").json()["members"]
    }
    assert members[nick] is not None and members[nick].startswith(on)
    assert members[never] is None
    assert list(members)[-1] == never


@then(parsers.parse('the Wednesday officer counts {count:d} sign-ins on "{on}"'))
def officer_counts(hub: Hub, people: dict[str, Any], count: int, on: str) -> None:
    recent = {d["date"]: d["sign_ins"] for d in _audit(hub, people["Wednesday"], "wed").json()["recent"]}
    assert recent[on] == count


@then("the raider is refused Wednesday's sign-ins")
def raider_refused(hub: Hub, people: dict[str, Any]) -> None:
    assert _audit(hub, people["raider"], "wed").status_code == 403


@then("the Sunday officer is refused Wednesday's sign-ins")
def sibling_refused(hub: Hub, people: dict[str, Any]) -> None:
    assert _audit(hub, people["Sunday"], "wed").status_code == 403


@then(parsers.parse('the Sunday officer does not see "{nick}" in Sunday\'s sign-ins'))
def sibling_sees_own_only(hub: Hub, people: dict[str, Any], nick: str) -> None:
    names = _names(hub, people["Sunday"], "sun")
    assert nick not in names
    members = [m["member_name"] for m in _audit(hub, people["Sunday"], "sun").json()["members"]]
    assert nick not in members


@then("the Sunday officer is refused the sign-ins of members on no raid night")
def sibling_refused_unplaced(hub: Hub, people: dict[str, Any]) -> None:
    assert _audit(hub, people["Sunday"], None).status_code == 403


@then(
    parsers.parse(
        'the global officer sees "{raider}" in Wednesday\'s sign-ins and "{member}" among members on no raid night'
    )
)
def global_sees(hub: Hub, people: dict[str, Any], raider: str, member: str) -> None:
    assert raider in _names(hub, people["global"], "wed")
    assert member in _names(hub, people["global"], None)
    assert member not in _names(hub, people["global"], "wed")


@then(parsers.parse('the Wednesday officer\'s sign-ins for "{on}" are refused as invalid'))
def future_refused(hub: Hub, people: dict[str, Any], on: str) -> None:
    assert _audit(hub, people["Wednesday"], "wed", on).status_code == 422
