"""Members' awards (docs/awards.md): the rules in AwardService, the routes, and the catalogue against the web app's.
Also the Discord username the hub now keeps for every member."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from hub_db import AuditEntry, Member, MemberAward
from sqlalchemy import select
from toads_api.awards.catalog import AWARDS, AwardKind
from toads_api.awards.repository import InMemoryAwardRepository
from toads_api.awards.service import AwardError, AwardService

from conftest import Hub

ROOT = Path(__file__).resolve().parents[3]


def _service() -> AwardService:
    return AwardService(InMemoryAwardRepository(members={1, 2}), lambda ids: {i: f"Toad {i}" for i in ids})


# ---------------------------------------------------------------- rules


def test_give_and_list() -> None:
    svc = _service()
    v = svc.give(1, "level-60", by=2, note="  Ding!  ")
    assert (v.name, v.kind, v.member_name, v.period, v.note) == (
        "Level 60",
        AwardKind.ACHIEVEMENT,
        "Toad 1",
        None,
        "Ding!",
    )
    svc.give(1, "banker", by=2)
    assert [a.award_id for a in svc.held_by(1)] == ["banker", "level-60"]
    assert svc.held_by(2) == []
    assert len(svc.wall()) == 2


def test_an_award_is_held_once() -> None:
    svc = _service()
    svc.give(1, "raids-10", by=2)
    with pytest.raises(AwardError) as info:
        svc.give(1, "raids-10", by=2)
    assert info.value.status == 409


def test_raider_of_the_month_is_held_once_per_month() -> None:
    svc = _service()
    svc.give(1, "raider-of-the-month", by=2, period="2026-09")
    svc.give(1, "raider-of-the-month", by=2, period="2026-10")
    with pytest.raises(AwardError) as info:
        svc.give(1, "raider-of-the-month", by=2, period="2026-10")
    assert info.value.status == 409
    assert {a.period for a in svc.held_by(1)} == {"2026-09", "2026-10"}


@pytest.mark.parametrize("period", [None, "", "2026-13", "26-09", "2026/09", "September"])
def test_a_monthly_award_needs_a_month(period: str | None) -> None:
    with pytest.raises(AwardError) as info:
        _service().give(1, "raider-of-the-month", by=2, period=period)
    assert info.value.status == 422


def test_a_weekly_honour_is_held_once_per_raid_week() -> None:
    svc = _service()
    v = svc.give(1, "sunder-king", by=2, period="2026-W43", note="Five stacks before the rogues opened")
    assert (v.name, v.kind, v.period) == ("Sunder King", AwardKind.HONOUR, "2026-W43")
    svc.give(1, "sunder-king", by=2, period="2026-W53")  # 2026 has 53 ISO weeks
    svc.give(1, "sunder-king", by=2, period="2026-W44")
    svc.give(2, "sunder-king", by=1, period="2026-W44")
    with pytest.raises(AwardError) as info:
        svc.give(1, "sunder-king", by=2, period="2026-W44")
    assert info.value.status == 409


@pytest.mark.parametrize("period", [None, "", "2026-10", "2026-W00", "2026-W54", "2025-W53", "2026W43", "2026-w43"])
def test_a_weekly_honour_needs_a_week(period: str | None) -> None:
    with pytest.raises(AwardError) as info:
        _service().give(1, "raider-of-the-week", by=2, period=period)
    assert info.value.status == 422


def test_every_honour_is_weekly_and_nothing_else_is() -> None:
    assert {a.id for a in AWARDS.values() if a.weekly} == {a.id for a in AWARDS.values() if a.kind is AwardKind.HONOUR}
    assert "raider-of-the-week" in AWARDS


@pytest.mark.parametrize("period", ["2026-09", "2026-W43"])
def test_other_awards_take_no_period(period: str) -> None:
    with pytest.raises(AwardError) as info:
        _service().give(1, "level-60", by=2, period=period)
    assert info.value.status == 422


def test_other_awards_take_no_month() -> None:
    with pytest.raises(AwardError) as info:
        _service().give(1, "level-60", by=2, period="2026-09")
    assert info.value.status == 422


@pytest.mark.parametrize(("member_id", "award_id", "status"), [(1, "not-an-award", 422), (3, "level-60", 404)])
def test_unknown_award_or_member(member_id: int, award_id: str, status: int) -> None:
    with pytest.raises(AwardError) as info:
        _service().give(member_id, award_id, by=2)
    assert info.value.status == status


def test_long_note_is_refused() -> None:
    with pytest.raises(AwardError) as info:
        _service().give(1, "level-60", by=2, note="x" * 201)
    assert info.value.status == 422


def test_take_back() -> None:
    svc = _service()
    v = svc.give(1, "chef", by=2)
    svc.take_back(v.id, by=2)
    assert svc.held_by(1) == []
    with pytest.raises(AwardError) as info:
        svc.take_back(v.id, by=2)
    assert info.value.status == 404


# ---------------------------------------------------------------- catalogue


def test_catalogue_matches_the_web_app() -> None:
    """Every milestone and achievement the web app has artwork for is awardable, and nothing else is."""
    ts = (ROOT / "apps/web/src/lib/milestones.ts").read_text(encoding="utf-8")
    web = set(re.findall(r"\{ id: '([a-z0-9-]+)'", ts))
    assert web == {a.id for a in AWARDS.values() if a.kind is not AwardKind.TITLE}
    toads = (ROOT / "apps/web/src/lib/toads.ts").read_text(encoding="utf-8")
    for title in (a for a in AWARDS.values() if a.kind is AwardKind.TITLE):
        assert f"ranks/{title.id}" in toads
    for a in AWARDS.values():
        assert any((ROOT / "apps/web/static/logos").glob(f"*/{a.id}-badge.svg")), a.id


# ---------------------------------------------------------------- routes


def _member_id(hub: Hub, sid: str) -> int:
    return int(hub.get("/api/session", sid).json()["member_id"])


def test_routes_need_a_session(hub: Hub) -> None:
    assert hub.get("/api/me/awards", None).status_code == 401
    assert hub.get("/api/awards", None).status_code == 401
    assert hub.post("/api/admin/awards", None, {"member_id": 1, "award_id": "chef"}).status_code == 401


@pytest.mark.security
def test_only_the_global_tier_gives_awards(hub: Hub) -> None:
    raider = hub.login(hub.user(("wed", "raider")))
    day_officer = hub.login(hub.user(("wed", "officer")))
    target = _member_id(hub, raider)
    for sid in (raider, day_officer):
        assert hub.post("/api/admin/awards", sid, {"member_id": target, "award_id": "chef"}).status_code == 403
    with hub.db() as db:
        assert db.scalars(select(MemberAward)).all() == []


def test_global_officer_gives_and_takes_back(hub: Hub) -> None:
    raider = hub.login(hub.user(("wed", "raider"), nick="Hopscotch"))
    officer = hub.login(hub.user(("global", "officer")))
    target = _member_id(hub, raider)

    r = hub.post(
        "/api/admin/awards",
        officer,
        {"member_id": target, "award_id": "raider-of-the-month", "period": "2026-09", "note": "Carried Vashj"},
    )
    assert r.status_code == 201, r.text
    given = r.json()
    assert (given["name"], given["member_name"], given["period"], given["kind"]) == (
        "Raider of the Month",
        "Hopscotch",
        "2026-09",
        "milestone",
    )
    assert hub.post("/api/admin/awards", officer, {"member_id": target, "award_id": "level-60"}).status_code == 201

    mine = hub.get("/api/me/awards", raider).json()
    assert [a["award_id"] for a in mine] == ["level-60", "raider-of-the-month"]
    assert len(hub.get("/api/awards", officer).json()) == 2

    again = hub.post(
        "/api/admin/awards", officer, {"member_id": target, "award_id": "raider-of-the-month", "period": "2026-09"}
    )
    assert again.status_code == 409

    assert hub.delete(f"/api/admin/awards/{given['id']}", officer).status_code == 204
    assert [a["award_id"] for a in hub.get("/api/me/awards", raider).json()] == ["level-60"]
    assert hub.delete(f"/api/admin/awards/{given['id']}", officer).status_code == 404

    with hub.db() as db:
        actions = [e.action for e in db.scalars(select(AuditEntry).order_by(AuditEntry.id))]
    assert actions.count("award.give") == 2 and actions.count("award.take_back") == 1


def test_bad_requests_are_refused(hub: Hub) -> None:
    officer = hub.login(hub.user(("global", "officer")))
    target = _member_id(hub, officer)
    assert hub.post("/api/admin/awards", officer, {"member_id": target, "award_id": "nope"}).status_code == 422
    assert hub.post("/api/admin/awards", officer, {"member_id": 9999, "award_id": "chef"}).status_code == 404
    monthly = {"member_id": target, "award_id": "raider-of-the-month"}
    assert hub.post("/api/admin/awards", officer, monthly).status_code == 422


# ---------------------------------------------------------------- Discord usernames


def test_session_carries_the_discord_username_not_the_nickname(hub: Hub) -> None:
    user = hub.user(("wed", "raider"), nick="Lord Ribbit")
    sid = hub.login(user)
    s = hub.get("/api/session", sid).json()
    assert (s["display_name"], s["discord_username"]) == ("Lord Ribbit", user.username)
    with hub.db() as db:
        row = db.scalars(select(Member).where(Member.discord_user_id == user.user_id)).one()
    assert (row.display_name, row.discord_username) == ("Lord Ribbit", user.username)


def test_username_survives_a_role_refresh(hub: Hub) -> None:
    user = hub.user(("wed", "raider"), nick="Before")
    sid = hub.login(user)
    user.nick = "After"
    hub.pass_time(hub.services.settings.role_refresh_seconds + 1)
    assert hub.get("/api/session", sid).json()["discord_username"] == user.username
