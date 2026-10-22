"""Rules for members' professions and the guild's crafters. No RBAC, web framework or storage imports: the routes decide
who may call (and for which raid day), and the repository decides where things live."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime

from toads_api.professions.catalog import MAX_SKILL, PROFESSIONS
from toads_api.professions.repository import CrafterRecord, ProfessionRecord, ProfessionRepository

NOTE_MAX = 200


class ProfessionError(Exception):
    """A request the rules refuse. `status` is the HTTP code the adapter should answer with."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


@dataclass(frozen=True)
class Named:
    """A profession a member is one of the guild's crafters for."""

    profession: str
    note: str | None
    designated_by: str | None
    designated_at: datetime


@dataclass(frozen=True)
class MemberProfessions:
    """A member's professions and the ones officers named them a guild crafter for."""

    member_id: int
    name: str
    professions: list[ProfessionRecord]
    crafter_for: list[Named]


@dataclass(frozen=True)
class CrafterView:
    """One of the guild's crafters, with the skill and specialisation they list for the profession."""

    profession: str
    member_id: int
    member_name: str
    skill: int | None
    specialisation: str | None
    note: str | None
    designated_by: str | None
    designated_at: datetime


def check_professions(records: list[ProfessionRecord]) -> None:
    """Known professions, each once, a skill from 1 to MAX_SKILL and a specialisation of that profession."""
    seen: set[str] = set()
    for r in records:
        known = PROFESSIONS.get(r.profession)
        if known is None:
            raise ProfessionError("Unknown profession", status=422)
        if r.profession in seen:
            raise ProfessionError(f"{known.name} is listed twice", status=422)
        seen.add(r.profession)
        if r.skill is not None and not 1 <= r.skill <= MAX_SKILL:
            raise ProfessionError(f"Skill runs from 1 to {MAX_SKILL}", status=422)
        if r.specialisation is not None and r.specialisation not in dict(known.specialisations):
            raise ProfessionError(f"Choose a {known.name} specialisation", status=422)


def _note(note: str | None) -> str | None:
    note = " ".join((note or "").split())
    if len(note) > NOTE_MAX:
        raise ProfessionError(f"Keep the note to {NOTE_MAX} characters", status=422)
    return note or None


class ProfessionService:
    def __init__(self, repo: ProfessionRepository, shown_names: Callable[[Iterable[int]], Mapping[int, str]]) -> None:
        self.repo = repo
        self._names = shown_names

    # ---------------------------------------------------------------- a member's own

    def mine(self, member_id: int) -> MemberProfessions:
        found = self._gather([member_id], keep_empty=True)
        return found[0] if found else MemberProfessions(member_id, "", [], [])

    def set_mine(self, member_id: int, records: list[ProfessionRecord]) -> tuple[MemberProfessions, list[str]]:
        """Replace the member's professions. Returns them with the professions whose crafter naming went because the
        member no longer lists them."""
        records = [ProfessionRecord(member_id, r.profession, r.skill, r.specialisation) for r in records]
        check_professions(records)
        gone = self.repo.set_professions(member_id, sorted(records, key=lambda r: r.profession))
        return self.mine(member_id), gone

    # ---------------------------------------------------------------- officers

    def roster(self, raid_day: str) -> list[MemberProfessions]:
        """Everyone on the raid day, with professions or without, sorted by name."""
        return self._gather(self.repo.members_on(raid_day), keep_empty=True)

    def everyone(self) -> list[MemberProfessions]:
        """Every member who lists a profession, guild-wide, sorted by name."""
        ids = {r.member_id for r in self.repo.professions()}
        return self._gather(ids, keep_empty=False)

    def crafters(self) -> list[CrafterView]:
        """The guild's crafters, guild-wide, by profession in catalogue order then name."""
        named = self.repo.crafters()
        ids = {c.member_id for c in named} | {c.designated_by for c in named if c.designated_by is not None}
        names = self._names(ids)
        listed = {(r.member_id, r.profession): r for r in self.repo.professions({c.member_id for c in named})}
        order = list(PROFESSIONS)
        views = []
        for c in named:
            if c.member_id not in names:
                continue
            had = listed.get((c.member_id, c.profession))
            views.append(
                CrafterView(
                    c.profession,
                    c.member_id,
                    names[c.member_id],
                    had.skill if had else None,
                    had.specialisation if had else None,
                    c.note,
                    names.get(c.designated_by) if c.designated_by is not None else None,
                    c.designated_at,
                )
            )
        return sorted(views, key=lambda v: (order.index(v.profession), v.member_name.casefold(), v.member_id))

    def designate(
        self, profession: str, member_id: int, note: str | None, by: int, raid_day: str | None = None
    ) -> CrafterView:
        """Name a member a guild crafter for a profession they list. From a raid day's page (`raid_day` set) only that
        night's members can be named; the global tier names anyone."""
        known = PROFESSIONS.get(profession)
        if known is None:
            raise ProfessionError("Unknown profession", status=422)
        self._check_reach(member_id, raid_day)
        held = next((r for r in self.repo.professions([member_id]) if r.profession == profession), None)
        if held is None:
            raise ProfessionError(f"They do not list {known.name} on Me", status=422)
        row = self.repo.designate(profession, member_id, _note(note), by, raid_day)
        names = self._names([member_id, by])
        return CrafterView(
            profession,
            member_id,
            names[member_id],
            held.skill,
            held.specialisation,
            row.note,
            names.get(by),
            row.designated_at,
        )

    def undesignate(self, profession: str, member_id: int, by: int, raid_day: str | None = None) -> None:
        self._check_reach(member_id, raid_day)
        if not self.repo.undesignate(profession, member_id, by, raid_day):
            raise ProfessionError("They are not named for that profession", status=404)

    # ---------------------------------------------------------------- helpers

    def _check_reach(self, member_id: int, raid_day: str | None) -> None:
        if member_id not in self._names([member_id]):
            raise ProfessionError("No such member", status=404)
        if raid_day is not None and member_id not in self.repo.members_on(raid_day):
            raise ProfessionError("They are not on this raid night", status=404)

    def _gather(self, member_ids: Iterable[int], *, keep_empty: bool) -> list[MemberProfessions]:
        ids = list(member_ids)
        names = self._names(ids)
        listed: dict[int, list[ProfessionRecord]] = defaultdict(list)
        for r in self.repo.professions(ids):
            listed[r.member_id].append(r)
        named: dict[int, list[CrafterRecord]] = defaultdict(list)
        for c in self.repo.crafters(ids):
            named[c.member_id].append(c)
        by_names = self._names({c.designated_by for cs in named.values() for c in cs if c.designated_by is not None})
        out = []
        for member_id in ids:
            if member_id not in names or not (keep_empty or listed.get(member_id)):
                continue
            crafter_for = [
                Named(c.profession, c.note, by_names.get(c.designated_by) if c.designated_by else None, c.designated_at)
                for c in named.get(member_id, [])
            ]
            out.append(MemberProfessions(member_id, names[member_id], listed.get(member_id, []), crafter_for))
        return sorted(out, key=lambda m: (m.name.casefold(), m.member_id))
