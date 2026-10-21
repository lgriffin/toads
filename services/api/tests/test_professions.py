"""Members' professions and the guild's crafters (docs/professions.md): the rules in ProfessionService, the routes, and
the catalogue against the web app's list."""

from __future__ import annotations

import re
from pathlib import Path

import httpx
import pytest
from hub_db import AuditEntry
from sqlalchemy import select
from toads_api.professions.catalog import PROFESSIONS
from toads_api.professions.repository import InMemoryProfessionRepository, ProfessionRecord
from toads_api.professions.service import ProfessionError, ProfessionService

from conftest import Hub

ROOT = Path(__file__).resolve().parents[3]
NAMES = {1: "Hopscotch", 2: "Lilypadd", 3: "Ribbit"}


def _service(repo: InMemoryProfessionRepository | None = None) -> ProfessionService:
    return ProfessionService(
        repo or InMemoryProfessionRepository(), lambda ids: {i: NAMES[i] for i in ids if i in NAMES}
    )


def _p(profession: str, skill: int | None = None, spec: str | None = None) -> ProfessionRecord:
    return ProfessionRecord(0, profession, skill, spec)


# ---------------------------------------------------------------- rules


def test_professions_are_known_listed_once_with_a_skill_in_range_and_their_own_specialisation() -> None:
    svc = _service()
    mine, gone = svc.set_mine(1, [_p("tailoring", 375, "spellfire"), _p("alchemy"), _p("cooking", 300)])
    assert [(r.member_id, r.profession) for r in mine.professions] == [(1, "alchemy"), (1, "cooking"), (1, "tailoring")]
    assert gone == []
    for bad in (
        [_p("archaeology")],
        [_p("alchemy"), _p("alchemy", 10)],
        [_p("alchemy", 0)],
        [_p("alchemy", 376)],
        [_p("alchemy", 300, "spellfire")],
        [_p("enchanting", 300, "anything")],
    ):
        with pytest.raises(ProfessionError) as info:
            svc.set_mine(1, bad)
        assert info.value.status == 422, bad
    assert [r.profession for r in svc.mine(1).professions] == ["alchemy", "cooking", "tailoring"]
    assert svc.set_mine(1, [])[0].professions == []


def test_officers_name_crafters_only_for_professions_the_member_lists() -> None:
    svc = _service()
    svc.set_mine(2, [_p("alchemy", 375, "transmute")])
    with pytest.raises(ProfessionError) as info:
        svc.designate("tailoring", 2, None, by=1)
    assert info.value.status == 422
    for profession, member in (("archaeology", 2), ("alchemy", 42)):
        with pytest.raises(ProfessionError):
            svc.designate(profession, member, None, by=1)
    view = svc.designate("alchemy", 2, "  Flasks   and transmutes ", by=1)
    assert (view.member_name, view.skill, view.specialisation, view.note, view.designated_by) == (
        "Lilypadd",
        375,
        "transmute",
        "Flasks and transmutes",
        "Hopscotch",
    )
    with pytest.raises(ProfessionError):
        svc.designate("alchemy", 2, "x" * 201, by=1)
    assert [n.profession for n in svc.mine(2).crafter_for] == ["alchemy"]
    svc.undesignate("alchemy", 2, by=1)
    with pytest.raises(ProfessionError) as info:
        svc.undesignate("alchemy", 2, by=1)
    assert info.value.status == 404


def test_dropping_a_profession_ends_its_crafter_naming() -> None:
    svc = _service()
    svc.set_mine(2, [_p("alchemy"), _p("enchanting")])
    svc.designate("alchemy", 2, None, by=1)
    svc.designate("enchanting", 2, None, by=1)
    mine, gone = svc.set_mine(2, [_p("enchanting", 375)])
    assert gone == ["alchemy"]
    assert [n.profession for n in mine.crafter_for] == ["enchanting"]


def test_a_nights_officers_reach_only_that_nights_members() -> None:
    repo = InMemoryProfessionRepository(raid_days={1: ["wed"], 2: ["wed"], 3: ["sun"]})
    svc = _service(repo)
    svc.set_mine(3, [_p("mining")])
    svc.set_mine(2, [_p("enchanting", 375)])
    assert [(m.name, len(m.professions)) for m in svc.roster("wed")] == [("Hopscotch", 0), ("Lilypadd", 1)]
    with pytest.raises(ProfessionError) as info:
        svc.designate("mining", 3, None, by=1, raid_day="wed")
    assert info.value.status == 404
    svc.designate("mining", 3, None, by=1, raid_day="sun")
    with pytest.raises(ProfessionError):
        svc.undesignate("mining", 3, by=1, raid_day="wed")
    # The guild-wide list holds only members who list something, and the crafters in catalogue order.
    svc.designate("enchanting", 2, None, by=1)
    assert [m.name for m in svc.everyone()] == ["Lilypadd", "Ribbit"]
    assert [(c.profession, c.member_name) for c in svc.crafters()] == [("enchanting", "Lilypadd"), ("mining", "Ribbit")]


# ---------------------------------------------------------------- catalogue


def test_catalogue_matches_the_web_app() -> None:
    ts = (ROOT / "apps/web/src/lib/professions.ts").read_text(encoding="utf-8")
    web = re.findall(r"\{ id: '([a-z-]+)', name: '([^']+)', secondary: (true|false), specialisations: \[(.*?)\] \}", ts)
    assert [(i, n, s == "true") for i, n, s, _ in web] == [(p.id, p.name, p.secondary) for p in PROFESSIONS.values()]
    for (pid, _, _, specs), p in zip(web, PROFESSIONS.values(), strict=True):
        assert re.findall(r"\['([a-z-]+)', '([^']+)'\]", specs) == list(p.specialisations), pid


# ---------------------------------------------------------------- routes


def _put(hub: Hub, path: str, sid: str | None, body: object) -> httpx.Response:
    return hub.client.put(path, headers=hub.as_(sid), json=body)


def test_a_member_sets_and_reads_their_professions(hub: Hub) -> None:
    sid = hub.login(hub.user(("wed", "raider")))
    assert hub.get("/api/me/professions", sid).json() == {"professions": [], "crafter_for": [], "unnamed": []}
    body = {
        "professions": [{"profession": "alchemy", "skill": 375, "specialisation": "elixir"}, {"profession": "fishing"}]
    }
    r = _put(hub, "/api/me/professions", sid, body)
    assert r.status_code == 200, r.text
    assert hub.get("/api/me/professions", sid).json()["professions"] == [
        {"profession": "alchemy", "skill": 375, "specialisation": "elixir"},
        {"profession": "fishing", "skill": None, "specialisation": None},
    ]
    assert (
        _put(hub, "/api/me/professions", sid, {"professions": [{"profession": "alchemy", "skill": 400}]}).status_code
        == 422
    )
    assert hub.get("/api/me/professions", None).status_code == 401


def test_a_nights_officer_sees_its_professions_and_names_crafters(hub: Hub) -> None:
    lily = hub.login(hub.user(("wed", "raider"), nick="Lilypadd"))
    ribbit = hub.login(hub.user(("sun", "raider"), nick="Ribbit"))
    hub.user(("wed", "trial"), nick="Tadpole")
    officer = hub.login(hub.user(("wed", "officer"), nick="Croak"))
    sunday = hub.login(hub.user(("sun", "officer"), nick="Bogwort"))
    _put(hub, "/api/me/professions", lily, {"professions": [{"profession": "alchemy", "skill": 375}]})
    _put(hub, "/api/me/professions", ribbit, {"professions": [{"profession": "tailoring"}]})

    night = hub.get("/api/days/wed/professions", officer)
    assert night.status_code == 200, night.text
    members = {m["name"]: m for m in night.json()["members"]}
    assert sorted(members) == ["Croak", "Lilypadd", "Tadpole"]
    assert members["Lilypadd"]["professions"][0]["profession"] == "alchemy"
    lily_id = members["Lilypadd"]["member_id"]
    assert hub.get("/api/days/wed/professions", sunday).status_code == 403
    assert hub.get("/api/days/wed/professions", lily).status_code == 403

    named = _put(hub, f"/api/days/wed/crafters/alchemy/{lily_id}", officer, {"note": "Flasks"})
    assert named.status_code == 200, named.text
    assert (named.json()["member_name"], named.json()["note"], named.json()["designated_by"]) == (
        "Lilypadd",
        "Flasks",
        "Croak",
    )
    # Another night's officer cannot reach Wednesday's members, from their own night or Wednesday's.
    assert _put(hub, f"/api/days/sun/crafters/alchemy/{lily_id}", sunday, {}).status_code == 404
    assert _put(hub, f"/api/days/wed/crafters/alchemy/{lily_id}", sunday, {}).status_code == 403
    assert _put(hub, f"/api/days/wed/crafters/enchanting/{lily_id}", officer, {}).status_code == 422
    # The crafters are guild-wide, so the Sunday officer sees Wednesday's alchemist, and the member sees it on Me.
    assert [c["member_name"] for c in hub.get("/api/days/sun/professions", sunday).json()["crafters"]] == ["Lilypadd"]
    assert hub.get("/api/me/professions", lily).json()["crafter_for"][0]["note"] == "Flasks"
    with hub.db() as db:
        actions = list(db.scalars(select(AuditEntry.action).where(AuditEntry.action.like("crafter.%"))))
    assert actions == ["crafter.name"]

    assert hub.delete(f"/api/days/wed/crafters/alchemy/{lily_id}", officer).status_code == 204
    assert hub.delete(f"/api/days/wed/crafters/alchemy/{lily_id}", officer).status_code == 404


def test_the_global_tier_sees_everyone_and_names_anyone(hub: Hub) -> None:
    lily = hub.login(hub.user(("wed", "raider"), nick="Lilypadd"))
    hub.login(hub.user(("sun", "raider"), nick="Ribbit"))
    chief = hub.login(hub.user(("global", "officer"), nick="Kingtoad"))
    officer = hub.login(hub.user(("wed", "officer"), nick="Croak"))
    _put(hub, "/api/me/professions", lily, {"professions": [{"profession": "enchanting", "skill": 375}]})

    overview = hub.get("/api/admin/professions", chief)
    assert overview.status_code == 200, overview.text
    assert [m["name"] for m in overview.json()["members"]] == ["Lilypadd"]
    lily_id = overview.json()["members"][0]["member_id"]
    assert hub.get("/api/admin/professions", officer).status_code == 403
    assert _put(hub, f"/api/admin/crafters/enchanting/{lily_id}", officer, {}).status_code == 403
    assert _put(hub, f"/api/admin/crafters/enchanting/{lily_id}", chief, {}).status_code == 200

    # Dropping the profession on Me ends the naming, and the reply says so.
    dropped = _put(hub, "/api/me/professions", lily, {"professions": []})
    assert dropped.json()["unnamed"] == ["enchanting"]
    assert hub.get("/api/admin/professions", chief).json() == {"members": [], "crafters": []}
    assert hub.delete(f"/api/admin/crafters/enchanting/{lily_id}", chief).status_code == 404
