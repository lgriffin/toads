"""Members' awards (docs/awards.md).

- GET    /api/me/awards                  the caller's own awards, newest first
- GET    /api/awards                     every award in the guild, newest first (any signed-in member)
- POST   /api/admin/awards               give a member an award (global officers and super admins)
- DELETE /api/admin/awards/{award_id}    take one back

Awards are guild-wide rather than a raid day's, so giving them is the global tier's job, under /api/admin like every
guild-wide officer route.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

import anyio
import structlog
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from toads_api.awards.catalog import AwardKind
from toads_api.awards.service import NOTE_LIMIT, AwardError, AwardService, AwardView
from toads_api.rbac import Permission, Principal
from toads_api.rbac.deps import get_services, require

log = structlog.get_logger(__name__)
router = APIRouter(tags=["awards"])


def get_awards(request: Request) -> AwardService:
    return get_services(request).awards


Awards = Annotated[AwardService, Depends(get_awards)]
SignedIn = Annotated[Principal, Depends(require(Permission.VIEW_GUILD_RAIDS))]
Manager = Annotated[Principal, Depends(require(Permission.MANAGE_AWARDS))]


class AwardOut(BaseModel):
    id: int
    award_id: str
    name: str
    kind: AwardKind
    member_id: int
    member_name: str
    period: str | None
    note: str | None
    awarded_at: datetime


class AwardIn(BaseModel):
    member_id: int = Field(gt=0)
    award_id: str = Field(min_length=1, max_length=48)
    # "YYYY-MM": required for a monthly award (Raider of the Month), refused for the rest.
    period: str | None = Field(default=None, max_length=7)
    note: str | None = Field(default=None, max_length=NOTE_LIMIT)


def _out(v: AwardView) -> AwardOut:
    return AwardOut(
        id=v.id,
        award_id=v.award_id,
        name=v.name,
        kind=v.kind,
        member_id=v.member_id,
        member_name=v.member_name,
        period=v.period,
        note=v.note,
        awarded_at=v.awarded_at,
    )


def _refused(exc: AwardError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.message)


@router.get("/api/me/awards")
async def my_awards(principal: SignedIn, awards: Awards) -> list[AwardOut]:
    return [_out(v) for v in await anyio.to_thread.run_sync(awards.held_by, principal.member_id)]


@router.get("/api/awards")
async def guild_awards(principal: SignedIn, awards: Awards) -> list[AwardOut]:
    return [_out(v) for v in await anyio.to_thread.run_sync(awards.wall)]


@router.post("/api/admin/awards", status_code=status.HTTP_201_CREATED)
async def give_award(body: AwardIn, principal: Manager, awards: Awards) -> AwardOut:
    try:
        view = await anyio.to_thread.run_sync(
            lambda: awards.give(body.member_id, body.award_id, principal.member_id, body.period, body.note)
        )
    except AwardError as exc:
        raise _refused(exc) from None
    log.info("award.given", by=principal.member_id, member_id=body.member_id, award=body.award_id)
    return _out(view)


@router.delete("/api/admin/awards/{award_id}", status_code=status.HTTP_204_NO_CONTENT)
async def take_back_award(award_id: int, principal: Manager, awards: Awards) -> Response:
    try:
        await anyio.to_thread.run_sync(awards.take_back, award_id, principal.member_id)
    except AwardError as exc:
        raise _refused(exc) from None
    log.info("award.taken_back", by=principal.member_id, award_row=award_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def include_awards(app: FastAPI) -> None:
    app.include_router(router)
