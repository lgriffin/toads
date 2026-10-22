"""Officers' loot priority (docs/loot.md): the rules in LootService, the item catalogue and the routes' edges. The main
journeys are the REQ-HUB-LOOT scenarios (tests/step_defs/test_hub_loot.py)."""

from __future__ import annotations

import gzip
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from toads_api.loot import catalogue as catalogue_module
from toads_api.loot.catalogue import CatalogueItem, ItemCatalogue, bundled, parse
from toads_api.loot.repository import InMemoryLootRepository
from toads_api.loot.service import ITEM_LIMIT, LINE_LIMIT, NOTE_LIMIT, LootError, LootService

from conftest import Hub

NOW = datetime(2026, 10, 22, 20, 0, tzinfo=UTC)
ITEMS = ItemCatalogue(
    [
        CatalogueItem(19019, "Thunderfury, Blessed Blade of the Windseeker", 5, 80, "INVTYPE_WEAPON", "Forever"),
        CatalogueItem(18423, "Head of Onyxia", 4, 60, "INVTYPE_NON_EQUIP_IGNORE", "Forever"),
        CatalogueItem(18422, "Head of Onyxia", 4, 60, "INVTYPE_NON_EQUIP_IGNORE", "Forever"),
        CatalogueItem(17076, "Bonereaver's Edge", 4, 77, "INVTYPE_2HWEAPON", "Vanilla"),
        CatalogueItem(2459, "Swiftness Potion", 1, 25, "", "Forever"),
        CatalogueItem(3000, "Thunder Ale", 1, 10, "", "Forever"),
    ],
    "test items",
)
NAMES = {1: "Hopscotch", 2: "Lilypad", 3: "Toadstool", 4: "Bogwalker"}
ROSTER = {"wed": [1, 2, 3], "sun": [4]}


def _svc(repo: InMemoryLootRepository | None = None, catalogue: ItemCatalogue = ITEMS) -> LootService:
    return LootService(
        repo or InMemoryLootRepository(),
        lambda: catalogue,
        lambda ids: {i: NAMES[i] for i in ids if i in NAMES},
        roster=lambda day: ROSTER.get(day, []),
        clock=lambda: NOW,
    )


def _refused(status: int, call: Any) -> str:
    with pytest.raises(LootError) as exc:
        call()
    assert exc.value.status == status
    return exc.value.message


# ---------------------------------------------------------------- the catalogue


def test_search_puts_whole_names_then_prefixes_then_the_best_quality_first() -> None:
    assert [i.id for i in ITEMS.search("thunder")] == [19019, 3000]
    assert [i.id for i in ITEMS.search("head of onyxia")] == [18422, 18423]
    assert [i.id for i in ITEMS.search("  BLADE   thunderfury ")] == [19019]
    assert [i.id for i in ITEMS.search("ess")] == [19019, 2459]
    # A name that starts with the query beats a better item that only holds it.
    assert [i.id for i in ITEMS.search("swift")] == [2459]


def test_search_ignores_one_letter_and_typographic_apostrophes() -> None:
    assert ITEMS.search("t") == []
    assert [i.id for i in ITEMS.search("bonereaver\u2019s")] == [17076]
    assert ITEMS.search("thunder", limit=1)[0].id == 19019
    assert ITEMS.search("thunder", limit=0) == []


def test_parse_reads_the_tsv_and_skips_short_lines() -> None:
    lines = [
        "# LibItemDB ItemDB-v1.7.0, enUS: 2 items\n",
        "# licence line\n",
        "id\tname\tquality\tclass_id\tsubclass_id\tslot\titem_level\tflavour\n",
        "19019\tThunderfury\t5\t2\t7\tINVTYPE_WEAPON\t80\tForever\n",
        "broken line\n",
        "25\tWorn Shortsword\t1\t2\t7\tINVTYPE_WEAPONMAINHAND\t2\n",
    ]
    catalogue = parse(lines)
    assert catalogue.source == "LibItemDB ItemDB-v1.7.0, enUS: 2 items"
    assert len(catalogue) == 2
    assert catalogue.get(19019) == CatalogueItem(19019, "Thunderfury", 5, 80, "INVTYPE_WEAPON", "Forever")
    assert catalogue.get(25) == CatalogueItem(25, "Worn Shortsword", 1, 2, "INVTYPE_WEAPONMAINHAND", "")


def test_the_bundled_catalogue_holds_forever_and_classic_raid_loot() -> None:
    items = bundled()
    assert len(items) > 20_000
    assert items.source.startswith("LibItemDB")
    assert items.get(19019) == CatalogueItem(
        19019, "Thunderfury, Blessed Blade of the Windseeker", 5, 80, "INVTYPE_WEAPON", "Forever"
    )
    # Forever's beta data lacks much of Molten Core; Classic fills it in.
    edge = items.get(17076)
    assert edge is not None and (edge.name, edge.flavour) == ("Bonereaver's Edge", "Vanilla")


def test_the_bundled_data_names_its_licence() -> None:
    data = Path(catalogue_module.__file__).parent / "data"
    notice = (data / "NOTICE").read_text(encoding="utf-8")
    assert "MIT License" in notice and "Pimptasty" in notice
    with gzip.open(data / "items.tsv.gz", "rt", encoding="utf-8") as f:
        assert "Pimptasty" in "".join(f.readline() for _ in range(2))


# ---------------------------------------------------------------- rules


def test_an_item_goes_on_by_its_canonical_name_with_nobody_in_line() -> None:
    svc = _svc()
    view = svc.add("wed", item_id=19019, note="  Bindings first \n", by=1)
    assert (view.entry.item_name, view.entry.note, view.recipients) == (
        "Thunderfury, Blessed Blade of the Windseeker",
        "Bindings first",
        [],
    )
    assert view.item is not None and view.item.quality == 5
    assert [v.entry.item_id for v in svc.loot("wed")] == [19019]
    assert svc.loot("sun") == []


def test_unknown_duplicate_and_over_long_items_are_refused() -> None:
    svc = _svc()
    svc.add("wed", item_id=19019, by=1)
    assert "search for it" in _refused(422, lambda: svc.add("wed", item_id=1, by=1))
    assert "already" in _refused(409, lambda: svc.add("wed", item_id=19019, by=1))
    _refused(422, lambda: svc.add("wed", item_id=18423, note="x" * (NOTE_LIMIT + 1), by=1))
    # Another night keeps its own list.
    assert svc.add("sun", item_id=19019, by=1).entry.raid_day == "sun"


def test_a_full_list_refuses_more() -> None:
    repo = InMemoryLootRepository()
    svc = _svc(repo)
    for n in range(ITEM_LIMIT):
        repo.add("wed", 100_000 + n, f"Item {n}", "", 1, NOW)
    assert "take finished" in _refused(409, lambda: svc.add("wed", item_id=19019, by=1))


def test_the_line_is_ranked_and_the_first_without_the_item_is_next_up() -> None:
    svc = _svc()
    entry = svc.add("wed", item_id=19019, by=1).entry.id
    view = svc.set_line("wed", entry, member_ids=[2, 1, 3], by=1)
    assert [(r.rank, r.name, r.next_up) for r in view.recipients] == [
        (1, "Lilypad", True),
        (2, "Hopscotch", False),
        (3, "Toadstool", False),
    ]
    view = svc.mark("wed", entry, 2, received=True, by=1)
    assert view.entry.updated_at == NOW
    assert [(r.name, r.received_at, r.next_up) for r in view.recipients][:2] == [
        ("Lilypad", NOW, False),
        ("Hopscotch", None, True),
    ]
    # Reordering keeps who has received theirs.
    view = svc.set_line("wed", entry, member_ids=[1, 2], by=1)
    assert [(r.name, r.received_at is not None, r.next_up) for r in view.recipients] == [
        ("Hopscotch", False, True),
        ("Lilypad", True, False),
    ]
    view = svc.mark("wed", entry, 1, received=True, by=1)
    assert not any(r.next_up for r in view.recipients)


def test_the_line_takes_only_the_nights_raid_group_once_each() -> None:
    svc = _svc()
    entry = svc.add("wed", item_id=19019, by=1).entry.id
    assert "raid group" in _refused(422, lambda: svc.set_line("wed", entry, member_ids=[1, 4], by=1))
    assert "twice" in _refused(422, lambda: svc.set_line("wed", entry, member_ids=[1, 1], by=1))
    many = list(range(1, LINE_LIMIT + 2))
    _refused(422, lambda: svc.set_line("wed", entry, member_ids=many, by=1))
    _refused(404, lambda: svc.set_line("wed", 99, member_ids=[1], by=1))
    _refused(404, lambda: svc.set_line("sun", entry, member_ids=[4], by=1))


def test_someone_who_left_the_night_keeps_their_place_until_taken_off() -> None:
    roster = {"wed": [1, 2]}
    svc = LootService(
        InMemoryLootRepository(),
        lambda: ITEMS,
        lambda ids: {i: NAMES[i] for i in ids if i in NAMES and i != 2},
        roster=lambda day: roster[day],
        clock=lambda: NOW,
    )
    entry = svc.add("wed", item_id=19019, by=1).entry.id
    svc.set_line("wed", entry, member_ids=[2, 1], by=1)
    roster["wed"] = [1]
    view = svc.set_line("wed", entry, member_ids=[1, 2], by=1)
    # Member 2 is no longer a member of the hub: no name, still in line.
    assert [(r.member_id, r.name) for r in view.recipients] == [(1, "Hopscotch"), (2, "")]


def test_notes_marks_and_removal_need_the_item_and_the_member() -> None:
    svc = _svc()
    entry = svc.add("wed", item_id=19019, by=1).entry.id
    svc.set_line("wed", entry, member_ids=[1], by=1)
    assert svc.set_note("wed", entry, note=" Tanks first ", by=1).entry.note == "Tanks first"
    _refused(404, lambda: svc.set_note("wed", 99, note="", by=1))
    _refused(404, lambda: svc.mark("wed", 99, 1, received=True, by=1))
    assert "not in line" in _refused(404, lambda: svc.mark("wed", entry, 3, received=True, by=1))
    _refused(404, lambda: svc.remove("sun", entry, by=1))
    svc.remove("wed", entry, by=1)
    assert svc.loot("wed") == []
    _refused(404, lambda: svc.remove("wed", entry, by=1))


def test_an_item_a_newer_catalogue_dropped_keeps_its_name() -> None:
    repo = InMemoryLootRepository()
    _svc(repo).add("wed", item_id=19019, by=1)
    [view] = _svc(repo, ItemCatalogue([])).loot("wed")
    assert (view.entry.item_name, view.item) == ("Thunderfury, Blessed Blade of the Windseeker", None)


# ---------------------------------------------------------------- routes, through the database


def _officer(hub: Hub) -> str:
    return hub.login(hub.user(("wed", "officer")))


def _raider(hub: Hub, nick: str, day: str = "wed") -> int:
    sid = hub.login(hub.user((day, "raider"), nick=nick))
    return int(hub.get("/api/session", sid).json()["member_id"])


def test_routes_add_rank_note_mark_and_remove_through_the_database(hub: Hub) -> None:
    sid = _officer(hub)
    a, b = _raider(hub, "Hopscotch"), _raider(hub, "Lilypad")
    found = hub.get("/api/days/wed/loot/items?q=bonereaver", sid).json()
    assert found[0]["flavour"] == "Vanilla"
    entry = hub.post("/api/days/wed/loot", sid, {"item_id": found[0]["id"], "note": "Warriors"}).json()
    assert (entry["item_name"], entry["note"], entry["quality"]) == ("Bonereaver's Edge", "Warriors", 4)
    path = f"/api/days/wed/loot/{entry['id']}"
    assert hub.put(f"{path}/line", sid, {"member_ids": [b, a]}).status_code == 200
    before = hub.get("/api/days/wed/loot", sid).json()["items"][0]["updated_at"]
    hub.now += 60
    r = hub.put(f"{path}/line/{b}/received", sid, {"received": True})
    assert [x["next_up"] for x in r.json()["recipients"]] == [False, True]
    assert r.json()["updated_at"] > before
    # Dropping someone from the line forgets them; the others keep their marks and move up.
    r = hub.put(f"{path}/line", sid, {"member_ids": [a, b]})
    assert [(x["name"], x["rank"], x["received_at"] is not None) for x in r.json()["recipients"]] == [
        ("Hopscotch", 1, False),
        ("Lilypad", 2, True),
    ]
    r = hub.put(f"{path}/line", sid, {"member_ids": [b]})
    assert [(x["name"], x["rank"]) for x in r.json()["recipients"]] == [("Lilypad", 1)]
    assert hub.put(path, sid, {"note": "  "}).json()["note"] == ""
    assert hub.put(f"{path}/line/{a}/received", sid, {"received": True}).status_code == 404
    assert hub.delete(path, sid).status_code == 204
    assert hub.delete(path, sid).status_code == 404
    assert hub.get("/api/days/wed/loot", sid).json()["items"] == []


def test_routes_refuse_bad_input_and_another_days_path(hub: Hub) -> None:
    sid = _officer(hub)
    entry = hub.post("/api/days/wed/loot", sid, {"item_id": 19019}).json()
    assert hub.post("/api/days/wed/loot", sid, {"item_id": 0}).status_code == 422
    assert hub.put(f"/api/days/wed/loot/{entry['id']}/line", sid, {"member_ids": [1, 1]}).status_code == 422
    assert hub.put(f"/api/days/wed/loot/{entry['id']}", sid, {"note": "x" * (NOTE_LIMIT + 1)}).status_code == 422
    assert hub.get("/api/days/wed/loot/items?q=" + "x" * 81, sid).status_code == 422
    assert hub.get("/api/days/nope/loot", sid).status_code == 404
    # A global officer reaching Wednesday's item through Sunday's path finds nothing.
    glob = hub.login(hub.user(("global", "officer")))
    assert hub.put(f"/api/days/sun/loot/{entry['id']}", glob, {"note": "x"}).status_code == 404
    assert hub.put(f"/api/days/sun/loot/{entry['id']}/line", glob, {"member_ids": []}).status_code == 404
    assert hub.delete(f"/api/days/sun/loot/{entry['id']}", glob).status_code == 404
    assert hub.get("/api/days/wed/loot", sid).json()["items"][0]["note"] == ""


def test_an_insert_that_fails_for_another_reason_is_not_called_a_duplicate(
    hub: Hub, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sqlalchemy.exc import IntegrityError
    from toads_api.loot import sql

    def broken(*args: Any, **kwargs: Any) -> None:
        raise IntegrityError("INSERT INTO audit", {}, Exception("audit is broken"))

    monkeypatch.setattr(sql.audit, "record", broken)
    repo = sql.SqlLootRepository(hub.services.db)
    with pytest.raises(IntegrityError):
        repo.add("wed", 19019, "Thunderfury", "", 1, NOW)
    assert repo.entries("wed") == []
