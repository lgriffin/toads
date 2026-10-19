"""Logs routes (docs/logs.md).

- GET /api/logs                         the raid list and the boss history, with what the caller may open in full
- GET /api/logs/{report}                a raid's analysis: in full for a global officer, else its overview
- GET /api/days/{day}/logs/{report}     the same, in full for that raid day's officers when the raid is on its weekday
- PUT /api/worker/logs                  the worker, with the service token: the raid list and the boss history;
                                        answers with the raids whose analysis it still needs
- PUT /api/worker/logs/{report}         the worker: one raid's analysis

The raid day comes from the path (REQ-HUB-DAY-023), so a Wednesday officer reads Wednesday raids in full and only the
overview of the rest.
"""

from __future__ import annotations

from typing import Annotated, Any

import anyio
import structlog
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Path, Request
from pydantic import BaseModel, Field

from toads_api.community.deps import require_service
from toads_api.logs.service import MAX_BOSSES, MAX_RAIDS, LogError, LogService, Overview, RaidView, Viewer
from toads_api.rbac import Permission, Principal
from toads_api.rbac.deps import get_services, require
from toads_api.rbac.permissions import can
from toads_api.services import Services

log = structlog.get_logger(__name__)
router = APIRouter(tags=["logs"])
worker = APIRouter(prefix="/api/worker", tags=["worker"], dependencies=[Depends(require_service)])

REPORT_ID = r"^[A-Za-z0-9]{1,32}$"
PAGE_HASH = r"^[0-9a-f]{64}$"


def get_logs(request: Request) -> LogService:
    return get_services(request).logs


Logs = Annotated[LogService, Depends(get_logs)]
Live = Annotated[Services, Depends(get_services)]
SignedIn = Annotated[Principal, Depends(require(Permission.VIEW_GUILD_RAIDS))]
DayViewer = Annotated[Principal, Depends(require(Permission.VIEW_GUILD_RAIDS, scoped=True))]
Report = Annotated[str, Path(pattern=REPORT_ID)]


class RaidRowOut(BaseModel):
    # wcl-app's RaidSummary.to_dict() (guides/raid_pages.md in lgriffin/warcraftlogs_project).
    summary: dict[str, Any]
    # The hub holds its analysis.
    analysed: bool
    # Read the full analysis under /api/days/{day}/logs/{report}; null reads /api/logs/{report}.
    day: str | None
    # The caller sees per-player numbers for this raid.
    full: bool


class OverviewOut(BaseModel):
    # When the worker last sent the list; null until it has.
    generated_at: str | None
    raids: list[RaidRowOut]
    # wcl-app's boss_history, per-player rows only on the weekdays in `full_weekdays`.
    bosses: list[dict[str, Any]]
    # Weekdays (0 is Monday) whose per-player numbers the caller sees; null for every weekday.
    full_weekdays: list[int] | None


class RaidOut(BaseModel):
    full: bool
    # RaidPage.to_dict() when full, else its overview (docs/logs.md).
    page: dict[str, Any]


class SummaryIn(BaseModel, extra="allow"):
    report_id: str = Field(pattern=REPORT_ID)
    title: str = Field(max_length=300)
    zone: str = Field(max_length=100)
    raid_date: str = Field(max_length=19)
    weekday: int | None = Field(ge=0, le=6)
    size: int = Field(ge=0, le=100)
    url: str = Field(max_length=200)


class IndexIn(BaseModel):
    version: int
    generated_at: str = Field(max_length=40)
    raids: list[SummaryIn] = Field(max_length=MAX_RAIDS)
    bosses: list[dict[str, Any]] = Field(max_length=MAX_BOSSES)
    # The worker's sha256 of each analysis it built, by raid; a raid it could not read is left out.
    hashes: dict[Annotated[str, Field(pattern=REPORT_ID)], Annotated[str, Field(pattern=PAGE_HASH)]] = Field(
        default_factory=dict, max_length=MAX_RAIDS
    )


class IndexAnswer(BaseModel):
    raids: int
    # Raids whose analysis the hub still needs, newest first.
    missing: list[str]


class PageIn(BaseModel):
    page: dict[str, Any]
    # The hash the worker listed for this analysis; a newer list wanting another build refuses it (409).
    hash: str = Field(pattern=PAGE_HASH)


def _viewer(principal: Principal, live: Services) -> Viewer:
    days = tuple(d.id for d in live.raid_days.raid_days if can(principal, Permission.VIEW_OTHERS, d.id))
    return Viewer(everything=principal.global_officer, officer_days=days)


def _refused(exc: LogError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.message)


def _overview(o: Overview) -> OverviewOut:
    return OverviewOut(
        generated_at=o.generated_at,
        raids=[RaidRowOut(summary=r.summary, analysed=r.analysed, day=r.day, full=r.full) for r in o.raids],
        bosses=o.bosses,
        full_weekdays=o.full_weekdays,
    )


async def _raid(logs: LogService, report: str, viewer: Viewer, day: str | None) -> RaidOut:
    try:
        view: RaidView = await anyio.to_thread.run_sync(logs.raid, report, viewer, day)
    except LogError as exc:
        raise _refused(exc) from None
    return RaidOut(full=view.full, page=view.page)


@router.get("/api/logs")
async def overview(principal: SignedIn, logs: Logs, live: Live) -> OverviewOut:
    return _overview(await anyio.to_thread.run_sync(logs.overview, _viewer(principal, live)))


@router.get("/api/logs/{report}")
async def raid(report: Report, principal: SignedIn, logs: Logs, live: Live) -> RaidOut:
    return await _raid(logs, report, _viewer(principal, live), None)


@router.get("/api/days/{day}/logs/{report}")
async def day_raid(day: str, report: Report, principal: DayViewer, logs: Logs, live: Live) -> RaidOut:
    return await _raid(logs, report, _viewer(principal, live), day)


@worker.put("/logs")
async def publish_index(body: IndexIn, logs: Logs) -> IndexAnswer:
    raids = [r.model_dump() for r in body.raids]
    try:
        missing = await anyio.to_thread.run_sync(
            logs.publish_index, body.version, body.generated_at, raids, body.bosses, body.hashes
        )
    except LogError as exc:
        raise _refused(exc) from None
    log.info("logs.index_published", raids=len(raids), missing=len(missing))
    return IndexAnswer(raids=len(raids), missing=missing)


@worker.put("/logs/{report}")
async def publish_page(report: Report, body: PageIn, logs: Logs) -> dict[str, str]:
    try:
        await anyio.to_thread.run_sync(logs.publish_page, report, body.page, body.hash)
    except LogError as exc:
        raise _refused(exc) from None
    return {"report_id": report}


def include_logs(app: FastAPI) -> None:
    for r in (router, worker):
        app.include_router(r)
