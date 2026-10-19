"""REQ-HUB-RAID-*: the Logs page's raid list and raid analysis (docs/logs.md).

Thin steps over the `hub` fixture (root conftest.py): the real API wired to the fake Discord server, with the worker's
pages sent as the worker sends them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from conftest import Hub

FEATURES = Path(__file__).resolve().parents[1] / "features"
scenarios(str(FEATURES / "hub_raid.feature"))

WORKER = {"Authorization": "Bearer test-service-token"}
WEEKDAYS = {"Wednesday": 2, "Thursday": 3}
DATES = {2: "2026-10-14 19:30:00", 3: "2026-10-15 20:00:00"}


def _summary(report: str, weekday: int) -> dict[str, Any]:
    return {
        "report_id": report,
        "title": f"Raid {report}",
        "zone": "Serpentshrine Cavern",
        "raid_date": DATES[weekday],
        "weekday": weekday,
        "size": 25,
        "url": f"https://fresh.warcraftlogs.com/reports/{report}",
    }


def _page(report: str, weekday: int) -> dict[str, Any]:
    rogue = {"name": "Hopscotch", "player_class": "Rogue"}
    return {
        "version": 1,
        "summary": _summary(report, weekday),
        "duration_ms": 7_200_000,
        "composition": {"tanks": [], "healers": [], "melee": [rogue], "ranged": []},
        "melee": [{**rogue, "damage": 900_000, "active_percent": 98.0}],
        "consumable_names": ["Haste Potion"],
        "consumables": [{"name": "Hopscotch", "role": "melee", "counts": {"Haste Potion": 3}}],
        "boss_vs_trash": [{"name": "Haste Potion", "boss": 2, "trash": 1}],
        "interrupts": [{**rogue, "spell_name": "Kick", "count": 7}],
        "cancelled_casts": [{**rogue, "total_casts": 40, "cancelled_casts": 2, "cancel_rate": 5.0, "spells": []}],
        "encounters": [
            {
                "encounter_id": 623,
                "name": "Hydross the Unstable",
                "duration_ms": 300_000,
                "damage": 900_000,
                "healing": 0,
                "players": [{**rogue, "role": "melee", "damage": 900_000, "healing": 0}],
            }
        ],
    }


@pytest.fixture
def people() -> dict[str, Any]:
    return {}


@given(parsers.parse('the worker has published a Wednesday raid "{wed}" and a Thursday raid "{thu}"'))
def published(hub: Hub, wed: str, thu: str) -> None:
    raids = [(wed, WEEKDAYS["Wednesday"]), (thu, WEEKDAYS["Thursday"])]
    # Any 64-hex hash per build; the hub only compares them.
    hashes = {report: f"{i:064x}" for i, (report, _) in enumerate(raids)}
    index = {
        "version": 1,
        "generated_at": "2026-10-19 08:00:00",
        "raids": [_summary(*r) for r in raids],
        "bosses": [],
        "hashes": hashes,
    }
    assert hub.client.put("/api/worker/logs", headers=WORKER, json=index).status_code == 200
    for report, weekday in raids:
        body = {"page": _page(report, weekday), "hash": hashes[report]}
        r = hub.client.put(f"/api/worker/logs/{report}", headers=WORKER, json=body)
        assert r.status_code == 200, r.text


@given("a Wednesday raider")
def a_raider(hub: Hub, people: dict[str, Any]) -> None:
    people["raider"] = hub.login(hub.user(("wed", "raider")))


@given("a Wednesday officer")
def a_wednesday_officer(hub: Hub, people: dict[str, Any]) -> None:
    people["officer"] = hub.login(hub.user(("wed", "officer")))


@given("a global officer")
def a_global_officer(hub: Hub, people: dict[str, Any]) -> None:
    people["global"] = hub.login(hub.user(("global", "officer")))


def _open(hub: Hub, sid: str, report: str) -> dict[str, Any]:
    row = next(r for r in hub.get("/api/logs", sid).json()["raids"] if r["summary"]["report_id"] == report)
    path = f"/api/days/{row['day']}/logs/{report}" if row["day"] else f"/api/logs/{report}"
    r = hub.get(path, sid)
    assert r.status_code == 200, r.text
    view: dict[str, Any] = r.json()
    return view


@when(parsers.parse('the Wednesday officer opens "{report}"'))
def officer_opens(hub: Hub, people: dict[str, Any], report: str) -> None:
    people["opened"] = _open(hub, people["officer"], report)


@then("the raid shows its role breakdown, consumables split by boss and trash, interrupts and cancelled casts")
def full_analysis(people: dict[str, Any]) -> None:
    view = people["opened"]
    assert view["full"]
    page = view["page"]
    assert page["composition"]["melee"] == [{"name": "Hopscotch", "player_class": "Rogue"}]
    assert page["boss_vs_trash"] == [{"name": "Haste Potion", "boss": 2, "trash": 1}]
    assert page["interrupts"][0]["count"] == 7
    assert page["cancelled_casts"][0]["cancelled_casts"] == 2


@when("the raider lists the raids")
def raider_lists(hub: Hub, people: dict[str, Any]) -> None:
    people["listed"] = hub.get("/api/logs", people["raider"]).json()


@then(parsers.parse('"{wed}" is listed on weekday {wed_day:d} and "{thu}" on weekday {thu_day:d}'))
def listed_by_weekday(people: dict[str, Any], wed: str, wed_day: int, thu: str, thu_day: int) -> None:
    weekdays = {r["summary"]["report_id"]: r["summary"]["weekday"] for r in people["listed"]["raids"]}
    assert weekdays == {wed: wed_day, thu: thu_day}


@then(parsers.parse('the {who} sees "{report}" without anyone\'s numbers'))
def overview_only(hub: Hub, people: dict[str, Any], who: str, report: str) -> None:
    view = _open(hub, people["raider" if who == "raider" else "officer"], report)
    assert not view["full"]
    assert "Hopscotch" not in repr(view["page"])
    assert view["page"]["composition_counts"]["melee"] == 1
    assert view["page"]["encounters"][0]["damage"] == 900_000


@then(parsers.parse('the global officer sees "{report}" in full'))
def global_full(hub: Hub, people: dict[str, Any], report: str) -> None:
    view = _open(hub, people["global"], report)
    assert view["full"] and view["page"]["melee"][0]["name"] == "Hopscotch"
