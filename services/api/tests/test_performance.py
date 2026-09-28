"""The "Your performance" widget: the member's own main character against the guild median for the same role."""

from __future__ import annotations

from typing import Any

import pytest
from toads_api.home.performance import MatchedBy, PerformanceService, candidates
from toads_api.home.repository import InMemoryHomeRepository, MemberCharacters
from toads_api.home.service import HomeError

from conftest import Hub

RAID = {"report_id": "aBcD1234eFgH5678", "title": "Karazhan", "date": "2026-09-23"}


def _player(name: str, value: float = 800.0) -> dict[str, Any]:
    return {
        "name": name,
        "class": "Priest",
        "role": "healer",
        "metric": "Healing",
        "unit": "amount",
        "value": value,
        "median": 700.0,
        "rank": 1,
        "of": 3,
        "recent": [],
    }


def _chars(
    nickname: str = "Hopscotch", chosen: str | None = None, approved: tuple[str, ...] = (), others: tuple[str, ...] = ()
) -> MemberCharacters:
    return MemberCharacters(nickname, chosen, list(approved), frozenset(n.casefold() for n in others))


def _service(chars: MemberCharacters | None, players: list[dict[str, Any]] | None = None) -> PerformanceService:
    repo = InMemoryHomeRepository(characters={1: chars} if chars else {})
    svc = PerformanceService(repo)
    if players is not None:
        svc.publish(1, "2026-09-24 08:00:00", RAID, players)
    return svc


def test_chosen_character_beats_claims_and_nickname() -> None:
    chars = _chars(chosen="Ribbit", approved=("Lilypad", "Ribbit"))
    assert candidates(chars) == [
        ("Ribbit", MatchedBy.CHOSEN),
        ("Lilypad", MatchedBy.CLAIM),
        ("Hopscotch", MatchedBy.NICKNAME),
    ]
    mine = _service(chars, [_player("Lilypad"), _player("Ribbit", 950)]).mine(1)
    assert mine.entry is not None and mine.entry["name"] == "Ribbit" and mine.matched_by is MatchedBy.CHOSEN


def test_a_claimed_character_in_the_raid_is_used_when_the_chosen_one_sat_out() -> None:
    mine = _service(_chars(chosen="Ribbit", approved=("Lilypad", "Ribbit")), [_player("Lilypad")]).mine(1)
    assert mine.entry is not None and (mine.entry["name"], mine.matched_by) == ("Lilypad", MatchedBy.CLAIM)


def test_nickname_matches_regardless_of_case() -> None:
    mine = _service(_chars(nickname="hopscotch"), [_player("Hopscotch")]).mine(1)
    assert mine.matched_by is MatchedBy.NICKNAME


@pytest.mark.security
def test_a_character_someone_else_claims_is_never_matched_by_nickname() -> None:
    chars = _chars(nickname="Croak", others=("Croak",))
    assert candidates(chars) == []
    mine = _service(chars, [_player("Croak")]).mine(1)
    assert (mine.entry, mine.matched_by, mine.raid) == (None, None, RAID)


def test_missing_from_the_last_raid() -> None:
    mine = _service(_chars(approved=("Lilypad",)), [_player("Someone")]).mine(1)
    assert mine.entry is None and mine.looked_for == ["Lilypad", "Hopscotch"]


def test_nothing_published_yet() -> None:
    mine = _service(_chars()).mine(1)
    assert (mine.generated_at, mine.raid, mine.entry) == (None, None, None)


@pytest.mark.parametrize(
    ("version", "generated_at", "raid", "players", "status"),
    [
        (2, "2026-09-24 08:00:00", RAID, [], 422),
        (1, "yesterday", RAID, [], 422),
        (1, "2026-09-24 08:00:00", None, [_player("A")], 422),
        (1, "2026-09-24 08:00:00", RAID, [_player("A"), _player("a")], 422),
        (1, "2026-09-23 08:00:00", RAID, [], 409),
    ],
)
def test_refused_pages(
    version: int, generated_at: str, raid: dict[str, Any] | None, players: list[dict[str, Any]], status: int
) -> None:
    svc = _service(_chars(), [])
    with pytest.raises(HomeError) as info:
        svc.publish(version, generated_at, raid, players)
    assert info.value.status == status


TOKEN = "test-service-token"  # noqa: S105  (conftest.make_settings)
WORKER = {"Authorization": f"Bearer {TOKEN}"}


def test_performance_routes(hub: Hub) -> None:
    sid = hub.login(hub.user(("wed", "raider"), nick="Lilypad"))
    empty = hub.get("/api/me/performance", sid).json()
    assert (empty["generated_at"], empty["entry"], empty["looked_for"]) == (None, None, ["Lilypad"])

    page = {"version": 1, "generated_at": "2026-09-24 08:00:00", "raid": RAID, "players": [_player("Lilypad", 900)]}
    r = hub.client.put("/api/worker/performance", headers=WORKER, json=page)
    assert r.status_code == 200 and r.json() == {"players": 1}
    mine = hub.get("/api/me/performance", sid).json()
    assert mine["matched_by"] == "nickname"
    assert mine["entry"]["class"] == "Priest" and mine["entry"]["value"] == 900


@pytest.mark.security
def test_only_the_worker_publishes_performance(hub: Hub) -> None:
    sid = hub.login(hub.user(("sun", "officer")))
    page = {"version": 1, "generated_at": "2026-09-24 08:00:00", "raid": RAID, "players": []}
    assert hub.client.put("/api/worker/performance", json=page).status_code == 401
    assert hub.client.put("/api/worker/performance", headers=hub.as_(sid), json=page).status_code == 401
    assert hub.get("/api/me/performance", None).status_code == 401


def test_malformed_players_are_refused(hub: Hub) -> None:
    bad = {**_player("A"), "role": "bard"}
    page = {"version": 1, "generated_at": "2026-09-24 08:00:00", "raid": RAID, "players": [bad]}
    assert hub.client.put("/api/worker/performance", headers=WORKER, json=page).status_code == 422
