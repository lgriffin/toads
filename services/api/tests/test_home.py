"""The customisable hub home: the rules in HomeService, and the /api/me/home routes."""

from __future__ import annotations

import pytest
from toads_api.home.repository import InMemoryHomeRepository, StoredWidget
from toads_api.home.service import CATALOGUE, Audience, HomeError, HomeService, catalogue_for

from conftest import Hub

MEMBER, OFFICER = Audience.MEMBER, Audience.OFFICER
DEFAULT_MEMBER = [w.id for w in catalogue_for(MEMBER) if w.default_shown]


def _service() -> HomeService:
    return HomeService(InMemoryHomeRepository())


def test_catalogue_ids_are_unique() -> None:
    assert len({w.id for w in CATALOGUE}) == len(CATALOGUE)


def test_default_layout() -> None:
    layout = _service().layout(1, MEMBER)
    assert not layout.customised
    assert layout.shown == DEFAULT_MEMBER
    assert "officer_desk" not in [c.widget.id for c in layout.widgets]
    assert "officer_desk" in _service().layout(1, OFFICER).shown


def test_save_shows_exactly_the_chosen_widgets_in_order() -> None:
    svc = _service()
    layout = svc.save(1, MEMBER, ["recruiting", "next_raid"])
    assert layout.customised
    assert layout.shown == ["recruiting", "next_raid"]
    # Every other widget stays placeable, hidden, after the shown ones.
    assert [c.widget.id for c in layout.widgets][2:] == [
        i for i in (w.id for w in catalogue_for(MEMBER)) if i not in ("recruiting", "next_raid")
    ]
    assert svc.layout(1, MEMBER).shown == ["recruiting", "next_raid"]


def test_empty_home_is_allowed() -> None:
    assert _service().save(1, MEMBER, []).shown == []


def test_reset_goes_back_to_default() -> None:
    svc = _service()
    svc.save(1, MEMBER, ["posts"])
    layout = svc.reset(1, MEMBER)
    assert (layout.customised, layout.shown) == (False, DEFAULT_MEMBER)


@pytest.mark.parametrize(
    ("shown", "status"),
    [(["nope"], 422), (["posts", "posts"], 422), (["officer_desk"], 403)],
)
def test_refused_layouts(shown: list[str], status: int) -> None:
    with pytest.raises(HomeError) as info:
        _service().save(1, MEMBER, shown)
    assert info.value.status == status


def test_new_widgets_appear_with_their_default_and_retired_ones_drop() -> None:
    repo = InMemoryHomeRepository({1: [StoredWidget("retired", True), StoredWidget("posts", True)]})
    layout = HomeService(repo).layout(1, MEMBER)
    ids = [c.widget.id for c in layout.widgets]
    assert ids[0] == "posts" and "retired" not in ids
    assert layout.shown == ["posts"] + [i for i in DEFAULT_MEMBER if i != "posts"]


def test_officer_widgets_survive_stepping_down() -> None:
    svc = _service()
    svc.save(1, OFFICER, ["officer_desk", "posts"])
    # Stepped down: the desk disappears from their home...
    assert svc.layout(1, MEMBER).shown == ["posts"]
    svc.save(1, MEMBER, ["next_raid", "posts"])
    # ...and comes back, still shown, if they return.
    assert "officer_desk" in svc.layout(1, OFFICER).shown


def test_routes_need_a_session(hub: Hub) -> None:
    assert hub.get("/api/me/home", None).status_code == 401
    assert hub.client.put("/api/me/home", json={"shown": []}).status_code == 401
    assert hub.delete("/api/me/home", None).status_code == 401


def test_member_customises_their_home(hub: Hub) -> None:
    sid = hub.login(hub.user(("wed", "raider")))
    home = hub.get("/api/me/home", sid).json()
    assert home["customised"] is False
    assert [w["id"] for w in home["widgets"] if w["shown"]] == DEFAULT_MEMBER
    assert not any(w["officer_only"] for w in home["widgets"])

    r = hub.client.put("/api/me/home", headers=hub.as_(sid), json={"shown": ["raid_totals", "next_raid"]})
    assert r.status_code == 200
    assert [w["id"] for w in r.json()["widgets"] if w["shown"]] == ["raid_totals", "next_raid"]
    assert hub.get("/api/me/home", sid).json()["customised"] is True

    reset = hub.delete("/api/me/home", sid).json()
    assert reset["customised"] is False


@pytest.mark.security
def test_members_cannot_place_officer_widgets(hub: Hub) -> None:
    sid = hub.login(hub.user(("wed", "raider")))
    r = hub.client.put("/api/me/home", headers=hub.as_(sid), json={"shown": ["officer_desk"]})
    assert r.status_code == 403


def test_officers_see_the_desk(hub: Hub) -> None:
    sid = hub.login(hub.user(("sun", "officer")))
    home = hub.get("/api/me/home", sid).json()
    desk = next(w for w in home["widgets"] if w["id"] == "officer_desk")
    assert desk["officer_only"] and desk["shown"]


def test_layouts_are_per_member(hub: Hub) -> None:
    a = hub.login(hub.user(("wed", "raider")))
    b = hub.login(hub.user(("wed", "raider")))
    hub.client.put("/api/me/home", headers=hub.as_(a), json={"shown": ["posts"]})
    assert hub.get("/api/me/home", b).json()["customised"] is False


def test_too_many_widgets_is_refused(hub: Hub) -> None:
    sid = hub.login(hub.user(("wed", "raider")))
    r = hub.client.put("/api/me/home", headers=hub.as_(sid), json={"shown": ["posts"] * (len(CATALOGUE) + 1)})
    assert r.status_code == 422


# --- the analyzer's page, published by the worker ------------------------------------------------------------------

TOKEN = "test-service-token"  # noqa: S105  (conftest.make_settings)
WORKER = {"Authorization": f"Bearer {TOKEN}"}
PAGE = {
    "version": 1,
    "generated_at": "2026-09-27 12:00:00",
    "widgets": [
        {"id": "quick_actions", "title": "Quick actions", "kind": "actions", "size": "full", "actions": []},
        {
            "id": "last_raid",
            "title": "Last raid",
            "kind": "stats",
            "size": "full",
            "subtitle": "Serpentshrine Cavern",
            "link": {"kind": "raid", "params": {"report_id": "aBcD1234eFgH5678"}},
            "empty": "",
            "error": "",
            "tiles": [{"label": "Bosses", "value": 4, "display": "4", "hint": ""}],
        },
        {"id": "from_the_future", "title": "New", "kind": "list", "size": "half", "items": []},
    ],
}


def test_publish_keeps_only_widgets_the_hub_places() -> None:
    svc = _service()
    assert svc.analyzer_page() is None
    assert svc.publish_analyzer_page(1, "2026-09-27 12:00:00", PAGE["widgets"]) == 1  # type: ignore[arg-type]
    page = svc.analyzer_page()
    assert page is not None and [w["id"] for w in page.widgets] == ["last_raid"]


def test_publish_refuses_an_unknown_version() -> None:
    with pytest.raises(HomeError) as info:
        _service().publish_analyzer_page(2, "2026-09-27 12:00:00", [])
    assert info.value.status == 422


def test_analyzer_page_round_trip(hub: Hub) -> None:
    sid = hub.login(hub.user(("wed", "raider")))
    empty = hub.get("/api/home/analyzer", sid).json()
    assert (empty["generated_at"], empty["widgets"]) == (None, [])

    r = hub.client.put("/api/worker/home-page", headers=WORKER, json=PAGE)
    assert r.status_code == 200 and r.json() == {"widgets": 1}
    page = hub.get("/api/home/analyzer", sid).json()
    assert page["generated_at"] == "2026-09-27 12:00:00"
    assert page["widgets"][0]["tiles"][0]["display"] == "4"

    # A second build replaces the first.
    hub.client.put("/api/worker/home-page", headers=WORKER, json={**PAGE, "widgets": []})
    assert hub.get("/api/home/analyzer", sid).json()["widgets"] == []


@pytest.mark.security
def test_only_the_worker_publishes_the_page(hub: Hub) -> None:
    sid = hub.login(hub.user(("sun", "officer")))
    assert hub.client.put("/api/worker/home-page", json=PAGE).status_code == 401
    assert hub.client.put("/api/worker/home-page", headers=hub.as_(sid), json=PAGE).status_code == 401
    assert hub.get("/api/home/analyzer", None).status_code == 401


def test_widgets_say_where_their_data_comes_from(hub: Hub) -> None:
    sid = hub.login(hub.user(("wed", "raider")))
    sources = {w["id"]: w["source"] for w in hub.get("/api/me/home", sid).json()["widgets"]}
    assert sources["last_raid"] == "analyzer" and sources["posts"] == "hub"


@pytest.mark.parametrize(
    "widget",
    [
        {"id": "last_raid", "title": "Last raid", "kind": "stats", "tiles": "4 bosses"},
        {"id": "top_damage", "title": "Top damage", "kind": "table", "columns": [], "rows": [1, 2]},
        {"id": "class_mix", "title": "Class mix", "kind": "pie", "bars": []},
        {"id": "recent_raids", "title": "Recent raids", "kind": "list", "items": [{}] * 201},
        {"id": "attendance", "kind": "table", "columns": [], "rows": []},
    ],
)
def test_malformed_widgets_are_refused(widget: dict[str, object]) -> None:
    with pytest.raises(HomeError) as info:
        _service().publish_analyzer_page(1, "2026-09-27 12:00:00", [widget])
    assert info.value.status == 422


def test_an_older_build_does_not_replace_a_newer_one() -> None:
    svc = _service()
    svc.publish_analyzer_page(1, "2026-09-27 12:00:00", [])
    with pytest.raises(HomeError) as info:
        svc.publish_analyzer_page(1, "2026-09-27 11:59:59", [])
    assert info.value.status == 409
    with pytest.raises(HomeError):
        svc.publish_analyzer_page(1, "yesterday", [])
