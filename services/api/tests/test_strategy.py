"""Raid strategy docs (docs/strategy.md): the rules in StrategyService and the routes' edges. The main journeys are
the REQ-HUB-STRAT scenarios (tests/step_defs/test_hub_strat.py)."""

from __future__ import annotations

import pytest
from toads_api.strategy.repository import InMemoryStrategyRepository
from toads_api.strategy.service import KEEP, RAIDS, StrategyError, StrategyService, google_link

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


def test_every_raid_is_listed_in_order_even_with_no_doc() -> None:
    library = _svc().library()
    assert [r.raid.short for r in library] == ["MC", "BWL", "ZG", "AQ20", "AQ40", "Naxx", "TBD"]
    assert all(r.pinned is None and r.replaced == [] for r in library)


def test_a_new_doc_replaces_the_pinned_one_and_keeps_it_below() -> None:
    svc = _svc()
    first = svc.pin("naxx", url=DOC + "1", by=1)
    assert (first.doc.title, first.added_by) == ("Naxxramas strategy", "Hopscotch")
    svc.pin("naxx", url=f"  {DOC}2 ", title="  Naxx   full clear ", by=2)
    naxx = next(r for r in svc.library() if r.raid.id == "naxx")
    assert naxx.pinned is not None
    assert (naxx.pinned.doc.title, naxx.pinned.doc.url, naxx.pinned.added_by) == ("Naxx full clear", DOC + "2", None)
    assert [v.doc.url for v in naxx.replaced] == [DOC + "1"]


def test_a_raid_keeps_only_its_newest_docs() -> None:
    svc = _svc()
    for i in range(KEEP + 2):
        svc.pin("mc", url=f"{DOC}{i}", by=1)
    svc.pin("bwl", url=DOC + "bwl", by=1)
    mc = next(r for r in svc.library() if r.raid.id == "mc")
    assert mc.pinned is not None and mc.pinned.doc.url == f"{DOC}{KEEP + 1}"
    assert len(mc.replaced) == KEEP - 1


@pytest.mark.parametrize(
    ("raid", "url", "title"),
    [("kara", DOC + "1", ""), ("mc", "https://example.com/doc", ""), ("mc", DOC + "1", "x" * 81)],
)
def test_bad_pins_are_refused(raid: str, url: str, title: str) -> None:
    with pytest.raises(StrategyError) as info:
        _svc().pin(raid, url=url, title=title, by=1)
    assert info.value.status == 422


def test_taking_down_the_pinned_doc_pins_the_one_before() -> None:
    svc = _svc()
    svc.pin("zg", url=DOC + "1", by=1)
    second = svc.pin("zg", url=DOC + "2", by=1)
    svc.remove(second.doc.id, by=1)
    assert svc.night("wed").raid is None
    svc.set_night("wed", "zg", by=1)
    night = svc.night("wed")
    assert night.raid == RAIDS["zg"] and night.pinned is not None and night.pinned.doc.url == DOC + "1"
    with pytest.raises(StrategyError) as info:
        svc.remove(second.doc.id, by=1)
    assert info.value.status == 404


def test_a_night_running_a_raid_with_no_doc_shows_the_raid_alone() -> None:
    svc = _svc()
    night = svc.set_night("sun", "tbd", by=1)
    assert (night.raid, night.pinned) == (RAIDS["tbd"], None)
    with pytest.raises(StrategyError):
        svc.set_night("sun", "kara", by=1)
    assert svc.set_night("sun", None, by=1).raid is None
    assert svc.night_raids() == {}


def test_a_night_whose_raid_was_retired_shows_none() -> None:
    svc = _svc(InMemoryStrategyRepository(nights={"wed": "kara"}))
    assert svc.night("wed").raid is None


# ---------------------------------------------------------------- routes


def test_the_database_keeps_only_a_raids_newest_docs(hub: Hub) -> None:
    sid = hub.login(hub.user(("global", "officer")))
    for i in range(KEEP + 1):
        r = hub.post("/api/admin/strategy", sid, {"raid": "aq40", "url": f"{DOC}{i}"})
        assert r.status_code == 201, r.text
    aq40 = next(x for x in hub.get("/api/strategy", sid).json()["raids"] if x["raid"]["id"] == "aq40")
    assert aq40["pinned"]["url"] == f"{DOC}{KEEP}"
    assert [d["url"] for d in aq40["replaced"]] == [f"{DOC}{i}" for i in range(KEEP - 1, 0, -1)]
    assert aq40["pinned"]["added_by"]


def test_a_night_can_be_moved_between_raids_and_cleared(hub: Hub) -> None:
    sid = hub.login(hub.user(("wed", "officer")))
    for raid in ("mc", "aq20", None):
        r = hub.put("/api/days/wed/strategy", sid, {"raid": raid})
        assert r.status_code == 200, r.text
    assert hub.put("/api/days/wed/strategy", sid, {"raid": None}).json()["raid"] is None
    assert hub.get("/api/days/nope/strategy", sid).status_code == 404


def test_strategy_needs_a_signed_in_member(hub: Hub) -> None:
    assert hub.get("/api/strategy", None).status_code == 401
    member = hub.login(hub.user())
    assert hub.get("/api/strategy", member).status_code == 200
    assert hub.post("/api/admin/strategy", member, {"raid": "mc", "url": DOC + "1"}).status_code == 403
