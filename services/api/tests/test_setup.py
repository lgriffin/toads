"""The first sign-in setup: sign-in lands on it until it is done, the first main, and named characters the logs have not
seen yet (REQ-HUB-ME-007, docs/setup.md)."""

from __future__ import annotations

from hub_db import AuditEntry, DeclaredCharacter
from sqlalchemy import select
from toads_api.testing.fake_discord import FakeUser

from conftest import HUB, Hub


def _land(hub: Hub, user: FakeUser) -> str:
    r = hub.callback(hub.authorize(hub.start_login(), user))
    assert r.status_code == 303
    hub.client.cookies.clear()
    return str(r.headers["location"])


def test_a_raider_lands_on_setup_until_they_finish_it(hub: Hub) -> None:
    user = hub.user(("wed", "raider"), nick="Hopscotch")
    assert _land(hub, user) == f"{HUB}/setup"
    sid = hub.login(user)
    assert hub.get("/api/session", sid).json()["needs_setup"] is True
    assert hub.get("/api/me/setup", sid).json() == {"done": False, "main": None, "declared": [], "main_open": True}

    assert hub.post("/api/me/setup/done", sid).json() == {"done": True}
    assert hub.get("/api/session", sid).json()["needs_setup"] is False
    assert hub.get("/api/me/setup", sid).json()["done"] is True
    assert _land(hub, user) == f"{HUB}/hub"


def test_members_without_a_raid_role_and_recruits_skip_setup(hub: Hub) -> None:
    guest = hub.user(nick="Newt")
    assert _land(hub, guest) == f"{HUB}/hub"
    assert hub.get("/api/session", hub.login(guest)).json()["needs_setup"] is False
    assert hub.get("/api/me/setup", hub.login(guest)).status_code == 403
    raider = hub.user(("wed", "raider"))
    login = hub.client.get("/auth/login?next=recruit", follow_redirects=False)
    assert hub.callback(hub.authorize(login, raider)).headers["location"] == f"{HUB}/recruit"


def test_the_main_claimed_first_stays_main_after_an_alt_is_approved(hub: Hub) -> None:
    sid = hub.login(hub.user(("wed", "raider"), nick="Ribbit"))
    croak = hub.post("/api/claims", sid, {"character_id": 3}).json()
    assert croak["status"] == "pending"
    assert hub.post("/api/me/setup/main", sid, {"character_id": 3}).status_code == 204
    assert hub.get("/api/me/setup", sid).json()["main"] == {"name": "Croak", "status": "pending"}
    # Ribbit matches the nickname, so it is approved at once; Croak stays the named main once an officer approves it.
    assert hub.post("/api/claims", sid, {"character_id": 2}).json()["status"] == "approved"
    wed = hub.login(hub.user(("wed", "officer")))
    hub.post(f"/api/days/wed/claims/{croak['id']}/approve", wed)
    assert hub.get("/api/me/main", sid).json()["main"] == {"character_id": 3, "character_name": "Croak"}
    assert hub.get("/api/me/setup", sid).json()["main"] == {"name": "Croak", "status": "approved"}
    # Holding approved characters, the main changes only by a main swap.
    assert hub.get("/api/me/setup", sid).json()["main_open"] is False
    assert hub.post("/api/me/setup/main", sid, {"character_id": 2}).status_code == 409


def test_the_first_main_must_be_a_live_claim_of_theirs(hub: Hub) -> None:
    sid = hub.login(hub.user(("wed", "raider")))
    assert hub.post("/api/me/setup/main", sid, {"character_id": 3}).status_code == 404
    other = hub.login(hub.user(("wed", "raider")))
    hub.post("/api/claims", other, {"character_id": 3})
    assert hub.post("/api/me/setup/main", sid, {"character_id": 3}).status_code == 404


def test_a_character_the_logs_know_is_claimed_at_once(hub: Hub) -> None:
    sid = hub.login(hub.user(("wed", "raider")))
    r = hub.post("/api/me/setup/characters", sid, {"name": "  croak ", "wow_class": "mage", "main": True})
    assert r.status_code == 201
    out = r.json()
    assert out["declared"] is None
    assert (out["claim"]["character_name"], out["claim"]["status"]) == ("Croak", "pending")
    with hub.db() as db:
        assert [a.action for a in db.scalars(select(AuditEntry))] == ["setup.main"]


def test_a_new_alt_waits_by_name_and_class_until_the_logs_see_it(hub: Hub) -> None:
    sid = hub.login(hub.user(("wed", "raider")))
    r = hub.post("/api/me/setup/characters", sid, {"name": "Tadpole", "wow_class": "druid", "main": True})
    assert r.status_code == 201
    named = r.json()["declared"]
    assert (named["name"], named["wow_class"], named["main"]) == ("Tadpole", "druid", True)
    assert hub.post("/api/me/setup/characters", sid, {"name": "tadpole", "wow_class": "druid"}).status_code == 409
    alt = hub.post("/api/me/setup/characters", sid, {"name": "Lily  Pad", "wow_class": "priest"}).json()["declared"]
    assert alt["name"] == "Lily Pad"
    state = hub.get("/api/me/setup", sid).json()
    assert [d["name"] for d in state["declared"]] == ["Tadpole", "Lily Pad"]
    assert state["main"] == {"name": "Tadpole", "status": "not_in_logs"}

    # The worker sees Tadpole in a log: the next visit claims it and makes it the main once approved.
    hub.characters.names[9] = "Tadpole"
    state = hub.get("/api/me/setup", sid).json()
    assert [d["name"] for d in state["declared"]] == ["Lily Pad"]
    (claim,) = hub.get("/api/claims", sid).json()
    assert (claim["character_name"], claim["status"]) == ("Tadpole", "pending")
    wed = hub.login(hub.user(("wed", "officer")))
    hub.post(f"/api/days/wed/claims/{claim['id']}/approve", wed)
    assert hub.get("/api/me/main", sid).json()["main"]["character_name"] == "Tadpole"

    assert hub.delete(f"/api/me/setup/characters/{alt['id']}", sid).status_code == 204
    assert hub.get("/api/me/setup", sid).json()["declared"] == []


def test_a_named_character_someone_else_holds_stays_named(hub: Hub) -> None:
    holder = hub.login(hub.user(("wed", "raider")))
    sid = hub.login(hub.user(("wed", "raider")))
    hub.post("/api/me/setup/characters", sid, {"name": "Toadstool", "wow_class": "rogue"})
    hub.characters.names[10] = "Toadstool"
    hub.post("/api/claims", holder, {"character_id": 10})
    assert [d["name"] for d in hub.get("/api/me/setup", sid).json()["declared"]] == ["Toadstool"]


def test_named_characters_are_the_members_own(hub: Hub) -> None:
    sid = hub.login(hub.user(("wed", "raider")))
    other = hub.login(hub.user(("wed", "raider")))
    row = hub.post("/api/me/setup/characters", sid, {"name": "Tadpole", "wow_class": "druid"}).json()["declared"]
    assert hub.delete(f"/api/me/setup/characters/{row['id']}", other).status_code == 404
    assert hub.post("/api/me/setup/characters", sid, {"name": "Newt", "wow_class": "bard"}).status_code == 422
    with hub.db() as db:
        assert db.scalars(select(DeclaredCharacter.name)).all() == ["Tadpole"]


def test_a_named_main_is_refused_once_they_hold_an_approved_character(hub: Hub) -> None:
    sid = hub.login(hub.user(("wed", "raider"), nick="Hopscotch"))
    hub.post("/api/claims", sid, {"character_id": 1})
    r = hub.post("/api/me/setup/characters", sid, {"name": "Tadpole", "wow_class": "druid", "main": True})
    assert r.status_code == 409
    assert hub.post("/api/me/setup/characters", sid, {"name": "Tadpole", "wow_class": "druid"}).status_code == 201
