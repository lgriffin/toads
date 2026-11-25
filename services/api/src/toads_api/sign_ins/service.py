"""Rules for the officers' sign-in audit. No RBAC, web framework or storage imports: the routes decide who may ask for
which raid night, and the repository decides where sign-ins live.

A raid night's view holds the sign-ins of members who were on that night when they signed in, and the last sign-in of
every member on it now. The no-night view (`raid_day` None, the global tier's) holds everyone else: sign-ins of members
on no night, and the members on no night who have ever signed in.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from toads_api.sign_ins.repository import MemberRecord, SignInRecord, SignInRepository

# Days the view counts back from the chosen one, so officers can see at a glance which days to look at.
RECENT_DAYS = 14


class SignInError(Exception):
    """A request the rules refuse. `status` is the HTTP code the adapter should answer with."""

    def __init__(self, message: str, status: int = 422) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


@dataclass(frozen=True)
class SignInView:
    member_id: int
    member_name: str
    at: datetime


@dataclass(frozen=True)
class LastSignInView:
    member_id: int
    member_name: str
    # None: they have never signed in (the hub knows them from their Discord roles).
    last_signed_in_at: datetime | None


@dataclass(frozen=True)
class DayCount:
    date: date
    sign_ins: int
    members: int


@dataclass(frozen=True)
class AuditDayView:
    raid_day: str | None
    date: date
    # That day's sign-ins, newest first.
    sign_ins: list[SignInView]
    # Everyone in the view, most recently signed in first and those who never have last.
    members: list[LastSignInView]
    # The RECENT_DAYS days up to and including `date`, newest first.
    recent: list[DayCount]


def _a_year_before(today: date) -> date:
    """The same date a calendar year back (28 February for 29 February): how far back an officer may look. Sign-ins are
    kept, but the audit is about who is using the hub now."""
    try:
        return today.replace(year=today.year - 1)
    except ValueError:
        return today.replace(year=today.year - 1, day=28)


def _most_recent_first(v: LastSignInView) -> tuple[bool, float, str]:
    at = v.last_signed_in_at
    return (at is None, -at.timestamp() if at else 0.0, v.member_name.casefold())


def _in_view(raid_days: Iterable[str], raid_day: str | None) -> bool:
    days = tuple(raid_days)
    return raid_day in days if raid_day is not None else not days


class SignInService:
    def __init__(
        self,
        repo: SignInRepository,
        shown_names: Callable[[Iterable[int]], dict[int, str]],
        zone: ZoneInfo,
        today: Callable[[], date],
    ) -> None:
        self.repo = repo
        self._shown_names = shown_names
        # Days start and end at midnight in the guild's time zone (raid_days.yaml), as officers read them.
        self._zone = zone
        self._today = today

    def _start(self, day: date) -> datetime:
        return datetime.combine(day, time.min, self._zone)

    def day(self, raid_day: str | None, on: date | None = None) -> AuditDayView:
        today = self._today()
        on = on or today
        if on > today:
            raise SignInError("That day has not happened yet")
        if on < _a_year_before(today):
            raise SignInError("The sign-in audit looks back one year at most")
        first = on - timedelta(days=RECENT_DAYS - 1)
        sign_ins = [
            s
            for s in self.repo.between(self._start(first), self._start(on + timedelta(days=1)))
            if _in_view(s.raid_days, raid_day)
        ]
        members = [m for m in self.repo.members() if self._member_in_view(m, raid_day)]
        that_day = [s for s in sign_ins if s.at.astimezone(self._zone).date() == on]
        names = self._shown_names({s.member_id for s in that_day} | {m.member_id for m in members})
        return AuditDayView(
            raid_day=raid_day,
            date=on,
            sign_ins=[self._sign_in(s, names) for s in sorted(that_day, key=lambda s: s.at, reverse=True)],
            members=self._last(members, names),
            recent=self._recent(sign_ins, on),
        )

    @staticmethod
    def _member_in_view(member: MemberRecord, raid_day: str | None) -> bool:
        if raid_day is not None:
            return raid_day in member.raid_days
        # Off every night: only people who have used the hub, not every Discord member the hub has met.
        return not member.raid_days and member.signed_in_at is not None

    @staticmethod
    def _sign_in(s: SignInRecord, names: dict[int, str]) -> SignInView:
        return SignInView(s.member_id, names.get(s.member_id, f"Member {s.member_id}"), s.at)

    @staticmethod
    def _last(members: list[MemberRecord], names: dict[int, str]) -> list[LastSignInView]:
        views = [
            LastSignInView(m.member_id, names.get(m.member_id, f"Member {m.member_id}"), m.signed_in_at)
            for m in members
        ]
        return sorted(views, key=_most_recent_first)

    def _recent(self, sign_ins: list[SignInRecord], on: date) -> list[DayCount]:
        by_day: Counter[date] = Counter()
        people: dict[date, set[int]] = {}
        for s in sign_ins:
            local = s.at.astimezone(self._zone).date()
            by_day[local] += 1
            people.setdefault(local, set()).add(s.member_id)
        days = [on - timedelta(days=n) for n in range(RECENT_DAYS)]
        return [DayCount(d, by_day[d], len(people.get(d, ()))) for d in days]
