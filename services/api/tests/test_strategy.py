"""Raid strategy docs (docs/strategy.md): the rules in StrategyService and the routes' edges. The main journeys are
the REQ-HUB-STRAT scenarios (tests/step_defs/test_hub_strat.py)."""

from __future__ import annotations

import pytest
from toads_api.strategy.repository import InMemoryStrategyRepository
from toads_api.strategy.service import KEEP, RAIDS, Slot, StrategyError, StrategyService, google_link

from conftest import Hub

DOC = "https://docs.google.com/document/d/"


def _svc(repo: InMemoryStrategyRepository | None = None) -> StrategyService:
    names = {1: "Hopscotch"}
    return StrategyService(repo or InMemoryStrategyRepository(), lambda ids: {i: names[i] for i in ids if i in names})


@pytest.mark.parametrize(
    ("url", "ok"),
    [
        (DOC + "abc/edit", True),
        ("https://drive.google.com/file/d/abc/view", True),
        ("https://docs.google.com:443/spreadsheets/d/abc", True),
        ("http://docs.google.com/document/d/abc", False),
        ("https://docs.google.com.evil.example/document/d/abc", False),
        ("https://evil.example/?u=https://docs.google.com/", False),
        ("https://user:pw@docs.google.com/document/d/abc", False),
        ("https://docs.google.com:99999/document/d/abc", False),
        ("https://docs.google.com/document/d/a b", False),
        ("javascript:alert(1)", False),
        ("", False),
    ],
)
def test_only_https_google_docs_and_drive_links_are_pinned(url: str, ok: bool) -> None:
    assert google_link(url) is ok


def _slots(svc: StrategyService, raid: str, nights: tuple[str, ...] = ()) -> list[Slot]:
    return next(r for r in svc.library(nights) if r.raid.id == raid).slots


def test_every_raid_is_listed_in_order_even_with_no_doc() -> None:
    library = _svc().library()
    assert [r.raid.short for r in library] == ["MC", "BWL", "ZG", "AQ20", "AQ40", "Naxx", "TBD"]
    assert all(r.slots == [] for r in library)


def test_a_new_doc_replaces_the_pinned_one_and_keeps_it_below() -> None:
    svc = _svc()
    first = svc.pin("naxx", url=DOC + "1", by=1)
    assert (first.doc.title, first.added_by) == ("Naxxramas strategy", "Hopscotch")
    svc.pin("naxx", url=f"  {DOC}2 ", title="  Naxx   full clear ", by=2)
    [slot] = _slots(svc, "naxx")
    assert (slot.raid_day, slot.pinned.doc.title, slot.pinned.doc.url, slot.pinned.added_by) == (
        None,
        "Naxx full clear",
        DOC + "2",
        None,
    )
    assert [v.doc.url for v in slot.replaced] == [DOC + "1"]


def test_a_raid_keeps_only_its_newest_docs_for_each_night() -> None:
    svc = _svc()
    for i in range(KEEP + 2):
        svc.pin("mc", url=f"{DOC}{i}", by=1)
        svc.pin("mc", url=f"{DOC}wed{i}", by=1, raid_day="wed")
    svc.pin("bwl", url=DOC + "bwl", by=1)
    every, wed = _slots(svc, "mc")
    assert (every.raid_day, every.pinned.doc.url, len(every.replaced)) == (None, f"{DOC}{KEEP + 1}", KEEP - 1)
    assert (wed.raid_day, wed.pinned.doc.url, len(wed.replaced)) == ("wed", f"{DOC}wed{KEEP + 1}", KEEP - 1)


def test_nights_slots_follow_the_order_asked_for_after_every_night() -> None:
    svc = _svc()
    for day in ("zz", "wed", "sun", "aa"):
        svc.pin("zg", url=DOC + day, by=1, raid_day=day)
    svc.pin("zg", url=DOC + "all", by=1)
    assert [s.raid_day for s in _slots(svc, "zg", ("sun", "wed"))] == [None, "sun", "wed", "aa", "zz"]


@pytest.mark.parametrize(
    ("raid", "url", "title"),
    [("kara", DOC + "1", ""), ("mc", "https://example.com/doc", ""), ("mc", DOC + "1", "x" * 81)],
)
def test_bad_pins_are_refused(raid: str, url: str, title: str) -> None:
    svc = _svc()
    with pytest.raises(StrategyError) as info:
        svc.pin(raid, url=url, title=title, by=1, raid_day="wed")
    assert info.value.status == 422
    assert svc.night_raids() == {}


def test_taking_down_the_pinned_doc_pins_the_one_before() -> None:
    svc = _svc()
    svc.pin("zg", url=DOC + "1", by=1)
    second = svc.pin("zg", url=DOC + "2", by=1)
    svc.remove(second.doc.id, by=1)
    assert svc.night("wed").raids == []
    svc.set_night("wed", ["zg"], by=1)
    [zg] = svc.night("wed").raids
    assert zg.raid == RAIDS["zg"] and zg.pinned is not None and zg.pinned.doc.url == DOC + "1"
    with pytest.raises(StrategyError) as info:
        svc.remove(second.doc.id, by=1)
    assert info.value.status == 404


def test_a_night_takes_down_only_its_own_and_every_night_docs() -> None:
    svc = _svc()
    sun = svc.pin("naxx", url=DOC + "sun", by=1, raid_day="sun")
    every = svc.pin("naxx", url=DOC + "all", by=1)
    with pytest.raises(StrategyError):
        svc.remove(sun.doc.id, by=1, nights=frozenset({"wed", None}))
    svc.remove(every.doc.id, by=1, nights=frozenset({"wed", None}))
    assert [s.raid_day for s in _slots(svc, "naxx")] == ["sun"]


def test_a_doc_pinned_for_a_night_adds_its_raid_to_the_night_once() -> None:
    svc = _svc()
    svc.set_night("wed", ["mc"], by=1)
    svc.pin("bwl", url=DOC + "1", by=1, raid_day="wed")
    svc.pin("bwl", url=DOC + "2", by=1, raid_day="wed")
    svc.pin("zg", url=DOC + "3", by=1)
    assert svc.night_raids() == {"wed": ["mc", "bwl"]}
    mc, bwl = svc.night("wed").raids
    assert (mc.pinned, bwl.pinned and bwl.pinned.doc.url) == (None, DOC + "2")


def test_a_nights_own_doc_comes_before_the_every_night_one() -> None:
    svc = _svc()
    svc.pin("aq40", url=DOC + "all", by=1)
    svc.pin("aq40", url=DOC + "sun", by=1, raid_day="sun")
    svc.set_night("wed", ["aq40"], by=1)
    assert [r.pinned and r.pinned.doc.url for r in svc.night("sun").raids] == [DOC + "sun"]
    assert [r.pinned and r.pinned.doc.url for r in svc.night("wed").raids] == [DOC + "all"]


def test_a_night_runs_its_raids_in_order_once_each_and_can_be_cleared() -> None:
    svc = _svc()
    night = svc.set_night("sun", ["tbd", "mc", "tbd"], by=1)
    assert [(r.raid.id, r.pinned) for r in night.raids] == [("tbd", None), ("mc", None)]
    with pytest.raises(StrategyError):
        svc.set_night("sun", ["mc", "kara"], by=1)
    assert svc.night_raids() == {"sun": ["tbd", "mc"]}
    assert svc.set_night("sun", [], by=1).raids == []
    assert svc.night_raids() == {}


def test_a_night_skips_a_raid_that_was_retired() -> None:
    svc = _svc(InMemoryStrategyRepository(nights={"wed": ["kara", "mc"]}))
    assert [r.raid.id for r in svc.night("wed").raids] == ["mc"]


# ---------------------------------------------------------------- routes


def test_the_database_keeps_only_a_raids_newest_docs(hub: Hub) -> None:
    sid = hub.login(hub.user(("global", "officer")))
    for i in range(KEEP + 1):
        r = hub.post("/api/admin/strategy", sid, {"raid": "aq40", "url": f"{DOC}{i}"})
        assert r.status_code == 201, r.text
    aq40 = next(x for x in hub.get("/api/strategy", sid).json()["raids"] if x["raid"]["id"] == "aq40")
    [slot] = aq40["slots"]
    assert (slot["raid_day"], slot["name"], slot["pinned"]["url"]) == (None, "Every night", f"{DOC}{KEEP}")
    assert [d["url"] for d in slot["replaced"]] == [f"{DOC}{i}" for i in range(KEEP - 1, 0, -1)]
    assert slot["pinned"]["added_by"]


def test_the_global_tier_pins_for_a_night_that_exists(hub: Hub) -> None:
    sid = hub.login(hub.user(("global", "officer")))
    r = hub.post("/api/admin/strategy", sid, {"raid": "mc", "url": DOC + "1", "raid_day": "nope"})
    assert (r.status_code, r.json()["detail"]) == (422, "Unknown raid night")
    r = hub.post("/api/admin/strategy", sid, {"raid": "mc", "url": DOC + "1", "raid_day": "sun"})
    assert (r.status_code, r.json()["raid_day"]) == (201, "sun")
    library = hub.get("/api/strategy", sid).json()
    assert next(n for n in library["nights"] if n["raid_day"] == "sun")["raids"] == ["mc"]
    assert hub.delete(f"/api/admin/strategy/{r.json()['id']}", sid).status_code == 204
    assert hub.delete(f"/api/admin/strategy/{r.json()['id']}", sid).status_code == 404


def test_a_nights_officer_pins_for_their_night_or_every_night(hub: Hub) -> None:
    sid = hub.login(hub.user(("wed", "officer")))
    own = hub.post("/api/days/wed/strategy/docs", sid, {"raid": "bwl", "url": DOC + "1"})
    every = hub.post("/api/days/wed/strategy/docs", sid, {"raid": "bwl", "url": DOC + "2", "every_night": True})
    assert (own.json()["raid_day"], every.json()["raid_day"]) == ("wed", None)
    bad = hub.post("/api/days/wed/strategy/docs", sid, {"raid": "bwl", "url": "https://example.com/x"})
    assert bad.status_code == 422
    assert hub.post("/api/days/sun/strategy/docs", sid, {"raid": "bwl", "url": DOC + "3"}).status_code == 403
    assert hub.delete(f"/api/days/wed/strategy/docs/{own.json()['id']}", sid).status_code == 204
    assert hub.delete(f"/api/days/wed/strategy/docs/{own.json()['id']}", sid).status_code == 404


def test_a_night_can_be_moved_between_raids_and_cleared(hub: Hub) -> None:
    sid = hub.login(hub.user(("wed", "officer")))
    for raids in (["mc"], ["aq20", "zg"], []):
        r = hub.put("/api/days/wed/strategy", sid, {"raids": raids})
        assert r.status_code == 200, r.text
        assert [x["raid"]["id"] for x in r.json()["raids"]] == raids
    assert hub.put("/api/days/wed/strategy", sid, {"raids": ["kara"]}).status_code == 422
    assert hub.get("/api/days/wed/strategy", sid).json() == {"raid_day": "wed", "raids": []}
    assert hub.get("/api/days/nope/strategy", sid).status_code == 404


def test_strategy_needs_a_signed_in_member(hub: Hub) -> None:
    assert hub.get("/api/strategy", None).status_code == 401
    member = hub.login(hub.user())
    assert hub.get("/api/strategy", member).status_code == 200
    assert hub.post("/api/admin/strategy", member, {"raid": "mc", "url": DOC + "1"}).status_code == 403


def test_a_night_picked_twice_at_once_ends_up_updated(hub: Hub) -> None:
    from hub_db import NightRaid
    from sqlalchemy.exc import IntegrityError
    from toads_api.strategy.sql import SqlStrategyRepository

    repo = SqlStrategyRepository(hub.services.db)
    real = repo._set_night_raids
    calls = 0

    def racing(raid_day: str, raids: list[str], by: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            # Another officer's pick lands between this one's delete and its insert, so its insert collides.
            with hub.services.db.begin() as db:
                db.add(NightRaid(raid_day_id=raid_day, raid="mc"))
            raise IntegrityError("INSERT INTO night_raid_choices", {}, Exception("duplicate key"))
        real(raid_day, raids, by)

    repo._set_night_raids = racing  # type: ignore[method-assign]
    repo.set_night_raids("wed", ["bwl", "mc"], 1)
    assert (calls, repo.night_raids()) == (2, {"wed": ["bwl", "mc"]})

    def always(raid_day: str, raids: list[str], by: int) -> None:
        raise IntegrityError("INSERT INTO night_raid_choices", {}, Exception("duplicate key"))

    repo._set_night_raids = always  # type: ignore[method-assign]
    with pytest.raises(IntegrityError):
        repo.set_night_raids("wed", ["mc"], 1)


def test_the_audit_log_names_the_night_an_officer_acted_through(hub: Hub) -> None:
    from hub_db import AuditEntry
    from sqlalchemy import select

    sid = hub.login(hub.user(("wed", "officer")))
    every = hub.post("/api/days/wed/strategy/docs", sid, {"raid": "mc", "url": DOC + "1", "every_night": True}).json()
    hub.post("/api/days/wed/strategy/docs", sid, {"raid": "bwl", "url": DOC + "2"})
    assert hub.delete(f"/api/days/wed/strategy/docs/{every['id']}", sid).status_code == 204
    with hub.services.db() as db:
        rows = [
            (a.action, a.raid_day_id, a.detail)
            for a in db.scalars(select(AuditEntry).where(AuditEntry.action.like("strategy.%")).order_by(AuditEntry.id))
        ]
    assert rows == [
        ("strategy.pin", "wed", "mc for every night"),
        ("strategy.pin", "wed", "bwl for wed"),
        ("strategy.remove", "wed", "mc for every night"),
    ]


def test_a_doc_pinned_for_a_night_joins_the_end_of_its_raids_in_the_same_write(hub: Hub) -> None:
    from toads_api.strategy.sql import SqlStrategyRepository

    repo = SqlStrategyRepository(hub.services.db)
    repo.pin("bwl", "sun", "BWL", DOC + "1", 1, KEEP)
    repo.set_night_raids("wed", ["zg", "mc"], 1)
    repo.pin("aq20", "wed", "AQ20", DOC + "2", 1, KEEP)
    repo.pin("zg", "wed", "ZG", DOC + "3", 1, KEEP)
    repo.pin("naxx", None, "Naxx", DOC + "4", 1, KEEP)
    assert repo.night_raids() == {"sun": ["bwl"], "wed": ["zg", "mc", "aq20"]}


def test_postgres_saves_of_one_nights_raids_take_turns() -> None:
    from types import SimpleNamespace
    from typing import Any

    from toads_api.strategy.sql import _lock_night

    for dialect, locks in (("postgresql", 1), ("sqlite", 0)):
        seen: list[Any] = []
        db = SimpleNamespace(
            get_bind=lambda d=dialect: SimpleNamespace(dialect=SimpleNamespace(name=d)),
            execute=lambda stmt, params, seen=seen: seen.append((str(stmt), params)),
        )
        _lock_night(db, "wed")  # type: ignore[arg-type]
        assert len(seen) == locks
        if locks:
            assert "pg_advisory_xact_lock" in seen[0][0] and seen[0][1] == {"key": "night_raid:wed"}
