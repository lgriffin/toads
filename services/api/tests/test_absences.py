"""Absences (docs/absences.md): the rules in AbsenceService. The routes and RBAC are covered by
tests/features/hub_absence.feature and the RBAC matrix."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from toads_api.absences.repository import InMemoryAbsenceRepository
from toads_api.absences.service import MAX_UPCOMING, TEAM_NIGHTS, AbsenceError, AbsenceService

TODAY = date(2026, 10, 19)  # a Monday
WED, SUN = 2, 6


def _service(weekdays: dict[str, int] | None = None) -> AbsenceService:
    return AbsenceService(
        InMemoryAbsenceRepository(),
        lambda ids: {i: f"Toad {i}" for i in ids},
        {"wed": WED, "sun": SUN} if weekdays is None else weekdays,
        today=lambda: TODAY,
    )


def test_nights_are_the_raid_days_weekdays_in_the_range() -> None:
    svc = _service()
    assert svc.nights("wed", date(2026, 10, 21), date(2026, 11, 4)) == [
        date(2026, 10, 21),
        date(2026, 10, 28),
        date(2026, 11, 4),
    ]
    assert svc.nights("sun", date(2026, 10, 19), date(2026, 10, 24)) == []
    assert svc.nights("sun", date(2026, 10, 30), date(2026, 10, 20)) == []
    assert svc.nights("unknown", date(2026, 10, 19), date(2026, 10, 30)) == []


def test_report_lists_mine_soonest_first_and_trims_the_note() -> None:
    svc = _service()
    later = svc.report(1, "wed", date(2026, 11, 4), date(2026, 11, 4), "  Wedding  ")
    sooner = svc.report(1, "sun", date(2026, 10, 25), date(2026, 10, 25), "   ")
    assert (later.note, sooner.note, later.member_name) == ("Wedding", None, "Toad 1")
    assert [a.id for a in svc.mine(1)] == [sooner.id, later.id]
    assert svc.mine(2) == []


@pytest.mark.parametrize(
    ("first", "last", "note", "status"),
    [
        (date(2026, 10, 18), date(2026, 10, 21), None, 422),  # starts yesterday
        (date(2026, 10, 28), date(2026, 10, 21), None, 422),  # ends before it starts
        (date(2026, 10, 21), date(2027, 1, 21), None, 422),  # a season and more
        (date(2027, 10, 27), date(2027, 10, 27), None, 422),  # more than a year away
        (date(2026, 10, 22), date(2026, 10, 27), None, 422),  # no Wednesday in it
        (date(2026, 10, 21), date(2026, 10, 21), "x" * 201, 422),
    ],
)
def test_report_refuses(first: date, last: date, note: str | None, status: int) -> None:
    with pytest.raises(AbsenceError) as exc:
        _service().report(1, "wed", first, last, note)
    assert exc.value.status == status


def test_a_day_without_a_weekday_takes_any_dates() -> None:
    svc = _service({})
    assert svc.report(1, "wed", date(2026, 10, 22), date(2026, 10, 22)).nights == []
    assert svc.team("wed").nights == []


def test_overlaps_conflict_only_on_the_same_team() -> None:
    svc = _service()
    svc.report(1, "wed", date(2026, 10, 21), date(2026, 10, 28))
    with pytest.raises(AbsenceError) as exc:
        svc.report(1, "wed", date(2026, 10, 28), date(2026, 11, 4))
    assert exc.value.status == 409
    svc.report(1, "sun", date(2026, 10, 25), date(2026, 10, 25))
    svc.report(2, "wed", date(2026, 10, 21), date(2026, 10, 21))


def test_upcoming_absences_are_capped_per_team() -> None:
    svc = _service()
    for week in range(MAX_UPCOMING):
        night = date(2026, 10, 21) + timedelta(weeks=week)
        svc.report(1, "wed", night, night)
    with pytest.raises(AbsenceError) as exc:
        svc.report(1, "wed", date(2027, 6, 2), date(2027, 6, 2))
    assert exc.value.status == 409


def test_cancel_only_ones_own() -> None:
    svc = _service()
    a = svc.report(1, "wed", date(2026, 10, 21), date(2026, 10, 21))
    with pytest.raises(AbsenceError) as exc:
        svc.cancel(2, a.id)
    assert exc.value.status == 404
    svc.cancel(1, a.id)
    assert svc.mine(1) == []
    with pytest.raises(AbsenceError):
        svc.cancel(1, a.id)


def test_team_lists_the_next_nights_with_who_is_away() -> None:
    svc = _service()
    svc.report(2, "wed", date(2026, 10, 28), date(2026, 11, 4), "Holiday")
    svc.report(1, "wed", date(2026, 10, 28), date(2026, 10, 28))
    svc.report(3, "sun", date(2026, 10, 25), date(2026, 10, 25))
    team = svc.team("wed")
    assert len(team.nights) == TEAM_NIGHTS
    assert team.nights[0].date == date(2026, 10, 21) and team.nights[0].absent == []
    assert [a.member_name for a in team.nights[1].absent] == ["Toad 1", "Toad 2"]
    assert [a.member_name for a in team.nights[2].absent] == ["Toad 2"]
    assert [a.member_id for a in team.absences] == [2, 1]
