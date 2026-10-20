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


# ------------------------------------------------------------- Raid-Helper imports


@given("a Sunday raider who has never signed in to the hub")
def unsigned_sunday_raider(hub: Hub, people: dict[str, Any]) -> None:
    people["unsigned"] = hub.user(("sun", "raider"), nick="Tadpole")


@given(parsers.parse('a Sunday raider who set their own specs to "{spec}"'))
def sunday_raider_with_specs(hub: Hub, people: dict[str, Any], spec: str) -> None:
    user = hub.user(("sun", "raider"), nick="Ribbit")
    people["chooser"], people["chooser_sid"] = user, hub.login(user)
    body = {"wow_class": spec.split("-", 1)[0], "primary": spec, "secondary": None}
    assert hub.client.put("/api/me/specs", headers=hub.as_(people["chooser_sid"]), json=body).status_code == 200


def _export(users: list[Any], class_name: str, spec_name: str) -> dict[str, Any]:
    # The pink of a paladin, as Raid-Helper sends with its "Tank" pseudo-class.
    colour = {"Tank": "#F48CBA", "Priest": "#FFFFFF"}[class_name]
    slots = [
        {
            "name": f"Signup{i}",
            "userId": str(u.user_id),
            "className": class_name,
            "specName": spec_name,
            "color": colour,
        }
        | {"isConfirmed": "confirmed", "groupNumber": 1, "slotNumber": i}
        for i, u in enumerate(users, 1)
    ]
    return {"title": "Composition Tool", "slots": slots}


@when(parsers.parse('the Sunday officer imports a Raid-Helper export seating both raiders as "{cls}" "{spec}"'))
def officer_imports_both(hub: Hub, people: dict[str, Any], cls: str, spec: str) -> None:
    r = hub.post(
        "/api/days/sun/comps/raid-helper",
        people["sunday_officer"],
        _export([people["unsigned"], people["chooser"]], cls, spec),
    )
    assert r.status_code == 200, r.text


@when(parsers.parse('the Sunday officer imports a Raid-Helper export seating the raider as "{cls}" "{spec}"'))
def officer_imports(hub: Hub, people: dict[str, Any], cls: str, spec: str) -> None:
    r = hub.post("/api/days/sun/comps/raid-helper", people["sunday_officer"], _export([people["unsigned"]], cls, spec))
    assert r.status_code == 200, r.text


@when(parsers.parse('the Wednesday officer sends the Toad Bot a Sunday export seating the raider as "{cls}" "{spec}"'))
def wednesday_officer_uses_the_bot(hub: Hub, people: dict[str, Any], cls: str, spec: str) -> None:
    officer = hub.user(("wed", "officer"), nick="Croak")
    headers = {"authorization": "Bearer test-service-token", "x-toads-acting-member": str(officer.user_id)}
    body = _export([people["unsigned"]], cls, spec)
    people["last"] = hub.client.post("/api/days/sun/comps/raid-helper", headers=headers, json=body)


@when("the raider signs in")
def raider_signs_in(hub: Hub, people: dict[str, Any]) -> None:
    people["raider"] = hub.login(people["unsigned"])


@when("the raider confirms their specs")
def raider_confirms(hub: Hub, people: dict[str, Any]) -> None:
    got = hub.get("/api/me/specs", people["raider"]).json()
    body = {k: got[k] for k in ("wow_class", "primary", "secondary")}
    assert hub.client.put("/api/me/specs", headers=hub.as_(people["raider"]), json=body).status_code == 200


def _sunday_pool(hub: Hub, people: dict[str, Any]) -> list[dict[str, Any]]:
    r = hub.get("/api/days/sun/comps/pool", people["sunday_officer"])
    assert r.status_code == 200, r.text
    pool: list[dict[str, Any]] = r.json()
    return pool


@then(parsers.parse('the raider who never signed in is on Sunday\'s roster as "{spec}"'))
def unsigned_on_roster(hub: Hub, people: dict[str, Any], spec: str) -> None:
    entry = next(e for e in _sunday_pool(hub, people) if e["name"] == "Tadpole")
    assert (entry["primary"], entry["signed_in"]) == (spec, False)


@then(parsers.parse('the raider who set their own specs is still "{spec}"'))
def chooser_kept(hub: Hub, people: dict[str, Any], spec: str) -> None:
    got = hub.get("/api/me/specs", people["chooser_sid"]).json()
    assert (got["primary"], got["imported"]) == (spec, False)


@then(parsers.parse('their specs read back as "{spec}", marked as imported'))
def specs_imported(hub: Hub, people: dict[str, Any], spec: str) -> None:
    got = hub.get("/api/me/specs", people["raider"]).json()
    assert (got["primary"], got["imported"]) == (spec, True)


@then(parsers.parse('their specs read back as "{spec}", not marked as imported'))
def specs_own(hub: Hub, people: dict[str, Any], spec: str) -> None:
    got = hub.get("/api/me/specs", people["raider"]).json()
    assert (got["primary"], got["imported"]) == (spec, False)


@then(parsers.parse('their badges include "{first}" and "{second}"'))
def badges_include(hub: Hub, people: dict[str, Any], first: str, second: str) -> None:
    ids = {b["id"] for b in hub.get("/api/me/role-badges", people["raider"]).json()}
    assert {first, second} <= ids


@then("the import is refused")
def import_refused(people: dict[str, Any]) -> None:
    assert people["last"].status_code == 403, people["last"].text


@then("the raider has no specs")
def raider_has_no_specs(hub: Hub, people: dict[str, Any]) -> None:
    assert hub.get("/api/me/specs", hub.login(people["unsigned"])).json() is None
