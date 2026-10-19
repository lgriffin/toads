"""REQ-HUB-BOARD-*: the officers' task board, one per raid day (docs/officer-board.md).

Thin steps over the `hub` fixture (root conftest.py): the real API wired to the fake Discord server.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from hub_db import AuditEntry
from pytest_bdd import given, parsers, scenarios, then, when
from sqlalchemy import select

from conftest import Hub

FEATURES = Path(__file__).resolve().parents[1] / "features"
scenarios(str(FEATURES / "hub_board.feature"))

DAYS = {"Wednesday": "wed", "Sunday": "sun"}
LANES = {"To do": "todo", "In progress": "doing", "Done": "done"}


@pytest.fixture
def people() -> dict[str, Any]:
    return {}


def _board(hub: Hub, sid: str, day: str) -> dict[str, Any]:
    r = hub.get(f"/api/days/{DAYS[day]}/board", sid)
    assert r.status_code == 200, r.text
    board: dict[str, Any] = r.json()
    return board


def _cards(board: dict[str, Any]) -> list[dict[str, Any]]:
    return [c for lane in board["lanes"] for c in lane["cards"]]


def _lane(board: dict[str, Any], name: str) -> list[str]:
    return next([c["title"] for c in lane["cards"]] for lane in board["lanes"] if lane["name"] == name)


def _card_id(hub: Hub, people: dict[str, Any], title: str, day: str = "Wednesday") -> int:
    return int(next(c["id"] for c in _cards(_board(hub, people["officer"], day)) if c["title"] == title))


def _add(hub: Hub, sid: str, day: str, body: dict[str, Any]) -> Any:
    r = hub.post(f"/api/days/{DAYS[day]}/board/cards", sid, body)
    assert r.status_code == 201, r.text
    return r.json()


def _move(hub: Hub, people: dict[str, Any], title: str, lane: str, position: int = 0) -> None:
    card = _card_id(hub, people, title)
    r = hub.post(
        f"/api/days/wed/board/cards/{card}/move", people["officer"], {"lane": LANES[lane], "position": position}
    )
    assert r.status_code == 200, r.text


@given("a Wednesday officer")
def a_day_officer(hub: Hub, people: dict[str, Any]) -> None:
    people["officer"] = hub.login(hub.user(("wed", "officer")))


@given(parsers.parse('a raider who goes by the nickname "{nick}"'))
def a_raider(hub: Hub, people: dict[str, Any], nick: str) -> None:
    sid = hub.login(hub.user(("wed", "raider"), nick=nick))
    people["raider"] = sid
    people["raider_id"] = int(hub.get("/api/session", sid).json()["member_id"])


@given(parsers.parse('Wednesday\'s board holds "{a}", "{b}" and "{c}" in "To do"'))
def board_holds(hub: Hub, people: dict[str, Any], a: str, b: str, c: str) -> None:
    for title in (a, b, c):
        _add(hub, people["officer"], "Wednesday", {"title": title})


@when(parsers.parse('the Wednesday officer adds "{title}" for the raider due "{due}" to Wednesday\'s board'))
def officer_adds_for_raider(hub: Hub, people: dict[str, Any], title: str, due: str) -> None:
    _add(
        hub, people["officer"], "Wednesday", {"title": title, "assignee_member_id": people["raider_id"], "due_on": due}
    )


@when(parsers.parse('the Wednesday officer adds "{title}" due yesterday to Wednesday\'s board'))
def officer_adds_overdue(hub: Hub, people: dict[str, Any], title: str) -> None:
    today = datetime.fromtimestamp(hub.now, ZoneInfo(hub.services.raid_days.timezone)).date()
    _add(hub, people["officer"], "Wednesday", {"title": title, "due_on": (today - timedelta(days=1)).isoformat()})


@when(parsers.parse('the Wednesday officer moves "{title}" to the top of "{lane}"'))
def officer_moves(hub: Hub, people: dict[str, Any], title: str, lane: str) -> None:
    _move(hub, people, title, lane)


@when("a Sunday officer asks for Wednesday's board")
def sunday_officer_asks(hub: Hub, people: dict[str, Any]) -> None:
    people["last"] = hub.get("/api/days/wed/board", hub.login(hub.user(("sun", "officer"))))


@when(parsers.parse('a global officer adds "{title}" to Sunday\'s board'))
def global_officer_adds(hub: Hub, people: dict[str, Any], title: str) -> None:
    people["global"] = hub.login(hub.user(("global", "officer")))
    _add(hub, people["global"], "Sunday", {"title": title})


@then(parsers.parse('Wednesday\'s board shows "{title}" in "{lane}" assigned to "{name}" due "{due}"'))
def board_shows(hub: Hub, people: dict[str, Any], title: str, lane: str, name: str, due: str) -> None:
    # Another Wednesday officer sees the same board.
    board = _board(hub, hub.login(hub.user(("wed", "officer"))), "Wednesday")
    assert _lane(board, lane) == [title]
    card = _cards(board)[0]
    assert (card["assignee_name"], card["due_on"], card["overdue"]) == (name, due, False)
    assert name in [a["display_name"] for a in board["assignees"]]


@then(parsers.parse('the audit log records "{action}" for Wednesday'))
def audit_records(hub: Hub, action: str) -> None:
    with hub.db() as db:
        entries = db.scalars(select(AuditEntry).where(AuditEntry.action == action)).all()
    assert [e.raid_day_id for e in entries] == ["wed"]


@then(parsers.parse('"{lane}" holds just "{title}"'))
def lane_holds_one(hub: Hub, people: dict[str, Any], lane: str, title: str) -> None:
    assert _lane(_board(hub, people["officer"], "Wednesday"), lane) == [title]


@then(parsers.parse('"{lane}" holds "{first}" then "{second}"'))
def lane_holds_two(hub: Hub, people: dict[str, Any], lane: str, first: str, second: str) -> None:
    assert _lane(_board(hub, people["officer"], "Wednesday"), lane) == [first, second]


@then("the request is refused as forbidden")
def refused(people: dict[str, Any]) -> None:
    assert people["last"].status_code == 403, people["last"].text


@then("a Wednesday raider cannot see or change Wednesday's board")
def raider_refused(hub: Hub, people: dict[str, Any]) -> None:
    sid = hub.login(hub.user(("wed", "raider")))
    card = _card_id(hub, people, "Flasks")
    assert hub.get("/api/days/wed/board", sid).status_code == 403
    assert hub.post("/api/days/wed/board/cards", sid, {"title": "Sneaky"}).status_code == 403
    assert hub.post(f"/api/days/wed/board/cards/{card}/move", sid, {"lane": "done", "position": 0}).status_code == 403
    assert hub.delete(f"/api/days/wed/board/cards/{card}", sid).status_code == 403


@then(parsers.parse("Wednesday's board still holds {count:d} cards"))
def still_holds(hub: Hub, people: dict[str, Any], count: int) -> None:
    board = _board(hub, people["officer"], "Wednesday")
    assert len(_cards(board)) == count
    assert _lane(board, "To do") == ["Flasks", "Drums", "Soulstones"]


@then(parsers.parse('Sunday\'s board holds only "{title}"'))
def sunday_holds(hub: Hub, people: dict[str, Any], title: str) -> None:
    assert [c["title"] for c in _cards(_board(hub, people["global"], "Sunday"))] == [title]


@then(parsers.parse("the global officer sees {count:d} cards on Wednesday's board"))
def global_sees(hub: Hub, people: dict[str, Any], count: int) -> None:
    assert len(_cards(_board(hub, people["global"], "Wednesday"))) == count


@then(parsers.parse('the card "{title}" is overdue'))
def is_overdue(hub: Hub, people: dict[str, Any], title: str) -> None:
    card = next(c for c in _cards(_board(hub, people["officer"], "Wednesday")) if c["title"] == title)
    assert card["overdue"] is True


@then(parsers.parse('after it moves to "{lane}" it is not overdue'))
def not_overdue_when_done(hub: Hub, people: dict[str, Any], lane: str) -> None:
    _move(hub, people, "Restock the bank", lane)
    card = _cards(_board(hub, people["officer"], "Wednesday"))[0]
    assert (card["lane"], card["overdue"]) == ("done", False)
