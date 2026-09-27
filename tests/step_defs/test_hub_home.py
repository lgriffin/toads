"""The customisable hub home: REQ-HUB-HOME-002 to 005. Thin steps over the `hub` fixture (root conftest.py)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, scenario, then, when
from toads_api.home.service import Audience, catalogue_for

from conftest import HUB, Hub

FEATURES = Path(__file__).resolve().parents[1] / "features"
CHOSEN = ["recruiting", "raid_totals"]


def _bind(number: int) -> Any:
    """Bind REQ-HUB-HOME-<nnn> from hub_home.feature (the id is built, not written out)."""
    req_id = f"REQ-HUB-HOME-{number:03d}"
    for line in (FEATURES / "hub_home.feature").read_text(encoding="utf-8").splitlines():
        m = re.match(rf"\s*Scenario: ({req_id} .*)$", line)
        if m:
            return scenario(str(FEATURES / "hub_home.feature"), m.group(1))
    raise LookupError(req_id)


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
