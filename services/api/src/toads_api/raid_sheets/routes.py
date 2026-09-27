"""Raid sheet routes.

- /api/raid-sheets/recent                     members: the latest raids with sheets (home page)
- /api/raid-sheets/trend                      members: each recent raid's CBA and RPB totals (home page)
- /api/days/{day}/raids/{raid_date}/sheets    members: the sheets attached to one raid
- /api/days/{day}/raids/{raid_date}/sheets/summary  members: one raid's totals and per-player lines
- /api/days/{day}/sheets/{snapshot_id}        members: one sheet tab's rows
- /api/worker/raid-sheets                     the worker, with the service token: a downloaded spreadsheet
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, FastAPI, Path, Query, Request
from fastapi.responses import JSONResponse

from toads_api.community.deps import require_service
from toads_api.raid_sheets.schemas import ImportResult, RaidSheets, SheetImport, SheetSnapshot
from toads_api.raid_sheets.service import RaidSheetError, RaidSheetService
from toads_api.raid_sheets.summary import RaidHeadline, RaidSummary
from toads_api.rbac.deps import get_services, require
from toads_api.rbac.permissions import Permission, Principal

_DAY = r"^[a-z0-9_-]{1,32}$"


def get_sheets(request: Request) -> RaidSheetService:
    return get_services(request).raid_sheets


S = Depends(get_sheets)
_VIEW = Depends(require(Permission.VIEW_GUILD_RAIDS))
_VIEW_DAY = Depends(require(Permission.VIEW_GUILD_RAIDS, scoped=True))

member = APIRouter(tags=["raid sheets"])
worker = APIRouter(prefix="/api/worker", tags=["worker"], dependencies=[Depends(require_service)])


@member.get("/api/raid-sheets/recent")
async def recent(
    svc: RaidSheetService = S,
    _: Principal = _VIEW,
    day: str | None = Query(default=None, pattern=_DAY),
    limit: int = Query(default=8, ge=1, le=52),
) -> list[RaidSheets]:
    return svc.recent(day, limit)


@member.get("/api/raid-sheets/trend")
async def trend(
    svc: RaidSheetService = S,
    _: Principal = _VIEW,
    day: str | None = Query(default=None, pattern=_DAY),
    limit: int = Query(default=12, ge=1, le=52),
) -> list[RaidHeadline]:
    return svc.trend(day, limit)


@member.get("/api/days/{day}/raids/{raid_date}/sheets/summary")
async def raid_summary(day: str, raid_date: date, svc: RaidSheetService = S, _: Principal = _VIEW_DAY) -> RaidSummary:
    return svc.summary(day, raid_date)


@member.get("/api/days/{day}/raids/{raid_date}/sheets")
async def raid_sheets(day: str, raid_date: date, svc: RaidSheetService = S, _: Principal = _VIEW_DAY) -> RaidSheets:
    return svc.for_raid(day, raid_date)


@member.get("/api/days/{day}/sheets/{snapshot_id}")
async def sheet(
    day: str,
    snapshot_id: int = Path(gt=0, lt=2**31),
    svc: RaidSheetService = S,
    _: Principal = _VIEW_DAY,
) -> SheetSnapshot:
    return svc.snapshot(day, snapshot_id)


@worker.post("/raid-sheets")
async def import_sheet(body: SheetImport, svc: RaidSheetService = S) -> ImportResult:
    return svc.record_import(body)


async def _error(_: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RaidSheetError):
        raise exc
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})


def include_raid_sheets(app: FastAPI) -> None:
    app.add_exception_handler(RaidSheetError, _error)
    app.include_router(member)
    app.include_router(worker)
