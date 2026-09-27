"""Community routes. Every route declares its permission; raid-day scope comes from the path only.

- /api/public/*                 the outward story, no login
- /api/posts, /api/highlights,
  /api/applications, /api/me/*  signed-in members
- /api/days/{day}/admin/*       that raid day's officers (and the global tier)
- /api/admin/*                  the global tier only: Principal.role_for(None) never yields officer for a day officer
- /api/bot/*                    the bot, with its service token
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, FastAPI, Path, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from toads_api.community.deps import (
    audience_of,
    curation_audience_allowed,
    get_service,
    officer_scopes,
    officer_transition_allowed,
    post_audience_allowed,
    require_service,
    scope_of,
)
from toads_api.community.schemas import (
    Application,
    ApplicationCreate,
    ApplicationTransition,
    ConsentDecision,
    CurationDecision,
    DeskSummary,
    DiscordMessageIn,
    Highlight,
    HighlightCreate,
    HighlightReview,
    OutboxAck,
    OutboxJob,
    Post,
    PostCreate,
    PublicStory,
    RecruitmentNeed,
    Spotlight,
    SpotlightCreate,
)
from toads_api.community.service import CommunityError, CommunityService
from toads_api.rbac import Permission, Principal
from toads_api.rbac.deps import require


class BotJob(BaseModel):
    job: OutboxJob
    post: Post | None = None


public = APIRouter(prefix="/api/public", tags=["public"])
member = APIRouter(prefix="/api", tags=["community"])


async def _day(day: str = Path(pattern=r"^[a-z0-9_-]{1,32}$")) -> str:
    """Declares the raid day path parameter (and its shape) on every raid-day officer route."""
    return day


day_admin = APIRouter(prefix="/api/days/{day}/admin", tags=["raid-day officers"], dependencies=[Depends(_day)])
global_admin = APIRouter(prefix="/api/admin", tags=["global officers"])
bot = APIRouter(prefix="/api/bot", tags=["bot"], dependencies=[Depends(require_service)])

S = Depends(get_service)
_VIEW = Depends(require(Permission.VIEW_GUILD_RAIDS))
_SUBMIT = Depends(require(Permission.SUBMIT_HIGHLIGHT))
_APPLY = Depends(require(Permission.APPLY))


# ---------------------------------------------------------------- public story


@public.get("/story")
async def story(svc: CommunityService = S) -> PublicStory:
    return svc.public_story()


@public.get("/recruitment")
async def recruitment_needs(svc: CommunityService = S) -> list[RecruitmentNeed]:
    return svc.needs()


# --------------------------------------------------------------------- members


@member.get("/posts")
async def posts_feed(svc: CommunityService = S, p: Principal = _VIEW) -> list[Post]:
    return svc.feed(audience_of(p))


@member.get("/highlights")
async def highlights(
    svc: CommunityService = S,
    p: Principal = _VIEW,
) -> list[Highlight]:
    return svc.highlights_for(audience_of(p))


@member.post("/highlights", status_code=status.HTTP_201_CREATED)
async def submit_highlight(
    body: HighlightCreate,
    svc: CommunityService = S,
    p: Principal = _SUBMIT,
) -> Highlight:
    return svc.submit_highlight(p.member_id, body)


@member.post("/applications", status_code=status.HTTP_201_CREATED)
async def apply(
    body: ApplicationCreate,
    svc: CommunityService = S,
    p: Principal = _APPLY,
) -> Application:
    return svc.apply(p.member_id, body)


@member.get("/applications/mine")
async def my_applications(
    svc: CommunityService = S,
    p: Principal = _APPLY,
) -> list[Application]:
    return svc.my_applications(p.member_id)


@member.post("/applications/{app_id}/withdraw")
async def withdraw(
    app_id: int,
    svc: CommunityService = S,
    p: Principal = _APPLY,
) -> Application:
    return svc.withdraw(p.member_id, app_id)


@member.get("/me/spotlights")
async def my_spotlights(
    svc: CommunityService = S,
    p: Principal = _VIEW,
) -> list[Spotlight]:
    return svc.spotlights_about(p.member_id)


@member.post("/me/spotlights/{sp_id}/consent")
async def spotlight_consent(
    sp_id: int,
    body: ConsentDecision,
    svc: CommunityService = S,
    p: Principal = _VIEW,
) -> Spotlight:
    return svc.decide_consent(p.member_id, sp_id, body.grant)


@member.get("/desk")
async def desk(svc: CommunityService = S, p: Principal = _VIEW) -> DeskSummary:
    # A member who leads no raid day has nothing waiting: an empty desk, not a refusal.
    return svc.desk(officer_scopes(p))


# --------------------------------------------- officers: one raid day or global


def _officer_routes(router: APIRouter, scoped: bool) -> None:
    """The same officer actions, mounted once per scope. `day` is None on the global routes."""

    recruit = Depends(require(Permission.MANAGE_RECRUITMENT, scoped=scoped))
    posts = Depends(require(Permission.MANAGE_POSTS, scoped=scoped))
    # Tier checks (who may reach the public story, who may withdraw) run before the handler, in the adapter.
    post_audience = [Depends(post_audience_allowed)]
    curation_audience = [Depends(curation_audience_allowed)]
    officer_transition = [Depends(officer_transition_allowed)]

    @router.get("/applications")
    async def applications(request: Request, svc: CommunityService = S, _: Principal = recruit) -> list[Application]:
        return svc.applications_for(scope_of(request))

    @router.post("/applications/{app_id}/transition", dependencies=officer_transition)
    async def transition(
        request: Request, app_id: int, body: ApplicationTransition, svc: CommunityService = S, p: Principal = recruit
    ) -> Application:
        return svc.transition(p.member_id, scope_of(request), app_id, body.to, body.note)

    @router.post("/applications/{app_id}/interview-room", status_code=status.HTTP_202_ACCEPTED)
    async def interview_room(
        request: Request, app_id: int, svc: CommunityService = S, p: Principal = recruit
    ) -> Application:
        return svc.open_interview_room(p.member_id, scope_of(request), app_id)

    @router.get("/curation")
    async def curation(request: Request, svc: CommunityService = S, _: Principal = posts) -> list[Post]:
        return svc.curation_queue(scope_of(request))

    @router.post("/curation/{post_id}", dependencies=curation_audience)
    async def curate(
        request: Request, post_id: int, body: CurationDecision, svc: CommunityService = S, p: Principal = posts
    ) -> Post:
        return svc.curate(p.member_id, scope_of(request), post_id, body.action, body.visibility)

    @router.post("/posts", status_code=status.HTTP_201_CREATED, dependencies=post_audience)
    async def create_post(request: Request, body: PostCreate, svc: CommunityService = S, p: Principal = posts) -> Post:
        return svc.create_post(p.member_id, scope_of(request), body)

    @router.put("/posts/{post_id}", dependencies=post_audience)
    async def update_post(
        request: Request, post_id: int, body: PostCreate, svc: CommunityService = S, p: Principal = posts
    ) -> Post:
        return svc.update_post(p.member_id, scope_of(request), post_id, body)


_officer_routes(day_admin, scoped=True)
_officer_routes(global_admin, scoped=False)

_highlights = Depends(require(Permission.MANAGE_HIGHLIGHTS))
_recruitment = Depends(require(Permission.MANAGE_RECRUITMENT))


@global_admin.put("/recruitment/needs")
async def set_needs(
    body: list[RecruitmentNeed], svc: CommunityService = S, p: Principal = _recruitment
) -> list[RecruitmentNeed]:
    return svc.set_needs(p.member_id, body)


@global_admin.get("/highlights")
async def highlights_to_review(svc: CommunityService = S, _: Principal = _highlights) -> list[Highlight]:
    return svc.highlights_to_review()


@global_admin.post("/highlights/{hl_id}/review")
async def review_highlight(
    hl_id: int, body: HighlightReview, svc: CommunityService = S, p: Principal = _highlights
) -> Highlight:
    return svc.review_highlight(p.member_id, hl_id, body.action)


@global_admin.get("/spotlights")
async def spotlights(svc: CommunityService = S, _: Principal = _highlights) -> list[Spotlight]:
    return svc.all_spotlights()


@global_admin.post("/spotlights", status_code=status.HTTP_201_CREATED)
async def create_spotlight(body: SpotlightCreate, svc: CommunityService = S, p: Principal = _highlights) -> Spotlight:
    return svc.create_spotlight(p.member_id, body)


@global_admin.post("/spotlights/{sp_id}/publish")
async def publish_spotlight(sp_id: int, svc: CommunityService = S, p: Principal = _highlights) -> Spotlight:
    return svc.publish_spotlight(p.member_id, sp_id)


@global_admin.post("/spotlights/{sp_id}/retire")
async def retire_spotlight(sp_id: int, svc: CommunityService = S, p: Principal = _highlights) -> Spotlight:
    return svc.retire_spotlight(p.member_id, sp_id)


# ------------------------------------------------------------------------- bot


@bot.get("/outbox")
async def outbox(svc: CommunityService = S) -> list[BotJob]:
    return [BotJob(job=j, post=svc.post_for_job(j)) for j in svc.pending_jobs()]


@bot.post("/outbox/{job_id}/ack")
async def ack(job_id: int, body: OutboxAck, svc: CommunityService = S) -> OutboxJob:
    return svc.ack(job_id, body)


@bot.post("/discord-messages", status_code=status.HTTP_202_ACCEPTED)
async def discord_message(body: DiscordMessageIn, svc: CommunityService = S) -> Post | None:
    return svc.ingest_discord_message(body)


@bot.post("/discord-messages/{message_id}/deleted", status_code=status.HTTP_204_NO_CONTENT)
async def discord_message_deleted(message_id: int, svc: CommunityService = S) -> Response:
    svc.discord_message_deleted(message_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ------------------------------------------------------------------------ wiring


async def _community_error(_: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, CommunityError):
        raise exc
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})


def include_community(app: FastAPI) -> None:
    app.add_exception_handler(CommunityError, _community_error)
    for router in (public, member, day_admin, global_admin, bot):
        app.include_router(router)
