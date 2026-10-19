"""REQ-HUB-ABSENCE-*: absences members report for the raid nights they will miss (docs/absences.md).

Thin steps over the `hub` fixture (root conftest.py): the real API wired to the fake Discord server.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest
from hub_db import MemberAbsence
from pytest_bdd import given, parsers, scenarios, then, when
from sqlalchemy import select

from conftest import Hub

FEATURES = Path(__file__).resolve().parents[1] / "features"
scenarios(str(FEATURES / "hub_absence.feature"))

DAY_IDS = {"Wednesday": "wed", "Sunday": "sun"}


@pytest.fixture
def people() -> dict[str, Any]:
    return {}


@given(parsers.parse('today is "{today}"'))
def today_is(hub: Hub, today: str) -> None:
    hub.now = datetime.combine(date.fromisoformat(today), datetime.min.time(), UTC).replace(hour=12).timestamp()


@given(parsers.parse('a Wednesday raider "{nick}"'))
def a_raider(hub: Hub, people: dict[str, Any], nick: str) -> None:
    people["raider"] = hub.login(hub.user(("wed", "raider"), nick=nick))


@given(parsers.parse("a {day} officer"))
def a_day_officer(hub: Hub, people: dict[str, Any], day: str) -> None:
    if day == "global":
        people["global"] = hub.login(hub.user(("global", "officer")))
    else:
        people[day] = hub.login(hub.user((DAY_IDS[day], "officer")))


def _report(hub: Hub, people: dict[str, Any], day: str, first: str, last: str, note: str = "") -> Any:
    body = {"first_date": first, "last_date": last, "note": note or None}
    r = hub.post(f"/api/days/{DAY_IDS[day]}/absences", people["raider"], body)
    people["last"] = r
    return r


@when(parsers.parse('the raider reports an absence from {day} from "{first}" to "{last}" saying "{note}"'))
def raider_reports(hub: Hub, people: dict[str, Any], day: str, first: str, last: str, note: str) -> None:
    r = _report(hub, people, day, first, last, note)
    if r.status_code == 201:
        people["absence"] = r.json()["id"]


@then(parsers.parse('the raider\'s absences cover the nights "{nights}"'))
def raider_nights(hub: Hub, people: dict[str, Any], nights: str) -> None:
    mine = hub.get("/api/me/absences", people["raider"]).json()
    assert [n for a in mine for n in a["nights"]] == nights.split(", ")


def _team(hub: Hub, sid: str, day: str = "wed") -> Any:
    return hub.get(f"/api/days/{day}/absences", sid)


def _away(hub: Hub, sid: str, night: str) -> list[dict[str, Any]]:
    nights = {n["date"]: n["absent"] for n in _team(hub, sid).json()["nights"]}
    away: list[dict[str, Any]] = nights[night]
    return away


@then(parsers.parse('the Wednesday officer sees "{name}" away on "{first}" and "{second}" saying "{note}"'))
def officer_sees(hub: Hub, people: dict[str, Any], name: str, first: str, second: str, note: str) -> None:
    for night in (first, second):
        assert [(a["member_name"], a["note"]) for a in _away(hub, people["Wednesday"], night)] == [(name, note)]


@then(parsers.parse('the Wednesday officer sees nobody away on "{night}"'))
def officer_sees_nobody(hub: Hub, people: dict[str, Any], night: str) -> None:
    assert _away(hub, people["Wednesday"], night) == []


@then("the request is refused as forbidden")
def refused_forbidden(people: dict[str, Any]) -> None:
    assert people["last"].status_code == 403


@then("no absence is stored")
def none_stored(hub: Hub) -> None:
    with hub.db() as db:
        assert db.scalars(select(MemberAbsence)).all() == []


@then("the raider is refused Wednesday's absences")
def raider_refused(hub: Hub, people: dict[str, Any]) -> None:
    assert _team(hub, people["raider"]).status_code == 403


@then("the Sunday officer is refused Wednesday's absences")
def sibling_refused(hub: Hub, people: dict[str, Any]) -> None:
    assert _team(hub, people["Sunday"]).status_code == 403
    assert _team(hub, people["Sunday"], "sun").status_code == 200


@then("the global officer sees Wednesday's and Sunday's absences")
def global_sees(hub: Hub, people: dict[str, Any]) -> None:
    assert [_team(hub, people["global"], d).json()["raid_day"] for d in ("wed", "sun")] == ["wed", "sun"]


@then(parsers.parse('reporting {day} from "{first}" to "{last}" is refused as {why}'))
def refused(hub: Hub, people: dict[str, Any], day: str, first: str, last: str, why: str) -> None:
    assert _report(hub, people, day, first, last).status_code == {"invalid": 422, "a conflict": 409}[why]


@then("the Wednesday officer cannot cancel it")
def officer_cannot_cancel(hub: Hub, people: dict[str, Any]) -> None:
    assert hub.delete(f"/api/me/absences/{people['absence']}", people["Wednesday"]).status_code == 404


@when("the raider cancels it")
def raider_cancels(hub: Hub, people: dict[str, Any]) -> None:
    assert hub.delete(f"/api/me/absences/{people['absence']}", people["raider"]).status_code == 204


@then("the raider has no absences")
def raider_has_none(hub: Hub, people: dict[str, Any]) -> None:
    assert hub.get("/api/me/absences", people["raider"]).json() == []
