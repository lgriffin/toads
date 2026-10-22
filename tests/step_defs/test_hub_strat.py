"""REQ-HUB-STRAT-*: raid strategy docs, pinned per raid for every night or one night, shown for each raid a night is
running on its Raid page (docs/strategy.md).

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
SNEAKY = {"raid": "naxx", "url": "https://docs.google.com/document/d/sneaky"}


@pytest.fixture
def people() -> dict[str, Any]:
    return {}


def _login(hub: Hub, people: dict[str, Any], who: str, role: tuple[str, str]) -> str:
    if who not in people:
        people[who] = hub.login(hub.user(role))
    sid: str = people[who]
    return sid


def _pin(hub: Hub, sid: str, url: str, raid: str, title: str = "", raid_day: str | None = None) -> Any:
    return hub.post("/api/admin/strategy", sid, {"raid": raid, "url": url, "title": title, "raid_day": raid_day})


def _slot(hub: Hub, people: dict[str, Any], raid: str, raid_day: str | None = None) -> dict[str, Any]:
    r = hub.get("/api/strategy", people["global"])
    assert r.status_code == 200, r.text
    slots = next(x for x in r.json()["raids"] if x["raid"]["id"] == raid)["slots"]
    found: dict[str, Any] = next(s for s in slots if s["raid_day"] == raid_day)
    return found


def _night(hub: Hub, sid: str, day: str) -> dict[str, Any]:
    r = hub.get(f"/api/days/{DAYS.get(day, day)}/strategy", sid)
    assert r.status_code == 200, r.text
    night: dict[str, Any] = r.json()
    return night


def _set(hub: Hub, sid: str, day: str, raids: list[str]) -> Any:
    return hub.put(f"/api/days/{day}/strategy", sid, {"raids": raids})


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
    assert r.json()["raid_day"] is None


@when(parsers.parse('the global officer pins "{url}" to "{raid}" as "{title}"'))
def global_pins_titled(hub: Hub, people: dict[str, Any], url: str, raid: str, title: str) -> None:
    r = _pin(hub, people["global"], url, raid, title)
    assert r.status_code == 201, r.text
    assert r.json()["title"] == title


@when(parsers.parse('the global officer pins "{url}" to "{raid}" for night "{day}"'))
def global_pins_night(hub: Hub, people: dict[str, Any], url: str, raid: str, day: str) -> None:
    r = _pin(hub, people["global"], url, raid, raid_day=day)
    assert r.status_code == 201, r.text
    assert r.json()["raid_day"] == day


@when(parsers.parse('the global officer takes down the "{raid}" pinned doc'))
def take_down(hub: Hub, people: dict[str, Any], raid: str) -> None:
    doc = _slot(hub, people, raid)["pinned"]
    assert hub.delete(f"/api/admin/strategy/{doc['id']}", people["global"]).status_code == 204
    assert hub.delete(f"/api/admin/strategy/{doc['id']}", people["global"]).status_code == 404


@when(parsers.re(r'a Wednesday officer says Wednesday is running "(?P<raid>[^"]+)"$'))
def night_officer_sets(hub: Hub, people: dict[str, Any], raid: str) -> None:
    r = _set(hub, _login(hub, people, "wed_officer", ("wed", "officer")), "wed", [raid])
    assert r.status_code == 200, r.text
    assert [x["raid"]["id"] for x in r.json()["raids"]] == [raid]


@when(parsers.parse('a Wednesday officer says Wednesday is running "{a}" then "{b}" then "{c}"'))
def night_officer_sets_three(hub: Hub, people: dict[str, Any], a: str, b: str, c: str) -> None:
    sid = _login(hub, people, "wed_officer", ("wed", "officer"))
    r = _set(hub, sid, "wed", [a, b, a, c])
    assert r.status_code == 200, r.text


@when(parsers.parse('a Wednesday officer pins "{url}" to "{raid}" through Wednesday'))
def night_officer_pins(hub: Hub, people: dict[str, Any], url: str, raid: str) -> None:
    sid = _login(hub, people, "wed_officer", ("wed", "officer"))
    r = hub.post("/api/days/wed/strategy/docs", sid, {"raid": raid, "url": url})
    assert r.status_code == 201, r.text
    assert r.json()["raid_day"] == "wed"


@when(parsers.parse('a Wednesday officer pins "{url}" to "{raid}" for every night through Wednesday'))
def night_officer_pins_every_night(hub: Hub, people: dict[str, Any], url: str, raid: str) -> None:
    sid = _login(hub, people, "wed_officer", ("wed", "officer"))
    r = hub.post("/api/days/wed/strategy/docs", sid, {"raid": raid, "url": url, "every_night": True})
    assert r.status_code == 201, r.text
    assert r.json()["raid_day"] is None


@then(parsers.parse('the "{raid}" strategy is "{title}" at "{url}"'))
def strategy_is(hub: Hub, people: dict[str, Any], raid: str, title: str, url: str) -> None:
    pinned = _slot(hub, people, raid)["pinned"]
    assert (pinned["title"], pinned["url"]) == (title, url)


@then(parsers.parse('the "{raid}" strategy for Wednesday is "{url}"'))
def strategy_for_wednesday(hub: Hub, people: dict[str, Any], raid: str, url: str) -> None:
    slot = _slot(hub, people, raid, "wed")
    assert (slot["name"], slot["pinned"]["url"]) == ("Wednesday", url)
    assert _slot(hub, people, raid)["name"] == "Every night"


@then(parsers.parse('the "{raid}" strategy lists "{url}" as replaced'))
def strategy_replaced(hub: Hub, people: dict[str, Any], raid: str, url: str) -> None:
    assert [d["url"] for d in _slot(hub, people, raid)["replaced"]] == [url]


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


@then(parsers.parse('pinning "{url}" to "{raid}" for night "{day}" is refused'))
def pin_refused_night(hub: Hub, people: dict[str, Any], url: str, raid: str, day: str) -> None:
    assert _pin(hub, people["global"], url, raid, raid_day=day).status_code == 422


@then("a Wednesday raider cannot pin a doc")
def raider_cannot_pin(hub: Hub, people: dict[str, Any]) -> None:
    sid = _login(hub, people, "wed_raider", ("wed", "raider"))
    assert _pin(hub, sid, SNEAKY["url"], "naxx").status_code == 403
    assert hub.post("/api/days/wed/strategy/docs", sid, SNEAKY).status_code == 403


@then("a Wednesday officer cannot pin a doc through Sunday")
def officer_cannot_pin_elsewhere(hub: Hub, people: dict[str, Any]) -> None:
    sid = _login(hub, people, "wed_officer", ("wed", "officer"))
    assert _pin(hub, sid, SNEAKY["url"], "naxx").status_code == 403
    assert hub.post("/api/days/sun/strategy/docs", sid, SNEAKY).status_code == 403
    doc = _slot(hub, people, "naxx")["pinned"]["id"]
    assert hub.delete(f"/api/days/sun/strategy/docs/{doc}", sid).status_code == 403


@then(parsers.parse('a {day} raider sees "{name}" with "{url}" on {day2}\'s Raid page'))
def raider_sees(hub: Hub, people: dict[str, Any], day: str, name: str, url: str, day2: str) -> None:
    sid = _login(hub, people, f"{DAYS[day]}_raider", (DAYS[day], "raider"))
    raids = _night(hub, sid, day2)["raids"]
    assert [(r["raid"]["name"], r["pinned"]["url"]) for r in raids] == [(name, url)]


@then(parsers.parse('when the global officer pins "{url}" to "{raid}" the raider sees "{seen}"'))
def repin_propagates(hub: Hub, people: dict[str, Any], url: str, raid: str, seen: str) -> None:
    global_pins(hub, people, url, raid)
    assert _night(hub, people["wed_raider"], "Wednesday")["raids"][0]["pinned"]["url"] == seen


@then("Sunday's Raid page shows no raid")
def sunday_has_none(hub: Hub, people: dict[str, Any]) -> None:
    assert _night(hub, people["global"], "Sunday") == {"raid_day": "sun", "raids": []}


@then(parsers.parse("a {day} {role} cannot change Wednesday's raids"))
def cannot_change(hub: Hub, people: dict[str, Any], day: str, role: str) -> None:
    sid = _login(hub, people, f"{DAYS[day]}_{role}", (DAYS[day], role))
    assert _set(hub, sid, "wed", ["mc"]).status_code == 403
    assert [r["raid"]["id"] for r in _night(hub, people["global"], "Wednesday")["raids"]] == ["bwl"]


@given(parsers.parse('the global officer can say Sunday is running "{raid}"'))
@then(parsers.parse('the global officer can say Sunday is running "{raid}"'))
def global_sets_sunday(hub: Hub, people: dict[str, Any], raid: str) -> None:
    r = _set(hub, people["global"], "sun", [raid])
    assert r.status_code == 200, r.text
    assert _set(hub, people["global"], "sun", ["kara"]).status_code == 422
    nights = {n["raid_day"]: n["raids"] for n in hub.get("/api/strategy", people["global"]).json()["nights"]}
    assert nights["sun"] == [raid]


@then("the global officer can clear Sunday's raids")
def global_clears_sunday(hub: Hub, people: dict[str, Any]) -> None:
    assert _set(hub, people["global"], "sun", []).json()["raids"] == []


@then(parsers.parse('when the Wednesday officer takes down the "{raid}" Wednesday doc a Wednesday raider sees "{url}"'))
def night_officer_takes_down(hub: Hub, people: dict[str, Any], raid: str, url: str) -> None:
    doc = _slot(hub, people, raid, "wed")["pinned"]["id"]
    assert hub.delete(f"/api/days/wed/strategy/docs/{doc}", people["wed_officer"]).status_code == 204
    assert hub.delete(f"/api/days/wed/strategy/docs/{doc}", people["wed_officer"]).status_code == 404
    assert _night(hub, people["wed_raider"], "Wednesday")["raids"][0]["pinned"]["url"] == url


@then(parsers.parse('Wednesday\'s Raid page shows "{a}" at "{url_a}", "{b}" at "{url_b}" and "{c}" with no doc'))
def shows_several(hub: Hub, people: dict[str, Any], a: str, url_a: str, b: str, url_b: str, c: str) -> None:
    sid = _login(hub, people, "wed_raider", ("wed", "raider"))
    raids = [(r["raid"]["id"], (r["pinned"] or {}).get("url")) for r in _night(hub, sid, "Wednesday")["raids"]]
    assert raids == [(a, url_a), (b, url_b), (c, None)]


@then(parsers.parse('the Wednesday officer cannot take down Sunday\'s "{raid}" doc'))
def cannot_take_down_sunday(hub: Hub, people: dict[str, Any], raid: str) -> None:
    doc = _slot(hub, people, raid, "sun")["pinned"]["id"]
    assert hub.delete(f"/api/days/wed/strategy/docs/{doc}", people["wed_officer"]).status_code == 404
    assert _slot(hub, people, raid, "sun")["pinned"]["id"] == doc


@then(parsers.parse('the Wednesday officer can take down the every-night "{raid}" doc'))
def take_down_every_night(hub: Hub, people: dict[str, Any], raid: str) -> None:
    doc = _slot(hub, people, raid)["pinned"]["id"]
    assert hub.delete(f"/api/days/wed/strategy/docs/{doc}", people["wed_officer"]).status_code == 204
    slots = next(x for x in hub.get("/api/strategy", people["global"]).json()["raids"] if x["raid"]["id"] == raid)
    assert [s["raid_day"] for s in slots["slots"]] == ["sun"]


def _web(path: str) -> str:
    return (WEB / path).read_text(encoding="utf-8")


@given("the Raid page and the Strategy page", target_fixture="pages")
def pages() -> dict[str, str]:
    return {
        "raid": _web("routes/raid/+page.svelte"),
        "band": _web("lib/components/NightStrategy.svelte"),
        "picker": _web("lib/components/RaidPicker.svelte"),
        "strategy": _web("routes/officers/strategy/+page.svelte"),
        "lib": _web("lib/strategy.ts"),
    }


@then("the Raid page shows the night's strategy docs")
def raid_page_shows(pages: dict[str, str]) -> None:
    assert "<NightStrategy" in pages["raid"]
    assert "/api/days/${encodeURIComponent(day)}/strategy" in pages["lib"]
    assert "{#each night.raids" in pages["band"]
    assert 'target="_blank"' in pages["band"]


@then("the Strategy page lists the raids, pins docs for every night or one night and picks each night's raids")
def strategy_page(pages: dict[str, str]) -> None:
    assert "/api/admin/strategy" in pages["lib"]
    assert "/strategy/docs" in pages["lib"]
    assert "every_night" in pages["lib"]
    assert "<RaidPicker" in pages["strategy"] and "<RaidPicker" in pages["band"]
    assert 'type="checkbox"' in pages["picker"]
