"""REQ-HUB-ME-*: a member's own raids on Me, from the analyzer's character pages (docs/me.md).

Thin steps over the `hub` fixture (root conftest.py): the real API wired to the fake Discord server, with the worker's
pages sent as the worker sends them. The trend threshold lives in the web app, so its steps read the source.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
from hub_db import CharacterClaim, ClaimStatus
from pytest_bdd import given, parsers, scenarios, then, when

from conftest import Hub

FEATURES = Path(__file__).resolve().parents[1] / "features"
scenarios(str(FEATURES / "hub_me.feature"))

WEB = Path(__file__).resolve().parents[2] / "apps" / "web" / "src" / "lib"
WORKER = {"Authorization": "Bearer test-service-token"}
GENERATED = "2026-10-16 08:00:00"


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


def _member_id(hub: Hub, sid: str) -> int:
    member_id: int = hub.get("/api/session", sid).json()["member_id"]
    return member_id


def _raid(value: float, median: float) -> dict[str, Any]:
    return {
        "report_id": "pondWed1014",
        "title": "Serpentshrine Cavern",
        "zone": "Serpentshrine Cavern",
        "raid_date": "2026-10-14 20:00:00",
        "weekday": 2,
        "role": "healer",
        "metric": "Healing",
        "value": value,
        "display": f"{value / 1_000_000:.1f}M",
        "median": median,
        "median_display": f"{median / 1_000_000:.1f}M",
        "rank": 2,
        "of": 6,
        "percent": 18.2,
    }


def _page(name: str, value: float = 1_000_000, median: float = 900_000) -> dict[str, Any]:
    """wcl_app CharacterPage.to_dict() (guides/character_pages.md in lgriffin/warcraftlogs_project)."""
    return {
        "version": 1,
        "name": name,
        "player_class": "Priest",
        "raids": 1,
        "first_raid": "2026-10-14 20:00:00",
        "last_raid": "2026-10-14 20:00:00",
        "role_counts": {"healer": 1},
        "recent": [_raid(value, median)],
        "metrics": [],
        "casts": [],
        "consumables": [],
        "bests": [],
        "charts": [],
    }


def _publish(hub: Hub, *pages: dict[str, Any]) -> None:
    body = {"version": 1, "generated_at": GENERATED, "pages": list(pages)}
    r = hub.client.put("/api/worker/character-pages", headers=WORKER, json=body)
    assert r.status_code == 200, r.text


@given("a Wednesday raider signed in to the hub")
def raider_signed_in(hub: Hub, ctx: dict[str, Any]) -> None:
    ctx["sid"] = hub.login(hub.user(("wed", "raider")))


@given(parsers.parse('they hold an approved claim on "{name}"'))
def own_claim(hub: Hub, ctx: dict[str, Any], name: str) -> None:
    ctx["claims"] = ctx.get("claims", 100) + 1
    with hub.db.begin() as db:
        db.add(
            CharacterClaim(
                character_id=ctx["claims"],
                member_id=_member_id(hub, ctx["sid"]),
                character_name=name,
                status=ClaimStatus.APPROVED,
            )
        )


@when(
    parsers.parse(
        'the worker publishes a character page where "{name}" healed {value:d} against a healer median of {median:d}'
    )
)
def publish_one(hub: Hub, name: str, value: int, median: int) -> None:
    _publish(hub, _page(name, value, median))


@when(parsers.parse('the worker publishes character pages for "{first}", "{second}" and "{third}"'))
def publish_three(hub: Hub, first: str, second: str, third: str) -> None:
    _publish(hub, _page(first), _page(second), _page(third))


@then(parsers.parse('their raids show "{name}" healing {value:d} against the healer median of {median:d}'))
def shows_raid(hub: Hub, ctx: dict[str, Any], name: str, value: int, median: int) -> None:
    mine = hub.get("/api/me/character-page", ctx["sid"]).json()
    assert mine["page"]["name"] == name
    (raid,) = mine["page"]["recent"]
    assert (raid["role"], raid["metric"], raid["value"], raid["median"]) == ("healer", "Healing", value, median)


@then(parsers.parse('a member without a claim on "{name}" sees no raids'))
def others_see_nothing(hub: Hub, name: str) -> None:
    other = hub.login(hub.user(("wed", "raider")))
    mine = hub.get(f"/api/me/character-page?name={name}", other).json()
    assert mine["generated_at"] == GENERATED
    assert (mine["page"], mine["characters"]) == (None, [])


@then(parsers.parse('they can switch between the raids of "{first}" and "{second}"'))
def can_switch(hub: Hub, ctx: dict[str, Any], first: str, second: str) -> None:
    mine = hub.get("/api/me/character-page", ctx["sid"]).json()
    assert mine["characters"] == [first, second]
    assert mine["page"]["name"] == first
    assert hub.get(f"/api/me/character-page?name={second.lower()}", ctx["sid"]).json()["page"]["name"] == second


@then(parsers.parse('asking for "{other}" shows "{name}" instead'))
def no_other_page(hub: Hub, ctx: dict[str, Any], other: str, name: str) -> None:
    mine = hub.get(f"/api/me/character-page?name={other}", ctx["sid"]).json()
    assert mine["page"]["name"] == name


@given("the raids card on Me")
def raids_card(ctx: dict[str, Any]) -> None:
    ctx["lib"] = (WEB / "characters.ts").read_text(encoding="utf-8")
    ctx["card"] = (WEB / "components" / "CharacterCard.svelte").read_text(encoding="utf-8")


@then(parsers.parse("it draws trend lines only from {n:d} guild raids"))
def trend_threshold(ctx: dict[str, Any], n: int) -> None:
    assert re.search(rf"export const MIN_TREND_RAIDS = {n};", ctx["lib"])
    assert "page.raids >= MIN_TREND_RAIDS" in ctx["lib"]
    # The charts sit inside the showTrends branch only.
    trends = ctx["card"].index("{#if showTrends(page)}")
    assert trends < ctx["card"].index("<PayloadChart") < ctx["card"].index("{:else}", trends)


@then("below that it says the history is building")
def building(ctx: dict[str, Any]) -> None:
    after = ctx["card"][ctx["card"].index("{#if showTrends(page)}") :]
    assert "Building your history." in after[: after.index("{/if}")]


@then(parsers.parse('their raids open on their main "{main}" with "{other}" after it'))
def opens_on_main(hub: Hub, ctx: dict[str, Any], main: str, other: str) -> None:
    mine = hub.get("/api/me/character-page", ctx["sid"]).json()
    assert (mine["main"], mine["characters"], mine["page"]["name"]) == (main, [main, other], main)


@then("the raids card picks characters from a dropdown that names the main")
def dropdown(ctx: dict[str, Any]) -> None:
    card = (WEB / "components" / "CharacterCard.svelte").read_text(encoding="utf-8")
    assert '<select id="character-pick"' in card
    assert "characterLabel(c, mine.main" in card
    assert "(main)" in (WEB / "main-swap.ts").read_text(encoding="utf-8")


# --- the first sign-in setup (007) ------------------------------------------------------------------

ROUTES = Path(__file__).resolve().parents[2] / "apps" / "web" / "src" / "routes"


@given("a Wednesday raider in the Toads server who has never signed in")
def new_raider(hub: Hub, ctx: dict[str, Any]) -> None:
    ctx["user"] = hub.user(("wed", "raider"))


@when("they sign in with Discord")
def sign_in(hub: Hub, ctx: dict[str, Any]) -> None:
    r = hub.callback(hub.authorize(hub.start_login(), ctx["user"]))
    ctx["landed"] = r.headers["location"]
    hub.client.cookies.clear()
    ctx["sid"] = hub.login(ctx["user"])


@then("the hub sends them to the setup page")
def on_setup(ctx: dict[str, Any]) -> None:
    from conftest import HUB

    assert ctx["landed"] == f"{HUB}/setup"


@when(parsers.parse('they name "{name}", a {wow_class} the guild\'s logs have not seen, as their main'))
def name_main(hub: Hub, ctx: dict[str, Any], name: str, wow_class: str) -> None:
    body = {"name": name, "wow_class": wow_class, "main": True}
    assert hub.post("/api/me/setup/characters", ctx["sid"], body).json()["declared"]["name"] == name


@when(parsers.parse('they add the alt "{name}" from the guild\'s logs'))
def add_alt(hub: Hub, ctx: dict[str, Any], name: str) -> None:
    (found,) = [c for c in hub.get(f"/api/characters?q={name}", ctx["sid"]).json() if c["name"] == name]
    assert hub.post("/api/claims", ctx["sid"], {"character_id": found["id"]}).status_code == 201


@when("they finish setup")
def finish(hub: Hub, ctx: dict[str, Any]) -> None:
    assert hub.post("/api/me/setup/done", ctx["sid"]).status_code == 200


@then(parsers.parse('setup shows "{main}" as their main, waiting for its first logged raid, and "{alt}" as an alt'))
def setup_shows(hub: Hub, ctx: dict[str, Any], main: str, alt: str) -> None:
    state = hub.get("/api/me/setup", ctx["sid"]).json()
    assert state["main"] == {"name": main, "status": "not_in_logs"}
    assert state["done"] is True
    assert [c["character_name"] for c in hub.get("/api/claims", ctx["sid"]).json()] == [alt]


@then("signing in again takes them to their hub home")
def back_to_hub(hub: Hub, ctx: dict[str, Any]) -> None:
    from conftest import HUB

    r = hub.callback(hub.authorize(hub.start_login(), ctx["user"]))
    hub.client.cookies.clear()
    assert r.headers["location"] == f"{HUB}/hub"


@then("the setup page welcomes them to the Pond from Gail and the officers")
def welcome(ctx: dict[str, Any]) -> None:
    copy = (WEB / "setup.ts").read_text(encoding="utf-8")
    assert "heading: 'Welcome to the Pond'" in copy
    assert "signoff: 'Gail and the officers'" in copy
    assert "Thanks for logging in" in copy
    page = (ROUTES / "setup" / "+page.svelte").read_text(encoding="utf-8")
    assert "art/gail-640.webp" in page
