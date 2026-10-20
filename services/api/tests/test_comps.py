"""Members' specs and the officers' comp builder (docs/comps.md): the rules in CompService, the routes, and the
catalogue against the web app's list."""

from __future__ import annotations

import re
from pathlib import Path

import anyio
import pytest
from hub_db import AuditEntry, Member
from sqlalchemy import select
from toads_api.comps.catalog import CLASSES, SPECS
from toads_api.comps.repository import InMemoryCompRepository, Seat
from toads_api.comps.service import CompError, CompService
from toads_api.identity import ROSTERS_SYNCED_KEY

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


def test_the_pool_marks_role_holders_who_never_signed_in() -> None:
    repo = InMemoryCompRepository(raid_days={1: ["wed"], 2: ["wed"]}, unsigned={2})
    assert [(e.name, e.signed_in) for e in _service(repo).pool("wed")] == [("Hopscotch", True), ("Lilypadd", False)]


def test_a_comp_is_named_sized_and_seats_each_member_once() -> None:
    svc = _service()
    svc.set_specs(2, "shaman", "shaman-restoration", None)
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
        ("Wrong class", 10, [Seat("mage-frost", 2)] + [None] * 9),
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


def test_losing_a_nights_role_takes_the_member_off_its_roster(hub: Hub) -> None:
    user = hub.user(("wed", "raider"))
    sid = hub.login(user)
    user.roles.clear()
    hub.pass_time(hub.services.settings.role_refresh_seconds + 1)
    assert hub.get("/api/session", sid).status_code == 401
    with hub.db() as db:
        row = db.scalars(select(Member).where(Member.discord_user_id == user.user_id)).one()
    assert row.raid_days == []


def _officer_pool(hub: Hub, sid: str, day: str = "wed") -> dict[str, dict[str, object]]:
    r = hub.get(f"/api/days/{day}/comps/pool", sid)
    assert r.status_code == 200, r.text
    return {e["name"]: e for e in r.json()}


def test_the_roster_lists_the_servers_role_holders_who_never_signed_in(hub: Hub) -> None:
    officer = hub.login(hub.user(("wed", "officer"), nick="Croak"))
    hub.user(("wed", "raider"), nick="Lilypadd")
    hub.user(("wed", "trial"), nick="Tadpole")
    hub.user(("sun", "raider"), nick="Ribbit")
    hub.user(nick="Lurker")
    hub.user(("wed", "raider"), nick="Gone", in_guild=False)
    with hub.db() as db:
        croak = db.scalars(select(Member.id).where(Member.display_name == "Croak")).one()
    # A role a super admin tied to the night's Toad badge counts as a raider role, as at sign-in.
    hub.services.role_badges.tie(77, "Wednesday alts", "wednesday-toad", by=croak)
    hub.user(nick="Alt").roles.add(77)

    pool = _officer_pool(hub, officer)
    assert sorted(pool) == ["Alt", "Croak", "Lilypadd", "Tadpole"]
    assert {n: e["signed_in"] for n, e in pool.items()} == {
        "Alt": False,
        "Croak": True,
        "Lilypadd": False,
        "Tadpole": False,
    }
    assert pool["Lilypadd"]["wow_class"] is None

    # Officers can seat them before they sign in; signing in keeps the same member, so the seat stays theirs.
    slots: list[object] = [None] * 10
    slots[0] = {"spec": "shaman-restoration", "member_id": pool["Lilypadd"]["member_id"]}
    assert hub.post("/api/days/wed/comps", officer, {"name": "Kara", "size": 10, "slots": slots}).status_code == 201
    lily = next(u for u in hub.fake.users.values() if u.nick == "Lilypadd")
    lily_sid = hub.login(lily)
    _put(hub, "/api/me/specs", lily_sid, {"wow_class": "shaman", "primary": "shaman-restoration"})
    entry = _officer_pool(hub, officer)["Lilypadd"]
    assert (entry["member_id"], entry["signed_in"], entry["primary"]) == (
        pool["Lilypadd"]["member_id"],
        True,
        "shaman-restoration",
    )
    assert hub.get("/api/days/wed/comps", officer).json()[0]["slots"][0]["member_name"] == "Lilypadd"


def test_the_server_is_read_once_per_role_refresh_and_losing_the_role_drops_them(hub: Hub) -> None:
    officer = hub.login(hub.user(("wed", "officer"), nick="Croak"))
    lily = hub.user(("wed", "raider"), nick="Lilypadd")
    assert "Lilypadd" in _officer_pool(hub, officer)
    lily.roles.clear()
    # Still listed until the next read of the server, at most role_refresh_seconds later.
    assert "Lilypadd" in _officer_pool(hub, officer)
    anyio.run(hub.redis.delete, ROSTERS_SYNCED_KEY)
    assert "Lilypadd" not in _officer_pool(hub, officer)


def test_when_discord_is_down_the_roster_reads_as_last_seen(hub: Hub) -> None:
    officer = hub.login(hub.user(("wed", "officer"), nick="Croak"))
    hub.fake.members_down = True
    hub.user(("wed", "raider"), nick="Lilypadd")
    assert sorted(_officer_pool(hub, officer)) == ["Croak"]
    hub.fake.members_down = False
    # The failed read did not count as a read, so the next request tries again.
    assert sorted(_officer_pool(hub, officer)) == ["Croak", "Lilypadd"]


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


def test_signing_in_stamps_the_sign_in(hub: Hub) -> None:
    user = hub.user(("wed", "raider"))
    officer = hub.login(hub.user(("wed", "officer")))
    hub.get("/api/days/wed/comps/pool", officer)
    with hub.db() as db:
        assert db.scalars(select(Member.signed_in_at).where(Member.discord_user_id == user.user_id)).one() is None
    hub.login(user)
    with hub.db() as db:
        assert db.scalars(select(Member.signed_in_at).where(Member.discord_user_id == user.user_id)).one() is not None
