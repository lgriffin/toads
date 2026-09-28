"""Reference comparison routes. Officers only (REQ-HUB-INS-001): every route needs VIEW_INSIGHTS on the raid day in
its path, so a raid-day officer works from their own day and a global officer from any.

- GET    /api/days/{day}/reference                              login state, stored raids, comparisons, recent jobs
- POST   /api/days/{day}/reference/login                        start connecting the dedicated Warcraft Logs account
- DELETE /api/days/{day}/reference/login                        disconnect it
- POST   /api/days/{day}/reference/imports                      queue importing another guild's report
- POST   /api/days/{day}/reference/comparisons                  queue comparing one of our raids with a reference
- GET    /api/days/{day}/reference/comparisons/{guild}/{ref}    a built comparison
- PUT    /api/days/{day}/reference/references/{report}/label    queue relabelling a reference
- DELETE /api/days/{day}/reference/references/{report}          queue deleting a reference
- GET    /api/reference/login/callback                          where Warcraft Logs sends the officer back
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from urllib.parse import urlencode

import anyio
import structlog
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from toads_api import audit
from toads_api.rbac import Permission, Principal
from toads_api.rbac.deps import get_services, require
from toads_api.rbac.permissions import can
from toads_api.reference.login import CALLBACK_PATH, WclLogin, WclLoginError
from toads_api.reference.repository import Job
from toads_api.reference.service import MAX_LABEL_LENGTH, MAX_REPORT_INPUT, ReferenceRequestError, ReferenceService
from toads_api.services import Services

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/days/{day}/reference", tags=["reference"])
callback = APIRouter(tags=["reference"])

PAGE_PATH = "/officers/reference/"


def get_reference(request: Request) -> ReferenceService:
    return get_services(request).reference


def get_login(request: Request) -> WclLogin:
    return get_services(request).wcl_login


Reference = Annotated[ReferenceService, Depends(get_reference)]
Login = Annotated[WclLogin, Depends(get_login)]
Live = Annotated[Services, Depends(get_services)]
Officer = Annotated[Principal, Depends(require(Permission.VIEW_INSIGHTS, scoped=True))]
SignedIn = Annotated[Principal, Depends(require(Permission.VIEW_GUILD_RAIDS))]


class LoginOut(BaseModel):
    configured: bool
    connected: bool
    status: str | None
    connected_by: str | None
    connected_at: datetime | None


class ComparisonSummaryOut(BaseModel):
    guild_report: str
    reference_report: str
    guild_title: str
    reference_title: str
    generated_at: str


class JobOut(BaseModel):
    id: str
    kind: str
    status: str
    message: str
    report: str
    created_at: datetime
    updated_at: datetime


class OverviewOut(BaseModel):
    login: LoginOut
    # When the worker last listed the stored raids; null until it has.
    generated_at: str | None
    references: list[dict[str, Any]]
    guild_raids: list[dict[str, Any]]
    comparisons: list[ComparisonSummaryOut]
    jobs: list[JobOut]


class LoginStartOut(BaseModel):
    authorize_url: str


class ImportIn(BaseModel):
    report: str = Field(min_length=1, max_length=MAX_REPORT_INPUT)
    label: str | None = Field(default=None, max_length=MAX_LABEL_LENGTH * 2)


class CompareIn(BaseModel):
    guild_report: str = Field(min_length=1, max_length=MAX_REPORT_INPUT)
    reference_report: str = Field(min_length=1, max_length=MAX_REPORT_INPUT)


class LabelIn(BaseModel):
    label: str | None = Field(max_length=MAX_LABEL_LENGTH * 2)


class ComparisonOut(BaseModel):
    generated_at: str
    # wcl-app's ReferenceComparison.to_dict() (guides/reference_comparison.md in lgriffin/warcraftlogs_project).
    comparison: dict[str, Any]


def _job(job: Job) -> JobOut:
    return JobOut(
        id=job.id,
        kind=job.kind,
        status=job.status,
        message=job.message,
        report=job.report,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def _refused(exc: ReferenceRequestError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.message)


def _audit(live: Services, principal: Principal, action: str, target: str, day: str | None) -> None:
    with live.db.begin() as db:
        audit.record(db, actor=principal.member_id, action=action, target=target, raid_day=day)


@router.get("")
async def overview(_: Officer, reference: Reference) -> OverviewOut:
    o = await anyio.to_thread.run_sync(reference.overview)
    return OverviewOut(
        login=LoginOut(
            configured=o.configured,
            connected=o.login.connected,
            status=o.login.status,
            connected_by=o.login.connected_by,
            connected_at=o.login.connected_at,
        ),
        generated_at=o.page.generated_at if o.page else None,
        references=o.page.references if o.page else [],
        guild_raids=o.page.guild_raids if o.page else [],
        comparisons=[ComparisonSummaryOut(**vars(c)) for c in o.comparisons],
        jobs=[_job(j) for j in o.jobs],
    )


@router.post("/login")
async def start_login(day: str, principal: Officer, reference: Reference, login: Login) -> LoginStartOut:
    try:
        reference.require_configured()
    except ReferenceRequestError as exc:
        raise _refused(exc) from None
    return LoginStartOut(authorize_url=await login.begin(principal.member_id, day))


@router.delete("/login", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect(day: str, principal: Officer, reference: Reference, live: Live) -> Response:
    if await anyio.to_thread.run_sync(reference.disconnect):
        await anyio.to_thread.run_sync(_audit, live, principal, "reference.disconnect", "warcraft logs login", day)
        log.info("reference.login_disconnected", member_id=principal.member_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/imports", status_code=status.HTTP_202_ACCEPTED)
async def request_import(day: str, body: ImportIn, principal: Officer, reference: Reference, live: Live) -> JobOut:
    try:
        job = await anyio.to_thread.run_sync(
            reference.request_import, day, principal.member_id, body.report, body.label
        )
    except ReferenceRequestError as exc:
        raise _refused(exc) from None
    await anyio.to_thread.run_sync(_audit, live, principal, "reference.import", f"report {job.report}", day)
    return _job(job)


@router.post("/comparisons", status_code=status.HTTP_202_ACCEPTED)
async def request_compare(day: str, body: CompareIn, principal: Officer, reference: Reference) -> JobOut:
    try:
        job = await anyio.to_thread.run_sync(
            reference.request_compare, day, principal.member_id, body.guild_report, body.reference_report
        )
    except ReferenceRequestError as exc:
        raise _refused(exc) from None
    return _job(job)


@router.get("/comparisons/{guild_report}/{reference_report}")
async def comparison(_: Officer, guild_report: str, reference_report: str, reference: Reference) -> ComparisonOut:
    try:
        found = await anyio.to_thread.run_sync(reference.comparison, guild_report, reference_report)
    except ReferenceRequestError as exc:
        raise _refused(exc) from None
    if found is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not compared yet")
    return ComparisonOut(generated_at=found.generated_at, comparison=found.payload)


@router.put("/references/{report}/label", status_code=status.HTTP_202_ACCEPTED)
async def request_label(day: str, report: str, body: LabelIn, principal: Officer, reference: Reference) -> JobOut:
    try:
        job = await anyio.to_thread.run_sync(reference.request_label, day, principal.member_id, report, body.label)
    except ReferenceRequestError as exc:
        raise _refused(exc) from None
    return _job(job)


@router.delete("/references/{report}", status_code=status.HTTP_202_ACCEPTED)
async def request_delete(day: str, report: str, principal: Officer, reference: Reference, live: Live) -> JobOut:
    try:
        job = await anyio.to_thread.run_sync(reference.request_delete, day, principal.member_id, report)
    except ReferenceRequestError as exc:
        raise _refused(exc) from None
    await anyio.to_thread.run_sync(_audit, live, principal, "reference.delete", f"report {job.report}", day)
    return _job(job)


def _back(live: Services, day: str | None, outcome: str) -> RedirectResponse:
    query = urlencode({"day": day, "login": outcome} if day else {"login": outcome})
    public = live.settings.public_base_url.rstrip("/")
    return RedirectResponse(f"{public}{PAGE_PATH}?{query}", status_code=status.HTTP_303_SEE_OTHER)


@callback.get(CALLBACK_PATH, include_in_schema=False)
async def login_callback(
    principal: SignedIn,
    reference: Reference,
    login: Login,
    live: Live,
    code: str | None = None,
    state: str | None = None,
) -> RedirectResponse:
    pending = await login.take(state) if state else None
    if pending is None:
        log.info("reference.login_refused", reason="state")
        return _back(live, None, "failed")
    # The officer who started the login finishes it, and must still hold officer powers on that day.
    if pending.member_id != principal.member_id or not can(principal, Permission.VIEW_INSIGHTS, pending.raid_day):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if not code:
        return _back(live, pending.raid_day, "cancelled")
    try:
        token = await login.exchange(code, live.clock())
    except WclLoginError as exc:
        log.info("reference.login_refused", reason=str(exc))
        return _back(live, pending.raid_day, "failed")
    await anyio.to_thread.run_sync(reference.connect, token, principal.member_id)
    await anyio.to_thread.run_sync(
        _audit, live, principal, "reference.connect", "warcraft logs login", pending.raid_day
    )
    log.info("reference.login_connected", member_id=principal.member_id)
    return _back(live, pending.raid_day, "ok")


def include_reference(app: FastAPI) -> None:
    for r in (router, callback):
        app.include_router(r)
