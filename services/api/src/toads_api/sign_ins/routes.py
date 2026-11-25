"""The officers' sign-in audit (docs/sign-ins.md): who signed in to the hub on a day, and when each member last did.

- GET /api/days/{day}/sign-ins?on=YYYY-MM-DD  that raid night's members (its officers; global officers see every night)
- GET /api/admin/sign-ins?on=YYYY-MM-DD       members on no raid night (global officers and super admins)

The raid night comes from the path only (REQ-HUB-SIGNIN-002): a Sunday officer never sees Wednesday's members.
`on` defaults to today in the guild's time zone.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

import anyio
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel

from toads_api.rbac import Permission, Principal
from toads_api.rbac.deps import get_services, require
from toads_api.sign_ins.service import AuditDayView, SignInError, SignInService

router = APIRouter(tags=["sign-ins"])


def get_sign_ins(request: Request) -> SignInService:
    return get_services(request).sign_ins


SignIns = Annotated[SignInService, Depends(get_sign_ins)]
NightOfficer = Annotated[Principal, Depends(require(Permission.VIEW_SIGN_INS, scoped=True))]
# Without a raid day in the path only the global tier holds an officer permission.
GlobalOfficer = Annotated[Principal, Depends(require(Permission.VIEW_SIGN_INS))]


class SignInOut(BaseModel):
    member_id: int
    member_name: str
    at: datetime


class LastSignInOut(BaseModel):
    member_id: int
    member_name: str
    last_signed_in_at: datetime | None


class DayCountOut(BaseModel):
    date: date
    sign_ins: int
    members: int


class AuditDayOut(BaseModel):
    raid_day: str | None
    date: date
    sign_ins: list[SignInOut]
    members: list[LastSignInOut]
    recent: list[DayCountOut]


def _out(v: AuditDayView) -> AuditDayOut:
    return AuditDayOut(
        raid_day=v.raid_day,
        date=v.date,
        sign_ins=[SignInOut(member_id=s.member_id, member_name=s.member_name, at=s.at) for s in v.sign_ins],
        members=[
            LastSignInOut(member_id=m.member_id, member_name=m.member_name, last_signed_in_at=m.last_signed_in_at)
            for m in v.members
        ],
        recent=[DayCountOut(date=d.date, sign_ins=d.sign_ins, members=d.members) for d in v.recent],
    )


async def _day(sign_ins: SignInService, raid_day: str | None, on: date | None) -> AuditDayOut:
    try:
        return _out(await anyio.to_thread.run_sync(sign_ins.day, raid_day, on))
    except SignInError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message) from None


@router.get("/api/days/{day}/sign-ins")
async def night_sign_ins(day: str, _: NightOfficer, sign_ins: SignIns, on: date | None = None) -> AuditDayOut:
    return await _day(sign_ins, day, on)


@router.get("/api/admin/sign-ins")
async def unplaced_sign_ins(_: GlobalOfficer, sign_ins: SignIns, on: date | None = None) -> AuditDayOut:
    return await _day(sign_ins, None, on)


def include_sign_ins(app: FastAPI) -> None:
    app.include_router(router)
