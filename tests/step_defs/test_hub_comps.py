"""REQ-HUB-COMP-*: members' primary and secondary specs and the officers' comp builder (docs/comps.md).

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
scenarios(str(FEATURES / "hub_comp.feature"))


@pytest.fixture
def people() -> dict[str, Any]:
    return {}


@given("a Wednesday raider")
def wednesday_raider(hub: Hub, people: dict[str, Any]) -> None:
    people["raider"] = hub.login(hub.user(("wed", "raider"), nick="Lilypadd"))


@given("a Sunday raider")
def sunday_raider(hub: Hub, people: dict[str, Any]) -> None:
    people["sunday_raider"] = hub.login(hub.user(("sun", "raider"), nick="Ribbit"))


@given("a Wednesday officer")
def wednesday_officer(hub: Hub, people: dict[str, Any]) -> None:
    people["officer"] = hub.login(hub.user(("wed", "officer"), nick="Croak"))


@given("a Sunday officer")
def sunday_officer(hub: Hub, people: dict[str, Any]) -> None:
    people["sunday_officer"] = hub.login(hub.user(("sun", "officer"), nick="Bogwort"))


@given("a Wednesday raider who has never signed in to the hub")
def unsigned_raider(hub: Hub) -> None:
    hub.user(("wed", "raider"), nick="Duckweed")


def _set(hub: Hub, sid: str, primary: str, secondary: str) -> Any:
    body = {"wow_class": primary.split("-", 1)[0], "primary": primary, "secondary": secondary}
    return hub.client.put("/api/me/specs", headers=hub.as_(sid), json=body)


@when(parsers.parse('the raider sets their specs to "{primary}" and "{secondary}"'))
def raider_sets(hub: Hub, people: dict[str, Any], primary: str, secondary: str) -> None:
    assert _set(hub, people["raider"], primary, secondary).status_code == 200


@when(parsers.parse('the raider tries to set their specs to "{primary}" and "{secondary}"'))
def raider_tries(hub: Hub, people: dict[str, Any], primary: str, secondary: str) -> None:
    people["last"] = _set(hub, people["raider"], primary, secondary)


def _pool(hub: Hub, people: dict[str, Any]) -> list[dict[str, Any]]:
    r = hub.get("/api/days/wed/comps/pool", people["officer"])
    assert r.status_code == 200, r.text
    pool: list[dict[str, Any]] = r.json()
    return pool


@when(parsers.parse('the Wednesday officer locks in "{name}" seating the raider as "{spec}"'))
def officer_locks_in(hub: Hub, people: dict[str, Any], name: str, spec: str) -> None:
    raider = next(e for e in _pool(hub, people) if e["name"] == "Lilypadd")
    slots: list[object] = [None] * 10
    slots[0] = {"spec": spec, "member_id": raider["member_id"]}
    r = hub.post("/api/days/wed/comps", people["officer"], {"name": name, "size": 10, "slots": slots})
    assert r.status_code == 201, r.text


@then(parsers.parse('their specs read back as "{primary}" and "{secondary}"'))
def specs_read_back(hub: Hub, people: dict[str, Any], primary: str, secondary: str) -> None:
    got = hub.get("/api/me/specs", people["raider"]).json()
    assert (got["primary"], got["secondary"]) == (primary, secondary)


@then("the request is refused as invalid")
def refused_invalid(people: dict[str, Any]) -> None:
    assert people["last"].status_code == 422


@then(parsers.parse('the Wednesday officer\'s roster lists the Wednesday raider with "{primary}" and "{secondary}"'))
def roster_lists(hub: Hub, people: dict[str, Any], primary: str, secondary: str) -> None:
    entry = next(e for e in _pool(hub, people) if e["name"] == "Lilypadd")
    assert (entry["primary"], entry["secondary"]) == (primary, secondary)


@then("the Wednesday officer's roster lists the raider who has never signed in, marked as not signed in")
def roster_lists_unsigned(hub: Hub, people: dict[str, Any]) -> None:
    entry = next(e for e in _pool(hub, people) if e["name"] == "Duckweed")
    assert (entry["signed_in"], entry["wow_class"]) == (False, None)


@then("the Wednesday officer's roster does not list the Sunday raider")
def roster_leaves_out(hub: Hub, people: dict[str, Any]) -> None:
    assert "Ribbit" not in [e["name"] for e in _pool(hub, people)]


@then(parsers.parse('Wednesday\'s comps include "{name}" with the raider as "{spec}"'))
def comps_include(hub: Hub, people: dict[str, Any], name: str, spec: str) -> None:
    comps = hub.get("/api/days/wed/comps", people["officer"]).json()
    comp = next(c for c in comps if c["name"] == name)
    assert {"spec": spec, "member_name": "Lilypadd"}.items() <= comp["slots"][0].items()


@then(parsers.parse('the audit log records "{action}"'))
def audit_records(hub: Hub, action: str) -> None:
    with hub.db() as db:
        assert action in list(db.scalars(select(AuditEntry.action)))


@then("the raider is refused Wednesday's roster")
def raider_refused(hub: Hub, people: dict[str, Any]) -> None:
    assert hub.get("/api/days/wed/comps/pool", people["raider"]).status_code == 403


@then("the Sunday officer is refused Wednesday's roster")
def sunday_refused(hub: Hub, people: dict[str, Any]) -> None:
    assert hub.get("/api/days/wed/comps/pool", people["sunday_officer"]).status_code == 403
