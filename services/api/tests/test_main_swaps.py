"""A member's main and their asks to swap it, decided by their raid night's officers (REQ-HUB-CLAIM-006,
REQ-HUB-ME-006)."""

from __future__ import annotations

import json

import pytest
from hub_db import AuditEntry, CharacterClaim, ClaimStatus, Member, main_claim
from sqlalchemy import select
from toads_api.notify import OFFICERS_OUTBOX

from conftest import Hub


def audit(hub: Hub) -> list[tuple[str, str | None]]:
    with hub.db() as db:
        return [(a.action, a.raid_day_id) for a in db.scalars(select(AuditEntry).order_by(AuditEntry.id))]


def _claim(cid: int, character_id: int) -> CharacterClaim:
    return CharacterClaim(id=cid, member_id=1, character_id=character_id, character_name=f"c{character_id}")


def test_main_is_the_approved_choice_while_held_else_the_first_claim() -> None:
    first, second = _claim(5, 50), _claim(9, 90)
    assert main_claim(None, [second, first]) is first
    assert main_claim(90, [first, second]) is second
    assert main_claim(77, [first, second]) is first
    assert main_claim(None, []) is None


@pytest.fixture
def two(hub: Hub) -> dict[str, str]:
    """A Wednesday raider whose first approved character is Hopscotch (their nickname) with Ribbit approved after, and
    sessions for officers of both nights and the global tier."""
    member = hub.login(hub.user(("wed", "raider"), nick="Hopscotch"))
    hub.post("/api/claims", member, {"character_id": 1})
    ribbit = hub.post("/api/claims", member, {"character_id": 2}).json()
    wed = hub.login(hub.user(("wed", "officer")))
    hub.post(f"/api/days/wed/claims/{ribbit['id']}/approve", wed)
    return {
        "member": member,
        "wed": wed,
        "sun": hub.login(hub.user(("sun", "officer"))),
        "global": hub.login(hub.user(("global", "officer"))),
    }


def test_the_first_approved_character_is_the_main(hub: Hub, two: dict[str, str]) -> None:
    mine = hub.get("/api/me/main", two["member"]).json()
    assert mine["main"] == {"character_id": 1, "character_name": "Hopscotch"}
    assert mine["alts"] == [{"character_id": 2, "character_name": "Ribbit"}]
    assert mine["request"] is None


def test_asking_waits_for_the_members_night_and_approval_swaps_the_main(hub: Hub, two: dict[str, str]) -> None:
    r = hub.post("/api/me/main", two["member"], {"character_id": 2})
    assert r.status_code == 201
    swap = r.json()
    assert (swap["status"], swap["character_name"], swap["raid_day_id"]) == ("pending", "Ribbit", "wed")
    raw = hub.client.portal.call(hub.redis.lrange, OFFICERS_OUTBOX, 0, -1)
    assert json.loads(raw[-1]) == {
        "kind": "main_swap_pending",
        "swap_id": swap["id"],
        "character": "Ribbit",
        "raid_day": "wed",
    }

    (queued,) = hub.get("/api/days/wed/main-swaps", two["wed"]).json()
    assert (queued["member_name"], queued["current_main"], queued["nights"]) == ("Hopscotch", "Hopscotch", ["wed"])
    assert hub.get("/api/days/sun/main-swaps", two["sun"]).json() == []
    assert hub.get("/api/admin/main-swaps", two["global"]).json() == []

    # A sibling night's officer is refused and recorded; the global tier reaches it only through its night.
    assert hub.post(f"/api/days/sun/main-swaps/{swap['id']}/approve", two["sun"]).status_code == 403
    assert audit(hub)[-1] == ("rbac.denied", "wed")
    assert hub.post(f"/api/days/sun/main-swaps/{swap['id']}/approve", two["global"]).status_code == 404

    r = hub.post(f"/api/days/wed/main-swaps/{swap['id']}/approve", two["wed"])
    assert r.json()["status"] == "approved"
    assert audit(hub)[-1] == ("main.approve", "wed")
    assert hub.post(f"/api/days/wed/main-swaps/{swap['id']}/approve", two["wed"]).status_code == 409
    mine = hub.get("/api/me/main", two["member"]).json()
    assert (mine["main"]["character_name"], [a["character_name"] for a in mine["alts"]]) == ("Ribbit", ["Hopscotch"])
    assert mine["request"] is None


def test_a_rejection_keeps_the_main_and_tells_the_member_why(hub: Hub, two: dict[str, str]) -> None:
    swap = hub.post("/api/me/main", two["member"], {"character_id": 2}).json()
    path = f"/api/days/wed/main-swaps/{swap['id']}/reject"
    assert hub.post(path, two["wed"], {"reason": ""}).status_code == 422
    assert hub.post(path, two["wed"], {"reason": "We need the healer"}).json()["status"] == "rejected"
    mine = hub.get("/api/me/main", two["member"]).json()
    assert mine["main"]["character_name"] == "Hopscotch"
    assert (mine["request"]["status"], mine["request"]["reason"]) == ("rejected", "We need the healer")


def test_only_an_approved_alt_can_be_asked_for(hub: Hub, two: dict[str, str]) -> None:
    assert hub.post("/api/me/main", two["member"], {"character_id": 1}).status_code == 409
    assert hub.post("/api/me/main", two["member"], {"character_id": 3}).status_code == 422
    # Someone else's character: not theirs, so no different from one they never claimed.
    other = hub.login(hub.user(("wed", "raider"), nick="Croak"))
    hub.post("/api/claims", other, {"character_id": 3})
    assert hub.post("/api/me/main", two["member"], {"character_id": 3}).status_code == 422
    assert hub.get("/api/days/wed/main-swaps", two["wed"]).json() == []


def test_a_new_ask_replaces_the_pending_one_and_can_be_withdrawn(hub: Hub, two: dict[str, str]) -> None:
    member = two["member"]
    croak = hub.post("/api/claims", member, {"character_id": 3}).json()
    hub.post(f"/api/days/wed/claims/{croak['id']}/approve", two["wed"])
    first = hub.post("/api/me/main", member, {"character_id": 2}).json()
    second = hub.post("/api/me/main", member, {"character_id": 3}).json()
    assert first["id"] == second["id"]
    assert [s["character_name"] for s in hub.get("/api/days/wed/main-swaps", two["wed"]).json()] == ["Croak"]
    assert hub.delete("/api/me/main/request", member).status_code == 204
    assert hub.delete("/api/me/main/request", member).status_code == 404
    assert hub.get("/api/days/wed/main-swaps", two["wed"]).json() == []
    assert ("main.withdraw", "wed") in audit(hub)


def test_an_alt_given_away_before_approval_cannot_become_the_main(hub: Hub, two: dict[str, str]) -> None:
    swap = hub.post("/api/me/main", two["member"], {"character_id": 2}).json()
    with hub.db.begin() as db:
        db.delete(db.scalar(select(CharacterClaim).where(CharacterClaim.character_id == 2)))
    assert hub.post(f"/api/days/wed/main-swaps/{swap['id']}/approve", two["wed"]).status_code == 409


def test_unclaiming_the_main_falls_back_to_the_first_claim_left(hub: Hub, two: dict[str, str]) -> None:
    swap = hub.post("/api/me/main", two["member"], {"character_id": 2}).json()
    hub.post(f"/api/days/wed/main-swaps/{swap['id']}/approve", two["wed"])
    ribbit = next(c for c in hub.get("/api/claims", two["member"]).json() if c["character_id"] == 2)
    hub.delete(f"/api/claims/{ribbit['id']}", two["member"])
    assert hub.get("/api/me/main", two["member"]).json()["main"]["character_name"] == "Hopscotch"


def test_asks_from_members_on_no_night_go_to_the_global_tier(hub: Hub, two: dict[str, str]) -> None:
    lone = hub.login(hub.user(("global", "officer"), nick="Someone"))
    lone_id = hub.get("/api/session", lone).json()["member_id"]
    with hub.db.begin() as db:
        for character_id, name in ((3, "Croak"), (4, "Höpscotch")):
            db.add(
                CharacterClaim(
                    member_id=lone_id, character_id=character_id, character_name=name, status=ClaimStatus.APPROVED
                )
            )
    swap = hub.post("/api/me/main", lone, {"character_id": 4}).json()
    assert [s["id"] for s in hub.get("/api/admin/main-swaps", two["global"]).json()] == [swap["id"]]
    assert hub.get("/api/admin/main-swaps", two["wed"]).status_code == 403
    assert hub.post(f"/api/days/wed/main-swaps/{swap['id']}/approve", two["wed"]).status_code == 403
    assert hub.post(f"/api/admin/main-swaps/{swap['id']}/approve", two["global"]).status_code == 200
    with hub.db() as db:
        assert db.get(Member, lone_id).main_character_id == 4


def test_me_opens_on_the_main_and_lists_it_first(hub: Hub, two: dict[str, str]) -> None:
    pages = [
        {
            "version": 1, "name": name, "player_class": "Priest", "raids": 1, "first_raid": None, "last_raid": None,
            "role_counts": {}, "recent": [], "metrics": [], "casts": [], "consumables": [], "bests": [], "charts": [],
        }
        for name in ("Hopscotch", "Ribbit")
    ]  # fmt: skip
    body = {"version": 1, "generated_at": "2026-10-21 08:00:00", "pages": pages}
    assert hub.client.put(
        "/api/worker/character-pages", headers={"Authorization": "Bearer test-service-token"}, json=body
    ).is_success
    mine = hub.get("/api/me/character-page", two["member"]).json()
    assert (mine["main"], mine["characters"], mine["page"]["name"]) == (
        "Hopscotch",
        ["Hopscotch", "Ribbit"],
        "Hopscotch",
    )
    swap = hub.post("/api/me/main", two["member"], {"character_id": 2}).json()
    hub.post(f"/api/days/wed/main-swaps/{swap['id']}/approve", two["wed"])
    mine = hub.get("/api/me/character-page", two["member"]).json()
    assert (mine["main"], mine["characters"], mine["page"]["name"]) == ("Ribbit", ["Ribbit", "Hopscotch"], "Ribbit")


def test_withdrawing_a_new_ask_does_not_bring_back_an_old_rejection(hub: Hub, two: dict[str, str]) -> None:
    member = two["member"]
    croak = hub.post("/api/claims", member, {"character_id": 3}).json()
    hub.post(f"/api/days/wed/claims/{croak['id']}/approve", two["wed"])
    swap = hub.post("/api/me/main", member, {"character_id": 2}).json()
    hub.post(f"/api/days/wed/main-swaps/{swap['id']}/reject", two["wed"], {"reason": "We need the healer"})
    hub.post("/api/me/main", member, {"character_id": 3})
    assert hub.delete("/api/me/main/request", member).status_code == 204
    assert hub.get("/api/me/main", member).json()["request"] is None
    assert ("main.reject", "wed") in audit(hub)
