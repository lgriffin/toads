"""SignInService over the in-memory repository: day boundaries in the guild's time zone, who each view holds, and the
days it refuses (docs/sign-ins.md). The routes and RBAC are covered by tests/step_defs/test_hub_sign_ins.py."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from hub_db import Base, Member, SignIn
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from toads_api.sign_ins.repository import InMemorySignInRepository, MemberRecord, SignInRecord
from toads_api.sign_ins.service import RECENT_DAYS, SignInError, SignInService
from toads_api.sign_ins.sql import SqlSignInRepository

PARIS = ZoneInfo("Europe/Paris")
TODAY = date(2026, 11, 25)
NAMES = {1: "Hopscotch", 2: "Lilypad", 3: "Tadpole", 4: "Ribbit"}


def _at(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 11, day, hour, minute, tzinfo=UTC)


def _service(repo: InMemorySignInRepository) -> SignInService:
    return SignInService(repo, lambda ids: {i: NAMES[i] for i in ids if i in NAMES}, PARIS, today=lambda: TODAY)


@pytest.fixture
def repo() -> InMemorySignInRepository:
    return InMemorySignInRepository(
        sign_ins=[
            SignInRecord(1, _at(24, 9), ("wed",)),
            # 23:30 UTC on the 24th is 00:30 on the 25th in Paris: the guild's day, not UTC's.
            SignInRecord(1, _at(24, 23, 30), ("wed",)),
            SignInRecord(3, _at(25, 8), ()),
            SignInRecord(4, _at(25, 9), ("sun",)),
            SignInRecord(9, _at(25, 10), ("wed",)),
        ],
        known=[
            MemberRecord(1, ("wed",), _at(24, 23, 30)),
            MemberRecord(2, ("wed",), None),
            MemberRecord(3, (), _at(25, 8)),
            MemberRecord(4, ("sun",), _at(25, 9)),
            # Met only through Discord, on no night: not someone who uses the hub.
            MemberRecord(5, (), None),
            MemberRecord(9, ("wed", "sun"), _at(25, 10)),
        ],
    )


def test_a_night_sees_its_own_sign_ins_newest_first_by_the_guilds_day(repo: InMemorySignInRepository) -> None:
    view = _service(repo).day("wed")
    assert view.date == TODAY
    assert [(s.member_id, s.member_name) for s in view.sign_ins] == [(9, "Member 9"), (1, "Hopscotch")]
    assert [s.member_id for s in _service(repo).day("wed", date(2026, 11, 24)).sign_ins] == [1]


def test_last_sign_ins_put_the_most_recent_first_and_never_last(repo: InMemorySignInRepository) -> None:
    members = _service(repo).day("wed").members
    assert [(m.member_id, m.last_signed_in_at is None) for m in members] == [(9, False), (1, False), (2, True)]


def test_the_no_night_view_holds_only_members_on_no_night_who_have_signed_in(repo: InMemorySignInRepository) -> None:
    view = _service(repo).day(None)
    assert [s.member_name for s in view.sign_ins] == ["Tadpole"]
    assert [m.member_id for m in view.members] == [3]


def test_recent_counts_sign_ins_and_people_for_each_day(repo: InMemorySignInRepository) -> None:
    recent = _service(repo).day("wed").recent
    assert len(recent) == RECENT_DAYS
    assert (recent[0].date, recent[0].sign_ins, recent[0].members) == (TODAY, 2, 2)
    assert (recent[1].date, recent[1].sign_ins, recent[1].members) == (date(2026, 11, 24), 1, 1)
    assert recent[-1].sign_ins == 0


@pytest.mark.parametrize("on", [date(2026, 11, 26), date(2025, 11, 1)])
def test_refuses_a_day_ahead_or_more_than_a_year_back(repo: InMemorySignInRepository, on: date) -> None:
    with pytest.raises(SignInError) as refused:
        _service(repo).day("wed", on)
    assert refused.value.status == 422


@pytest.mark.parametrize(
    ("today", "earliest"),
    [
        (date(2026, 11, 25), date(2025, 11, 25)),
        (date(2028, 2, 29), date(2027, 2, 28)),
        (date(2028, 3, 1), date(2027, 3, 1)),
    ],
)
def test_looks_back_one_calendar_year_to_the_day(today: date, earliest: date) -> None:
    service = SignInService(InMemorySignInRepository(), lambda ids: {}, PARIS, today=lambda: today)
    assert service.day("wed", earliest).date == earliest
    with pytest.raises(SignInError):
        service.day("wed", earliest - timedelta(days=1))


def test_the_sql_repository_reads_guild_local_days_in_utc() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    db = sessionmaker(engine, expire_on_commit=False)
    with db.begin() as s:
        member = Member(discord_user_id=1, display_name="Hopscotch", raid_days=["wed"], signed_in_at=_at(11, 23, 30))
        s.add(member)
        s.flush()
        # 23:30 UTC on the 11th is 00:30 on the 12th in Paris; 22:30 is still the 11th there.
        s.add_all(
            [
                SignIn(member_id=member.id, at=_at(11, 22, 30), raid_days=["wed"]),
                SignIn(member_id=member.id, at=_at(11, 23, 30), raid_days=["wed"]),
            ]
        )
    repo = SqlSignInRepository(db)
    start = datetime(2026, 11, 12, tzinfo=PARIS)
    found = repo.between(start, start + timedelta(days=1))
    assert [s.at for s in found] == [_at(11, 23, 30)]
    assert found[0].raid_days == ("wed",)
    assert repo.members() == [MemberRecord(member.id, ("wed",), _at(11, 23, 30))]
