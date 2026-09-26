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

from toads_api.community.deps import get_store, require_service
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
    HighlightStatus,
    OutboxAck,
    OutboxJob,
    Post,
    PostCreate,
    PublicStory,
    RecruitmentNeed,
    Spotlight,
    SpotlightCreate,
)
from toads_api.community.store import CommunityError, CommunityStore, Forbidden
from toads_api.rbac import HubRole, Permission, Principal
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

S = Depends(get_store)
_VIEW = Depends(require(Permission.VIEW_GUILD_RAIDS))
_SUBMIT = Depends(require(Permission.SUBMIT_HIGHLIGHT))
_APPLY = Depends(require(Permission.APPLY))


# ---------------------------------------------------------------- public story


@public.get("/story")
async def story(store: CommunityStore = S) -> PublicStory:
    return store.public_story()


@public.get("/recruitment")
async def recruitment_needs(store: CommunityStore = S) -> list[RecruitmentNeed]:
    return store.needs


# --------------------------------------------------------------------- members


@member.get("/posts")
async def posts_feed(store: CommunityStore = S, p: Principal = _VIEW) -> list[Post]:
    return store.feed(p)


@member.get("/highlights")
async def highlights(
    store: CommunityStore = S,
    p: Principal = _VIEW,
) -> list[Highlight]:
    return store.highlights_for(p)


@member.post("/highlights", status_code=status.HTTP_201_CREATED)
async def submit_highlight(
    body: HighlightCreate,
    store: CommunityStore = S,
    p: Principal = _SUBMIT,
) -> Highlight:
    return store.submit_highlight(p.member_id, body)


@member.post("/applications", status_code=status.HTTP_201_CREATED)
async def apply(
    body: ApplicationCreate,
    store: CommunityStore = S,
    p: Principal = _APPLY,
) -> Application:
    return store.apply(p.member_id, body)


@member.get("/applications/mine")
async def my_applications(
    store: CommunityStore = S,
    p: Principal = _APPLY,
) -> list[Application]:
    return store.my_applications(p.member_id)


@member.post("/applications/{app_id}/withdraw")
async def withdraw(
    app_id: int,
    store: CommunityStore = S,
    p: Principal = _APPLY,
) -> Application:
    return store.withdraw(p.member_id, app_id)


@member.get("/me/spotlights")
async def my_spotlights(
    store: CommunityStore = S,
    p: Principal = _VIEW,
) -> list[Spotlight]:
    return store.spotlights_about(p.member_id)


@member.post("/me/spotlights/{sp_id}/consent")
async def spotlight_consent(
    sp_id: int,
    body: ConsentDecision,
    store: CommunityStore = S,
    p: Principal = _VIEW,
) -> Spotlight:
    return store.decide_consent(p.member_id, sp_id, body.grant)


@member.get("/desk")
async def desk(store: CommunityStore = S, p: Principal = _VIEW) -> DeskSummary:
    if not p.global_officer and HubRole.OFFICER not in p.day_roles.values():
        raise Forbidden("The raid leader desk is for officers")
    return store.desk(p)


# --------------------------------------------- officers: one raid day or global


def _officer_routes(router: APIRouter, scoped: bool) -> None:
    """The same officer actions, mounted once per scope. `day` is None on the global routes."""

    def day_of(request: Request) -> str | None:
        return request.path_params.get("day") if scoped else None

    recruit = Depends(require(Permission.MANAGE_RECRUITMENT, scoped=scoped))
    posts = Depends(require(Permission.MANAGE_POSTS, scoped=scoped))

    @router.get("/applications")
    async def applications(request: Request, store: CommunityStore = S, _: Principal = recruit) -> list[Application]:
        return store.applications_for(day_of(request))

    @router.post("/applications/{app_id}/transition")
    async def transition(
        request: Request, app_id: int, body: ApplicationTransition, store: CommunityStore = S, p: Principal = recruit
    ) -> Application:
        return store.transition(p, day_of(request), app_id, body.to, body.note)

    @router.post("/applications/{app_id}/interview-room", status_code=status.HTTP_202_ACCEPTED)
    async def interview_room(
        request: Request, app_id: int, store: CommunityStore = S, p: Principal = recruit
    ) -> Application:
        return store.open_interview_room(p, day_of(request), app_id)

    @router.get("/curation")
    async def curation(request: Request, store: CommunityStore = S, _: Principal = posts) -> list[Post]:
        return store.curation_queue(day_of(request))

    @router.post("/curation/{post_id}")
    async def curate(
        request: Request, post_id: int, body: CurationDecision, store: CommunityStore = S, p: Principal = posts
    ) -> Post:
        return store.curate(p, day_of(request), post_id, body.action, body.visibility)

    @router.post("/posts", status_code=status.HTTP_201_CREATED)
    async def create_post(request: Request, body: PostCreate, store: CommunityStore = S, p: Principal = posts) -> Post:
        return store.create_post(p, day_of(request), body)

    @router.put("/posts/{post_id}")
    async def update_post(
        request: Request, post_id: int, body: PostCreate, store: CommunityStore = S, p: Principal = posts
    ) -> Post:
        return store.update_post(p, day_of(request), post_id, body)


_officer_routes(day_admin, scoped=True)
_officer_routes(global_admin, scoped=False)

_highlights = Depends(require(Permission.MANAGE_HIGHLIGHTS))
_recruitment = Depends(require(Permission.MANAGE_RECRUITMENT))


@global_admin.put("/recruitment/needs")
async def set_needs(
    body: list[RecruitmentNeed], store: CommunityStore = S, p: Principal = _recruitment
) -> list[RecruitmentNeed]:
    return store.set_needs(p, body)


@global_admin.get("/highlights")
async def highlights_to_review(store: CommunityStore = S, _: Principal = _highlights) -> list[Highlight]:
    return [h for h in store.highlights.values() if h.status is HighlightStatus.SUBMITTED]


@global_admin.post("/highlights/{hl_id}/review")
async def review_highlight(
    hl_id: int, body: HighlightReview, store: CommunityStore = S, p: Principal = _highlights
) -> Highlight:
    return store.review_highlight(p, hl_id, body.action)


@global_admin.get("/spotlights")
async def spotlights(store: CommunityStore = S, _: Principal = _highlights) -> list[Spotlight]:
    return list(store.spotlights.values())


@global_admin.post("/spotlights", status_code=status.HTTP_201_CREATED)
async def create_spotlight(body: SpotlightCreate, store: CommunityStore = S, p: Principal = _highlights) -> Spotlight:
    return store.create_spotlight(p, body)


@global_admin.post("/spotlights/{sp_id}/publish")
async def publish_spotlight(sp_id: int, store: CommunityStore = S, p: Principal = _highlights) -> Spotlight:
    return store.publish_spotlight(p, sp_id)


@global_admin.post("/spotlights/{sp_id}/retire")
async def retire_spotlight(sp_id: int, store: CommunityStore = S, p: Principal = _highlights) -> Spotlight:
    return store.retire_spotlight(p, sp_id)


# ------------------------------------------------------------------------- bot


@bot.get("/outbox")
async def outbox(store: CommunityStore = S) -> list[BotJob]:
    return [BotJob(job=j, post=store.post_for_job(j)) for j in store.pending_jobs()]


@bot.post("/outbox/{job_id}/ack")
async def ack(job_id: int, body: OutboxAck, store: CommunityStore = S) -> OutboxJob:
    return store.ack(job_id, body)


@bot.post("/discord-messages", status_code=status.HTTP_202_ACCEPTED)
async def discord_message(body: DiscordMessageIn, store: CommunityStore = S) -> Post | None:
    return store.ingest_discord_message(body)


@bot.post("/discord-messages/{message_id}/deleted", status_code=status.HTTP_204_NO_CONTENT)
async def discord_message_deleted(message_id: int, store: CommunityStore = S) -> Response:
    store.discord_message_deleted(message_id)
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
