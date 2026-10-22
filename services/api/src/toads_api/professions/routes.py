"""Members' professions and the guild's crafters (docs/professions.md).

- GET    /api/me/professions                                  the caller's professions and what they are named for
- PUT    /api/me/professions                                  replace them
- GET    /api/days/{day}/professions                          the night's roster with everyone's professions, and the
                                                              guild's crafters (that night's officers)
- PUT    /api/days/{day}/crafters/{profession}/{member_id}    name one of the night's members a guild crafter
- DELETE /api/days/{day}/crafters/{profession}/{member_id}    take it back
- GET    /api/admin/professions                               every member who lists a profession, and the guild's
                                                              crafters (global officers and super admins)
- PUT    /api/admin/crafters/{profession}/{member_id}         name anyone a guild crafter
- DELETE /api/admin/crafters/{profession}/{member_id}         take it back

The guild's crafters are guild-wide: a night's officers name and un-name only members on their night, and the global
tier anyone. The /me routes act on the caller's own member id, taken from the session, never from the request.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

import anyio
import structlog
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from toads_api.identity import refresh_raid_rosters
from toads_api.professions.repository import ProfessionRecord
from toads_api.professions.service import (
    NOTE_MAX,
    CrafterView,
    MemberProfessions,
    ProfessionError,
    ProfessionService,
)
from toads_api.rbac import Permission, Principal
from toads_api.rbac.deps import get_services, require

log = structlog.get_logger(__name__)
router = APIRouter(tags=["professions"])


def get_professions(request: Request) -> ProfessionService:
    return get_services(request).professions


Professions = Annotated[ProfessionService, Depends(get_professions)]
SignedIn = Annotated[Principal, Depends(require(Permission.VIEW_GUILD_RAIDS))]
DayOfficer = Annotated[Principal, Depends(require(Permission.MANAGE_CRAFTERS, scoped=True))]
GlobalOfficer = Annotated[Principal, Depends(require(Permission.MANAGE_CRAFTERS))]
ID = r"^[a-z-]{1,32}$"


class ProfessionIn(BaseModel):
    profession: str = Field(pattern=ID)
    skill: int | None = None
    specialisation: str | None = Field(default=None, pattern=ID)


class ProfessionsIn(BaseModel):
    professions: list[ProfessionIn] = Field(max_length=20)


class ProfessionOut(BaseModel):
    profession: str
    skill: int | None
    specialisation: str | None


class NamedOut(BaseModel):
    profession: str
    note: str | None
    designated_by: str | None
    designated_at: datetime


class MemberProfessionsOut(BaseModel):
    member_id: int
    name: str
    professions: list[ProfessionOut]
    crafter_for: list[NamedOut]


class MyProfessionsOut(BaseModel):
    professions: list[ProfessionOut]
    crafter_for: list[NamedOut]
    # Set on a save: the professions the member was a guild crafter for and no longer lists, so that naming went.
    unnamed: list[str] = []


class CrafterOut(BaseModel):
    profession: str
    member_id: int
    member_name: str
    skill: int | None
    specialisation: str | None
    note: str | None
    designated_by: str | None
    designated_at: datetime


class OverviewOut(BaseModel):
    members: list[MemberProfessionsOut]
    crafters: list[CrafterOut]


class CrafterIn(BaseModel):
    note: str | None = Field(default=None, max_length=NOTE_MAX * 2)


def _member(m: MemberProfessions) -> MemberProfessionsOut:
    return MemberProfessionsOut(
        member_id=m.member_id,
        name=m.name,
        professions=[
            ProfessionOut(profession=r.profession, skill=r.skill, specialisation=r.specialisation)
            for r in m.professions
        ],
        crafter_for=[
            NamedOut(profession=n.profession, note=n.note, designated_by=n.designated_by, designated_at=n.designated_at)
            for n in m.crafter_for
        ],
    )


def _crafter(c: CrafterView) -> CrafterOut:
    return CrafterOut(
        profession=c.profession,
        member_id=c.member_id,
        member_name=c.member_name,
        skill=c.skill,
        specialisation=c.specialisation,
        note=c.note,
        designated_by=c.designated_by,
        designated_at=c.designated_at,
    )


def _refused(exc: ProfessionError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.message)


def _mine(m: MemberProfessions, unnamed: list[str] | None = None) -> MyProfessionsOut:
    out = _member(m)
    return MyProfessionsOut(professions=out.professions, crafter_for=out.crafter_for, unnamed=unnamed or [])


@router.get("/api/me/professions")
async def my_professions(principal: SignedIn, professions: Professions) -> MyProfessionsOut:
    return _mine(await anyio.to_thread.run_sync(professions.mine, principal.member_id))


@router.put("/api/me/professions")
async def set_my_professions(body: ProfessionsIn, principal: SignedIn, professions: Professions) -> MyProfessionsOut:
    records = [ProfessionRecord(principal.member_id, p.profession, p.skill, p.specialisation) for p in body.professions]
    try:
        mine, gone = await anyio.to_thread.run_sync(professions.set_mine, principal.member_id, records)
    except ProfessionError as exc:
        raise _refused(exc) from None
    if gone:
        log.info("crafter.unlisted", member=principal.member_id, professions=gone)
    return _mine(mine, gone)


@router.get("/api/days/{day}/professions")
async def night_professions(day: str, principal: DayOfficer, professions: Professions, request: Request) -> OverviewOut:
    # The night's role holders come from the server itself, so people who never signed in are listed too.
    await refresh_raid_rosters(get_services(request))
    members = await anyio.to_thread.run_sync(professions.roster, day)
    crafters = await anyio.to_thread.run_sync(professions.crafters)
    return OverviewOut(members=[_member(m) for m in members], crafters=[_crafter(c) for c in crafters])


@router.get("/api/admin/professions")
async def all_professions(principal: GlobalOfficer, professions: Professions) -> OverviewOut:
    members = await anyio.to_thread.run_sync(professions.everyone)
    crafters = await anyio.to_thread.run_sync(professions.crafters)
    return OverviewOut(members=[_member(m) for m in members], crafters=[_crafter(c) for c in crafters])


async def _name(
    professions: ProfessionService, profession: str, member_id: int, note: str | None, by: int, day: str | None
) -> CrafterOut:
    try:
        view = await anyio.to_thread.run_sync(lambda: professions.designate(profession, member_id, note, by, day))
    except ProfessionError as exc:
        raise _refused(exc) from None
    log.info("crafter.named", by=by, member=member_id, profession=profession, raid_day=day)
    return _crafter(view)


async def _unname(
    professions: ProfessionService, profession: str, member_id: int, by: int, day: str | None
) -> Response:
    try:
        await anyio.to_thread.run_sync(lambda: professions.undesignate(profession, member_id, by, day))
    except ProfessionError as exc:
        raise _refused(exc) from None
    log.info("crafter.unnamed", by=by, member=member_id, profession=profession, raid_day=day)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/api/days/{day}/crafters/{profession}/{member_id}")
async def name_night_crafter(
    day: str, profession: str, member_id: int, body: CrafterIn, principal: DayOfficer, professions: Professions
) -> CrafterOut:
    return await _name(professions, profession, member_id, body.note, principal.member_id, day)


@router.delete("/api/days/{day}/crafters/{profession}/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unname_night_crafter(
    day: str, profession: str, member_id: int, principal: DayOfficer, professions: Professions
) -> Response:
    return await _unname(professions, profession, member_id, principal.member_id, day)


@router.put("/api/admin/crafters/{profession}/{member_id}")
async def name_crafter(
    profession: str, member_id: int, body: CrafterIn, principal: GlobalOfficer, professions: Professions
) -> CrafterOut:
    return await _name(professions, profession, member_id, body.note, principal.member_id, None)


@router.delete("/api/admin/crafters/{profession}/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unname_crafter(
    profession: str, member_id: int, principal: GlobalOfficer, professions: Professions
) -> Response:
    return await _unname(professions, profession, member_id, principal.member_id, None)


def include_professions(app: FastAPI) -> None:
    app.include_router(router)
