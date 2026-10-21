"""Character pages on Me: each member sees only their own characters' raids, as the analyzer built them."""

from __future__ import annotations

import json
from typing import Any

import pytest
from hub_db import CharacterClaim, ClaimStatus
from toads_api.home.characters import CharacterPageService
from toads_api.home.performance import MatchedBy
from toads_api.home.repository import InMemoryHomeRepository, MemberCharacters
from toads_api.home.service import HomeError

from conftest import Hub

TOKEN = "test-service-token"  # noqa: S105  (conftest.make_settings)
WORKER = {"Authorization": f"Bearer {TOKEN}"}
GENERATED = "2026-10-16 08:00:00"


def _chart() -> dict[str, Any]:
    """wcl_app.character_pages' chart: the character against the raid's median (guides/charts.md)."""
    return {
        "version": 1,
        "id": "character_healer",
        "title": "Healing as healer",
        "kind": "line",
        "subtitle": "",
        "x_label": "Raid",
        "y_label": "Healing",
        "categories": ["14/10"],
        "series": [
            {"key": "you", "name": "You", "values": [1_100_000], "display": ["1.1M"], "emphasis": True},
            {"key": "median", "name": "Healer median", "values": [1_000_000], "display": ["1.0M"], "emphasis": False},
        ],
        "y_max": 2_000_000,
        "references": [],
        "notes": [],
        "empty": "",
    }


def _page(name: str, *, chart: dict[str, Any] | None = None) -> dict[str, Any]:
    """wcl_app CharacterPage.to_dict() (guides/character_pages.md in lgriffin/warcraftlogs_project)."""
    raid = {
        "report_id": "pondWed1014",
        "title": "Serpentshrine Cavern",
        "zone": "Serpentshrine Cavern",
        "raid_date": "2026-10-14 20:00:00",
        "weekday": 2,
        "role": "healer",
        "metric": "Healing",
        "value": 1_100_000,
        "display": "1.1M",
        "median": 1_000_000,
        "median_display": "1.0M",
        "rank": 2,
        "of": 6,
        "percent": 18.2,
    }
    spread = {"name": "Healing", "min": 1e6, "mean": 1.1e6, "max": 1.2e6, "raids": 1, "total": 1.1e6}
    return {
        "version": 1,
        "name": name,
        "player_class": "Priest",
        "raids": 1,
        "first_raid": raid["raid_date"],
        "last_raid": raid["raid_date"],
        "role_counts": {"healer": 1},
        "recent": [raid],
        "metrics": [{**spread, "role": "healer", "raids_used": 1}],
        "casts": [],
        "consumables": [],
        "bests": [
            {
                "metric": "Healing",
                "role": "healer",
                "value": 1_100_000,
                "display": "1.1M",
                "report_id": "pondWed1014",
                "raid_date": raid["raid_date"],
            }
        ],
        "charts": [chart or _chart()],
    }


def _body(*pages: dict[str, Any], generated_at: str = GENERATED) -> dict[str, Any]:
    return {"version": 1, "generated_at": generated_at, "pages": list(pages)}


def _service(chars: MemberCharacters | None, pages: list[dict[str, Any]] | None = None) -> CharacterPageService:
    svc = CharacterPageService(InMemoryHomeRepository(characters={1: chars} if chars else {}))
    if pages is not None:
        svc.publish(1, GENERATED, pages)
    return svc


def test_a_member_sees_their_main_characters_page_and_can_pick_another() -> None:
    chars = MemberCharacters("Hopscotch", "Ribbit", ["Lilypad", "Ribbit"], frozenset())
    svc = _service(chars, [_page("Lilypad"), _page("Ribbit"), _page("Bogwalker")])
    mine = svc.mine(1)
    assert mine.page is not None and (mine.page["name"], mine.matched_by) == ("Ribbit", MatchedBy.CHOSEN)
    assert (mine.looked_for, mine.characters) == (["Ribbit", "Lilypad", "Hopscotch"], ["Ribbit", "Lilypad"])
    picked = svc.mine(1, "lilypad")
    assert picked.page is not None and (picked.page["name"], picked.matched_by) == ("Lilypad", MatchedBy.CLAIM)


def test_a_raid_line_comes_from_any_of_the_members_own_characters() -> None:
    alts = [f"Alt{i}" for i in range(5)]
    chars = MemberCharacters("Hopscotch", None, alts, frozenset())
    later = {**_page("Alt4"), "recent": [{**_page("Alt4")["recent"][0], "report_id": "pondSun1011"}]}
    svc = _service(chars, [_page("Alt0"), later, _page("Bogwalker")])
    line = svc.raid_line(1, "pondSun1011")
    assert line is not None and (line.name, line.raid["rank"]) == ("Alt4", 2)
    main = svc.raid_line(1, "pondWed1014")
    assert main is not None and main.name == "Alt0"
    assert svc.raid_line(1, "somebodyElses") is None
    # Bogwalker was in pondWed1014 too, but is not this member's.
    assert (
        _service(MemberCharacters("Croak", None, [], frozenset()), [_page("Bogwalker")]).raid_line(1, "pondWed1014")
        is None
    )


def test_asking_for_someone_elses_character_shows_your_own() -> None:
    chars = MemberCharacters("Hopscotch", None, ["Lilypad"], frozenset())
    mine = _service(chars, [_page("Lilypad"), _page("Bogwalker")]).mine(1, "Bogwalker")
    assert mine.page is not None and mine.page["name"] == "Lilypad"


def test_a_nickname_someone_else_claims_is_not_shown() -> None:
    chars = MemberCharacters("Croak", None, [], frozenset({"croak"}))
    mine = _service(chars, [_page("Croak")]).mine(1)
    assert (mine.page, mine.looked_for, mine.characters) == (None, [], [])
    assert mine.generated_at == GENERATED


def test_nothing_before_the_worker_publishes() -> None:
    mine = _service(MemberCharacters("Hopscotch", None, [], frozenset())).mine(1)
    assert (mine.generated_at, mine.page, mine.looked_for) == (None, None, ["Hopscotch"])


def test_the_worker_is_asked_for_every_name_a_member_goes_by() -> None:
    repo = InMemoryHomeRepository(
        characters={
            1: MemberCharacters("Hopscotch", None, ["Lilypad"], frozenset()),
            2: MemberCharacters("lilypad", None, [], frozenset()),
        }
    )
    assert [n.casefold() for n in CharacterPageService(repo).wanted()] == ["hopscotch", "lilypad"]


@pytest.mark.parametrize(
    ("version", "generated_at", "pages", "status"),
    [
        (2, GENERATED, [], 422),
        (1, "yesterday", [], 422),
        (1, GENERATED, [_page("Pad"), _page("PAD")], 422),
        (1, GENERATED, [_page("Pad", chart={**_chart(), "kind": "pie"})], 422),
        (1, "2026-10-16 07:59:59", [], 409),
    ],
)
def test_refused_pages(version: int, generated_at: str, pages: list[dict[str, Any]], status: int) -> None:
    svc = _service(MemberCharacters("Hopscotch", None, [], frozenset()), [_page("Hopscotch")])
    with pytest.raises(HomeError) as info:
        svc.publish(version, generated_at, pages)
    assert info.value.status == status


def _claim(hub: Hub, sid: str, character_id: int, name: str) -> None:
    member_id = hub.get("/api/session", sid).json()["member_id"]
    with hub.db.begin() as db:
        db.add(
            CharacterClaim(
                character_id=character_id, member_id=member_id, character_name=name, status=ClaimStatus.APPROVED
            )
        )


def test_character_page_routes(hub: Hub) -> None:
    sid = hub.login(hub.user(("wed", "raider"), nick="Lilypad"))
    _claim(hub, sid, 101, "Ribbit")
    empty = hub.get("/api/me/character-page", sid).json()
    assert (empty["generated_at"], empty["page"], empty["looked_for"]) == (None, None, ["Ribbit", "Lilypad"])

    wanted = hub.client.get("/api/worker/character-pages/wanted", headers=WORKER).json()["names"]
    assert {"Lilypad", "Ribbit"} <= set(wanted)

    r = hub.client.put("/api/worker/character-pages", headers=WORKER, json=_body(_page("Lilypad"), _page("Pad")))
    assert r.status_code == 200 and r.json() == {"pages": 2}
    mine = hub.get("/api/me/character-page", sid).json()
    assert (mine["matched_by"], mine["characters"]) == ("nickname", ["Lilypad"])
    assert mine["page"]["recent"][0]["median"] == 1_000_000
    assert mine["page"]["charts"][0]["id"] == "character_healer"
    line = hub.get("/api/me/raid-line?report=pondWed1014", sid).json()["line"]
    assert (line["name"], line["raid"]["rank"]) == ("Lilypad", 2)
    assert hub.get("/api/me/raid-line?report=elsewhere", sid).json() == {"line": None}
    assert hub.get("/api/me/raid-line?report=", sid).status_code == 422


def test_an_older_build_never_replaces_a_newer_one(hub: Hub) -> None:
    put = hub.client.put
    assert put("/api/worker/character-pages", headers=WORKER, json=_body(_page("A"))).status_code == 200
    stale = _body(_page("B"), generated_at="2026-10-16 07:00:00")
    assert put("/api/worker/character-pages", headers=WORKER, json=stale).status_code == 409
    sid = hub.login(hub.user(("wed", "raider"), nick="A"))
    assert hub.get("/api/me/character-page", sid).json()["page"]["name"] == "A"


def test_an_empty_build_still_holds_its_time(hub: Hub) -> None:
    put = hub.client.put
    assert put("/api/worker/character-pages", headers=WORKER, json=_body()).status_code == 200
    stale = _body(_page("B"), generated_at="2026-10-16 07:00:00")
    assert put("/api/worker/character-pages", headers=WORKER, json=stale).status_code == 409
    sid = hub.login(hub.user(("wed", "raider"), nick="B"))
    mine = hub.get("/api/me/character-page", sid).json()
    assert (mine["generated_at"], mine["page"]) == (GENERATED, None)


def test_an_empty_build_holds_its_time_in_memory() -> None:
    svc = _service(MemberCharacters("Hopscotch", None, [], frozenset()), [])
    with pytest.raises(HomeError) as info:
        svc.publish(1, "2026-10-16 07:00:00", [_page("Hopscotch")])
    assert info.value.status == 409
    assert svc.mine(1).generated_at == GENERATED


@pytest.mark.security
def test_only_the_worker_reads_and_publishes_character_pages(hub: Hub) -> None:
    sid = hub.login(hub.user(("sun", "officer")))
    assert hub.client.put("/api/worker/character-pages", json=_body()).status_code == 401
    assert hub.client.put("/api/worker/character-pages", headers=hub.as_(sid), json=_body()).status_code == 401
    assert hub.client.get("/api/worker/character-pages/wanted", headers=hub.as_(sid)).status_code == 401
    assert hub.get("/api/me/character-page", None).status_code == 401


@pytest.mark.parametrize(
    "bad",
    [
        {"role": "bard"},
        {"value": float("inf")},
        {"rank": -1},
        {"report_id": ""},
    ],
)
def test_malformed_raids_are_refused(hub: Hub, bad: dict[str, Any]) -> None:
    page = _page("A")
    page["recent"] = [{**page["recent"][0], **bad}]
    body = _body(page)
    r = hub.client.put(
        "/api/worker/character-pages",
        headers={**WORKER, "content-type": "application/json"},
        content=json.dumps(body, allow_nan=True),
    )
    assert r.status_code == 422
