"""Absences (docs/absences.md).

- GET    /api/me/absences                the caller's absences that have not ended, soonest first
- POST   /api/days/{day}/absences        report an absence from that raid day's team (its trials and raiders)
- PUT    /api/days/{day}/absences/{absence_id}  change the dates or note of one of the caller's own on that team
- DELETE /api/me/absences/{absence_id}   cancel one of the caller's own absences
- GET    /api/days/{day}/absences        that raid day's upcoming nights and who is away (its officers)

The raid day comes from the path (REQ-HUB-DAY-023): a member reports only for a team they are on, and officers see
only their own night's absences unless they are global officers.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

import anyio
import structlog
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from toads_api.absences.service import NOTE_LIMIT, AbsenceError, AbsenceService, AbsenceView, TeamView
from toads_api.rbac import Permission, Principal
from toads_api.rbac.deps import get_services, require

log = structlog.get_logger(__name__)
router = APIRouter(tags=["absences"])


def get_absences(request: Request) -> AbsenceService:
    return get_services(request).absences


Absences = Annotated[AbsenceService, Depends(get_absences)]
SignedIn = Annotated[Principal, Depends(require(Permission.VIEW_GUILD_RAIDS))]
DayReporter = Annotated[Principal, Depends(require(Permission.REPORT_ABSENCE, scoped=True))]
DayOfficer = Annotated[Principal, Depends(require(Permission.VIEW_ABSENCES, scoped=True))]


class AbsenceOut(BaseModel):
    id: int
    member_id: int
    member_name: str
    raid_day: str
    first_date: date
    last_date: date
    note: str | None
    # The raid nights it covers from today on.
    nights: list[date]


class NightOut(BaseModel):
    date: date
    absent: list[AbsenceOut]


class TeamOut(BaseModel):
    raid_day: str
    nights: list[NightOut]
    absences: list[AbsenceOut]


class AbsenceIn(BaseModel):
    first_date: date
    # Defaults to the first date: one night.
    last_date: date | None = None
    # Why, for the night's officers; required (the service refuses a blank one with a message).
    note: str | None = Field(default=None, max_length=NOTE_LIMIT)


def _out(v: AbsenceView) -> AbsenceOut:
    return AbsenceOut(
        id=v.id,
        member_id=v.member_id,
        member_name=v.member_name,
        raid_day=v.raid_day,
        first_date=v.first_date,
        last_date=v.last_date,
        note=v.note,
        nights=v.nights,
    )


def _team(v: TeamView) -> TeamOut:
    return TeamOut(
        raid_day=v.raid_day,
        nights=[NightOut(date=n.date, absent=[_out(a) for a in n.absent]) for n in v.nights],
        absences=[_out(a) for a in v.absences],
    )


def _refused(exc: AbsenceError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.message)


@router.get("/api/me/absences")
async def my_absences(principal: SignedIn, absences: Absences) -> list[AbsenceOut]:
    return [_out(v) for v in await anyio.to_thread.run_sync(absences.mine, principal.member_id)]


@router.post("/api/days/{day}/absences", status_code=status.HTTP_201_CREATED)
async def report_absence(day: str, body: AbsenceIn, principal: DayReporter, absences: Absences) -> AbsenceOut:
    last = body.last_date or body.first_date
    try:
        view = await anyio.to_thread.run_sync(
            lambda: absences.report(principal.member_id, day, body.first_date, last, body.note)
        )
    except AbsenceError as exc:
        raise _refused(exc) from None
    log.info("absence.reported", member_id=principal.member_id, day=day, nights=len(view.nights))
    return _out(view)


@router.put("/api/days/{day}/absences/{absence_id}")
async def change_absence(
    day: str, absence_id: int, body: AbsenceIn, principal: DayReporter, absences: Absences
) -> AbsenceOut:
    # Scoped like reporting: a member changes an absence only while they are on its team.
    last = body.last_date or body.first_date
    try:
        view = await anyio.to_thread.run_sync(
            lambda: absences.change(principal.member_id, day, absence_id, body.first_date, last, body.note)
        )
    except AbsenceError as exc:
        raise _refused(exc) from None
    log.info("absence.changed", member_id=principal.member_id, day=day, absence=absence_id)
    return _out(view)


@router.delete("/api/me/absences/{absence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_absence(absence_id: int, principal: SignedIn, absences: Absences) -> Response:
    # Any signed-in member, so someone who has left a team can still take back what they reported; the service only
    # cancels the caller's own absences.
    try:
        await anyio.to_thread.run_sync(absences.cancel, principal.member_id, absence_id)
    except AbsenceError as exc:
        raise _refused(exc) from None
    log.info("absence.cancelled", member_id=principal.member_id, absence=absence_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/api/days/{day}/absences")
async def team_absences(day: str, principal: DayOfficer, absences: Absences) -> TeamOut:
    return _team(await anyio.to_thread.run_sync(absences.team, day))


def include_absences(app: FastAPI) -> None:
    app.include_router(router)
