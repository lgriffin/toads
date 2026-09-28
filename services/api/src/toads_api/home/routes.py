"""A member's hub home layout. Every route acts on the caller's own member id, taken from the session; any signed-in
member may use them. Whether the caller sees officer widgets is decided here, from their roles.

- GET    /api/me/home   the widgets the member may place, in order, and which are shown
- PUT    /api/me/home   show exactly these widgets, in this order
- DELETE /api/me/home   back to the default layout
- GET    /api/home/analyzer        the analyzer's widgets (guild-wide), as the worker last built them; officer-only
                                  widgets (the roster's badges) only for officers
- GET    /api/me/badges            the caller's own Toads badges
- PUT    /api/worker/home-page     the worker, with the service token: a fresh build of the analyzer's page
- PUT    /api/worker/badges        the worker, with the service token: every raider's badges
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

import anyio
import structlog
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat

from toads_api.community.deps import require_service
from toads_api.home.badges import BadgeService
from toads_api.home.next_raid import NextRaidService
from toads_api.home.performance import PerformanceService
from toads_api.home.service import (
    MAX_ANALYZER_WIDGETS,
    MAX_HOLDER_BADGES,
    MAX_WIDGETS,
    Audience,
    HomeError,
    HomeLayout,
    HomeService,
)
from toads_api.rbac import Permission, Principal
from toads_api.rbac.deps import get_services, require

log = structlog.get_logger(__name__)
# Everyone who has raided with the guild; the worker sends the highest scores first when there are more.
MAX_BADGE_PLAYERS = 1000
router = APIRouter(prefix="/api/me", tags=["home"])
guild = APIRouter(prefix="/api/home", tags=["home"])
worker = APIRouter(prefix="/api/worker", tags=["worker"], dependencies=[Depends(require_service)])


def get_home(request: Request) -> HomeService:
    return get_services(request).home


def get_performance(request: Request) -> PerformanceService:
    return get_services(request).performance


def get_next_raid(request: Request) -> NextRaidService:
    return get_services(request).next_raid


def get_badges(request: Request) -> BadgeService:
    return get_services(request).badges


Home = Annotated[HomeService, Depends(get_home)]
Performance = Annotated[PerformanceService, Depends(get_performance)]
NextRaids = Annotated[NextRaidService, Depends(get_next_raid)]
Badges = Annotated[BadgeService, Depends(get_badges)]
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


class RaidRef(BaseModel):
    report_id: str = Field(min_length=1, max_length=64)
    title: str = Field(max_length=200)
    date: str = Field(max_length=10)


class RecentRaid(BaseModel):
    date: str = Field(max_length=10)
    value: FiniteFloat
    median: FiniteFloat


class PlayerEntry(BaseModel):
    """One player in the worker's performance page (toads_worker.jobs.performance)."""

    name: str = Field(min_length=1, max_length=64)
    # "class" is a Python keyword, so the field has another name here and keeps the page's on the wire.
    player_class: str = Field(alias="class", max_length=32)
    role: Literal["tank", "healer", "melee", "ranged"]
    metric: str = Field(max_length=32)
    unit: Literal["amount", "percent"]
    value: FiniteFloat
    median: FiniteFloat
    rank: int = Field(ge=1)
    of: int = Field(ge=1)
    recent: list[RecentRaid] = Field(default=[], max_length=20)

    model_config = ConfigDict(populate_by_name=True)


class PerformancePageIn(BaseModel):
    version: int
    generated_at: str = Field(max_length=40)
    raid: RaidRef | None
    players: list[PlayerEntry] = Field(max_length=200)


class MyPerformanceOut(BaseModel):
    """`generated_at` is null until the worker has published; `entry` is null when none of the member's characters
    was in the last raid. `looked_for` names the characters looked for, best first."""

    generated_at: str | None
    raid: RaidRef | None
    entry: PlayerEntry | None
    # "chosen", "claim" or "nickname": how the character was picked (toads_api.home.performance.MatchedBy).
    matched_by: str | None
    looked_for: list[str]


class BadgeEntry(BaseModel):
    """One badge for one player (guides/badges.md in lgriffin/warcraftlogs_project). `tier` 0 is not earned yet."""

    id: str = Field(min_length=1, max_length=40)
    name: str = Field(max_length=40)
    description: str = Field(max_length=200)
    icon: str = Field(max_length=40)
    glyph: str = Field(max_length=16)
    tier: int = Field(ge=0, le=4)
    quality: Literal["", "uncommon", "rare", "epic", "legendary"]
    tier_name: str = Field(max_length=20)
    value: int = Field(ge=0)
    display: str = Field(max_length=40)
    stacks: int = Field(ge=0)
    next_at: int | None = Field(ge=1)
    next_tier: str = Field(max_length=20)
    progress: FiniteFloat = Field(ge=0, le=1)


class PlayerBadgesEntry(BaseModel):
    """wcl_app PlayerBadges.to_dict(): every badge in play for one player, earned or not, in catalogue order."""

    name: str = Field(min_length=1, max_length=64)
    player_class: str = Field(max_length=32)
    score: int = Field(ge=0)
    badges: list[BadgeEntry] = Field(max_length=MAX_HOLDER_BADGES)


class BadgePageIn(BaseModel):
    version: int
    generated_at: str = Field(max_length=40)
    players: list[PlayerBadgesEntry] = Field(max_length=MAX_BADGE_PLAYERS)


class MyBadgesOut(BaseModel):
    """`generated_at` is null until the worker has published; `entry` is null when none of the member's characters
    has raided with the guild. `looked_for` names the characters looked for, best first."""

    generated_at: str | None
    entry: PlayerBadgesEntry | None
    # "chosen", "claim" or "nickname", as for performance.
    matched_by: str | None
    looked_for: list[str]


class NextRaidBody(BaseModel):
    name: str
    starts_at: datetime
    ends_at: datetime | None
    raid_day_id: str | None
    raid_day_name: str | None
    # "discord": a scheduled event officers posted; "schedule": the raid day's configured start time.
    source: str
    under_way: bool
    interested: int | None
    url: str | None


class NextRaidOut(BaseModel):
    # Null when Discord has no event coming up and no raid day has a start time.
    raid: NextRaidBody | None


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
async def analyzer_page(principal: SignedIn, home: Home) -> AnalyzerPageOut:
    page = await anyio.to_thread.run_sync(home.analyzer_page, audience_of(principal))
    if page is None:
        return AnalyzerPageOut(version=1, generated_at=None, widgets=[])
    return AnalyzerPageOut(version=page.version, generated_at=page.generated_at, widgets=page.widgets)


@router.get("/performance")
async def my_performance(principal: SignedIn, performance: Performance) -> MyPerformanceOut:
    mine = await anyio.to_thread.run_sync(performance.mine, principal.member_id)
    return MyPerformanceOut(
        generated_at=mine.generated_at,
        raid=RaidRef.model_validate(mine.raid) if mine.raid else None,
        entry=PlayerEntry.model_validate(mine.entry) if mine.entry else None,
        matched_by=mine.matched_by.value if mine.matched_by else None,
        looked_for=mine.looked_for,
    )


@router.get("/badges")
async def my_badges(principal: SignedIn, badges: Badges) -> MyBadgesOut:
    mine = await anyio.to_thread.run_sync(badges.mine, principal.member_id)
    return MyBadgesOut(
        generated_at=mine.generated_at,
        entry=PlayerBadgesEntry.model_validate(mine.entry) if mine.entry else None,
        matched_by=mine.matched_by.value if mine.matched_by else None,
        looked_for=mine.looked_for,
    )


@guild.get("/next-raid")
async def next_raid(_: SignedIn, next_raids: NextRaids) -> NextRaidOut:
    raid = await next_raids.next_raid()
    if raid is None:
        return NextRaidOut(raid=None)
    return NextRaidOut(
        raid=NextRaidBody(
            name=raid.name,
            starts_at=raid.starts_at,
            ends_at=raid.ends_at,
            raid_day_id=raid.raid_day_id,
            raid_day_name=raid.raid_day_name,
            source=raid.source.value,
            under_way=raid.under_way,
            interested=raid.interested,
            url=raid.url,
        )
    )


@worker.put("/performance")
async def publish_performance(body: PerformancePageIn, performance: Performance) -> dict[str, int]:
    raid = body.raid.model_dump() if body.raid else None
    players = [p.model_dump(by_alias=True) for p in body.players]
    try:
        kept = await anyio.to_thread.run_sync(performance.publish, body.version, body.generated_at, raid, players)
    except HomeError as exc:
        raise _refused(exc) from None
    log.info("home.performance_published", players=kept)
    return {"players": kept}


@worker.put("/badges")
async def publish_badges(body: BadgePageIn, badges: Badges) -> dict[str, int]:
    players = [p.model_dump() for p in body.players]
    try:
        kept = await anyio.to_thread.run_sync(badges.publish, body.version, body.generated_at, players)
    except HomeError as exc:
        raise _refused(exc) from None
    log.info("home.badges_published", players=kept)
    return {"players": kept}


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
