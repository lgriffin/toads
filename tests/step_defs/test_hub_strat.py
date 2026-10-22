"""REQ-HUB-STRAT-*: raid strategy docs, one pinned Google Doc per raid, shown on each night's Raid page
(docs/strategy.md).

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
WEB = Path(__file__).resolve().parents[2] / "apps" / "web" / "src"
scenarios(str(FEATURES / "hub_strat.feature"))

DAYS = {"Wednesday": "wed", "Sunday": "sun"}


@pytest.fixture
def people() -> dict[str, Any]:
    return {}


def _login(hub: Hub, people: dict[str, Any], who: str, role: tuple[str, str]) -> str:
    if who not in people:
        people[who] = hub.login(hub.user(role))
    sid: str = people[who]
    return sid


def _pin(hub: Hub, sid: str, url: str, raid: str, title: str = "") -> Any:
    return hub.post("/api/admin/strategy", sid, {"raid": raid, "url": url, "title": title})


def _raid(hub: Hub, people: dict[str, Any], raid: str) -> dict[str, Any]:
    r = hub.get("/api/strategy", people["global"])
    assert r.status_code == 200, r.text
    found: dict[str, Any] = next(x for x in r.json()["raids"] if x["raid"]["id"] == raid)
    return found


def _night(hub: Hub, sid: str, day: str) -> dict[str, Any]:
    r = hub.get(f"/api/days/{DAYS[day]}/strategy", sid)
    assert r.status_code == 200, r.text
    night: dict[str, Any] = r.json()
    return night


def _actions(hub: Hub) -> list[tuple[str, str | None]]:
    with hub.services.db() as db:
        return [(e.action, e.raid_day_id) for e in db.scalars(select(AuditEntry))]


@given("a global officer")
def a_global_officer(hub: Hub, people: dict[str, Any]) -> None:
    _login(hub, people, "global", ("global", "officer"))


@given(parsers.parse('the global officer pins "{url}" to "{raid}"'))
@when(parsers.parse('the global officer pins "{url}" to "{raid}"'))
def global_pins(hub: Hub, people: dict[str, Any], url: str, raid: str) -> None:
    r = _pin(hub, people["global"], url, raid)
    assert r.status_code == 201, r.text


@when(parsers.parse('the global officer pins "{url}" to "{raid}" as "{title}"'))
def global_pins_titled(hub: Hub, people: dict[str, Any], url: str, raid: str, title: str) -> None:
    r = _pin(hub, people["global"], url, raid, title)
    assert r.status_code == 201, r.text
    assert r.json()["title"] == title


@when(parsers.parse('the global officer takes down the "{raid}" pinned doc'))
def take_down(hub: Hub, people: dict[str, Any], raid: str) -> None:
    doc = _raid(hub, people, raid)["pinned"]
    r = hub.delete(f"/api/admin/strategy/{doc['id']}", people["global"])
    assert r.status_code == 204, r.text
    assert hub.delete(f"/api/admin/strategy/{doc['id']}", people["global"]).status_code == 404


@when(parsers.parse('a Wednesday officer says Wednesday is running "{raid}"'))
def night_officer_sets(hub: Hub, people: dict[str, Any], raid: str) -> None:
    sid = _login(hub, people, "wed_officer", ("wed", "officer"))
    r = hub.put("/api/days/wed/strategy", sid, {"raid": raid})
    assert r.status_code == 200, r.text
    assert r.json()["raid"]["id"] == raid


@then(parsers.parse('the "{raid}" strategy is "{title}" at "{url}"'))
def strategy_is(hub: Hub, people: dict[str, Any], raid: str, title: str, url: str) -> None:
    pinned = _raid(hub, people, raid)["pinned"]
    assert (pinned["title"], pinned["url"]) == (title, url)


@then(parsers.parse('the "{raid}" strategy lists "{url}" as replaced'))
def strategy_replaced(hub: Hub, people: dict[str, Any], raid: str, url: str) -> None:
    assert [d["url"] for d in _raid(hub, people, raid)["replaced"]] == [url]


@then(parsers.parse('the audit log records "{action}"'))
def audit_records(hub: Hub, action: str) -> None:
    assert (action, None) in _actions(hub)


@then(parsers.parse('the audit log records "{action}" for Wednesday'))
def audit_records_day(hub: Hub, action: str) -> None:
    assert (action, "wed") in _actions(hub)


@then("every raid from MC to Naxx, and a raid to be decided, can hold a doc")
def every_raid(hub: Hub, people: dict[str, Any]) -> None:
    raids = [x["raid"]["short"] for x in hub.get("/api/strategy", people["global"]).json()["raids"]]
    assert raids == ["MC", "BWL", "ZG", "AQ20", "AQ40", "Naxx", "TBD"]


@then(parsers.parse('pinning "{url}" to "{raid}" is refused'))
def pin_refused(hub: Hub, people: dict[str, Any], url: str, raid: str) -> None:
    assert _pin(hub, people["global"], url, raid).status_code == 422


@then("a Wednesday raider cannot pin a doc")
def raider_cannot_pin(hub: Hub, people: dict[str, Any]) -> None:
    sid = _login(hub, people, "wed_raider", ("wed", "raider"))
    body = {"raid": "naxx", "url": "https://docs.google.com/document/d/sneaky"}
    assert _pin(hub, sid, body["url"], "naxx").status_code == 403
    assert hub.post("/api/days/wed/strategy/docs", sid, body).status_code == 403


@then("a Wednesday officer cannot pin a doc through Sunday")
def officer_cannot_pin_elsewhere(hub: Hub, people: dict[str, Any]) -> None:
    sid = _login(hub, people, "wed_officer", ("wed", "officer"))
    body = {"raid": "naxx", "url": "https://docs.google.com/document/d/sneaky"}
    assert _pin(hub, sid, body["url"], "naxx").status_code == 403
    assert hub.post("/api/days/sun/strategy/docs", sid, body).status_code == 403
    doc = _raid(hub, people, "naxx")["pinned"]["id"]
    assert hub.delete(f"/api/days/sun/strategy/docs/{doc}", sid).status_code == 403


@when(parsers.parse('a Wednesday officer pins "{url}" to "{raid}" through Wednesday'))
def night_officer_pins(hub: Hub, people: dict[str, Any], url: str, raid: str) -> None:
    sid = _login(hub, people, "wed_officer", ("wed", "officer"))
    r = hub.post("/api/days/wed/strategy/docs", sid, {"raid": raid, "url": url})
    assert r.status_code == 201, r.text


@then(
    parsers.parse(
        'when the Wednesday officer takes down the "{raid}" pinned doc through Wednesday a Sunday raider sees "{url}"'
    )
)
def night_officer_takes_down(hub: Hub, people: dict[str, Any], raid: str, url: str) -> None:
    doc = _raid(hub, people, raid)["pinned"]["id"]
    assert hub.delete(f"/api/days/wed/strategy/docs/{doc}", people["wed_officer"]).status_code == 204
    assert hub.delete(f"/api/days/wed/strategy/docs/{doc}", people["wed_officer"]).status_code == 404
    assert _night(hub, people["sun_raider"], "Sunday")["pinned"]["url"] == url


@then(parsers.parse('a {day} raider sees "{name}" with "{url}" on {day2}\'s Raid page'))
def raider_sees(hub: Hub, people: dict[str, Any], day: str, name: str, url: str, day2: str) -> None:
    sid = _login(hub, people, f"{DAYS[day]}_raider", (DAYS[day], "raider"))
    night = _night(hub, sid, day2)
    assert (night["raid"]["name"], night["pinned"]["url"]) == (name, url)


@then(parsers.parse('when the global officer pins "{url}" to "{raid}" the raider sees "{seen}"'))
def repin_propagates(hub: Hub, people: dict[str, Any], url: str, raid: str, seen: str) -> None:
    global_pins(hub, people, url, raid)
    assert _night(hub, people["wed_raider"], "Wednesday")["pinned"]["url"] == seen


@then("Sunday's Raid page shows no raid")
def sunday_has_none(hub: Hub, people: dict[str, Any]) -> None:
    assert _night(hub, people["global"], "Sunday") == {"raid_day": "sun", "raid": None, "pinned": None}


@then(parsers.parse("a {day} {role} cannot change Wednesday's raid"))
def cannot_change(hub: Hub, people: dict[str, Any], day: str, role: str) -> None:
    sid = _login(hub, people, f"{DAYS[day]}_{role}", (DAYS[day], role))
    assert hub.put("/api/days/wed/strategy", sid, {"raid": "mc"}).status_code == 403
    assert _night(hub, people["global"], "Wednesday")["raid"]["id"] == "bwl"


@when(parsers.parse('the global officer can say Sunday is running "{raid}"'))
@then(parsers.parse('the global officer can say Sunday is running "{raid}"'))
def global_sets_sunday(hub: Hub, people: dict[str, Any], raid: str) -> None:
    r = hub.put("/api/days/sun/strategy", people["global"], {"raid": raid})
    assert r.status_code == 200, r.text
    assert hub.put("/api/days/sun/strategy", people["global"], {"raid": "kara"}).status_code == 422
    nights = {n["raid_day"]: n["raid"] for n in hub.get("/api/strategy", people["global"]).json()["nights"]}
    assert nights["sun"] == raid


@then("the global officer can clear Sunday's raid")
def global_clears_sunday(hub: Hub, people: dict[str, Any]) -> None:
    assert hub.put("/api/days/sun/strategy", people["global"], {"raid": None}).json()["raid"] is None


def _web(path: str) -> str:
    return (WEB / path).read_text(encoding="utf-8")


@given("the Raid page and the Strategy page", target_fixture="pages")
def pages() -> dict[str, str]:
    return {
        "raid": _web("routes/raid/+page.svelte"),
        "band": _web("lib/components/NightStrategy.svelte"),
        "strategy": _web("routes/officers/strategy/+page.svelte"),
        "lib": _web("lib/strategy.ts"),
    }


@then("the Raid page shows the night's strategy doc")
def raid_page_shows(pages: dict[str, str]) -> None:
    assert "<NightStrategy" in pages["raid"]
    assert "/api/days/${encodeURIComponent(day)}/strategy" in pages["lib"]
    assert 'target="_blank"' in pages["band"]


@then("the Strategy page lists the raids, pins docs for every officer and picks each night's raid")
def strategy_page(pages: dict[str, str]) -> None:
    assert "/api/admin/strategy" in pages["lib"]
    assert "/strategy/docs" in pages["lib"]
    assert "pinDay" in pages["strategy"]
    assert "officerDays" in pages["strategy"]
