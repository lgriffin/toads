"""Rules for awards. No RBAC, web framework or storage imports: the routes decide who may call, and the repository
decides where things live."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime

from toads_api.awards.catalog import AWARDS, AwardKind
from toads_api.awards.repository import AwardRecord, AwardRepository, DuplicateAwardError

PERIOD = re.compile(r"(20\d\d)-(0[1-9]|1[0-2])")
NOTE_LIMIT = 200


class AwardError(Exception):
    """A request the rules refuse. `status` is the HTTP code the adapter should answer with."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


@dataclass(frozen=True)
class AwardView:
    """An award as the site shows it: what it is, who holds it and why."""

    id: int
    award_id: str
    name: str
    kind: AwardKind
    member_id: int
    member_name: str
    # "YYYY-MM" for a monthly award, None otherwise.
    period: str | None
    note: str | None
    awarded_at: datetime


class AwardService:
    def __init__(self, repo: AwardRepository, shown_names: Callable[[Iterable[int]], dict[int, str]]) -> None:
        self.repo = repo
        self._shown_names = shown_names

    def _views(self, rows: list[AwardRecord]) -> list[AwardView]:
        # An award retired from the catalogue stays stored but is no longer shown.
        rows = [r for r in rows if r.award_id in AWARDS]
        names = self._shown_names({r.member_id for r in rows})
        views = [
            AwardView(
                id=r.id,
                award_id=r.award_id,
                name=AWARDS[r.award_id].name,
                kind=AWARDS[r.award_id].kind,
                member_id=r.member_id,
                member_name=names.get(r.member_id, ""),
                period=r.period or None,
                note=r.note,
                awarded_at=r.awarded_at,
            )
            for r in rows
        ]
        return sorted(views, key=lambda v: (v.awarded_at, v.id), reverse=True)

    def held_by(self, member_id: int) -> list[AwardView]:
        """A member's awards, newest first."""
        return self._views(self.repo.awards([member_id]))

    def wall(self) -> list[AwardView]:
        """Every award in the guild, newest first."""
        return self._views(self.repo.awards())

    def give(
        self, member_id: int, award_id: str, by: int, period: str | None = None, note: str | None = None
    ) -> AwardView:
        award = AWARDS.get(award_id)
        if award is None:
            raise AwardError("Unknown award", status=422)
        period = (period or "").strip()
        if award.monthly:
            if not PERIOD.fullmatch(period):
                raise AwardError("Say which month this is for, as YYYY-MM", status=422)
        elif period:
            raise AwardError(f"{award.name} is not given per month", status=422)
        note = (note or "").strip() or None
        if note is not None and len(note) > NOTE_LIMIT:
            raise AwardError(f"Keep the note under {NOTE_LIMIT} characters", status=422)
        if not self.repo.member_exists(member_id):
            raise AwardError("Unknown member", status=404)
        try:
            row = self.repo.add(member_id, award_id, period, note, by)
        except DuplicateAwardError:
            when = f" for {period}" if period else ""
            raise AwardError(f"They already hold {award.name}{when}", status=409) from None
        return self._views([row])[0]

    def take_back(self, award_row_id: int, by: int) -> None:
        if not self.repo.remove(award_row_id, by):
            raise AwardError("No such award", status=404)
