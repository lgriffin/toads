"""REQ-HUB-LOOT-*: officers' loot priority, one list per raid night (docs/loot.md).

Thin steps over the `hub` fixture (root conftest.py): the real API wired to the fake Discord server, and the item
catalogue that ships with the API.
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
scenarios(str(FEATURES / "hub_loot.feature"))

WEB = Path(__file__).resolve().parents[2] / "apps" / "web" / "src"


@pytest.fixture
def people() -> dict[str, Any]:
    return {"ids": {}}


def _loot(hub: Hub, sid: str, day: str = "wed") -> dict[str, Any]:
    r = hub.get(f"/api/days/{day}/loot", sid)
    assert r.status_code == 200, r.text
    loot: dict[str, Any] = r.json()
    return loot


def _ids(people: dict[str, Any], *names: str) -> list[int]:
    return [people["ids"][n] for n in names]


def _add(hub: Hub, people: dict[str, Any], item_id: int) -> Any:
    return hub.post("/api/days/wed/loot", people["officer"], {"item_id": item_id})


def _line(hub: Hub, people: dict[str, Any], *names: str) -> Any:
    return hub.put(
        f"/api/days/wed/loot/{people['entry']}/line", people["officer"], {"member_ids": _ids(people, *names)}
    )


def _mark(hub: Hub, people: dict[str, Any], name: str, received: bool) -> None:
    member = people["ids"][name]
    r = hub.put(
        f"/api/days/wed/loot/{people['entry']}/line/{member}/received", people["officer"], {"received": received}
    )
    assert r.status_code == 200, r.text


def _in_line(entry: dict[str, Any]) -> list[str]:
    return [r["name"] for r in entry["recipients"]]


def _next_up(hub: Hub, people: dict[str, Any]) -> str:
    entry = _loot(hub, people["officer"])["items"][0]
    return str(next(r["name"] for r in entry["recipients"] if r["next_up"]))


def _raider(hub: Hub, people: dict[str, Any], day: str, nick: str) -> None:
    sid = hub.login(hub.user((day, "raider"), nick=nick))
    people["ids"][nick] = int(hub.get("/api/session", sid).json()["member_id"])
    people.setdefault("raider_sid", {})[day] = sid


@given("a Wednesday officer")
def a_day_officer(hub: Hub, people: dict[str, Any]) -> None:
    people["officer"] = hub.login(hub.user(("wed", "officer")))


@given(parsers.parse('Wednesday raiders "{a}", "{b}" and "{c}"'))
def wednesday_raiders(hub: Hub, people: dict[str, Any], a: str, b: str, c: str) -> None:
    for nick in (a, b, c):
        _raider(hub, people, "wed", nick)


@given(parsers.parse('a Sunday raider "{nick}"'))
def sunday_raider(hub: Hub, people: dict[str, Any], nick: str) -> None:
    _raider(hub, people, "sun", nick)


@given(parsers.parse('item {item_id:d} on Wednesday\'s loot list with "{a}", "{b}" and "{c}" in line'))
def item_with_line(hub: Hub, people: dict[str, Any], item_id: int, a: str, b: str, c: str) -> None:
    officer_adds(hub, people, item_id)
    puts_in_line(hub, people, a, b, c)


@when(parsers.parse('the Wednesday officer searches the items for "{query}"'))
def officer_searches(hub: Hub, people: dict[str, Any], query: str) -> None:
    r = hub.get(f"/api/days/wed/loot/items?q={query}", people["officer"])
    assert r.status_code == 200, r.text
    people["found"] = r.json()


@when(parsers.parse("the Wednesday officer adds item {item_id:d} to Wednesday's loot list"))
def officer_adds(hub: Hub, people: dict[str, Any], item_id: int) -> None:
    r = _add(hub, people, item_id)
    assert r.status_code == 201, r.text
    people["entry"] = r.json()["id"]


@when(parsers.parse('puts "{a}", "{b}" and "{c}" in line for it'))
def puts_in_line(hub: Hub, people: dict[str, Any], a: str, b: str, c: str) -> None:
    r = _line(hub, people, a, b, c)
    assert r.status_code == 200, r.text


@when(parsers.parse('the Wednesday officer puts "{nick}" in line for it'))
def puts_outsider_in_line(hub: Hub, people: dict[str, Any], nick: str) -> None:
    people["last"] = _line(hub, people, "Lilypad", "Hopscotch", "Toadstool", nick)


@when(parsers.parse('the Wednesday officer marks "{nick}" received'))
def marks_received(hub: Hub, people: dict[str, Any], nick: str) -> None:
    _mark(hub, people, nick, True)


@when("a Sunday officer asks for Wednesday's loot list")
def sunday_officer_asks(hub: Hub, people: dict[str, Any]) -> None:
    people["last"] = hub.get("/api/days/wed/loot", hub.login(hub.user(("sun", "officer"))))


@then(parsers.parse('the first item offered is "{name}" with id {item_id:d}'))
def first_offered(people: dict[str, Any], name: str, item_id: int) -> None:
    first = people["found"][0]
    assert (first["name"], first["id"], first["quality"]) == (name, item_id, 5)


@then("a search of one letter is refused")
def one_letter_refused(hub: Hub, people: dict[str, Any]) -> None:
    assert hub.get("/api/days/wed/loot/items?q=t", people["officer"]).status_code == 422


@then(parsers.parse('another Wednesday officer sees "{name}" with "{a}", "{b}" and "{c}" in line'))
def another_sees(hub: Hub, name: str, a: str, b: str, c: str) -> None:
    loot = _loot(hub, hub.login(hub.user(("wed", "officer"))))
    [entry] = loot["items"]
    assert (entry["item_name"], entry["item_id"], entry["quality"]) == (name, 19019, 5)
    assert _in_line(entry) == [a, b, c]
    assert [r["rank"] for r in entry["recipients"]] == [1, 2, 3]
    assert {a, b, c} <= {m["name"] for m in loot["roster"]}
    assert loot["catalogue"].startswith("LibItemDB")


@then(parsers.parse('"{nick}" is next up'))
def is_next_up(hub: Hub, people: dict[str, Any], nick: str) -> None:
    assert _next_up(hub, people) == nick


@then(parsers.parse('the audit log records "{first}" and "{second}" for Wednesday'))
def audit_records(hub: Hub, first: str, second: str) -> None:
    with hub.db() as db:
        entries = db.scalars(select(AuditEntry).where(AuditEntry.action.in_([first, second]))).all()
    assert sorted((e.action, e.raid_day_id) for e in entries) == [(first, "wed"), (second, "wed")]


@then(parsers.parse('"{nick}" has received it'))
def has_received(hub: Hub, people: dict[str, Any], nick: str) -> None:
    entry = _loot(hub, people["officer"])["items"][0]
    assert next(r for r in entry["recipients"] if r["name"] == nick)["received_at"] is not None


@then(parsers.parse('after "{nick}" is unmarked "{again}" is next up again'))
def unmarked(hub: Hub, people: dict[str, Any], nick: str, again: str) -> None:
    _mark(hub, people, nick, False)
    assert _next_up(hub, people) == again


@then("the request is refused as unprocessable")
def unprocessable(people: dict[str, Any]) -> None:
    assert people["last"].status_code == 422, people["last"].text


@then(parsers.parse("adding item {item_id:d} is refused as unprocessable"))
def unknown_item(hub: Hub, people: dict[str, Any], item_id: int) -> None:
    assert _add(hub, people, item_id).status_code == 422


@then(parsers.parse("adding item {item_id:d} again is refused as a conflict"))
def duplicate_item(hub: Hub, people: dict[str, Any], item_id: int) -> None:
    assert _add(hub, people, item_id).status_code == 409


@then(parsers.parse('Wednesday\'s loot list still holds one item with "{a}", "{b}" and "{c}" in line'))
def still_holds(hub: Hub, people: dict[str, Any], a: str, b: str, c: str) -> None:
    [entry] = _loot(hub, people["officer"])["items"]
    assert _in_line(entry) == [a, b, c]
    assert all(r["received_at"] is None for r in entry["recipients"])


@then("the request is refused as forbidden")
def refused(people: dict[str, Any]) -> None:
    assert people["last"].status_code == 403, people["last"].text


@then("a Wednesday raider cannot see or change Wednesday's loot list")
def raider_refused(hub: Hub, people: dict[str, Any]) -> None:
    sid = people["raider_sid"]["wed"]
    entry, member = people["entry"], people["ids"]["Lilypad"]
    assert hub.get("/api/days/wed/loot", sid).status_code == 403
    assert hub.get("/api/days/wed/loot/items?q=thunder", sid).status_code == 403
    assert hub.post("/api/days/wed/loot", sid, {"item_id": 19019}).status_code == 403
    assert hub.put(f"/api/days/wed/loot/{entry}/line", sid, {"member_ids": [member]}).status_code == 403
    received = f"/api/days/wed/loot/{entry}/line/{member}/received"
    assert hub.put(received, sid, {"received": True}).status_code == 403
    assert hub.delete(f"/api/days/wed/loot/{entry}", sid).status_code == 403


@then("a global officer sees Wednesday's loot list")
def global_sees(hub: Hub) -> None:
    assert len(_loot(hub, hub.login(hub.user(("global", "officer"))))["items"]) == 1


@given("the night's officer section", target_fixture="night_page")
def night_page() -> str:
    return (WEB / "routes/officers/nights/[day]/+page.svelte").read_text(encoding="utf-8")


@then("it holds the night's loot list")
def holds_loot(night_page: str) -> None:
    shown = night_page[night_page.index("{:else if !runs}") :].split("{:else}", 1)[1]
    assert "<LootPriority backend={loot} {day}" in shown


@then("each loot item links to Wowhead by its item id")
def links_wowhead() -> None:
    lib = (WEB / "lib/loot.ts").read_text(encoding="utf-8")
    assert "https://www.wowhead.com/classic/item=${" in lib
    assert "wowheadItem(" in (WEB / "lib/components/LootPriority.svelte").read_text(encoding="utf-8")
