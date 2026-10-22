"""Raid strategy docs (docs/strategy.md).

- GET    /api/strategy                            every raid's docs and the docs each night pins (any signed-in member)
- POST   /api/admin/strategy                      add a Google Doc to a raid (global officers and super admins)
- DELETE /api/admin/strategy/{doc_id}             take a doc down, off every night that pins it
- POST   /api/days/{day}/strategy/docs            add a doc to a raid, as one of that night's officers
- DELETE /api/days/{day}/strategy/docs/{doc_id}   take down a doc no other night pins
- GET    /api/days/{day}/strategy                 the docs the night pins for its raiders (its Raid page)
- PUT    /api/days/{day}/strategy                 pin the night's docs, in order (that night's officers)

Every officer may add docs (Leigh, 2026-10-22): a night's officers through their night's path, which keeps officer
powers scoped to a raid day in the URL; the global tier through /api/admin. A doc shows to raiders only once a night
pins it, and only that night's officers (or the global tier) pin its docs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

import anyio
import structlog
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Path, Request, Response, status
from pydantic import BaseModel, Field

from toads_api.rbac import HubRole, Permission, Principal
from toads_api.rbac.deps import get_services, require
from toads_api.services import Services
from toads_api.strategy.service import (
    NIGHT_LIMIT,
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


class LibraryDocOut(DocOut):
    # The raid days that pin it for their raiders, in config order.
    nights: list[str]


class RaidDocsOut(BaseModel):
    raid: RaidOut
    docs: list[LibraryDocOut]


class NightDocsOut(BaseModel):
    raid_day: str
    name: str
    docs: list[int]


class LibraryOut(BaseModel):
    raids: list[RaidDocsOut]
    nights: list[NightDocsOut]


class NightDocOut(BaseModel):
    raid: RaidOut
    doc: DocOut


class NightStrategyOut(BaseModel):
    raid_day: str
    docs: list[NightDocOut]


class AddIn(BaseModel):
    raid: str = Field(pattern=RAID)
    url: str = Field(min_length=1, max_length=URL_LIMIT)
    title: str = Field(default="", max_length=TITLE_LIMIT)


class NightDocsIn(BaseModel):
    # In the order the Raid page lists them; [] pins none.
    docs: list[Annotated[int, Field(gt=0, lt=2**31)]] = Field(default_factory=list, max_length=NIGHT_LIMIT * 2)


def _raid(r: Raid) -> RaidOut:
    return RaidOut(id=r.id, short=r.short, name=r.name)


def _doc(v: DocView) -> DocOut:
    d = v.doc
    return DocOut(id=d.id, raid=d.raid, title=d.title, url=d.url, added_by=v.added_by, added_at=d.created_at)


def _night(day: str, n: NightStrategy) -> NightStrategyOut:
    return NightStrategyOut(raid_day=day, docs=[NightDocOut(raid=_raid(d.raid), doc=_doc(d.doc)) for d in n.docs])


def _refused(exc: StrategyError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.message)


def _library(strategy: StrategyService, services: Services) -> LibraryOut:
    names = {d.id: d.name for d in services.raid_days.raid_days}
    pinned = strategy.night_docs()
    raids = [
        RaidDocsOut(
            raid=_raid(r.raid),
            docs=[
                LibraryDocOut(**_doc(v).model_dump(), nights=[d for d in names if v.doc.id in pinned.get(d, [])])
                for v in r.docs
            ],
        )
        for r in strategy.library()
    ]
    nights = [NightDocsOut(raid_day=d, name=n, docs=pinned.get(d, [])) for d, n in names.items()]
    return LibraryOut(raids=raids, nights=nights)


@router.get("/api/strategy")
async def strategy_library(principal: SignedIn, strategy: Strategy, services: Hub) -> LibraryOut:
    return await anyio.to_thread.run_sync(_library, strategy, services)


async def _add(strategy: StrategyService, body: AddIn, principal: Principal, through: str | None) -> DocOut:
    try:
        view = await anyio.to_thread.run_sync(
            lambda: strategy.add(body.raid, url=body.url, title=body.title, by=principal.member_id, through=through)
        )
    except StrategyError as exc:
        raise _refused(exc) from None
    log.info("strategy.added", by=principal.member_id, day=through, raid=body.raid, doc=view.doc.id)
    return _doc(view)


async def _remove(strategy: StrategyService, doc_id: int, principal: Principal, through: str | None) -> Response:
    # A night's officers take down only docs no night they don't run pins; the global tier any doc.
    runs = None
    if through is not None and not principal.global_officer:
        runs = frozenset(d for d, role in principal.day_roles.items() if role is HubRole.OFFICER)
    try:
        await anyio.to_thread.run_sync(
            lambda: strategy.remove(doc_id, principal.member_id, through=through, nights=runs)
        )
    except StrategyError as exc:
        raise _refused(exc) from None
    log.info("strategy.removed", by=principal.member_id, day=through, doc=doc_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/api/admin/strategy", status_code=status.HTTP_201_CREATED)
async def add_strategy(body: AddIn, principal: GlobalOfficer, strategy: Strategy) -> DocOut:
    return await _add(strategy, body, principal, None)


@router.delete("/api/admin/strategy/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_strategy(doc_id: DocId, principal: GlobalOfficer, strategy: Strategy) -> Response:
    return await _remove(strategy, doc_id, principal, None)


@router.post("/api/days/{day}/strategy/docs", status_code=status.HTTP_201_CREATED)
async def night_add_strategy(day: str, body: AddIn, principal: DayOfficer, strategy: Strategy) -> DocOut:
    return await _add(strategy, body, principal, day)


@router.delete("/api/days/{day}/strategy/docs/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def night_remove_strategy(day: str, doc_id: DocId, principal: DayOfficer, strategy: Strategy) -> Response:
    return await _remove(strategy, doc_id, principal, day)


@router.get("/api/days/{day}/strategy")
async def night_strategy(day: str, principal: DayViewer, strategy: Strategy) -> NightStrategyOut:
    return _night(day, await anyio.to_thread.run_sync(strategy.night, day))


@router.put("/api/days/{day}/strategy")
async def pin_night_docs(day: str, body: NightDocsIn, principal: DayOfficer, strategy: Strategy) -> NightStrategyOut:
    try:
        night = await anyio.to_thread.run_sync(strategy.set_night, day, body.docs, principal.member_id)
    except StrategyError as exc:
        raise _refused(exc) from None
    log.info("strategy.night_pinned", by=principal.member_id, day=day, docs=body.docs)
    return _night(day, night)


def include_strategy(app: FastAPI) -> None:
    app.include_router(router)
