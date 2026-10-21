"""The officers' task board (docs/officer-board.md): the rules in OfficerBoardService and the routes' edges. The
main journeys are the REQ-HUB-BOARD scenarios (tests/step_defs/test_hub_board.py)."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from toads_api.officer_board.repository import CardFields, InMemoryBoardRepository
from toads_api.officer_board.service import CARD_LIMIT, LANES, LINK_LIMIT, BoardError, OfficerBoardService

from conftest import Hub

TODAY = date(2026, 10, 19)


def _svc(repo: InMemoryBoardRepository | None = None) -> OfficerBoardService:
    names = {1: "Hopscotch", 2: "Ribbit"}
    return OfficerBoardService(
        repo or InMemoryBoardRepository(), lambda ids: {i: names[i] for i in ids if i in names}, lambda: TODAY
    )


def _titles(svc: OfficerBoardService, day: str = "wed") -> dict[str, list[str]]:
    return {lane.id: [v.card.fields.title for v in lane.cards] for lane in svc.board(day)}


# ---------------------------------------------------------------- rules


def test_the_board_lists_every_lane_in_order_even_when_empty() -> None:
    assert [(lane.id, lane.name, lane.cards) for lane in _svc().board("wed")] == [
        (lane_id, name, []) for lane_id, name in LANES.items()
    ]


def test_titles_and_notes_are_tidied_and_checked() -> None:
    svc = _svc()
    view = svc.add("wed", title="  Book   the  tank ", notes="  call him \n", by=1)
    assert (view.card.fields.title, view.card.fields.notes) == ("Book the tank", "call him")
    for title in ("", "   ", "x" * 201):
        with pytest.raises(BoardError) as info:
            svc.add("wed", title=title, by=1)
        assert info.value.status == 422
    with pytest.raises(BoardError):
        svc.add("wed", title="Notes", notes="x" * 2001, by=1)


def test_only_members_of_the_hub_can_be_assigned() -> None:
    svc = _svc()
    assert svc.add("wed", title="Flasks", assignee=2, by=1).assignee_name == "Ribbit"
    with pytest.raises(BoardError) as info:
        svc.add("wed", title="Flasks", assignee=99, by=1)
    assert info.value.status == 422


def test_unknown_lane_is_refused() -> None:
    svc = _svc()
    with pytest.raises(BoardError):
        svc.add("wed", title="Flasks", lane="later", by=1)
    card = svc.add("wed", title="Flasks", by=1).card.id
    with pytest.raises(BoardError):
        svc.move("wed", card, lane="later", position=0, by=1)


def test_a_board_holds_a_limited_number_of_cards() -> None:
    svc = _svc()
    for i in range(CARD_LIMIT):
        svc.add("wed", title=f"Card {i}", by=1)
    with pytest.raises(BoardError) as info:
        svc.add("wed", title="One more", by=1)
    assert info.value.status == 409
    svc.add("sun", title="Sunday has its own room", by=1)


def test_moving_within_a_lane_and_past_its_end() -> None:
    svc = _svc()
    a, b, c = (svc.add("wed", title=t, by=1).card.id for t in ("A", "B", "C"))
    svc.move("wed", c, lane="todo", position=0, by=1)
    assert _titles(svc)["todo"] == ["C", "A", "B"]
    svc.move("wed", c, lane="todo", position=99, by=1)
    assert _titles(svc)["todo"] == ["A", "B", "C"]
    svc.move("wed", a, lane="done", position=5, by=1)
    svc.move("wed", b, lane="done", position=0, by=1)
    assert _titles(svc) == {"todo": ["C"], "doing": [], "done": ["B", "A"]}


def test_overdue_is_before_today_and_never_in_done() -> None:
    svc = _svc()
    svc.add("wed", title="Late", due_on=date(2026, 10, 18), by=1)
    svc.add("wed", title="Today", due_on=TODAY, by=1)
    done = svc.add("wed", title="Late but done", due_on=date(2026, 10, 1), lane="done", by=1)
    views = {v.card.fields.title: v.overdue for lane in svc.board("wed") for v in lane.cards}
    assert views == {"Late": True, "Today": False, "Late but done": False}
    assert done.overdue is False


def test_a_card_in_a_retired_lane_shows_under_to_do_and_keeps_its_lane() -> None:
    repo = InMemoryBoardRepository()
    old = repo.add("wed", "blocked", CardFields("Old lane"), by=1).id
    svc = _svc(repo)
    card = svc.add("wed", title="Flasks", by=1).card.id
    assert _titles(svc)["todo"] == ["Old lane", "Flasks"]
    svc.move("wed", card, lane="todo", position=0, by=1)
    svc.move("wed", card, lane="done", position=0, by=1)
    assert next(c.lane for c in repo.cards("wed") if c.id == old) == "blocked"


def test_a_move_stamps_the_moved_card() -> None:
    svc = _svc()
    card = svc.add("wed", title="Flasks", by=1).card
    after = svc.move("wed", card.id, lane="done", position=0, by=1)[2].cards[0].card
    assert after.updated_at > card.updated_at


def test_cards_belong_to_their_day() -> None:
    svc = _svc()
    card = svc.add("wed", title="Flasks", by=1).card.id
    for action in (
        lambda: svc.edit("sun", card, title="Mine now", by=1),
        lambda: svc.move("sun", card, lane="done", position=0, by=1),
        lambda: svc.remove("sun", card, by=1),
    ):
        with pytest.raises(BoardError) as info:
            action()
        assert info.value.status == 404
    assert _titles(svc)["todo"] == ["Flasks"]


def test_edit_rewrites_the_card_and_remove_takes_it_off() -> None:
    svc = _svc()
    card = svc.add("wed", title="Flasks", assignee=1, due_on=TODAY, by=1).card.id
    view = svc.edit("wed", card, title="Flasks and food", notes="for Gruul", by=2)
    assert view.card.fields == CardFields("Flasks and food", "for Gruul", None, None)
    svc.remove("wed", card, by=1)
    assert _titles(svc)["todo"] == []
    with pytest.raises(BoardError):
        svc.remove("wed", card, by=1)


# ---------------------------------------------------------------- routes


def _officer(hub: Hub) -> str:
    return hub.login(hub.user(("wed", "officer")))


def _put(hub: Hub, path: str, sid: str, body: dict[str, Any]) -> Any:
    return hub.client.put(path, headers=hub.as_(sid), json=body)


def test_routes_edit_move_and_remove_through_the_database(hub: Hub) -> None:
    sid = _officer(hub)
    first = hub.post("/api/days/wed/board/cards", sid, {"title": "Flasks"}).json()["id"]
    second = hub.post("/api/days/wed/board/cards", sid, {"title": "Drums", "lane": "doing"}).json()["id"]
    edited = _put(hub, f"/api/days/wed/board/cards/{first}", sid, {"title": "Flasks", "notes": "two each"})
    assert edited.status_code == 200, edited.text
    assert edited.json()["notes"] == "two each"
    lanes = hub.post(f"/api/days/wed/board/cards/{first}/move", sid, {"lane": "doing", "position": 1}).json()
    assert [[c["title"] for c in lane["cards"]] for lane in lanes] == [[], ["Drums", "Flasks"], []]
    assert hub.delete(f"/api/days/wed/board/cards/{second}", sid).status_code == 204
    assert hub.delete(f"/api/days/wed/board/cards/{second}", sid).status_code == 404
    third = hub.post("/api/days/wed/board/cards", sid, {"title": "Food", "lane": "doing"}).json()["id"]
    lanes = hub.get("/api/days/wed/board", sid).json()["lanes"]
    assert [c["id"] for c in lanes[1]["cards"]] == [first, third]


def test_routes_refuse_bad_input(hub: Hub) -> None:
    sid = _officer(hub)
    card = hub.post("/api/days/wed/board/cards", sid, {"title": "Flasks"}).json()["id"]
    for body in ({"title": ""}, {"title": "x", "lane": "later"}, {"title": "x", "due_on": "soon"}):
        assert hub.post("/api/days/wed/board/cards", sid, body).status_code == 422, body
    assert hub.post("/api/days/wed/board/cards", sid, {"title": "x", "assignee_member_id": 4242}).status_code == 422
    assert hub.post(f"/api/days/wed/board/cards/{card}/move", sid, {"lane": "doing", "position": -1}).status_code == 422
    assert _put(hub, "/api/days/wed/board/cards/0", sid, {"title": "x"}).status_code == 422
    assert _put(hub, "/api/days/wed/board/cards/999", sid, {"title": "x"}).status_code == 404
    assert hub.post("/api/days/wed/board/cards/999/move", sid, {"lane": "doing", "position": 0}).status_code == 404


def test_a_global_officer_cannot_reach_a_card_through_another_days_path(hub: Hub) -> None:
    sid = hub.login(hub.user(("global", "officer")))
    card = hub.post("/api/days/wed/board/cards", sid, {"title": "Flasks"}).json()["id"]
    assert _put(hub, f"/api/days/sun/board/cards/{card}", sid, {"title": "Moved"}).status_code == 404
    assert hub.delete(f"/api/days/sun/board/cards/{card}", sid).status_code == 404
    assert hub.get("/api/days/nope/board", sid).status_code == 404
    assert hub.get("/api/days/wed/board", None).status_code == 401


# ---------------------------------------------------------------- pinned links


def test_links_are_tidied_checked_and_kept_per_night() -> None:
    svc = _svc()
    link = svc.add_link("wed", label="  Kael   strategy ", url=" https://docs.google.com/document/d/abc ", by=1)
    assert (link.label, link.url) == ("Kael strategy", "https://docs.google.com/document/d/abc")
    for label, url in [
        ("", "https://drive.google.com/x"),
        ("x" * 81, "https://drive.google.com/x"),
        ("Roles", "http://drive.google.com/x"),
        ("Roles", "javascript:alert(1)"),
        ("Roles", "https://localhost/x"),
        ("Roles", "drive.google.com/x"),
        ("Roles", "https://" + "a" * 500 + ".com"),
        ("Roles", "https://[abc"),
        ("Roles", "https://example.com:abc/x"),
        ("Roles", "https://drive.google.com/a b"),
    ]:
        with pytest.raises(BoardError) as info:
            svc.add_link("wed", label=label, url=url, by=1)
        assert info.value.status == 422, (label, url)
    assert [x.label for x in svc.links("wed")] == ["Kael strategy"]
    assert svc.links("sun") == []


def test_a_night_holds_a_limited_number_of_links_and_unpinning_needs_the_right_night() -> None:
    svc = _svc()
    for i in range(LINK_LIMIT):
        svc.add_link("wed", label=f"Doc {i}", url=f"https://drive.google.com/{i}", by=1)
    with pytest.raises(BoardError) as info:
        svc.add_link("wed", label="One more", url="https://drive.google.com/x", by=1)
    assert info.value.status == 409
    first = svc.links("wed")[0].id
    with pytest.raises(BoardError) as missing:
        svc.remove_link("sun", first, by=1)
    assert missing.value.status == 404
    svc.remove_link("wed", first, by=1)
    assert len(svc.links("wed")) == LINK_LIMIT - 1


def test_link_routes_pin_list_and_unpin_through_the_database(hub: Hub) -> None:
    sid = _officer(hub)
    made = hub.post("/api/days/wed/links", sid, {"label": "Roles", "url": "https://drive.google.com/roles"})
    assert made.status_code == 201
    link = made.json()
    assert hub.get("/api/days/wed/links", sid).json() == [link]
    assert hub.post("/api/days/wed/links", sid, {"label": "Bad", "url": "ftp://x.com"}).status_code == 422
    assert (
        hub.delete(f"/api/days/sun/links/{link['id']}", hub.login(hub.user(("global", "officer")))).status_code == 404
    )
    assert hub.delete(f"/api/days/wed/links/{link['id']}", sid).status_code == 204
    assert hub.get("/api/days/wed/links", sid).json() == []
    raider = hub.login(hub.user(("wed", "raider")))
    assert hub.get("/api/days/wed/links", raider).status_code == 403
    assert hub.get("/api/days/wed/links", None).status_code == 401
