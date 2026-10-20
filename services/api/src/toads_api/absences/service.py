"""Rules for absences. No RBAC, web framework or storage imports: the routes decide who may call (and so which raid
day's team a member may report for), and the repository decides where things live."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import date, timedelta

from toads_api.absences.repository import AbsenceRecord, AbsenceRepository

NOTE_LIMIT = 200
# A season at most in one go, booked up to a year ahead; longer than that is a conversation with the officers.
MAX_SPAN_DAYS = 92
MAX_AHEAD_DAYS = 366
# Upcoming absences one member may hold on one raid day's team, so a stuck form cannot flood the officers' list.
MAX_UPCOMING = 20
# Raid nights the officers' view lists ahead.
TEAM_NIGHTS = 8


class AbsenceError(Exception):
    """A request the rules refuse. `status` is the HTTP code the adapter should answer with."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


@dataclass(frozen=True)
class AbsenceView:
    """An absence as the site shows it, with the raid nights it covers."""

    id: int
    member_id: int
    member_name: str
    raid_day: str
    first_date: date
    last_date: date
    note: str | None
    nights: list[date]


@dataclass(frozen=True)
class NightView:
    """One upcoming raid night and who has said they will miss it."""

    date: date
    absent: list[AbsenceView]


@dataclass(frozen=True)
class TeamView:
    """A raid day's upcoming absences for its officers: the next nights with who is away, and every absence ahead."""

    raid_day: str
    nights: list[NightView]
    absences: list[AbsenceView]


class AbsenceService:
    def __init__(
        self,
        repo: AbsenceRepository,
        shown_names: Callable[[Iterable[int]], dict[int, str]],
        weekdays: Mapping[str, int],
        today: Callable[[], date],
    ) -> None:
        self.repo = repo
        self._shown_names = shown_names
        # Each raid day's weekday (0 is Monday). A day without one still takes absences; it just lists no nights.
        self._weekdays = dict(weekdays)
        self._today = today

    def nights(self, raid_day: str, first: date, last: date) -> list[date]:
        """The raid nights of `raid_day` from `first` to `last`, both included."""
        weekday = self._weekdays.get(raid_day)
        if weekday is None or last < first:
            return []
        start = first + timedelta(days=(weekday - first.weekday()) % 7)
        return [start + timedelta(weeks=i) for i in range((last - start).days // 7 + 1)] if start <= last else []

    def _views(self, rows: list[AbsenceRecord]) -> list[AbsenceView]:
        names = self._shown_names({r.member_id for r in rows})
        today = self._today()
        return [
            AbsenceView(
                id=r.id,
                member_id=r.member_id,
                member_name=names.get(r.member_id, ""),
                raid_day=r.raid_day,
                first_date=r.first_date,
                last_date=r.last_date,
                note=r.note,
                nights=self.nights(r.raid_day, max(r.first_date, today), r.last_date),
            )
            for r in rows
        ]

    def mine(self, member_id: int) -> list[AbsenceView]:
        """The member's absences that have not ended yet, soonest first."""
        return self._views(self.repo.for_member(member_id, self._today()))

    def _checked(
        self, member_id: int, raid_day: str, first: date, last: date, note: str | None, editing: int | None = None
    ) -> str:
        """The trimmed note, once the dates and the note pass the rules; `editing` is the absence being changed, which
        neither overlaps itself nor counts towards the cap."""
        today = self._today()
        if last < first:
            raise AbsenceError("The last day comes before the first", status=422)
        if first < today:
            raise AbsenceError("Pick a date from today on", status=422)
        if (last - first).days >= MAX_SPAN_DAYS:
            raise AbsenceError(f"Keep one absence under {MAX_SPAN_DAYS} days; add another for the rest", status=422)
        if (first - today).days > MAX_AHEAD_DAYS:
            raise AbsenceError("That is more than a year away", status=422)
        if raid_day in self._weekdays and not self.nights(raid_day, first, last):
            raise AbsenceError("Those dates hold no raid night for this team", status=422)
        note = (note or "").strip()
        if not note:
            raise AbsenceError("Add a note so the officers know why", status=422)
        if len(note) > NOTE_LIMIT:
            raise AbsenceError(f"Keep the note under {NOTE_LIMIT} characters", status=422)
        upcoming = [r for r in self.repo.for_member(member_id, today) if r.raid_day == raid_day and r.id != editing]
        if any(r.first_date <= last and first <= r.last_date for r in upcoming):
            raise AbsenceError("You already have an absence on those dates; change that one instead", status=409)
        if len(upcoming) >= MAX_UPCOMING:
            raise AbsenceError(f"You have {MAX_UPCOMING} absences booked already", status=409)
        return note

    def report(self, member_id: int, raid_day: str, first: date, last: date, note: str | None) -> AbsenceView:
        note = self._checked(member_id, raid_day, first, last, note)
        return self._views([self.repo.add(member_id, raid_day, first, last, note)])[0]

    def change(
        self, member_id: int, raid_day: str, absence_id: int, first: date, last: date, note: str | None
    ) -> AbsenceView:
        """Change the dates or note of one of the member's own upcoming absences on `raid_day`'s team. Someone else's,
        one on another team or one already over answers as missing."""
        row = self.repo.get(absence_id)
        if row is None or row.member_id != member_id or row.raid_day != raid_day or row.last_date < self._today():
            raise AbsenceError("No such absence", status=404)
        note = self._checked(member_id, raid_day, first, last, note, editing=absence_id)
        changed = self.repo.change(absence_id, first, last, note)
        if changed is None:
            raise AbsenceError("No such absence", status=404)
        return self._views([changed])[0]

    def cancel(self, member_id: int, absence_id: int) -> None:
        """Take back one of the member's own absences. Someone else's answers as missing, so ids reveal nothing."""
        row = self.repo.get(absence_id)
        if row is None or row.member_id != member_id:
            raise AbsenceError("No such absence", status=404)
        self.repo.remove(absence_id)

    def team(self, raid_day: str, count: int = TEAM_NIGHTS) -> TeamView:
        """The officers' view of one raid day: the next `count` nights with who is away, and every upcoming absence."""
        today = self._today()
        absences = self._views(self.repo.for_day(raid_day, today))
        nights: list[NightView] = []
        weekday = self._weekdays.get(raid_day)
        if weekday is not None:
            first = today + timedelta(days=(weekday - today.weekday()) % 7)
            for i in range(count):
                night = first + timedelta(weeks=i)
                away = [a for a in absences if a.first_date <= night <= a.last_date]
                nights.append(NightView(night, sorted(away, key=lambda a: a.member_name.casefold())))
        return TeamView(raid_day, nights, absences)
