"""REQ-HUB-PROF-*: members' professions and the guild's crafters (docs/professions.md).

Thin steps over the `hub` fixture (root conftest.py): the real API wired to the fake Discord server.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from hub_db import AuditEntry
from pytest_bdd import given, parsers, scenarios, then, when
from sqlalchemy import select

from conftest import Hub

FEATURES = Path(__file__).resolve().parents[1] / "features"
scenarios(str(FEATURES / "hub_prof.feature"))


@pytest.fixture
def people() -> dict[str, Any]:
    return {}


@given("a Wednesday raider")
def wednesday_raider(hub: Hub, people: dict[str, Any]) -> None:
    people["raider"] = hub.login(hub.user(("wed", "raider"), nick="Lilypadd"))


@given("a Wednesday officer")
def wednesday_officer(hub: Hub, people: dict[str, Any]) -> None:
    people["officer"] = hub.login(hub.user(("wed", "officer"), nick="Croak"))


@given("a Sunday officer")
def sunday_officer(hub: Hub, people: dict[str, Any]) -> None:
    people["sunday_officer"] = hub.login(hub.user(("sun", "officer"), nick="Bogwort"))


@given(parsers.parse('a Sunday raider who lists "{profession}"'))
def sunday_raider(hub: Hub, people: dict[str, Any], profession: str) -> None:
    people["sunday_raider"] = hub.login(hub.user(("sun", "raider"), nick="Ribbit"))
    assert _put_mine(hub, people["sunday_raider"], [{"profession": profession}]).status_code == 200


@given("a Wednesday trial")
def wednesday_trial(hub: Hub, people: dict[str, Any]) -> None:
    people["trial"] = hub.login(hub.user(("wed", "trial"), nick="Tadpole"))


def _put_mine(hub: Hub, sid: str, professions: list[dict[str, Any]]) -> Any:
    return hub.client.put("/api/me/professions", headers=hub.as_(sid), json={"professions": professions})


@when(parsers.parse('the raider picks "{first}" at {skill:d} as "{spec}" and "{second}"'))
def raider_picks(hub: Hub, people: dict[str, Any], first: str, skill: int, spec: str, second: str) -> None:
    body = [{"profession": first, "skill": skill, "specialisation": spec}, {"profession": second}]
    assert _put_mine(hub, people["raider"], body).status_code == 200


@when("the raider drops every profession")
def raider_drops(hub: Hub, people: dict[str, Any]) -> None:
    assert _put_mine(hub, people["raider"], []).json()["unnamed"] == ["alchemy"]


def _raider_id(hub: Hub, people: dict[str, Any]) -> int:
    members = hub.get("/api/days/wed/professions", people["officer"]).json()["members"]
    return int(next(m["member_id"] for m in members if m["name"] == "Lilypadd"))


def _name(hub: Hub, sid: str, day: str, profession: str, member_id: int, note: str | None = None) -> Any:
    path = f"/api/days/{day}/crafters/{profession}/{member_id}"
    return hub.client.put(path, headers=hub.as_(sid), json={"note": note})


@when(parsers.parse('the Wednesday officer names the raider the guild\'s "{profession}" crafter for "{note}"'))
def officer_names(hub: Hub, people: dict[str, Any], profession: str, note: str) -> None:
    r = _name(hub, people["officer"], "wed", profession, _raider_id(hub, people), note)
    assert r.status_code == 200, r.text


@when(parsers.parse('a global officer names the Sunday raider the guild\'s "{profession}" crafter'))
def global_names(hub: Hub, people: dict[str, Any], profession: str) -> None:
    chief = hub.login(hub.user(("global", "officer"), nick="Kingtoad"))
    members = hub.get("/api/admin/professions", chief).json()["members"]
    ribbit = next(m["member_id"] for m in members if m["name"] == "Ribbit")
    path = f"/api/admin/crafters/{profession}/{ribbit}"
    assert hub.client.put(path, headers=hub.as_(chief), json={}).status_code == 200


@then(parsers.parse('the Wednesday trial sees the raider as Wednesday\'s "{profession}" crafter for "{note}"'))
def trial_sees(hub: Hub, people: dict[str, Any], profession: str, note: str) -> None:
    crafters = hub.get("/api/days/wed/crafters", people["trial"]).json()
    assert [(c["member_name"], c["profession"], c["note"]) for c in crafters] == [("Lilypadd", profession, note)]


@then("the Wednesday trial does not see the Sunday raider among Wednesday's crafters")
def trial_misses_sunday(hub: Hub, people: dict[str, Any]) -> None:
    assert "Ribbit" not in {c["member_name"] for c in hub.get("/api/days/wed/crafters", people["trial"]).json()}


@then(parsers.parse('the raider picking "{profession}" at {skill:d} is refused'))
def over_cap_refused(hub: Hub, people: dict[str, Any], profession: str, skill: int) -> None:
    assert _put_mine(hub, people["raider"], [{"profession": profession, "skill": skill}]).status_code == 422


@then(parsers.parse('their professions read back as "{first}" at {skill:d} as "{spec}" and "{second}"'))
def read_back(hub: Hub, people: dict[str, Any], first: str, skill: int, spec: str, second: str) -> None:
    got = hub.get("/api/me/professions", people["raider"]).json()["professions"]
    assert got == [
        {"profession": first, "skill": skill, "specialisation": spec},
        {"profession": second, "skill": None, "specialisation": None},
    ]


@then(parsers.parse('the Wednesday officer sees the raider with "{first}" and "{second}"'))
def officer_sees(hub: Hub, people: dict[str, Any], first: str, second: str) -> None:
    members = hub.get("/api/days/wed/professions", people["officer"]).json()["members"]
    raider = next(m for m in members if m["name"] == "Lilypadd")
    assert [p["profession"] for p in raider["professions"]] == [first, second]


@then("the Sunday officer is refused Wednesday's professions")
def sunday_refused(hub: Hub, people: dict[str, Any]) -> None:
    assert hub.get("/api/days/wed/professions", people["sunday_officer"]).status_code == 403


@then(parsers.parse('the guild\'s crafters include the raider for "{profession}"'))
def crafters_include(hub: Hub, people: dict[str, Any], profession: str) -> None:
    crafters = hub.get("/api/days/wed/professions", people["officer"]).json()["crafters"]
    assert [(c["member_name"], c["profession"]) for c in crafters] == [("Lilypadd", profession)]


@then("the guild's crafters do not include the raider")
def crafters_leave_out(hub: Hub, people: dict[str, Any]) -> None:
    assert hub.get("/api/days/wed/professions", people["officer"]).json()["crafters"] == []


@then(parsers.parse("the raider's Me shows them as the guild's \"{profession}\" crafter"))
def me_shows(hub: Hub, people: dict[str, Any], profession: str) -> None:
    named = hub.get("/api/me/professions", people["raider"]).json()["crafter_for"]
    assert [n["profession"] for n in named] == [profession]


@then(parsers.parse('the Wednesday officer naming the raider for "{profession}" is refused'))
def wednesday_refused(hub: Hub, people: dict[str, Any], profession: str) -> None:
    assert _name(hub, people["officer"], "wed", profession, _raider_id(hub, people)).status_code == 422


@then(parsers.parse('the Sunday officer naming the raider for "{profession}" is refused'))
def sunday_naming_refused(hub: Hub, people: dict[str, Any], profession: str) -> None:
    raider = _raider_id(hub, people)
    assert _name(hub, people["sunday_officer"], "sun", profession, raider).status_code == 404
    assert _name(hub, people["sunday_officer"], "wed", profession, raider).status_code == 403


@then(parsers.parse('the audit log records "{action}"'))
def audit_records(hub: Hub, action: str) -> None:
    with hub.db() as db:
        assert db.scalars(select(AuditEntry).where(AuditEntry.action == action)).first() is not None
