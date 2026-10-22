"""REQ-HUB-STRAT-*: raid strategy docs, added to each raid by officers and pinned per raid night for its raiders on
the night's Raid page (docs/strategy.md).

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
ROLES = {
    "global": ("global", "officer"),
    "wed_officer": ("wed", "officer"),
    "sun_officer": ("sun", "officer"),
    "wed_raider": ("wed", "raider"),
    "sun_raider": ("sun", "raider"),
}


@pytest.fixture
def people() -> dict[str, Any]:
    return {}


def _login(hub: Hub, people: dict[str, Any], who: str) -> str:
    if who not in people:
        people[who] = hub.login(hub.user(ROLES[who]))
    sid: str = people[who]
    return sid


def _library(hub: Hub, people: dict[str, Any]) -> dict[str, Any]:
    r = hub.get("/api/strategy", _login(hub, people, "global"))
    assert r.status_code == 200, r.text
    library: dict[str, Any] = r.json()
    return library


def _docs(hub: Hub, people: dict[str, Any], raid: str) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = next(x for x in _library(hub, people)["raids"] if x["raid"]["id"] == raid)["docs"]
    return docs


def _doc_id(hub: Hub, people: dict[str, Any], url: str) -> int:
    doc_id: int = next(d["id"] for r in _library(hub, people)["raids"] for d in r["docs"] if d["url"] == url)
    return doc_id


def _night(hub: Hub, sid: str, day: str) -> dict[str, Any]:
    r = hub.get(f"/api/days/{DAYS.get(day, day)}/strategy", sid)
    assert r.status_code == 200, r.text
    night: dict[str, Any] = r.json()
    return night


def _pin(hub: Hub, sid: str, day: str, ids: list[int]) -> Any:
    return hub.put(f"/api/days/{DAYS.get(day, day)}/strategy", sid, {"docs": ids})


def _actions(hub: Hub) -> list[tuple[str, str | None]]:
    with hub.services.db() as db:
        return [(e.action, e.raid_day_id) for e in db.scalars(select(AuditEntry))]


@given("a global officer")
def a_global_officer(hub: Hub, people: dict[str, Any]) -> None:
    _login(hub, people, "global")


@given(parsers.re(r'the global officer adds "(?P<url>[^"]+)" to "(?P<raid>[^"]+)"$'))
@when(parsers.re(r'the global officer adds "(?P<url>[^"]+)" to "(?P<raid>[^"]+)"$'))
def global_adds(hub: Hub, people: dict[str, Any], url: str, raid: str) -> None:
    r = hub.post("/api/admin/strategy", people["global"], {"raid": raid, "url": url})
    assert r.status_code == 201, r.text


@when(parsers.parse('the global officer adds "{url}" to "{raid}" as "{title}"'))
def global_adds_titled(hub: Hub, people: dict[str, Any], url: str, raid: str, title: str) -> None:
    r = hub.post("/api/admin/strategy", people["global"], {"raid": raid, "url": url, "title": title})
    assert r.status_code == 201, r.text


@when(parsers.parse('a Wednesday officer adds "{url}" to "{raid}" through Wednesday'))
def night_officer_adds(hub: Hub, people: dict[str, Any], url: str, raid: str) -> None:
    r = hub.post("/api/days/wed/strategy/docs", _login(hub, people, "wed_officer"), {"raid": raid, "url": url})
    assert r.status_code == 201, r.text


@then(parsers.re(r'the "(?P<raid>[a-z0-9]+)" docs are "(?P<first>[^"]+)" then "(?P<second>[^"]+)"'))
def docs_are_two(hub: Hub, people: dict[str, Any], raid: str, first: str, second: str) -> None:
    assert [d["title"] for d in _docs(hub, people, raid)] == [first, second]


@then(parsers.re(r'the "(?P<raid>[a-z0-9]+)" docs are "(?P<title>[^"]+)"$'))
def docs_are_one(hub: Hub, people: dict[str, Any], raid: str, title: str) -> None:
    docs = _docs(hub, people, raid)
    assert [d["title"] for d in docs] == [title]
    assert docs[0]["added_by"]


@then(parsers.parse('the "{raid}" docs are empty'))
def docs_are_empty(hub: Hub, people: dict[str, Any], raid: str) -> None:
    assert _docs(hub, people, raid) == []


@then(parsers.re(r'the audit log records "(?P<action>[a-z.]+)"$'))
def audit_records(hub: Hub, action: str) -> None:
    assert (action, None) in _actions(hub)


@then(parsers.parse('the audit log records "{action}" for Wednesday'))
def audit_records_for_night(hub: Hub, action: str) -> None:
    assert (action, "wed") in _actions(hub)


@then(parsers.parse("{day}'s Raid page shows no docs"))
def night_shows_none(hub: Hub, people: dict[str, Any], day: str) -> None:
    raider = _login(hub, people, f"{DAYS[day]}_raider")
    assert _night(hub, raider, day) == {"raid_day": DAYS[day], "docs": []}


@then("every raid from MC to Naxx, and a raid to be decided, can hold a doc")
def every_raid(hub: Hub, people: dict[str, Any]) -> None:
    raids = [r["raid"]["short"] for r in _library(hub, people)["raids"]]
    assert raids == ["MC", "BWL", "ZG", "AQ20", "AQ40", "Naxx", "TBD"]


@then(parsers.parse('adding "{url}" to "{raid}" is refused'))
def adding_refused(hub: Hub, people: dict[str, Any], url: str, raid: str) -> None:
    r = hub.post("/api/admin/strategy", people["global"], {"raid": raid, "url": url})
    assert r.status_code == 422, r.text


@then("a Wednesday officer cannot add a doc through Sunday")
def wrong_night_add(hub: Hub, people: dict[str, Any]) -> None:
    sid = _login(hub, people, "wed_officer")
    assert hub.post("/api/days/sun/strategy/docs", sid, SNEAKY).status_code == 403
    assert hub.post("/api/admin/strategy", sid, SNEAKY).status_code == 403


@then("a Wednesday raider cannot add a doc")
def raider_add(hub: Hub, people: dict[str, Any]) -> None:
    assert hub.post("/api/days/wed/strategy/docs", _login(hub, people, "wed_raider"), SNEAKY).status_code == 403


@given(parsers.re(r'a Wednesday officer pins "(?P<url>[^"]+)" for Wednesday$'))
@when(parsers.re(r'a Wednesday officer pins "(?P<url>[^"]+)" for Wednesday$'))
def night_officer_pins(hub: Hub, people: dict[str, Any], url: str) -> None:
    r = _pin(hub, _login(hub, people, "wed_officer"), "wed", [_doc_id(hub, people, url)])
    assert r.status_code == 200, r.text


@when(parsers.parse('a Wednesday officer pins "{first}" then "{second}" for Wednesday'))
def night_officer_pins_two(hub: Hub, people: dict[str, Any], first: str, second: str) -> None:
    ids = [_doc_id(hub, people, first), _doc_id(hub, people, second)]
    r = _pin(hub, _login(hub, people, "wed_officer"), "wed", ids)
    assert r.status_code == 200, r.text


@then(parsers.parse('a Wednesday raider sees "{a}" at "{a_url}" then "{b}" at "{b_url}"'))
def raider_sees_two(hub: Hub, people: dict[str, Any], a: str, a_url: str, b: str, b_url: str) -> None:
    night = _night(hub, _login(hub, people, "wed_raider"), "wed")
    assert [(d["raid"]["id"], d["doc"]["url"]) for d in night["docs"]] == [(a, a_url), (b, b_url)]


@then(parsers.parse('the "{raid}" doc lists Wednesday as pinning it'))
def doc_lists_night(hub: Hub, people: dict[str, Any], raid: str) -> None:
    assert [d["nights"] for d in _docs(hub, people, raid)] == [["wed"]]
    wed = next(n for n in _library(hub, people)["nights"] if n["raid_day"] == "wed")
    assert len(wed["docs"]) == 2 and wed["name"] == "Wednesday"


@then("a Sunday officer cannot pin Wednesday's docs")
def other_night_pins(hub: Hub, people: dict[str, Any]) -> None:
    assert _pin(hub, _login(hub, people, "sun_officer"), "wed", []).status_code == 403


@then("a Wednesday raider cannot pin Wednesday's docs")
def raider_pins(hub: Hub, people: dict[str, Any]) -> None:
    assert _pin(hub, _login(hub, people, "wed_raider"), "wed", []).status_code == 403
    assert len(_night(hub, people["wed_raider"], "wed")["docs"]) == 1


@then("pinning a doc that is not listed for Wednesday is refused")
def pin_unknown(hub: Hub, people: dict[str, Any]) -> None:
    r = _pin(hub, _login(hub, people, "wed_officer"), "wed", [999])
    assert r.status_code == 422, r.text


@given(parsers.parse('the global officer can pin "{url}" for Sunday'))
@then(parsers.parse('the global officer can pin "{url}" for Sunday'))
def global_pins_sunday(hub: Hub, people: dict[str, Any], url: str) -> None:
    r = _pin(hub, people["global"], "sun", [_doc_id(hub, people, url)])
    assert r.status_code == 200, r.text
    assert [d["doc"]["url"] for d in r.json()["docs"]] == [url]


@then("the global officer can clear Sunday's docs")
def global_clears(hub: Hub, people: dict[str, Any]) -> None:
    assert _pin(hub, people["global"], "sun", []).json()["docs"] == []


@then(parsers.parse('a Sunday officer can pin "{url}" for Sunday'))
def sunday_officer_pins(hub: Hub, people: dict[str, Any], url: str) -> None:
    r = _pin(hub, _login(hub, people, "sun_officer"), "sun", [_doc_id(hub, people, url)])
    assert r.status_code == 200, r.text


@when(parsers.parse('the global officer takes down "{url}"'))
def global_takes_down(hub: Hub, people: dict[str, Any], url: str) -> None:
    assert hub.delete(f"/api/admin/strategy/{_doc_id(hub, people, url)}", people["global"]).status_code == 204


@then(parsers.parse('the Wednesday officer cannot take down "{url}"'))
def night_cannot_take_down(hub: Hub, people: dict[str, Any], url: str) -> None:
    r = hub.delete(f"/api/days/wed/strategy/docs/{_doc_id(hub, people, url)}", people["wed_officer"])
    assert r.status_code == 409, r.text


@then(parsers.parse('the Wednesday officer can take down "{url}"'))
def night_can_take_down(hub: Hub, people: dict[str, Any], url: str) -> None:
    r = hub.delete(f"/api/days/wed/strategy/docs/{_doc_id(hub, people, url)}", people["wed_officer"])
    assert r.status_code == 204, r.text
    assert _night(hub, people["wed_officer"], "wed")["docs"] == []


def _web(path: str) -> str:
    return (WEB / path).read_text(encoding="utf-8")


@given("the Raid page and the Strategy page", target_fixture="pages")
def pages() -> dict[str, str]:
    return {
        "raid": _web("routes/raid/+page.svelte"),
        "band": _web("lib/components/NightStrategy.svelte"),
        "picker": _web("lib/components/DocPicker.svelte"),
        "strategy": _web("routes/officers/strategy/+page.svelte"),
        "lib": _web("lib/strategy.ts"),
    }


@then("the Raid page shows the night's pinned docs and lets its officers pin them")
def raid_page_shows(pages: dict[str, str]) -> None:
    assert "<NightStrategy" in pages["raid"]
    assert "/api/days/${encodeURIComponent(day)}/strategy" in pages["lib"]
    assert "{#each night.docs" in pages["band"]
    assert 'target="_blank"' in pages["band"]
    assert "<DocPicker" in pages["band"]
    assert 'type="checkbox"' in pages["picker"]


@then("the Strategy page adds docs to each raid and pins each night's docs")
def strategy_page(pages: dict[str, str]) -> None:
    assert "/api/admin/strategy" in pages["lib"]
    assert "/strategy/docs" in pages["lib"]
    assert "Add the doc" in pages["strategy"]
    assert "<DocPicker" in pages["strategy"]
