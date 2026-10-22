"""Raid strategy docs (docs/strategy.md): the rules in StrategyService and the routes' edges. The main journeys are
the REQ-HUB-STRAT scenarios (tests/step_defs/test_hub_strat.py)."""

from __future__ import annotations

from dataclasses import replace

import pytest
from toads_api.strategy.repository import InMemoryStrategyRepository
from toads_api.strategy.service import NIGHT_LIMIT, StrategyError, StrategyService, google_link

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


def _docs(svc: StrategyService, raid: str) -> list[str]:
    return [v.doc.url for v in next(r for r in svc.library() if r.raid.id == raid).docs]


def test_every_raid_is_listed_in_order_even_with_no_doc() -> None:
    library = _svc().library()
    assert [r.raid.short for r in library] == ["MC", "BWL", "ZG", "AQ20", "AQ40", "Naxx", "TBD"]
    assert all(r.docs == [] for r in library)


def test_docs_are_added_to_a_raid_newest_first_and_shown_to_no_night() -> None:
    svc = _svc()
    first = svc.add("naxx", url=DOC + "1", by=1)
    assert (first.doc.title, first.added_by) == ("Naxxramas strategy", "Hopscotch")
    second = svc.add("naxx", url=f"  {DOC}2 ", title="  Naxx   full clear ", by=2)
    assert (second.doc.title, second.doc.url, second.added_by) == ("Naxx full clear", DOC + "2", None)
    assert _docs(svc, "naxx") == [DOC + "2", DOC + "1"]
    assert svc.night("wed").docs == []


@pytest.mark.parametrize(
    ("raid", "url", "title"),
    [("kara", DOC + "1", ""), ("mc", "https://example.com/doc", ""), ("mc", DOC + "1", "x" * 81)],
)
def test_bad_docs_are_refused(raid: str, url: str, title: str) -> None:
    svc = _svc()
    with pytest.raises(StrategyError) as info:
        svc.add(raid, url=url, title=title, by=1)
    assert info.value.status == 422
    assert svc.repo.docs() == []


def test_a_night_shows_the_docs_it_pins_in_order_once_each() -> None:
    svc = _svc()
    zg = svc.add("zg", url=DOC + "zg", by=1).doc.id
    bwl = svc.add("bwl", url=DOC + "bwl", by=1).doc.id
    night = svc.set_night("wed", [bwl, zg, bwl], by=1)
    assert [(d.raid.id, d.doc.doc.url) for d in night.docs] == [("bwl", DOC + "bwl"), ("zg", DOC + "zg")]
    assert svc.night_docs() == {"wed": [bwl, zg]}
    assert svc.night("sun").docs == []
    assert svc.set_night("wed", [], by=1).docs == []
    assert svc.night_docs() == {}


def test_a_night_pins_only_listed_docs_and_not_too_many() -> None:
    svc = _svc()
    ids = [svc.add("mc", url=f"{DOC}{i}", by=1).doc.id for i in range(NIGHT_LIMIT + 1)]
    with pytest.raises(StrategyError) as info:
        svc.set_night("wed", [ids[0], 999], by=1)
    assert info.value.status == 422
    with pytest.raises(StrategyError):
        svc.set_night("wed", ids, by=1)
    assert svc.night_docs() == {}


def test_taking_a_doc_down_takes_it_off_every_night() -> None:
    svc = _svc()
    doc = svc.add("mc", url=DOC + "mc", by=1).doc.id
    keep = svc.add("mc", url=DOC + "keep", by=1).doc.id
    svc.set_night("wed", [doc, keep], by=1)
    svc.set_night("sun", [doc], by=1)
    svc.remove(doc, by=1)
    assert svc.night_docs() == {"wed": [keep]}
    with pytest.raises(StrategyError) as info:
        svc.remove(doc, by=1)
    assert info.value.status == 404


def test_a_night_takes_down_only_docs_no_other_night_pins() -> None:
    svc = _svc()
    sun = svc.add("naxx", url=DOC + "sun", by=1).doc.id
    both = svc.add("naxx", url=DOC + "both", by=1).doc.id
    own = svc.add("naxx", url=DOC + "own", by=1).doc.id
    svc.set_night("sun", [sun, both], by=1)
    svc.set_night("wed", [both, own], by=1)
    for doc in (sun, both):
        with pytest.raises(StrategyError) as info:
            svc.remove(doc, by=1, through="wed", nights=frozenset({"wed"}))
        assert info.value.status == 409
    svc.remove(own, by=1, through="wed", nights=frozenset({"wed"}))
    with pytest.raises(StrategyError) as info:
        svc.remove(own, by=1, through="wed", nights=frozenset({"wed"}))
    assert info.value.status == 404
    svc.remove(sun, by=1, through="wed", nights=frozenset({"wed", "sun"}))
    svc.remove(both, by=1)
    assert _docs(svc, "naxx") == []


def test_a_night_skips_a_doc_for_a_retired_raid_or_one_gone() -> None:
    svc = _svc()
    mc = svc.add("mc", url=DOC + "mc", by=1).doc.id
    svc.repo.rows.append(replace(svc.repo.rows[0], id=50, raid="kara"))
    svc.repo.nights["wed"] = [50, 77, mc]
    assert [d.raid.id for d in svc.night("wed").docs] == ["mc"]
    assert all(v.doc.raid != "kara" for r in svc.library() for v in r.docs)


# ---------------------------------------------------------------- routes


def test_the_library_lists_each_docs_nights_in_config_order(hub: Hub) -> None:
    sid = hub.login(hub.user(("global", "officer")))
    doc = hub.post("/api/admin/strategy", sid, {"raid": "aq40", "url": DOC + "1"}).json()
    assert (doc["raid"], doc["title"]) == ("aq40", "Temple of Ahn'Qiraj strategy")
    for day in ("sun", "wed"):
        assert hub.put(f"/api/days/{day}/strategy", sid, {"docs": [doc["id"]]}).status_code == 200
    library = hub.get("/api/strategy", sid).json()
    [aq40] = next(x for x in library["raids"] if x["raid"]["id"] == "aq40")["docs"]
    assert aq40["nights"] == ["wed", "sun"] and aq40["added_by"]
    assert [(n["raid_day"], n["docs"]) for n in library["nights"]] == [
        ("wed", [doc["id"]]),
        ("thu", []),
        ("sun", [doc["id"]]),
    ]
    assert hub.delete(f"/api/admin/strategy/{doc['id']}", sid).status_code == 204
    assert hub.delete(f"/api/admin/strategy/{doc['id']}", sid).status_code == 404
    assert hub.get("/api/days/wed/strategy", sid).json() == {"raid_day": "wed", "docs": []}


def test_a_nights_officer_adds_docs_and_pins_their_night(hub: Hub) -> None:
    sid = hub.login(hub.user(("wed", "officer")))
    doc = hub.post("/api/days/wed/strategy/docs", sid, {"raid": "bwl", "url": DOC + "1", "title": "BWL"}).json()
    bad = hub.post("/api/days/wed/strategy/docs", sid, {"raid": "bwl", "url": "https://example.com/x"})
    assert bad.status_code == 422
    assert hub.post("/api/days/sun/strategy/docs", sid, {"raid": "bwl", "url": DOC + "3"}).status_code == 403
    r = hub.put("/api/days/wed/strategy", sid, {"docs": [doc["id"]]})
    assert [(d["raid"]["short"], d["doc"]["title"]) for d in r.json()["docs"]] == [("BWL", "BWL")]
    assert hub.put("/api/days/wed/strategy", sid, {"docs": [doc["id"], 99]}).status_code == 422
    assert hub.put("/api/days/sun/strategy", sid, {"docs": []}).status_code == 403
    assert hub.get("/api/days/nope/strategy", sid).status_code == 404
    assert hub.delete(f"/api/days/wed/strategy/docs/{doc['id']}", sid).status_code == 204
    assert hub.delete(f"/api/days/wed/strategy/docs/{doc['id']}", sid).status_code == 404


def test_strategy_needs_a_signed_in_member(hub: Hub) -> None:
    assert hub.get("/api/strategy", None).status_code == 401
    member = hub.login(hub.user())
    assert hub.get("/api/strategy", member).status_code == 200
    assert hub.post("/api/admin/strategy", member, {"raid": "mc", "url": DOC + "1"}).status_code == 403


def test_the_audit_log_names_the_night_an_officer_acted_through(hub: Hub) -> None:
    from hub_db import AuditEntry
    from sqlalchemy import select

    sid = hub.login(hub.user(("wed", "officer")))
    doc = hub.post("/api/days/wed/strategy/docs", sid, {"raid": "mc", "url": DOC + "1"}).json()
    hub.put("/api/days/wed/strategy", sid, {"docs": [doc["id"]]})
    assert hub.delete(f"/api/days/wed/strategy/docs/{doc['id']}", sid).status_code == 204
    with hub.services.db() as db:
        rows = [
            (a.action, a.raid_day_id, a.detail)
            for a in db.scalars(select(AuditEntry).where(AuditEntry.action.like("strategy.%")).order_by(AuditEntry.id))
        ]
    assert rows == [
        ("strategy.add", "wed", "mc"),
        ("strategy.night", "wed", str(doc["id"])),
        ("strategy.remove", "wed", "mc"),
    ]


def test_a_night_saved_twice_at_once_ends_up_with_one_list(hub: Hub) -> None:
    from hub_db import NightDoc
    from sqlalchemy.exc import IntegrityError
    from toads_api.strategy.sql import SqlStrategyRepository

    repo = SqlStrategyRepository(hub.services.db)
    first, second = (repo.add("mc", "MC", f"{DOC}{i}", 1).id for i in range(2))
    real = repo._set_night_docs
    calls = 0

    def racing(raid_day: str, doc_ids: list[int], by: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            # Another officer's save lands between this one's delete and its insert, so its insert collides.
            with hub.services.db.begin() as db:
                db.add(NightDoc(raid_day_id=raid_day, doc_id=first))
            raise IntegrityError("INSERT INTO night_strategy_docs", {}, Exception("duplicate key"))
        real(raid_day, doc_ids, by)

    repo._set_night_docs = racing  # type: ignore[method-assign]
    repo.set_night_docs("wed", [second, first], 1)
    assert (calls, repo.night_docs()) == (2, {"wed": [second, first]})

    def always(raid_day: str, doc_ids: list[int], by: int) -> None:
        raise IntegrityError("INSERT INTO night_strategy_docs", {}, Exception("duplicate key"))

    repo._set_night_docs = always  # type: ignore[method-assign]
    with pytest.raises(IntegrityError):
        repo.set_night_docs("wed", [first], 1)


def test_postgres_saves_of_one_nights_docs_take_turns() -> None:
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
            assert "pg_advisory_xact_lock" in seen[0][0] and seen[0][1] == {"key": "night_strategy:wed"}


def test_the_database_checks_other_nights_pins_as_it_takes_a_doc_down(hub: Hub) -> None:
    from toads_api.strategy.sql import SqlStrategyRepository

    repo = SqlStrategyRepository(hub.services.db)
    doc = repo.add("mc", "MC", DOC + "1", 1).id
    repo.set_night_docs("sun", [doc], 1)
    assert repo.remove(doc, 1, "wed", frozenset({"wed"})) == "pinned"
    assert repo.remove(doc, 1, "wed", frozenset({"wed", "sun"})) == "removed"
    assert repo.remove(doc, 1, None, None) == "missing"
    assert repo.night_docs() == {}


def test_a_doc_taken_down_while_a_night_saves_is_left_out(hub: Hub) -> None:
    from toads_api.strategy.sql import SqlStrategyRepository

    repo = SqlStrategyRepository(hub.services.db)
    keep, gone = (repo.add("mc", "MC", f"{DOC}{i}", 1).id for i in range(2))
    repo.remove(gone, 1)
    repo.set_night_docs("wed", [gone, keep], 1)
    assert repo.night_docs() == {"wed": [keep]}
