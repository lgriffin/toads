"""Toads badges: each member sees their own main character's; raid leaders see the last raid's roster on the hub
home (the analyzer's officer-only `badges` widget)."""

from __future__ import annotations

from typing import Any

import pytest
from toads_api.home.badges import BadgeService
from toads_api.home.performance import MatchedBy
from toads_api.home.repository import InMemoryHomeRepository, MemberCharacters
from toads_api.home.service import Audience, HomeError, HomeService, catalogue_for

from conftest import Hub

TOKEN = "test-service-token"  # noqa: S105  (conftest.make_settings)
WORKER = {"Authorization": f"Bearer {TOKEN}"}
GENERATED = "2026-09-28 08:00:00"


def _badge(tier: int = 2, value: int = 20) -> dict[str, Any]:
    """wcl_app Badge.to_dict() for the attendance badge (guides/badges.md)."""
    names = ["", "Uncommon", "Rare", "Epic", "Legendary"]
    return {
        "id": "attendance",
        "name": "Loyal Toad",
        "description": "Raids attended",
        "icon": "attendance",
        "glyph": "🐸",
        "tier": tier,
        "quality": names[tier].lower(),
        "tier_name": names[tier],
        "value": value,
        "display": f"{value} raids",
        "stacks": value // 5,
        "next_at": None if tier == 4 else 40,
        "next_tier": "" if tier == 4 else names[tier + 1],
        "progress": 1.0 if tier == 4 else 0.2,
    }


def _player(name: str, tier: int = 2) -> dict[str, Any]:
    return {"name": name, "player_class": "Priest", "score": tier, "badges": [_badge(tier)]}


def _page(*players: dict[str, Any], generated_at: str = GENERATED) -> dict[str, Any]:
    return {"version": 1, "generated_at": generated_at, "players": list(players)}


def _service(chars: MemberCharacters | None, players: list[dict[str, Any]] | None = None) -> BadgeService:
    svc = BadgeService(InMemoryHomeRepository(characters={1: chars} if chars else {}))
    if players is not None:
        svc.publish(1, GENERATED, players)
    return svc


def test_a_member_sees_only_their_main_characters_badges() -> None:
    chars = MemberCharacters("Hopscotch", "Ribbit", ["Lilypad", "Ribbit"], frozenset())
    mine = _service(chars, [_player("Lilypad", 1), _player("Ribbit", 3), _player("Bogwalker", 4)]).mine(1)
    assert mine.entry is not None and (mine.entry["name"], mine.matched_by) == ("Ribbit", MatchedBy.CHOSEN)
    assert mine.looked_for == ["Ribbit", "Lilypad", "Hopscotch"]


def test_a_nickname_someone_else_claims_is_not_shown() -> None:
    chars = MemberCharacters("Croak", None, [], frozenset({"croak"}))
    mine = _service(chars, [_player("Croak")]).mine(1)
    assert (mine.entry, mine.matched_by, mine.looked_for) == (None, None, [])


def test_nothing_before_the_worker_publishes() -> None:
    mine = _service(MemberCharacters("Hopscotch", None, [], frozenset())).mine(1)
    assert (mine.generated_at, mine.entry, mine.looked_for) == (None, None, ["Hopscotch"])


@pytest.mark.parametrize(
    ("version", "generated_at", "players", "status"),
    [
        (2, GENERATED, [], 422),
        (1, "yesterday", [], 422),
        (1, GENERATED, [_player("Pad"), _player("PAD")], 422),
        (1, "2026-09-28 07:59:59", [], 409),
    ],
)
def test_refused_pages(version: int, generated_at: str, players: list[dict[str, Any]], status: int) -> None:
    svc = _service(MemberCharacters("Hopscotch", None, [], frozenset()), [])
    with pytest.raises(HomeError) as info:
        svc.publish(version, generated_at, players)
    assert info.value.status == status


def test_badge_routes(hub: Hub) -> None:
    sid = hub.login(hub.user(("wed", "raider"), nick="Lilypad"))
    empty = hub.get("/api/me/badges", sid).json()
    assert (empty["generated_at"], empty["entry"], empty["looked_for"]) == (None, None, ["Lilypad"])

    r = hub.client.put("/api/worker/badges", headers=WORKER, json=_page(_player("Lilypad", 3), _player("Pad")))
    assert r.status_code == 200 and r.json() == {"players": 2}
    mine = hub.get("/api/me/badges", sid).json()
    assert mine["matched_by"] == "nickname"
    assert mine["entry"]["name"] == "Lilypad" and mine["entry"]["badges"][0]["quality"] == "epic"


@pytest.mark.security
def test_only_the_worker_publishes_badges(hub: Hub) -> None:
    sid = hub.login(hub.user(("sun", "officer")))
    assert hub.client.put("/api/worker/badges", json=_page()).status_code == 401
    assert hub.client.put("/api/worker/badges", headers=hub.as_(sid), json=_page()).status_code == 401
    assert hub.get("/api/me/badges", None).status_code == 401


@pytest.mark.parametrize(
    "bad",
    [
        {**_badge(), "tier": 5},
        {**_badge(), "quality": "artifact"},
        {**_badge(), "progress": 1.5},
    ],
)
def test_malformed_badges_are_refused(hub: Hub, bad: dict[str, Any]) -> None:
    page = _page({**_player("A"), "badges": [bad]})
    assert hub.client.put("/api/worker/badges", headers=WORKER, json=page).status_code == 422


# --- the roster widget ----------------------------------------------------------------------------------------------


def _roster_widget(holders: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """wcl_app.home's `badges` widget (guides/home_widgets.md): the last raid's roster, earned badges only."""
    if holders is None:
        holders = [{"name": "Hopscotch", "player_class": "Rogue", "badges": [_badge(3)], "link": None}]
    return {"id": "badges", "title": "Toads badges", "kind": "badges", "size": "half", "holders": holders}


def test_the_roster_widget_is_for_officers() -> None:
    assert "badges" in [w.id for w in catalogue_for(Audience.OFFICER)]
    assert "badges" not in [w.id for w in catalogue_for(Audience.MEMBER)]


def test_members_never_receive_the_roster(hub: Hub) -> None:
    page = {"version": 1, "generated_at": GENERATED, "widgets": [_roster_widget()]}
    assert hub.client.put("/api/worker/home-page", headers=WORKER, json=page).json() == {"widgets": 1}
    raider = hub.login(hub.user(("wed", "raider")))
    officer = hub.login(hub.user(("sun", "officer")))
    assert hub.get("/api/home/analyzer", raider).json()["widgets"] == []
    roster = hub.get("/api/home/analyzer", officer).json()["widgets"]
    assert [w["id"] for w in roster] == ["badges"] and roster[0]["holders"][0]["name"] == "Hopscotch"


@pytest.mark.parametrize(
    "holders",
    [
        [{"name": "A", "badges": "lots"}],
        [{"name": "A", "badges": [1]}],
        [{"name": "A", "badges": [_badge()] * 51}],
    ],
)
def test_malformed_roster_widgets_are_refused(holders: list[dict[str, Any]]) -> None:
    with pytest.raises(HomeError) as info:
        HomeService(InMemoryHomeRepository()).publish_analyzer_page(1, GENERATED, [_roster_widget(holders)])
    assert info.value.status == 422
