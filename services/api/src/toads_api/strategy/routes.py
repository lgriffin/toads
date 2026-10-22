"""Raid strategy docs (docs/strategy.md).

- GET    /api/strategy                    every raid's pinned doc and the docs it replaced, and the raid each night is
                                          running (any signed-in member)
- POST   /api/admin/strategy              pin a Google Doc to a raid, replacing its pinned doc (global officers and
                                          super admins)
- DELETE /api/admin/strategy/{doc_id}     take a doc down
- GET    /api/days/{day}/strategy         the raid the night is running and its pinned doc, for its Raid page
- PUT    /api/days/{day}/strategy         say which raid the night is running (that night's officers)
- POST   /api/days/{day}/strategy/docs            pin a doc as one of that night's officers
- DELETE /api/days/{day}/strategy/docs/{doc_id}   take a doc down as one of that night's officers

A raid's pinned doc is guild-wide, but Leigh asked that every officer can pin and replace one, not only the global tier
(2026-10-22). So a night's officers pin through their night's path, which keeps officer powers scoped to a raid day in
the URL and puts the night on the audit log; the global tier uses /api/admin like every guild-wide officer route.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

import anyio
import structlog
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Path, Request, Response, status
from pydantic import BaseModel, Field

from toads_api.rbac import Permission, Principal
from toads_api.rbac.deps import get_services, require
from toads_api.services import Services
from toads_api.strategy.service import (
    RAIDS,
    TITLE_LIMIT,
    URL_LIMIT,
    DocView,
    NightStrategy,
    Raid,
    StrategyError,
    StrategyService,
)

log = structlog.get_logger(__name__)
router = APIRouter(tags=["strategy"])


def get_strategy(request: Request) -> StrategyService:
    return get_services(request).strategy


Strategy = Annotated[StrategyService, Depends(get_strategy)]
Hub = Annotated[Services, Depends(get_services)]
SignedIn = Annotated[Principal, Depends(require(Permission.VIEW_GUILD_RAIDS))]
DayViewer = Annotated[Principal, Depends(require(Permission.VIEW_GUILD_RAIDS, scoped=True))]
DayOfficer = Annotated[Principal, Depends(require(Permission.MANAGE_STRATEGY, scoped=True))]
GlobalOfficer = Annotated[Principal, Depends(require(Permission.MANAGE_STRATEGY))]
DocId = Annotated[int, Path(gt=0, lt=2**31)]
RAID = "^(" + "|".join(RAIDS) + ")$"


class RaidOut(BaseModel):
    id: str
    short: str
    name: str


class DocOut(BaseModel):
    id: int
    raid: str
    title: str
    url: str
    added_by: str | None
    added_at: datetime


class RaidStrategyOut(BaseModel):
    raid: RaidOut
    pinned: DocOut | None
    replaced: list[DocOut]


class NightRaidOut(BaseModel):
    raid_day: str
    name: str
    raid: str | None


class LibraryOut(BaseModel):
    raids: list[RaidStrategyOut]
    nights: list[NightRaidOut]


class NightStrategyOut(BaseModel):
    raid_day: str
    raid: RaidOut | None
    pinned: DocOut | None


class PinIn(BaseModel):
    raid: str = Field(pattern=RAID)
    url: str = Field(min_length=1, max_length=URL_LIMIT)
    title: str = Field(default="", max_length=TITLE_LIMIT)


class NightRaidIn(BaseModel):
    # None: the night has not settled on a raid yet, so its Raid page shows no doc.
    raid: str | None = Field(default=None, pattern=RAID)


def _raid(r: Raid) -> RaidOut:
    return RaidOut(id=r.id, short=r.short, name=r.name)


def _doc(v: DocView) -> DocOut:
    d = v.doc
    return DocOut(id=d.id, raid=d.raid, title=d.title, url=d.url, added_by=v.added_by, added_at=d.created_at)


def _night(day: str, n: NightStrategy) -> NightStrategyOut:
    return NightStrategyOut(
        raid_day=day,
        raid=_raid(n.raid) if n.raid else None,
        pinned=_doc(n.pinned) if n.pinned else None,
    )


def _refused(exc: StrategyError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.message)


def _library(strategy: StrategyService, services: Services) -> LibraryOut:
    raids = [
        RaidStrategyOut(
            raid=_raid(r.raid), pinned=_doc(r.pinned) if r.pinned else None, replaced=[_doc(v) for v in r.replaced]
        )
        for r in strategy.library()
    ]
    chosen = strategy.night_raids()
    nights = [NightRaidOut(raid_day=d.id, name=d.name, raid=chosen.get(d.id)) for d in services.raid_days.raid_days]
    return LibraryOut(raids=raids, nights=nights)


@router.get("/api/strategy")
async def strategy_library(principal: SignedIn, strategy: Strategy, services: Hub) -> LibraryOut:
    return await anyio.to_thread.run_sync(_library, strategy, services)


@router.post("/api/admin/strategy", status_code=status.HTTP_201_CREATED)
async def pin_strategy(body: PinIn, principal: GlobalOfficer, strategy: Strategy) -> DocOut:
    try:
        view = await anyio.to_thread.run_sync(
            lambda: strategy.pin(body.raid, url=body.url, title=body.title, by=principal.member_id)
        )
    except StrategyError as exc:
        raise _refused(exc) from None
    log.info("strategy.pinned", by=principal.member_id, raid=body.raid, doc=view.doc.id)
    return _doc(view)


@router.delete("/api/admin/strategy/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_strategy(doc_id: DocId, principal: GlobalOfficer, strategy: Strategy) -> Response:
    try:
        await anyio.to_thread.run_sync(strategy.remove, doc_id, principal.member_id)
    except StrategyError as exc:
        raise _refused(exc) from None
    log.info("strategy.removed", by=principal.member_id, doc=doc_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/api/days/{day}/strategy/docs", status_code=status.HTTP_201_CREATED)
async def night_pin_strategy(day: str, body: PinIn, principal: DayOfficer, strategy: Strategy) -> DocOut:
    try:
        view = await anyio.to_thread.run_sync(
            lambda: strategy.pin(body.raid, url=body.url, title=body.title, by=principal.member_id, raid_day=day)
        )
    except StrategyError as exc:
        raise _refused(exc) from None
    log.info("strategy.pinned", by=principal.member_id, day=day, raid=body.raid, doc=view.doc.id)
    return _doc(view)


@router.delete("/api/days/{day}/strategy/docs/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def night_remove_strategy(day: str, doc_id: DocId, principal: DayOfficer, strategy: Strategy) -> Response:
    try:
        await anyio.to_thread.run_sync(strategy.remove, doc_id, principal.member_id, day)
    except StrategyError as exc:
        raise _refused(exc) from None
    log.info("strategy.removed", by=principal.member_id, day=day, doc=doc_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/api/days/{day}/strategy")
async def night_strategy(day: str, principal: DayViewer, strategy: Strategy) -> NightStrategyOut:
    return _night(day, await anyio.to_thread.run_sync(strategy.night, day))


@router.put("/api/days/{day}/strategy")
async def set_night_raid(day: str, body: NightRaidIn, principal: DayOfficer, strategy: Strategy) -> NightStrategyOut:
    try:
        night = await anyio.to_thread.run_sync(strategy.set_night, day, body.raid, principal.member_id)
    except StrategyError as exc:
        raise _refused(exc) from None
    log.info("strategy.night_set", by=principal.member_id, day=day, raid=body.raid)
    return _night(day, night)


def include_strategy(app: FastAPI) -> None:
    app.include_router(router)
