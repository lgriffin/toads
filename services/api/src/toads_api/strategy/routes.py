"""Raid strategy docs (docs/strategy.md).

- GET    /api/strategy                            every raid's docs, for every night and each night's own, and the
                                                  raids each night is running (any signed-in member)
- POST   /api/admin/strategy                      pin a Google Doc to a raid for one night or every night (global
                                                  officers and super admins)
- DELETE /api/admin/strategy/{doc_id}             take a doc down
- POST   /api/days/{day}/strategy/docs            pin a doc for that night, or every night, as one of its officers
- DELETE /api/days/{day}/strategy/docs/{doc_id}   take down a doc pinned for that night or every night
- GET    /api/days/{day}/strategy                 the raids the night is running, each with its doc (its Raid page)
- PUT    /api/days/{day}/strategy                 say which raids the night is running (that night's officers)

Every officer may pin and replace docs (Leigh, 2026-10-22): a night's officers through their night's path, for that
night or for every night, which keeps officer powers scoped to a raid day in the URL; the global tier through /api/admin
for any night. Each night may keep its own doc for a raid, which its Raid page shows before the every-night one.
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
    # The night it is pinned for; None for every night.
    raid_day: str | None
    title: str
    url: str
    added_by: str | None
    added_at: datetime


class SlotOut(BaseModel):
    raid_day: str | None
    # "Every night", or the night's name.
    name: str
    pinned: DocOut
    replaced: list[DocOut]


class RaidStrategyOut(BaseModel):
    raid: RaidOut
    slots: list[SlotOut]


class NightRaidsOut(BaseModel):
    raid_day: str
    name: str
    raids: list[str]


class LibraryOut(BaseModel):
    raids: list[RaidStrategyOut]
    nights: list[NightRaidsOut]


class NightRaidDocOut(BaseModel):
    raid: RaidOut
    pinned: DocOut | None


class NightStrategyOut(BaseModel):
    raid_day: str
    raids: list[NightRaidDocOut]


class PinIn(BaseModel):
    raid: str = Field(pattern=RAID)
    url: str = Field(min_length=1, max_length=URL_LIMIT)
    title: str = Field(default="", max_length=TITLE_LIMIT)


class AdminPinIn(PinIn):
    # The night it is for; None for every night.
    raid_day: str | None = Field(default=None, max_length=32)


class NightPinIn(PinIn):
    # Pin it for every night instead of only the night in the path.
    every_night: bool = False


class NightRaidsIn(BaseModel):
    # In the order the night runs them; [] while the night has not settled on any.
    raids: list[str] = Field(default_factory=list, max_length=len(RAIDS))


def _raid(r: Raid) -> RaidOut:
    return RaidOut(id=r.id, short=r.short, name=r.name)


def _doc(v: DocView) -> DocOut:
    d = v.doc
    return DocOut(
        id=d.id, raid=d.raid, raid_day=d.raid_day, title=d.title, url=d.url, added_by=v.added_by, added_at=d.created_at
    )


def _night(day: str, n: NightStrategy) -> NightStrategyOut:
    return NightStrategyOut(
        raid_day=day,
        raids=[NightRaidDocOut(raid=_raid(r.raid), pinned=_doc(r.pinned) if r.pinned else None) for r in n.raids],
    )


def _refused(exc: StrategyError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.message)


def _library(strategy: StrategyService, services: Services) -> LibraryOut:
    names = {d.id: d.name for d in services.raid_days.raid_days}
    raids = [
        RaidStrategyOut(
            raid=_raid(r.raid),
            slots=[
                SlotOut(
                    raid_day=s.raid_day,
                    name="Every night" if s.raid_day is None else names.get(s.raid_day, s.raid_day),
                    pinned=_doc(s.pinned),
                    replaced=[_doc(v) for v in s.replaced],
                )
                for s in r.slots
            ],
        )
        for r in strategy.library(names)
    ]
    chosen = strategy.night_raids()
    nights = [NightRaidsOut(raid_day=d, name=n, raids=chosen.get(d, [])) for d, n in names.items()]
    return LibraryOut(raids=raids, nights=nights)


@router.get("/api/strategy")
async def strategy_library(principal: SignedIn, strategy: Strategy, services: Hub) -> LibraryOut:
    return await anyio.to_thread.run_sync(_library, strategy, services)


@router.post("/api/admin/strategy", status_code=status.HTTP_201_CREATED)
async def pin_strategy(body: AdminPinIn, principal: GlobalOfficer, strategy: Strategy, services: Hub) -> DocOut:
    if body.raid_day is not None and services.raid_days.day(body.raid_day) is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Unknown raid night")
    try:
        view = await anyio.to_thread.run_sync(
            lambda: strategy.pin(
                body.raid, url=body.url, title=body.title, by=principal.member_id, raid_day=body.raid_day
            )
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
async def night_pin_strategy(day: str, body: NightPinIn, principal: DayOfficer, strategy: Strategy) -> DocOut:
    night = None if body.every_night else day
    try:
        view = await anyio.to_thread.run_sync(
            lambda: strategy.pin(
                body.raid, url=body.url, title=body.title, by=principal.member_id, raid_day=night, through=day
            )
        )
    except StrategyError as exc:
        raise _refused(exc) from None
    log.info("strategy.pinned", by=principal.member_id, day=day, raid=body.raid, doc=view.doc.id)
    return _doc(view)


@router.delete("/api/days/{day}/strategy/docs/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def night_remove_strategy(day: str, doc_id: DocId, principal: DayOfficer, strategy: Strategy) -> Response:
    try:
        # A night's officers take down that night's docs and the every-night ones, never another night's.
        await anyio.to_thread.run_sync(strategy.remove, doc_id, principal.member_id, frozenset({day, None}), day)
    except StrategyError as exc:
        raise _refused(exc) from None
    log.info("strategy.removed", by=principal.member_id, day=day, doc=doc_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/api/days/{day}/strategy")
async def night_strategy(day: str, principal: DayViewer, strategy: Strategy) -> NightStrategyOut:
    return _night(day, await anyio.to_thread.run_sync(strategy.night, day))


@router.put("/api/days/{day}/strategy")
async def set_night_raids(day: str, body: NightRaidsIn, principal: DayOfficer, strategy: Strategy) -> NightStrategyOut:
    try:
        night = await anyio.to_thread.run_sync(strategy.set_night, day, body.raids, principal.member_id)
    except StrategyError as exc:
        raise _refused(exc) from None
    log.info("strategy.night_set", by=principal.member_id, day=day, raids=body.raids)
    return _night(day, night)


def include_strategy(app: FastAPI) -> None:
    app.include_router(router)
