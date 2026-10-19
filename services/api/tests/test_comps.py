"""Members' specs and the officers' comp builder (docs/comps.md): the rules in CompService, the routes, and the
catalogue against the web app's list."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from hub_db import AuditEntry, Member
from sqlalchemy import select
from toads_api.comps.catalog import CLASSES, SPECS
from toads_api.comps.repository import InMemoryCompRepository, Seat
from toads_api.comps.service import CompError, CompService

from conftest import Hub

ROOT = Path(__file__).resolve().parents[3]
NAMES = {1: "Hopscotch", 2: "Lilypadd", 3: "Ribbit"}


def _service(repo: InMemoryCompRepository | None = None) -> CompService:
    return CompService(repo or InMemoryCompRepository(), lambda ids: {i: NAMES[i] for i in ids if i in NAMES})


# ---------------------------------------------------------------- rules


def test_specs_must_be_of_the_chosen_class_and_differ() -> None:
    svc = _service()
    svc.set_specs(1, "shaman", "shaman-elemental", "shaman-restoration")
    assert svc.my_specs(1) is not None
    for args in (
        ("monk", "shaman-elemental", None),
        ("shaman", "mage-frost", None),
        ("shaman", "shaman-elemental", "druid-balance"),
        ("shaman", "shaman-elemental", "shaman-elemental"),
        ("shaman", "shaman-nope", None),
    ):
        with pytest.raises(CompError) as info:
            svc.set_specs(1, *args)
        assert info.value.status == 422, args
    svc.clear_specs(1)
    assert svc.my_specs(1) is None


def test_the_pool_is_the_raid_days_members_by_name_with_or_without_specs() -> None:
    repo = InMemoryCompRepository(raid_days={1: ["wed", "sun"], 2: ["wed"], 3: ["sun"], 9: ["wed"]})
    svc = _service(repo)
    svc.set_specs(2, "shaman", "shaman-restoration", "shaman-elemental")
    pool = svc.pool("wed")
    # Member 9 is no longer in the hub's directory, so they are left out.
    assert [(e.name, e.primary) for e in pool] == [("Hopscotch", None), ("Lilypadd", "shaman-restoration")]
    assert [e.name for e in svc.pool("sun")] == ["Hopscotch", "Ribbit"]


def test_a_comp_is_named_sized_and_seats_each_member_once() -> None:
    svc = _service()
    slots: list[Seat | None] = [None] * 10
    slots[0] = Seat("shaman-elemental", 1)
    slots[1] = Seat("mage-frost")
    view = svc.save_comp("wed", None, "  Molten   Core ", 10, slots, by=1)
    assert (view.name, view.updated_by) == ("Molten Core", "Hopscotch")
    assert view.slots[0] is not None and view.slots[0].member_name == "Hopscotch"
    assert view.slots[1] is not None and view.slots[1].member_name is None
    bad: list[tuple[str, int, list[Seat | None]]] = [
        ("", 10, [None] * 10),
        ("x" * 81, 10, [None] * 10),
        ("Odd", 25, [None] * 25),
        ("Short", 10, [None] * 5),
        ("Twice", 10, [Seat("mage-frost", 1), Seat("mage-fire", 1)] + [None] * 8),
        ("Spec", 10, [Seat("mage-nope")] + [None] * 9),
        ("Stranger", 10, [Seat("mage-frost", 42)] + [None] * 9),
    ]
    for name, size, seats in bad:
        with pytest.raises(CompError) as info:
            svc.save_comp("wed", None, name, size, seats, by=1)
        assert info.value.status == 422, name
    with pytest.raises(CompError) as info:
        svc.save_comp("wed", None, "Molten Core", 10, [None] * 10, by=1)
    assert info.value.status == 409
    # The same name on another night is fine, and a comp from another night cannot be replaced from this one.
    other = svc.save_comp("sun", None, "Molten Core", 10, [None] * 10, by=1)
    with pytest.raises(CompError) as info:
        svc.save_comp("wed", other.id, "Onyxia", 10, [None] * 10, by=1)
    assert info.value.status == 404
    with pytest.raises(CompError) as info:
        svc.delete_comp("wed", other.id, by=1)
    assert info.value.status == 404
    svc.delete_comp("sun", other.id, by=1)
    assert [c.name for c in svc.comps("wed")] == ["Molten Core"]
    assert svc.comps("sun") == []


# ---------------------------------------------------------------- catalogue


def test_catalogue_matches_the_web_app() -> None:
    ts = (ROOT / "apps/web/src/lib/comp.ts").read_text(encoding="utf-8")
    web_specs = re.findall(r"\{ id: '([a-z-]+)', wowClass: '([a-z]+)', name: '([^']+)', role: '([a-z]+)' \}", ts)
    assert web_specs == [(s.id, s.wow_class, s.name, s.role.value) for s in SPECS.values()]
    web_classes = re.findall(r"\{ id: '([a-z]+)', name: '([^']+)', colour: '#[0-9a-f]{6}' \}", ts)
    assert web_classes == list(CLASSES.items())
    for wow_class in CLASSES:
        assert (ROOT / f"apps/web/static/logos/classes/{wow_class}.svg").is_file(), wow_class


# ---------------------------------------------------------------- routes


def _put(hub: Hub, path: str, sid: str, body: object) -> object:
    return hub.client.put(path, headers=hub.as_(sid), json=body)


def test_a_member_sets_reads_and_clears_their_specs(hub: Hub) -> None:
    sid = hub.login(hub.user(("wed", "raider")))
    assert hub.get("/api/me/specs", sid).json() is None
    body = {"wow_class": "shaman", "primary": "shaman-elemental", "secondary": "shaman-restoration"}
    r = _put(hub, "/api/me/specs", sid, body)
    assert r.status_code == 200, r.text
    assert hub.get("/api/me/specs", sid).json() == body
    bad = _put(hub, "/api/me/specs", sid, {"wow_class": "shaman", "primary": "mage-frost"})
    assert bad.status_code == 422
    assert hub.delete("/api/me/specs", sid).status_code == 204
    assert hub.get("/api/me/specs", sid).json() is None
    assert hub.get("/api/me/specs", None).status_code == 401


def test_signing_in_records_the_raid_days_the_roles_give(hub: Hub) -> None:
    user = hub.user(("wed", "raider"), ("sun", "trial"))
    hub.login(user)
    with hub.db() as db:
        row = db.scalars(select(Member).where(Member.discord_user_id == user.user_id)).one()
    assert row.raid_days == ["wed", "sun"]


def test_officers_see_their_nights_roster_and_lock_in_comps(hub: Hub) -> None:
    ele = hub.user(("wed", "raider"), nick="Hopscotch")
    ele_sid = hub.login(ele)
    _put(hub, "/api/me/specs", ele_sid, {"wow_class": "shaman", "primary": "shaman-elemental"})
    hub.login(hub.user(("wed", "trial"), nick="Lilypadd"))
    hub.login(hub.user(("sun", "raider"), nick="Ribbit"))
    officer = hub.login(hub.user(("wed", "officer"), nick="Croak"))

    pool = hub.get("/api/days/wed/comps/pool", officer).json()
    assert [(e["name"], e["primary"]) for e in pool] == [
        ("Croak", None),
        ("Hopscotch", "shaman-elemental"),
        ("Lilypadd", None),
    ]
    hop = next(e["member_id"] for e in pool if e["name"] == "Hopscotch")

    slots: list[object] = [None] * 10
    slots[0] = {"spec": "shaman-elemental", "member_id": hop}
    slots[1] = {"spec": "warrior-protection"}
    made = hub.post("/api/days/wed/comps", officer, {"name": "Onyxia", "size": 10, "slots": slots})
    assert made.status_code == 201, made.text
    comp = made.json()
    assert comp["slots"][0] == {"spec": "shaman-elemental", "member_id": hop, "member_name": "Hopscotch"}
    assert comp["updated_by"] == "Croak"
    dup = hub.post("/api/days/wed/comps", officer, {"name": "Onyxia", "size": 10, "slots": [None] * 10})
    assert dup.status_code == 409

    slots[2] = {"spec": "priest-holy"}
    replaced = _put(hub, f"/api/days/wed/comps/{comp['id']}", officer, {"name": "Onyxia", "size": 10, "slots": slots})
    assert replaced.status_code == 200, replaced.text
    listed = hub.get("/api/days/wed/comps", officer).json()
    assert [c["name"] for c in listed] == ["Onyxia"]
    assert listed[0]["slots"][2]["spec"] == "priest-holy"

    assert hub.delete(f"/api/days/wed/comps/{comp['id']}", officer).status_code == 204
    assert hub.delete(f"/api/days/wed/comps/{comp['id']}", officer).status_code == 404
    with hub.db() as db:
        actions = list(db.scalars(select(AuditEntry.action).where(AuditEntry.action.like("comp.%"))))
    assert actions == ["comp.save", "comp.save", "comp.delete"]


def test_raiders_and_other_nights_officers_cannot_build_comps(hub: Hub) -> None:
    raider = hub.login(hub.user(("wed", "raider")))
    sunday = hub.login(hub.user(("sun", "officer")))
    for sid in (raider, sunday):
        assert hub.get("/api/days/wed/comps/pool", sid).status_code == 403
        assert hub.get("/api/days/wed/comps", sid).status_code == 403
        r = hub.post("/api/days/wed/comps", sid, {"name": "x", "size": 10, "slots": [None] * 10})
        assert r.status_code == 403
    assert hub.get("/api/days/sun/comps/pool", sunday).status_code == 200
    glob = hub.login(hub.user(("global", "officer")))
    assert hub.get("/api/days/wed/comps/pool", glob).status_code == 200
    assert hub.get("/api/days/nope/comps", glob).status_code == 404
