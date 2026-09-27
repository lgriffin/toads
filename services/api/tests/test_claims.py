"""Character claims: auto-approval, officer decisions scoped to a raid day, unclaim (REQ-HUB-CLAIM-001/003,
REQ-HUB-PRIV-003, REQ-HUB-DAY-010/011)."""

from __future__ import annotations

import json

import pytest
from hub_db import AuditEntry, CharacterClaim
from sqlalchemy import select
from toads_api.claims import names_match
from toads_api.notify import OFFICERS_OUTBOX

from conftest import Hub


def outbox(hub: Hub) -> list[dict[str, object]]:
    raw = hub.client.portal.call(hub.redis.lrange, OFFICERS_OUTBOX, 0, -1)
    return [json.loads(x) for x in raw]


def audit(hub: Hub) -> list[tuple[str, str | None]]:
    with hub.db() as db:
        return [(a.action, a.raid_day_id) for a in db.scalars(select(AuditEntry).order_by(AuditEntry.id))]


@pytest.mark.parametrize(
    ("character", "server_name", "match"),
    [
        ("Hopscotch", "Hopscotch", True),
        ("Hopscotch", "hopscotch ", True),
        ("\uff28opscotch", "Hopscotch", True),  # fullwidth H folds under NFKC
        ("Höpscotch", "Hopscotch", False),
        ("Hopscotch", "Hops", False),
        ("Hopscotch", "", False),
    ],
)
def test_names_match(character: str, server_name: str, match: bool) -> None:
    assert names_match(character, server_name) is match


def test_matching_nickname_is_auto_approved(hub: Hub) -> None:
    sid = hub.login(hub.user(("wed", "raider"), nick="Hopscotch"))
    r = hub.post("/api/claims", sid, {"character_id": 1})
    assert r.status_code == 201
    assert r.json()["status"] == "approved"
    assert r.json()["raid_day_id"] == "wed"
    assert outbox(hub) == [
        {"kind": "claim_auto_approved", "claim_id": r.json()["id"], "character": "Hopscotch", "raid_day": "wed"}
    ]
    assert audit(hub) == [("claim.auto_approve", "wed")]
    assert [c["character_name"] for c in hub.get("/api/claims", sid).json()] == ["Hopscotch"]


def test_accented_name_is_not_auto_approved(hub: Hub) -> None:
    sid = hub.login(hub.user(("wed", "raider"), nick="Hopscotch"))
    assert hub.post("/api/claims", sid, {"character_id": 4}).json()["status"] == "pending"


def test_global_name_counts_when_there_is_no_nickname(hub: Hub) -> None:
    user = hub.user(("wed", "raider"))
    user.global_name = "Ribbit"
    sid = hub.login(user)
    assert hub.post("/api/claims", sid, {"character_id": 2}).json()["status"] == "approved"


def test_other_name_waits_for_the_home_day_officers(hub: Hub) -> None:
    sid = hub.login(hub.user(("wed", "trial"), ("sun", "raider"), nick="Hops"))
    r = hub.post("/api/claims", sid, {"character_id": 1})
    assert r.json()["status"] == "pending"
    assert r.json()["raid_day_id"] == "sun"
    assert outbox(hub) == [
        {"kind": "claim_pending", "claim_id": r.json()["id"], "character": "Hopscotch", "raid_day": "sun"}
    ]


def test_plain_member_cannot_claim(hub: Hub) -> None:
    sid = hub.login(hub.user(nick="Hopscotch"))
    assert hub.post("/api/claims", sid, {"character_id": 1}).status_code == 403


def test_unknown_character_is_404(hub: Hub) -> None:
    sid = hub.login(hub.user(("wed", "raider")))
    assert hub.post("/api/claims", sid, {"character_id": 99}).status_code == 404


@pytest.mark.security
def test_client_cannot_supply_the_character_name(hub: Hub) -> None:
    sid = hub.login(hub.user(("wed", "raider"), nick="Ribbit"))
    r = hub.post("/api/claims", sid, {"character_id": 1, "character_name": "Ribbit"})
    assert r.json()["character_name"] == "Hopscotch"
    assert r.json()["status"] == "pending"


def test_character_has_one_owner(hub: Hub) -> None:
    a = hub.login(hub.user(("wed", "raider"), nick="Hopscotch"))
    b = hub.login(hub.user(("wed", "raider"), nick="Hopscotch"))
    assert hub.post("/api/claims", a, {"character_id": 1}).status_code == 201
    assert hub.post("/api/claims", b, {"character_id": 1}).status_code == 409
    assert hub.post("/api/claims", a, {"character_id": 1}).status_code == 409


def test_rejected_claim_can_be_claimed_again(hub: Hub) -> None:
    member = hub.login(hub.user(("wed", "raider"), nick="Hops"))
    officer = hub.login(hub.user(("wed", "officer")))
    claim = hub.post("/api/claims", member, {"character_id": 1}).json()
    hub.post(f"/api/days/wed/claims/{claim['id']}/reject", officer, {"reason": "not yours"})
    other = hub.login(hub.user(("sun", "raider"), nick="Hopscotch"))
    again = hub.post("/api/claims", other, {"character_id": 1}).json()
    assert again["id"] == claim["id"]
    assert (again["status"], again["raid_day_id"], again["reason"]) == ("approved", "sun", None)


def test_unclaim_detaches_immediately(hub: Hub) -> None:
    sid = hub.login(hub.user(("wed", "raider"), nick="Hopscotch"))
    claim = hub.post("/api/claims", sid, {"character_id": 1}).json()
    assert hub.delete(f"/api/claims/{claim['id']}", sid).status_code == 204
    assert hub.get("/api/claims", sid).json() == []
    assert hub.characters.name_of(1) == "Hopscotch"
    assert audit(hub)[-1] == ("claim.unclaim", "wed")


def test_cannot_unclaim_someone_elses_claim(hub: Hub) -> None:
    owner = hub.login(hub.user(("wed", "raider"), nick="Hopscotch"))
    other = hub.login(hub.user(("wed", "raider")))
    claim = hub.post("/api/claims", owner, {"character_id": 1}).json()
    assert hub.delete(f"/api/claims/{claim['id']}", other).status_code == 404
    assert len(hub.get("/api/claims", owner).json()) == 1


# --- officers ----------------------------------------------------------------------------------------


@pytest.fixture
def pending(hub: Hub) -> dict[str, object]:
    """A Wednesday raider's pending claim on Hopscotch, and sessions for officers of both days."""
    member = hub.login(hub.user(("wed", "raider"), nick="Hops"))
    claim = hub.post("/api/claims", member, {"character_id": 1}).json()
    return {
        "claim": claim,
        "member": member,
        "wed": hub.login(hub.user(("wed", "officer"))),
        "sun": hub.login(hub.user(("sun", "officer"))),
        "global": hub.login(hub.user(("global", "officer"))),
    }


def test_queue_is_per_day(hub: Hub, pending: dict[str, object]) -> None:
    claim = pending["claim"]
    assert [c["id"] for c in hub.get("/api/days/wed/claims", pending["wed"]).json()] == [claim["id"]]
    assert hub.get("/api/days/sun/claims", pending["sun"]).json() == []
    assert hub.get("/api/days/sun/claims", pending["wed"]).status_code == 403
    assert audit(hub)[-1] == ("rbac.denied", "sun")


def test_approve(hub: Hub, pending: dict[str, object]) -> None:
    cid = pending["claim"]["id"]
    r = hub.post(f"/api/days/wed/claims/{cid}/approve", pending["wed"])
    assert r.json()["status"] == "approved"
    assert hub.post(f"/api/days/wed/claims/{cid}/approve", pending["wed"]).status_code == 409
    assert audit(hub)[-1] == ("claim.approve", "wed")
    with hub.db() as db:
        assert db.get(CharacterClaim, cid).decided_by is not None


def test_reject_needs_a_reason(hub: Hub, pending: dict[str, object]) -> None:
    cid = pending["claim"]["id"]
    path = f"/api/days/wed/claims/{cid}/reject"
    assert hub.post(path, pending["wed"], {"reason": ""}).status_code == 422
    r = hub.post(path, pending["wed"], {"reason": "That is Ribbit's main"})
    assert (r.json()["status"], r.json()["reason"]) == ("rejected", "That is Ribbit's main")
    assert hub.get("/api/claims", pending["member"]).json()[0]["reason"] == "That is Ribbit's main"
    assert hub.post(f"/api/days/wed/claims/{cid}/reassign", pending["wed"], {"member_id": 1}).status_code == 409


def test_reassign(hub: Hub, pending: dict[str, object]) -> None:
    cid = pending["claim"]["id"]
    target = hub.get("/api/session", pending["sun"]).json()["member_id"]
    path = f"/api/days/wed/claims/{cid}/reassign"
    assert hub.post(path, pending["wed"], {"member_id": 424242}).status_code == 404
    r = hub.post(path, pending["wed"], {"member_id": target})
    assert (r.json()["status"], r.json()["member_id"]) == ("approved", target)
    assert hub.get("/api/claims", pending["member"]).json() == []
    assert audit(hub)[-1] == ("claim.reassign", "wed")


def test_sibling_day_officer_cannot_act_via_own_path(hub: Hub, pending: dict[str, object]) -> None:
    cid = pending["claim"]["id"]
    r = hub.post(f"/api/days/sun/claims/{cid}/approve", pending["sun"])
    assert r.status_code == 403
    assert audit(hub)[-1] == ("rbac.denied", "wed")
    assert hub.get("/api/claims", pending["member"]).json()[0]["status"] == "pending"


def test_global_officer_acts_through_the_claims_day(hub: Hub, pending: dict[str, object]) -> None:
    cid = pending["claim"]["id"]
    assert hub.post(f"/api/days/sun/claims/{cid}/approve", pending["global"]).status_code == 404
    assert hub.post(f"/api/days/wed/claims/{cid}/approve", pending["global"]).status_code == 200


def test_missing_claim_is_404(hub: Hub, pending: dict[str, object]) -> None:
    assert hub.post("/api/days/wed/claims/999/approve", pending["wed"]).status_code == 404


def test_claims_without_a_day_go_to_global_officers(hub: Hub, pending: dict[str, object]) -> None:
    lone = hub.login(hub.user(("global", "officer"), nick="Someone"))
    claim = hub.post("/api/claims", lone, {"character_id": 3}).json()
    assert claim["raid_day_id"] is None
    assert [c["id"] for c in hub.get("/api/days/sun/claims", pending["global"]).json()] == [claim["id"]]
    assert claim["id"] not in [c["id"] for c in hub.get("/api/days/wed/claims", pending["wed"]).json()]
    assert hub.post(f"/api/days/wed/claims/{claim['id']}/approve", pending["wed"]).status_code == 403
    assert hub.post(f"/api/days/sun/claims/{claim['id']}/approve", pending["global"]).status_code == 200


def test_concurrent_claim_race_is_409(hub: Hub, monkeypatch: pytest.MonkeyPatch) -> None:
    from sqlalchemy.exc import IntegrityError
    from toads_api import claims

    def lost_race(*_: object) -> None:
        raise IntegrityError("INSERT", {}, Exception("uq_claim_character"))

    monkeypatch.setattr(claims, "_create", lost_race)
    sid = hub.login(hub.user(("wed", "raider")))
    assert hub.post("/api/claims", sid, {"character_id": 1}).status_code == 409
