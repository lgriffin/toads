"""The hub home: REQ-HUB-HOME-001 to 013. Thin steps over the `hub` fixture (root conftest.py)."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from hub_db import CharacterClaim, ClaimStatus
from pytest_bdd import given, parsers, scenario, then, when
from toads_api.home.service import Audience, catalogue_for

from conftest import GUILD_ID, HUB, Hub

FEATURES = Path(__file__).resolve().parents[1] / "features"
CHOSEN = ["recruiting", "raid_totals"]
WORKER = {"Authorization": "Bearer test-service-token"}  # conftest.make_settings
SERVER_TIME = ZoneInfo("Europe/Paris")  # RaidDaysConfig's default timezone


def _bind(number: int) -> Any:
    """Bind REQ-HUB-HOME-<nnn> from hub_home.feature (the id is built, not written out)."""
    req_id = f"REQ-HUB-HOME-{number:03d}"
    for line in (FEATURES / "hub_home.feature").read_text(encoding="utf-8").splitlines():
        m = re.match(rf"\s*Scenario: ({req_id} .*)$", line)
        if m:
            return scenario(str(FEATURES / "hub_home.feature"), m.group(1))
    raise LookupError(req_id)


@_bind(1)
def test_home_001() -> None:
    pass


@_bind(2)
def test_home_002() -> None:
    pass


@_bind(3)
def test_home_003() -> None:
    pass


@_bind(4)
def test_home_004() -> None:
    pass


@_bind(5)
def test_home_005() -> None:
    pass


@_bind(6)
def test_home_006() -> None:
    pass


@_bind(7)
def test_home_007() -> None:
    pass


@_bind(8)
def test_home_008() -> None:
    pass


@_bind(9)
def test_home_009() -> None:
    pass


@_bind(10)
def test_home_010() -> None:
    pass


@_bind(11)
def test_home_011() -> None:
    pass


@_bind(12)
def test_home_012() -> None:
    pass


@_bind(13)
def test_home_013() -> None:
    pass


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


def _shown(hub: Hub, sid: str) -> list[str]:
    home = hub.get("/api/me/home", sid).json()
    return [w["id"] for w in home["widgets"] if w["shown"]]


@given("a Wednesday raider signed in to the hub")
def raider_signed_in(hub: Hub, ctx: dict[str, Any]) -> None:
    ctx["user"] = hub.user(("wed", "raider"))
    ctx["sid"] = hub.login(ctx["user"])


@given("a Wednesday raider in the Toads server")
def raider_in_server(hub: Hub, ctx: dict[str, Any]) -> None:
    ctx["user"] = hub.user(("wed", "raider"))


@given("they show only the recruiting and raid totals widgets, recruiting first")
@when("they show only the recruiting and raid totals widgets, recruiting first")
def show_two(hub: Hub, ctx: dict[str, Any]) -> None:
    r = hub.client.put("/api/me/home", headers=hub.as_(ctx["sid"]), json={"shown": CHOSEN})
    assert r.status_code == 200, r.text


@then("their home shows recruiting and then raid totals")
def shows_two(hub: Hub, ctx: dict[str, Any]) -> None:
    assert _shown(hub, ctx["sid"]) == CHOSEN


@then("after signing in again their home still shows recruiting and then raid totals")
def still_shows_two(hub: Hub, ctx: dict[str, Any]) -> None:
    assert _shown(hub, hub.login(ctx["user"])) == CHOSEN


@then("their home offers no officer widgets")
def no_officer_widgets(hub: Hub, ctx: dict[str, Any]) -> None:
    home = hub.get("/api/me/home", ctx["sid"]).json()
    assert home["widgets"] and not any(w["officer_only"] for w in home["widgets"])


@then("placing the raid leader desk is refused with 403")
def desk_refused(hub: Hub, ctx: dict[str, Any]) -> None:
    r = hub.client.put("/api/me/home", headers=hub.as_(ctx["sid"]), json={"shown": ["officer_desk"]})
    assert r.status_code == 403


@when("they reset their home")
def reset(hub: Hub, ctx: dict[str, Any]) -> None:
    assert hub.delete("/api/me/home", ctx["sid"]).status_code == 200


@then("their home shows the default widgets")
def default_widgets(hub: Hub, ctx: dict[str, Any]) -> None:
    assert _shown(hub, ctx["sid"]) == [w.id for w in catalogue_for(Audience.MEMBER) if w.default_shown]


@when("they complete Discord sign-in")
def sign_in(hub: Hub, ctx: dict[str, Any]) -> None:
    ctx["response"] = hub.callback(hub.authorize(hub.start_login(), ctx["user"]))


@then("the hub sends them to their hub home")
def lands_on_hub(ctx: dict[str, Any]) -> None:
    assert ctx["response"].status_code == 303
    assert ctx["response"].headers["location"] == f"{HUB}/hub"


# --- next raid (001, 006) --------------------------------------------------------------------------


def _next_wednesday(hub: Hub, hour: int, minute: int) -> datetime:
    """The next Wednesday after the hub's clock at this server time, in UTC."""
    today = datetime.fromtimestamp(hub.now, UTC).astimezone(SERVER_TIME).date()
    day = next(today + timedelta(days=n) for n in range(1, 8) if (today + timedelta(days=n)).weekday() == 2)
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=SERVER_TIME).astimezone(UTC)


def _next_raid(hub: Hub, sid: str) -> dict[str, Any]:
    r = hub.get("/api/home/next-raid", sid)
    assert r.status_code == 200, r.text
    raid: dict[str, Any] = r.json()["raid"]
    return raid


@given(parsers.parse('an officer has posted "{name}" as a Discord scheduled event for Wednesday evening'))
def event_posted(hub: Hub, ctx: dict[str, Any], name: str) -> None:
    ctx["start"] = _next_wednesday(hub, 20, 0)
    ctx["event"] = hub.fake.add_event(4242, name, ctx["start"], interested=12)


@given("Discord has no scheduled events")
def no_events(hub: Hub) -> None:
    hub.fake.events.clear()


@then(parsers.parse('their next raid is "{name}" on Wednesday with a link to sign up in Discord'))
def next_raid_is_event(hub: Hub, ctx: dict[str, Any], name: str) -> None:
    raid = _next_raid(hub, ctx["sid"])
    assert (raid["name"], raid["source"], raid["raid_day_id"], raid["interested"]) == (name, "discord", "wed", 12)
    assert datetime.fromisoformat(raid["starts_at"]) == ctx["start"]
    assert raid["url"] == f"https://discord.com/events/{GUILD_ID}/4242"


@when(parsers.parse('the officer moves "{name}" an hour later'))
def move_event(ctx: dict[str, Any], name: str) -> None:
    assert ctx["event"]["name"] == name
    ctx["event"]["scheduled_start_time"] = (ctx["start"] + timedelta(hours=1)).isoformat()


@when("5 minutes pass")
def five_minutes(hub: Hub) -> None:
    hub.pass_time(5 * 60)


@then("their next raid starts an hour later")
def next_raid_moved(hub: Hub, ctx: dict[str, Any]) -> None:
    raid = _next_raid(hub, ctx["sid"])
    assert datetime.fromisoformat(raid["starts_at"]) == ctx["start"] + timedelta(hours=1)


@then("their next raid is the next Wednesday at the configured start time")
def next_raid_from_schedule(hub: Hub, ctx: dict[str, Any]) -> None:
    raid = _next_raid(hub, ctx["sid"])
    assert (raid["name"], raid["source"], raid["raid_day_id"], raid["url"]) == (
        "Wednesday raid",
        "schedule",
        "wed",
        None,
    )
    assert datetime.fromisoformat(raid["starts_at"]) == _next_wednesday(hub, 19, 30)


# --- your performance (007, 008) -------------------------------------------------------------------


def _member_id(hub: Hub, sid: str) -> int:
    member_id: int = hub.get("/api/session", sid).json()["member_id"]
    return member_id


def _approve(hub: Hub, member_id: int, character_id: int, name: str) -> None:
    with hub.db.begin() as db:
        db.add(
            CharacterClaim(
                character_id=character_id, member_id=member_id, character_name=name, status=ClaimStatus.APPROVED
            )
        )


def _player(name: str, value: float, median: float, role: str = "healer") -> dict[str, Any]:
    return {
        "name": name,
        "class": "Priest",
        "role": role,
        "metric": "Healing",
        "unit": "amount",
        "value": value,
        "median": median,
        "rank": 1,
        "of": 3,
        "recent": [{"date": "2026-09-23", "value": value, "median": median}],
    }


def _publish(hub: Hub, players: list[dict[str, Any]]) -> None:
    page = {
        "version": 1,
        "generated_at": "2026-09-24 08:00:00",
        "raid": {"report_id": "aBcD1234eFgH5678", "title": "Karazhan", "date": "2026-09-23"},
        "players": players,
    }
    r = hub.client.put("/api/worker/performance", headers=WORKER, json=page)
    assert r.status_code == 200, r.text


@given(parsers.parse('a Wednesday raider nicknamed "{nick}" signed in to the hub'))
def nicknamed_raider(hub: Hub, ctx: dict[str, Any], nick: str) -> None:
    ctx["user"] = hub.user(("wed", "raider"), nick=nick)
    ctx["sid"] = hub.login(ctx["user"])


@given(parsers.parse('they hold an approved claim on the healer "{name}"'))
def own_claim(hub: Hub, ctx: dict[str, Any], name: str) -> None:
    _approve(hub, _member_id(hub, ctx["sid"]), 101, name)


@given(parsers.parse('another member holds an approved claim on "{name}"'))
def other_claim(hub: Hub, name: str) -> None:
    other = hub.login(hub.user(("wed", "raider")))
    _approve(hub, _member_id(hub, other), 102, name)


@when(
    parsers.parse('the worker publishes a raid where "{name}" healed {value:d} against a healer median of {median:d}')
)
def publish_healer(hub: Hub, name: str, value: int, median: int) -> None:
    _publish(hub, [_player(name, value, median), _player("Pad", 500, median)])


@when(parsers.parse('the worker publishes a raid with "{name}" in it'))
def publish_with(hub: Hub, name: str) -> None:
    _publish(hub, [_player(name, 800, 700)])


@then(parsers.parse('their performance shows "{name}" at {value:d} healing against a median of {median:d}'))
def shows_entry(hub: Hub, ctx: dict[str, Any], name: str, value: int, median: int) -> None:
    mine = hub.get("/api/me/performance", ctx["sid"]).json()
    assert mine["matched_by"] == "claim"
    entry = mine["entry"]
    assert (entry["name"], entry["class"], entry["value"], entry["median"]) == (name, "Priest", value, median)
    assert mine["raid"]["title"] == "Karazhan"


@then("their performance shows no character")
def shows_nothing(hub: Hub, ctx: dict[str, Any]) -> None:
    mine = hub.get("/api/me/performance", ctx["sid"]).json()
    assert (mine["entry"], mine["matched_by"], mine["looked_for"]) == (None, None, [])
    assert mine["raid"]["title"] == "Karazhan"


# --- weekly healing (REQ-HUB-HOME-009, 010) --------------------------------------------------------------------------

WORKER = {"Authorization": "Bearer test-service-token"}  # conftest.make_settings


def _healing_page(series: int = 1) -> dict[str, Any]:
    """A page as the worker publishes it: wcl_app.home's healing_weekly widget (guides/charts.md)."""
    chart = {
        "version": 1,
        "id": "healing_weekly",
        "title": "Weekly healing",
        "kind": "bar",
        "subtitle": "Effective healing per raid",
        "x_label": "Week starting",
        "y_label": "Healing per raid",
        "categories": ["14 Sep", "21 Sep"],
        "series": [
            {
                "key": f"s{i}",
                "name": "Healing per raid",
                "values": [4_000_000.0, 4_400_000.0],
                "display": ["4.0M", "4.4M"],
                "emphasis": i == 0,
            }
            for i in range(series)
        ],
        "y_max": 5_000_000.0,
        "references": [
            {"key": "baseline", "label": "4-week average", "value": 4_000_000.0, "display": "4.0M"},
        ],
        "notes": ["Per raid 4.4M: up, 10.0% above its 4-week average of 4.0M."],
        "empty": "",
    }
    widget = {"id": "healing_weekly", "title": "Weekly healing", "kind": "chart", "size": "full", "chart": chart}
    return {"version": 1, "generated_at": "2026-09-28 12:00:00", "widgets": [widget]}


@when("the worker publishes the analyzer's weekly healing chart")
def publish_healing(hub: Hub, ctx: dict[str, Any]) -> None:
    ctx["response"] = hub.client.put("/api/worker/home-page", headers=WORKER, json=_healing_page())
    assert ctx["response"].status_code == 200, ctx["response"].text


@when("the worker publishes a weekly healing chart with nine series")
def publish_oversized(hub: Hub, ctx: dict[str, Any]) -> None:
    ctx["response"] = hub.client.put("/api/worker/home-page", headers=WORKER, json=_healing_page(series=9))


@then("their home shows weekly healing by default")
def healing_shown(hub: Hub, ctx: dict[str, Any]) -> None:
    assert "healing_weekly" in _shown(hub, ctx["sid"])


@then("the weekly healing chart carries the four-week average and no target")
def healing_measured(hub: Hub, ctx: dict[str, Any]) -> None:
    page = hub.get("/api/home/analyzer", ctx["sid"]).json()
    chart = next(w for w in page["widgets"] if w["id"] == "healing_weekly")["chart"]
    assert [r["key"] for r in chart["references"]] == ["baseline"]


@then("the page is refused with 422")
def refused_422(ctx: dict[str, Any]) -> None:
    assert ctx["response"].status_code == 422


@then("the hub keeps no weekly healing chart")
def no_healing(hub: Hub, ctx: dict[str, Any]) -> None:
    page = hub.get("/api/home/analyzer", ctx["sid"]).json()
    assert all(w["id"] != "healing_weekly" for w in page["widgets"])


# --- badges (REQ-HUB-HOME-011, 012) ---------------------------------------------------------------------------------

QUALITIES = ["", "uncommon", "rare", "epic", "legendary"]


def _badge(quality: str, name: str = "Loyal Toad") -> dict[str, Any]:
    """wcl_app Badge.to_dict() (guides/badges.md in lgriffin/warcraftlogs_project)."""
    tier = QUALITIES.index(quality)
    return {
        "id": "attendance",
        "name": name,
        "description": "Raids attended",
        "icon": "attendance",
        "glyph": "\N{FROG FACE}",
        "tier": tier,
        "quality": quality,
        "tier_name": quality.title(),
        "value": 40,
        "display": "40 raids",
        "stacks": 8,
        "next_at": 100,
        "next_tier": "Legendary",
        "progress": 0.0,
    }


@when(parsers.parse('the worker publishes badges where "{name}" has the {tier} {badge} badge'))
def publish_badges(hub: Hub, name: str, tier: str, badge: str) -> None:
    players = [
        {"name": name, "player_class": "Priest", "score": 3, "badges": [_badge(tier.lower(), badge)]},
        {"name": "Pad", "player_class": "Druid", "score": 0, "badges": [_badge("", badge)]},
    ]
    page = {"version": 1, "generated_at": "2026-09-28 08:00:00", "players": players}
    r = hub.client.put("/api/worker/badges", headers=WORKER, json=page)
    assert r.status_code == 200, r.text


@then(parsers.parse('their badges show "{name}" with the {tier} {badge} badge'))
def shows_badges(hub: Hub, ctx: dict[str, Any], name: str, tier: str, badge: str) -> None:
    mine = hub.get("/api/me/badges", ctx["sid"]).json()
    assert mine["entry"]["name"] == name and mine["matched_by"] == "claim"
    assert [(b["name"], b["tier_name"]) for b in mine["entry"]["badges"]] == [(badge, tier)]


@given("a Sunday officer signed in to the hub")
def officer_signed_in(hub: Hub, ctx: dict[str, Any]) -> None:
    ctx["officer"] = hub.login(hub.user(("sun", "officer")))


@when("the worker publishes the last raid's badge roster")
def publish_roster(hub: Hub) -> None:
    widget = {
        "id": "badges",
        "title": "Toads badges",
        "kind": "badges",
        "size": "half",
        "holders": [{"name": "Hopscotch", "player_class": "Rogue", "badges": [_badge("epic")], "link": None}],
    }
    page = {"version": 1, "generated_at": "2026-09-28 08:00:00", "widgets": [widget]}
    r = hub.client.put("/api/worker/home-page", headers=WORKER, json=page)
    assert r.status_code == 200, r.text


@then(parsers.parse('the officer\'s home offers the badge roster with "{name}" in it'))
def officer_sees_roster(hub: Hub, ctx: dict[str, Any], name: str) -> None:
    assert "badges" in _shown(hub, ctx["officer"])
    page = hub.get("/api/home/analyzer", ctx["officer"]).json()
    roster = next(w for w in page["widgets"] if w["id"] == "badges")
    assert [h["name"] for h in roster["holders"]] == [name]


@then("the raider receives no badge roster")
def raider_sees_no_roster(hub: Hub, ctx: dict[str, Any]) -> None:
    assert "badges" not in [w["id"] for w in hub.get("/api/me/home", ctx["sid"]).json()["widgets"]]
    assert all(w["id"] != "badges" for w in hub.get("/api/home/analyzer", ctx["sid"]).json()["widgets"])


@when("they place the flasks widget")
def place_flasks(hub: Hub, ctx: dict[str, Any]) -> None:
    r = hub.client.put("/api/me/home", headers=hub.as_(ctx["sid"]), json={"shown": ["flasks"]})
    assert r.status_code == 200, r.text


@when(parsers.parse('the worker publishes the last raid\'s flasks table with "{name}" on a flask'))
def publish_flasks(hub: Hub, name: str) -> None:
    widget = {
        "id": "flasks",
        "title": "Flasks and elixirs",
        "kind": "table",
        "size": "half",
        "subtitle": "SSC: 1 of 1 prepared",
        "columns": [
            {"key": "name", "label": "Name", "align": "left"},
            {"key": "prepared", "label": "Prepared", "align": "left"},
        ],
        "rows": [
            {"cells": {"name": name, "prepared": "Flask"}, "values": {"name": name, "prepared": "flask"}, "link": None},
        ],
    }
    page = {"version": 1, "generated_at": "2026-10-02 08:00:00", "widgets": [widget]}
    r = hub.client.put("/api/worker/home-page", headers=WORKER, json=page)
    assert r.status_code == 200, r.text


@then(parsers.parse('their home shows "{name}" prepared with a flask'))
def shows_flasks(hub: Hub, ctx: dict[str, Any], name: str) -> None:
    assert _shown(hub, ctx["sid"]) == ["flasks"]
    page = hub.get("/api/home/analyzer", ctx["sid"]).json()
    flasks = next(w for w in page["widgets"] if w["id"] == "flasks")
    assert [(r["cells"]["name"], r["values"]["prepared"]) for r in flasks["rows"]] == [(name, "flask")]

