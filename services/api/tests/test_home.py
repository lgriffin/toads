"""The customisable hub home: the rules in HomeService, and the /api/me/home routes."""

from __future__ import annotations

import math

import pytest
from toads_api.home.repository import InMemoryHomeRepository, StoredWidget
from toads_api.home.service import ANALYZER_WIDGETS, CATALOGUE, Audience, HomeError, HomeService, catalogue_for

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
    assert r.status_code == 200 and r.json() == {"widgets": 1, "nights": {"wed": 2, "thu": 3, "sun": 6}}
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


# --- each raid night's page, for the Logs page ------------------------------------------------------------------------


def _nights() -> HomeService:
    return HomeService(InMemoryHomeRepository(), {"wed": 2, "sun": 6})


def test_a_night_page_is_kept_apart_from_the_guild_page_and_from_other_nights() -> None:
    svc = _nights()
    assert svc.night_page("wed") is None
    assert svc.publish_night_page("wed", 1, "2026-09-27 12:00:00", PAGE["widgets"]) == 1  # type: ignore[arg-type]
    wed = svc.night_page("wed")
    assert wed is not None and [w["id"] for w in wed.widgets] == ["last_raid"]
    assert svc.night_page("sun") is None and svc.analyzer_page() is None


def test_a_night_page_is_checked_like_the_guild_page() -> None:
    svc = _nights()
    with pytest.raises(HomeError) as unknown:
        svc.publish_night_page("mon", 1, "2026-09-27 12:00:00", [])
    assert unknown.value.status == 404
    with pytest.raises(HomeError) as version:
        svc.publish_night_page("wed", 2, "2026-09-27 12:00:00", [])
    assert version.value.status == 422
    svc.publish_night_page("wed", 1, "2026-09-27 12:00:00", [])
    with pytest.raises(HomeError) as older:
        svc.publish_night_page("wed", 1, "2026-09-27 11:59:59", [])
    assert older.value.status == 409
    # Another night's clock is its own.
    assert svc.publish_night_page("sun", 1, "2026-09-27 11:00:00", []) == 0


def test_a_night_page_hides_officer_widgets_from_members() -> None:
    svc = _nights()
    badges = {"id": "badges", "title": "Toads badges", "kind": "badges", "size": "half", "holders": []}
    svc.publish_night_page("wed", 1, "2026-09-27 12:00:00", [badges])
    assert (svc.night_page("wed", MEMBER) or pytest.fail()).widgets == []
    assert [w["id"] for w in (svc.night_page("wed", OFFICER) or pytest.fail()).widgets] == ["badges"]


def test_night_page_round_trip(hub: Hub) -> None:
    sid = hub.login(hub.user(("sun", "raider")))
    assert hub.get("/api/home/nights", sid).json() == {"nights": {"wed": 2, "thu": 3, "sun": 6}}
    empty = hub.get("/api/home/nights/wed", sid).json()
    assert (empty["generated_at"], empty["widgets"]) == (None, [])

    r = hub.client.put("/api/worker/home-page/nights/wed", headers=WORKER, json=PAGE)
    assert r.status_code == 200 and r.json() == {"widgets": 1}
    # Every member reads every night's page, as they read the guild-wide one.
    assert hub.get("/api/home/nights/wed", sid).json()["widgets"][0]["id"] == "last_raid"
    assert hub.get("/api/home/nights/thu", sid).json()["widgets"] == []
    assert hub.get("/api/home/nights/mon", sid).status_code == 404
    assert hub.client.put("/api/worker/home-page/nights/mon", headers=WORKER, json=PAGE).status_code == 404


@pytest.mark.security
def test_only_the_worker_publishes_a_night_page(hub: Hub) -> None:
    sid = hub.login(hub.user(("wed", "officer")))
    assert hub.client.put("/api/worker/home-page/nights/wed", json=PAGE).status_code == 401
    assert hub.client.put("/api/worker/home-page/nights/wed", headers=hub.as_(sid), json=PAGE).status_code == 401
    assert hub.get("/api/home/nights/wed", None).status_code == 401
    assert hub.get("/api/home/nights", None).status_code == 401


def test_the_home_offers_only_hub_widgets(hub: Hub) -> None:
    # The analyzer's raid widgets moved to Logs (ANALYZER_WIDGETS); a layout saved with them keeps the rest.
    sid = hub.login(hub.user(("wed", "raider")))
    sources = {w["id"]: w["source"] for w in hub.get("/api/me/home", sid).json()["widgets"]}
    assert "last_raid" not in sources and set(sources.values()) == {"hub"}


def test_a_layout_saved_with_analyzer_widgets_drops_them() -> None:
    repo = InMemoryHomeRepository()
    repo.save_layout(1, [StoredWidget("last_raid", True), StoredWidget("posts", True)])
    shown = HomeService(repo).layout(1, MEMBER).shown
    assert shown[0] == "posts" and "last_raid" not in shown


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


# --- chart widgets (week-on-week healing) ---------------------------------------------------------------------------


def _chart(**overrides: object) -> dict[str, object]:
    chart: dict[str, object] = {
        "version": 1,
        "id": "healing_weekly",
        "title": "Weekly healing",
        "kind": "bar",
        "subtitle": "Effective healing per raid",
        "x_label": "Week starting",
        "y_label": "Healing per raid",
        "categories": ["14 Sep", "21 Sep"],
        "series": [
            {
                "key": "healing_per_raid",
                "name": "Healing per raid",
                "values": [None, 1_100_000.0],
                "display": ["-", "1.1M"],
                "emphasis": True,
            }
        ],
        "y_max": 2_000_000.0,
        "references": [{"key": "target", "label": "Target", "value": 1_000_000.0, "display": "1.0M"}],
        "notes": ["Target 1.0M per raid met; met in 1 of 1 raided weeks."],
        "empty": "",
    }
    chart.update(overrides)
    return chart


def _chart_widget(chart: object, **extra: object) -> dict[str, object]:
    return {"id": "healing_weekly", "title": "Weekly healing", "kind": "chart", "size": "full", "chart": chart, **extra}


def test_weekly_healing_and_healers_are_analyzer_widgets() -> None:
    ids = {w.id for w in ANALYZER_WIDGETS}
    assert {"healing_weekly", "healers_weekly"} <= ids and not ids & {w.id for w in CATALOGUE}


def test_a_chart_widget_is_kept_as_published() -> None:
    svc = _service()
    assert svc.publish_analyzer_page(1, "2026-09-27 12:00:00", [_chart_widget(_chart())]) == 1
    page = svc.analyzer_page()
    assert page is not None and page.widgets[0]["chart"]["references"][0]["display"] == "1.0M"


def test_a_chart_widget_that_failed_to_build_is_kept_with_its_error() -> None:
    widget = _chart_widget(None, error="Storage unavailable")
    assert _service().publish_analyzer_page(1, "2026-09-27 12:00:00", [widget]) == 1


def test_an_empty_chart_is_kept() -> None:
    chart = _chart(categories=[], series=[], references=[], notes=[], y_max=0.0, empty="No guild raids.")
    assert _service().publish_analyzer_page(1, "2026-09-27 12:00:00", [_chart_widget(chart)]) == 1


_SERIES = _chart()["series"][0]  # type: ignore[index]


@pytest.mark.parametrize(
    ("chart", "problem"),
    [
        (None, "chart must be an object"),
        (_chart(version=2), "unsupported chart version"),
        (_chart(kind="pie"), "unsupported chart kind"),
        (_chart(title="x" * 121), "title must be text"),
        (_chart(categories=["w"] * 53, series=[]), "categories must be at most 52"),
        (_chart(notes=["n"] * 11), "notes must be at most 10"),
        (_chart(y_max=math.inf), "y_max must be a number"),
        (_chart(y_max=True), "y_max must be a number"),
        (_chart(series=[{**_SERIES, "key": f"s{i}"} for i in range(9)]), "series must be a list of at most 8"),
        (_chart(references=[{"key": "r", "label": "R", "value": 1, "display": "1"}] * 4), "at most 3"),
        (_chart(series=[{"values": []}]), "a series needs a key and a name"),
        (_chart(series=[{**_SERIES, "values": [1.0]}]), "does not line up"),
        (_chart(series=[{**_SERIES, "values": [None, 3_000_000.0]}]), "outside 0 to y_max"),
        (_chart(series=[{**_SERIES, "values": [None, "big"]}]), "outside 0 to y_max"),
        (_chart(series=[{**_SERIES, "emphasis": "yes"}]), "emphasis must be true or false"),
        (_chart(series=[_SERIES, _SERIES]), "series keys must be unique"),
        (_chart(references=[{"key": "r", "label": "R", "value": -1, "display": "-1"}]), "outside 0 to y_max"),
        (_chart(references=[{"key": "r", "value": 1}]), "a reference needs a key, label and display"),
        (_chart(references=[{"key": "r", "label": "R", "value": 1, "display": "1"}] * 2), "reference keys must be"),
        (_chart(y_max=10**400), "y_max must be a number"),
        (_chart(series=[{**_SERIES, "values": [None, 10**400]}]), "outside 0 to y_max"),
        ({k: v for k, v in _chart().items() if k != "notes"}, "notes must be at most"),
        ({k: v for k, v in _chart().items() if k != "references"}, "references must be a list"),
        ({k: v for k, v in _chart().items() if k != "subtitle"}, "subtitle must be text"),
        (_chart(id="healers_weekly"), "does not belong to widget 'healing_weekly'"),
    ],
)
def test_charts_that_break_the_contract_are_refused(chart: object, problem: str) -> None:
    with pytest.raises(HomeError) as info:
        _service().publish_analyzer_page(1, "2026-09-27 12:00:00", [_chart_widget(chart)])
    assert info.value.status == 422 and problem in info.value.message
