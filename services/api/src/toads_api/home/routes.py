"""A member's hub home layout. Every route acts on the caller's own member id, taken from the session; any signed-in
member may use them. Whether the caller sees officer widgets is decided here, from their roles.

- GET    /api/me/home   the widgets the member may place, in order, and which are shown
- PUT    /api/me/home   show exactly these widgets, in this order
- DELETE /api/me/home   back to the default layout
- GET    /api/home/analyzer        the analyzer's widgets (guild-wide), as the worker last built them
- PUT    /api/worker/home-page     the worker, with the service token: a fresh build of the analyzer's page
"""

from __future__ import annotations

from typing import Annotated, Any

import anyio
import structlog
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from toads_api.community.deps import require_service
from toads_api.home.service import (
    MAX_ANALYZER_WIDGETS,
    MAX_WIDGETS,
    Audience,
    HomeError,
    HomeLayout,
    HomeService,
)
from toads_api.rbac import Permission, Principal
from toads_api.rbac.deps import get_services, require

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/me", tags=["home"])
guild = APIRouter(prefix="/api/home", tags=["home"])
worker = APIRouter(prefix="/api/worker", tags=["worker"], dependencies=[Depends(require_service)])


def get_home(request: Request) -> HomeService:
    return get_services(request).home


Home = Annotated[HomeService, Depends(get_home)]
SignedIn = Annotated[Principal, Depends(require(Permission.VIEW_GUILD_RAIDS))]


class WidgetOut(BaseModel):
    id: str
    title: str
    description: str
    officer_only: bool
    # "hub" or "analyzer": where the widget's data comes from (analyzer widgets: GET /api/home/analyzer).
    source: str
    shown: bool


class HomeOut(BaseModel):
    widgets: list[WidgetOut]
    customised: bool


class HomeIn(BaseModel):
    shown: list[str] = Field(max_length=MAX_WIDGETS)


class AnalyzerPageOut(BaseModel):
    """The analyzer's page contract (guides/home_widgets.md in lgriffin/warcraftlogs_project). `generated_at` is
    null and `widgets` empty until the worker has published a page."""

    version: int
    generated_at: str | None
    widgets: list[dict[str, Any]]


class AnalyzerPageIn(BaseModel):
    version: int
    generated_at: str = Field(max_length=40)
    widgets: list[dict[str, Any]] = Field(max_length=MAX_ANALYZER_WIDGETS)


def audience_of(principal: Principal) -> Audience:
    return Audience.OFFICER if principal.is_officer else Audience.MEMBER


def _out(layout: HomeLayout) -> HomeOut:
    return HomeOut(
        widgets=[
            WidgetOut(
                id=c.widget.id,
                title=c.widget.title,
                description=c.widget.description,
                officer_only=c.widget.audience is Audience.OFFICER,
                source=c.widget.source.value,
                shown=c.shown,
            )
            for c in layout.widgets
        ],
        customised=layout.customised,
    )


def _refused(exc: HomeError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.message)


@router.get("/home")
async def get_layout(principal: SignedIn, home: Home) -> HomeOut:
    return _out(await anyio.to_thread.run_sync(home.layout, principal.member_id, audience_of(principal)))


@router.put("/home")
async def save_layout(body: HomeIn, principal: SignedIn, home: Home) -> HomeOut:
    try:
        layout = await anyio.to_thread.run_sync(home.save, principal.member_id, audience_of(principal), body.shown)
    except HomeError as exc:
        raise _refused(exc) from None
    return _out(layout)


@router.delete("/home")
async def reset_layout(principal: SignedIn, home: Home) -> HomeOut:
    return _out(await anyio.to_thread.run_sync(home.reset, principal.member_id, audience_of(principal)))


@guild.get("/analyzer")
async def analyzer_page(_: SignedIn, home: Home) -> AnalyzerPageOut:
    page = await anyio.to_thread.run_sync(home.analyzer_page)
    if page is None:
        return AnalyzerPageOut(version=1, generated_at=None, widgets=[])
    return AnalyzerPageOut(version=page.version, generated_at=page.generated_at, widgets=page.widgets)


@worker.put("/home-page")
async def publish_analyzer_page(body: AnalyzerPageIn, home: Home) -> dict[str, int]:
    try:
        kept = await anyio.to_thread.run_sync(home.publish_analyzer_page, body.version, body.generated_at, body.widgets)
    except HomeError as exc:
        raise _refused(exc) from None
    log.info("home.analyzer_page_published", widgets=kept)
    return {"widgets": kept}


def include_home(app: FastAPI) -> None:
    for r in (router, guild, worker):
        app.include_router(r)
