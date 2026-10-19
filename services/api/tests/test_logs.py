"""Logs: LogService's rules (who sees per-player numbers), and the routes the web and the worker use."""

from __future__ import annotations

import hashlib
from typing import Any

import pytest
from toads_api.logs.repository import InMemoryLogRepository
from toads_api.logs.service import MAX_MISSING, LogError, LogService, Viewer, overview_of

from conftest import Hub

TOKEN = "test-service-token"  # noqa: S105  (conftest.make_settings)
WORKER = {"Authorization": f"Bearer {TOKEN}"}
GENERATED = "2026-10-19 08:00:00"
# The conftest raid days: Wednesday (weekday 2) and Sunday (weekday 6).
WEDNESDAY, THURSDAY, SUNDAY = 2, 3, 6
WEEKDAYS = {"wed": WEDNESDAY, "sun": SUNDAY}


def _summary(report_id: str, weekday: int | None, date: str = "2026-10-14 19:30:00") -> dict[str, Any]:
    return {
        "report_id": report_id,
        "title": f"Raid {report_id}",
        "zone": "Serpentshrine Cavern",
        "raid_date": date,
        "weekday": weekday,
        "size": 25,
        "url": f"https://fresh.warcraftlogs.com/reports/{report_id}",
    }


def _page(report_id: str, weekday: int | None = WEDNESDAY) -> dict[str, Any]:
    player = {"name": "Hopscotch", "player_class": "Rogue", "role": "melee", "damage": 900, "healing": 0}
    return {
        "version": 1,
        "summary": _summary(report_id, weekday),
        "duration_ms": 7_200_000,
        "composition": {"tanks": [{"name": "Bogwort", "player_class": "Warrior"}], "melee": [player]},
        "melee": [{**player, "active_percent": 99.0}],
        "encounters": [
            {
                "encounter_id": 623,
                "name": "Hydross",
                "duration_ms": 300_000,
                "damage": 9000,
                "healing": 4000,
                "players": [player],
            }
        ],
    }


def _hash(report_id: str, build: int = 1) -> str:
    return hashlib.sha256(f"{report_id}:{build}".encode()).hexdigest()


def _boss() -> dict[str, Any]:
    day = {"kills": 1, "duration_ms": 300_000, "damage": 9000, "healing": 4000, "players": [{"name": "Hopscotch"}]}
    return {"encounter_id": 623, "name": "Hydross", "days": {str(WEDNESDAY): day, str(THURSDAY): dict(day)}}


def _service(*raids: tuple[str, int | None]) -> LogService:
    svc = LogService(InMemoryLogRepository(), WEEKDAYS)
    svc.publish_index(1, GENERATED, [_summary(r, w) for r, w in raids], [_boss()], {r: _hash(r) for r, _ in raids})
    for r, w in raids:
        svc.publish_page(r, _page(r, w), _hash(r))
    return svc


# ── Rules ──


def test_members_see_the_list_and_boss_kills_without_anyone_s_numbers() -> None:
    o = _service(("wedraid", WEDNESDAY), ("thuraid", THURSDAY)).overview(Viewer())
    assert [(r.summary["report_id"], r.analysed, r.day, r.full) for r in o.raids] == [
        ("wedraid", True, None, False),
        ("thuraid", True, None, False),
    ]
    assert o.full_weekdays == []
    assert all("players" not in d for d in o.bosses[0]["days"].values())
    assert o.bosses[0]["days"][str(WEDNESDAY)]["kills"] == 1


def test_a_day_officer_sees_their_weekday_in_full() -> None:
    svc = _service(("wedraid", WEDNESDAY), ("thuraid", THURSDAY))
    viewer = Viewer(officer_days=("wed",))
    o = svc.overview(viewer)
    assert [(r.day, r.full) for r in o.raids] == [("wed", True), (None, False)]
    assert o.full_weekdays == [WEDNESDAY]
    days = o.bosses[0]["days"]
    assert "players" in days[str(WEDNESDAY)] and "players" not in days[str(THURSDAY)]
    assert svc.raid("wedraid", viewer, "wed").full
    # Read guild-wide, or under a day whose weekday is not the raid's, it is the overview.
    assert not svc.raid("wedraid", viewer).full
    assert not svc.raid("thuraid", viewer, "wed").full
    # A day the caller is not an officer on opens nothing in full.
    assert not svc.raid("wedraid", Viewer(officer_days=("sun",)), "wed").full


def test_a_global_officer_sees_every_raid_in_full() -> None:
    svc = _service(("wedraid", WEDNESDAY), ("thuraid", THURSDAY), ("undated", None))
    o = svc.overview(Viewer(everything=True))
    assert all(r.full and r.day is None for r in o.raids)
    assert o.full_weekdays is None
    assert svc.raid("thuraid", Viewer(everything=True)).page["melee"]


def test_the_overview_keeps_totals_and_drops_players() -> None:
    shown = overview_of(_page("wedraid"))
    assert shown["composition_counts"] == {"tanks": 1, "healers": 0, "melee": 1, "ranged": 0}
    assert shown["encounters"] == [
        {"encounter_id": 623, "name": "Hydross", "duration_ms": 300_000, "damage": 9000, "healing": 4000}
    ]
    assert "melee" not in shown and "Hopscotch" not in repr(shown)


def test_the_worker_is_asked_only_for_missing_analysis() -> None:
    svc = LogService(InMemoryLogRepository(), WEEKDAYS)
    many = [_summary(f"r{i:03d}", WEDNESDAY, f"2026-10-{1 + i % 28:02d} 19:30:00") for i in range(MAX_MISSING + 5)]
    hashes = {r["report_id"]: _hash(r["report_id"]) for r in many}
    assert len(svc.publish_index(1, GENERATED, many, [], hashes)) == MAX_MISSING
    svc.publish_page("r000", _page("r000"), _hash("r000"))
    assert "r000" not in svc.publish_index(1, GENERATED, many, [], hashes)
    # A raid gone from the analyzer leaves the list with its analysis.
    assert svc.publish_index(1, GENERATED, many[1:2], [], hashes) == ["r001"]
    with pytest.raises(LogError) as gone:
        svc.raid("r000", Viewer(everything=True))
    assert gone.value.status == 404


def test_raids_the_worker_could_not_read_are_never_asked_for() -> None:
    svc = LogService(InMemoryLogRepository(), WEEKDAYS)
    unreadable = [_summary(f"u{i:03d}", WEDNESDAY, "2026-10-28 19:30:00") for i in range(MAX_MISSING)]
    readable = _summary("older", WEDNESDAY, "2026-10-01 19:30:00")
    # Newer raids with no page to send leave the slots to the one the worker can send.
    assert svc.publish_index(1, GENERATED, [*unreadable, readable], [], {"older": _hash("older")}) == ["older"]


def test_a_rebuilt_analysis_is_asked_for_and_an_older_build_refused() -> None:
    svc = _service(("wedraid", WEDNESDAY))
    raids = [_summary("wedraid", WEDNESDAY)]
    assert svc.publish_index(1, GENERATED, raids, [], {"wedraid": _hash("wedraid")}) == []
    # An analyzer fix or a re-imported report changes the build: the hub asks for it again.
    assert svc.publish_index(1, GENERATED, raids, [], {"wedraid": _hash("wedraid", 2)}) == ["wedraid"]
    # A late upload from the older run is refused rather than replacing the wanted build.
    with pytest.raises(LogError) as late:
        svc.publish_page("wedraid", _page("wedraid"), _hash("wedraid"))
    assert late.value.status == 409
    svc.publish_page("wedraid", _page("wedraid"), _hash("wedraid", 2))
    assert svc.publish_index(1, GENERATED, raids, [], {"wedraid": _hash("wedraid", 2)}) == []


def test_a_raid_the_worker_could_not_read_keeps_its_analysis() -> None:
    svc = _service(("wedraid", WEDNESDAY))
    # Listed without a hash: still listed, its analysis still served, and not asked for.
    assert svc.publish_index(1, GENERATED, [_summary("wedraid", WEDNESDAY)], []) == []
    assert svc.raid("wedraid", Viewer(everything=True)).page["melee"]


@pytest.mark.parametrize(
    ("change", "status"),
    [
        (lambda p: {**p, "version": 2}, 422),
        (lambda p: {**p, "summary": _summary("other", WEDNESDAY)}, 422),
    ],
)
def test_pages_must_match_the_contract_and_the_raid(change: Any, status: int) -> None:
    svc = _service(("wedraid", WEDNESDAY))
    with pytest.raises(LogError) as refused:
        svc.publish_page("wedraid", change(_page("wedraid")), _hash("wedraid"))
    assert refused.value.status == status


def test_lists_must_match_the_contract_and_be_newest() -> None:
    svc = _service(("wedraid", WEDNESDAY))
    for args, status in (
        ((2, GENERATED, [], []), 422),
        ((1, GENERATED, [_summary("a", 1), _summary("a", 1)], []), 422),
        ((1, "2026-10-19 07:00:00", [], []), 409),
    ):
        with pytest.raises(LogError) as refused:
            svc.publish_index(*args)
        assert refused.value.status == status
    with pytest.raises(LogError) as unknown:
        svc.publish_page("unlisted", _page("unlisted"), _hash("unlisted"))
    assert unknown.value.status == 404


# ── Routes ──


def _publish(hub: Hub) -> None:
    index = {
        "version": 1,
        "generated_at": GENERATED,
        "raids": [_summary("wedraid", WEDNESDAY), _summary("thuraid", THURSDAY, "2026-10-15 19:30:00")],
        "bosses": [_boss()],
        "hashes": {"wedraid": _hash("wedraid"), "thuraid": _hash("thuraid")},
    }
    r = hub.client.put("/api/worker/logs", headers=WORKER, json=index)
    assert r.status_code == 200, r.text
    assert r.json() == {"raids": 2, "missing": ["thuraid", "wedraid"]}
    for report, weekday in (("wedraid", WEDNESDAY), ("thuraid", THURSDAY)):
        body = {"page": _page(report, weekday), "hash": _hash(report)}
        r = hub.client.put(f"/api/worker/logs/{report}", headers=WORKER, json=body)
        assert r.status_code == 200, r.text


def test_the_stored_analysis_follows_the_worker_s_latest_build(hub: Hub) -> None:
    _publish(hub)
    later = {
        "version": 1,
        "generated_at": "2026-10-19 09:00:00",
        "raids": [_summary("wedraid", WEDNESDAY)],
        "bosses": [],
        "hashes": {"wedraid": _hash("wedraid", 2)},
    }
    r = hub.client.put("/api/worker/logs", headers=WORKER, json=later)
    assert r.json() == {"raids": 1, "missing": ["wedraid"]}
    stale = {"page": _page("wedraid"), "hash": _hash("wedraid")}
    assert hub.client.put("/api/worker/logs/wedraid", headers=WORKER, json=stale).status_code == 409
    fresh = {"page": _page("wedraid"), "hash": _hash("wedraid", 2)}
    assert hub.client.put("/api/worker/logs/wedraid", headers=WORKER, json=fresh).status_code == 200
    # An older run's list arriving late changes nothing.
    older = {**later, "generated_at": GENERATED, "raids": [], "hashes": {}}
    assert hub.client.put("/api/worker/logs", headers=WORKER, json=older).status_code == 409
    sid = hub.login(hub.user(("global", "officer")))
    assert [r["summary"]["report_id"] for r in hub.get("/api/logs", sid).json()["raids"]] == ["wedraid"]
    assert hub.get("/api/logs/wedraid", sid).json()["full"]


def test_a_member_lists_raids_and_opens_the_overview(hub: Hub) -> None:
    sid = hub.login(hub.user(("wed", "raider")))
    assert hub.get("/api/logs", sid).json() == {"generated_at": None, "raids": [], "bosses": [], "full_weekdays": []}
    assert hub.get("/api/logs/wedraid", sid).status_code == 404
    _publish(hub)
    listed = hub.get("/api/logs", sid).json()
    assert [(r["summary"]["report_id"], r["full"]) for r in listed["raids"]] == [("thuraid", False), ("wedraid", False)]
    raid = hub.get("/api/logs/wedraid", sid).json()
    assert not raid["full"] and "melee" not in raid["page"]
    assert not hub.get("/api/days/wed/logs/wedraid", sid).json()["full"]


def test_a_wednesday_officer_opens_wednesday_raids_in_full(hub: Hub) -> None:
    _publish(hub)
    sid = hub.login(hub.user(("wed", "officer")))
    listed = hub.get("/api/logs", sid).json()
    assert [(r["day"], r["full"]) for r in listed["raids"]] == [(None, False), ("wed", True)]
    assert listed["full_weekdays"] == [WEDNESDAY]
    assert hub.get("/api/days/wed/logs/wedraid", sid).json()["page"]["melee"]
    assert not hub.get("/api/days/wed/logs/thuraid", sid).json()["full"]
    assert not hub.get("/api/days/sun/logs/wedraid", sid).json()["full"]


def test_a_global_officer_opens_every_raid_in_full(hub: Hub) -> None:
    _publish(hub)
    sid = hub.login(hub.user(("global", "officer")))
    assert hub.get("/api/logs", sid).json()["full_weekdays"] is None
    assert hub.get("/api/logs/thuraid", sid).json()["full"]


@pytest.mark.security
def test_only_the_worker_publishes_logs_and_only_members_read_them(hub: Hub) -> None:
    sid = hub.login(hub.user(("global", "officer")))
    body = {"version": 1, "generated_at": GENERATED, "raids": [], "bosses": []}
    assert hub.client.put("/api/worker/logs", json=body).status_code == 401
    assert hub.client.put("/api/worker/logs", headers=hub.as_(sid), json=body).status_code == 401
    assert (
        hub.client.put(
            "/api/worker/logs/wedraid", headers=hub.as_(sid), json={"page": {}, "hash": _hash("x")}
        ).status_code
        == 401
    )
    assert hub.get("/api/logs", None).status_code == 401
    assert hub.get("/api/logs/wedraid", None).status_code == 401
    # Report ids are Warcraft Logs codes; anything else never reaches storage.
    assert hub.get("/api/logs/..%2Fetc", sid).status_code in (404, 422)
    bad = {**body, "raids": [_summary("not/a/code", WEDNESDAY)]}
    assert hub.client.put("/api/worker/logs", headers=WORKER, json=bad).status_code == 422
    assert hub.client.put("/api/worker/logs", headers=WORKER, json={**body, "hashes": {"a": "nope"}}).status_code == 422
