"""Community routes. Every route declares its permission; raid-day scope comes from the path only.

- /api/public/*                 the outward story, no login
- /api/posts, /api/highlights,
  /api/applications, /api/me/*  signed-in members
- /api/days/{day}/admin/*       that raid day's officers (and the global tier)
- /api/admin/*                  the global tier only: Principal.role_for(None) never yields officer for a day officer
- /api/bot/*                    the bot, with its service token
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Path, Query, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from toads_api.community.deps import (
    audience_of,
    curation_audience_allowed,
    ensure_in_discord,
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
    ApplicationDecision,
    ApplicationNote,
    ApplicationNoteAdd,
    ApplicationTransition,
    ConsentDecision,
    CurationDecision,
    DecisionBoard,
    DeskSummary,
    DiscordMessageIn,
    Highlight,
    HighlightCreate,
    HighlightReview,
    Interviewer,
    InterviewerAdd,
    InterviewPanel,
    OutboxAck,
    OutboxJob,
    Post,
    PostCreate,
    PublicStory,
    RaidNight,
    RecruitmentNeed,
    Spotlight,
    SpotlightCreate,
)
from toads_api.community.service import CommunityError, CommunityService
from toads_api.discord_api import DiscordError, GuildMember
from toads_api.rbac import Permission, Principal
from toads_api.rbac.deps import get_services, require
from toads_api.services import Services


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


@public.get("/raid-nights")
async def raid_nights(svc: CommunityService = S) -> list[RaidNight]:
    """The nights the recruit page offers, so an applicant's room gets that night's interview panel."""
    return svc.raid_nights()


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
    services: Services = Depends(get_services),  # noqa: B008
) -> Application:
    await ensure_in_discord(services, svc.discord_id_of(p.member_id))
    return with_room_url(svc.apply(p.member_id, body), services.settings.discord_guild_id)


@member.get("/applications/mine")
async def my_applications(
    svc: CommunityService = S,
    p: Principal = _APPLY,
    services: Services = Depends(get_services),  # noqa: B008
) -> list[Application]:
    guild_id = services.settings.discord_guild_id
    return [with_room_url(a, guild_id) for a in svc.my_applications(p.member_id)]


def with_room_url(app: Application, guild_id: int) -> Application:
    """The applicant's link straight into their room. Only a room the bot has opened gets one: an invite link would
    drop them in whichever channel the invite was made for."""
    if app.interview_channel_id is None:
        return app
    return app.model_copy(
        update={"interview_room_url": f"https://discord.com/channels/{guild_id}/{app.interview_channel_id}"}
    )


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

# ------------------------------------- one raid night's interview panel (docs/recruitment.md)

_panel = Depends(require(Permission.MANAGE_RECRUITMENT, scoped=True))
_hub = Depends(get_services)
DiscordId = Annotated[str, Path(pattern=r"^[1-9][0-9]{0,19}$")]


def _interviewer(member: GuildMember) -> Interviewer:
    return Interviewer(discord_user_id=str(member.user_id), username=member.username, display_name=member.server_name)


def _discord_down() -> HTTPException:
    return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Discord is not answering; try again shortly")


@day_admin.get("/interview-panel")
async def interview_panel(request: Request, svc: CommunityService = S, _: Principal = _panel) -> InterviewPanel:
    return svc.interview_panel(str(scope_of(request)))


@day_admin.get("/discord-members")
async def discord_members(
    q: Annotated[str, Query(min_length=1, max_length=32)], services: Services = _hub, _: Principal = _panel
) -> list[Interviewer]:
    """Members of the Toads Discord whose username or server nickname starts with `q`, to put on a panel."""
    try:
        found = await services.discord.search_members(q.strip(), limit=10)
    except DiscordError:
        raise _discord_down() from None
    return [_interviewer(m) for m in found]


@day_admin.post("/interview-panel", status_code=status.HTTP_201_CREATED)
async def add_interviewer(
    request: Request, body: InterviewerAdd, svc: CommunityService = S, services: Services = _hub, p: Principal = _panel
) -> InterviewPanel:
    try:
        member = await services.discord.guild_member(int(body.discord_user_id))
    except DiscordError:
        raise _discord_down() from None
    if member is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="They are not in the Toads Discord")
    return svc.add_interviewer(p.member_id, str(scope_of(request)), _interviewer(member))


@day_admin.delete("/interview-panel/{discord_user_id}")
async def remove_interviewer(
    request: Request, discord_user_id: DiscordId, svc: CommunityService = S, p: Principal = _panel
) -> InterviewPanel:
    return svc.remove_interviewer(p.member_id, str(scope_of(request)), discord_user_id)


# ------------------------------------------ one raid night's Decisions panel (docs/recruitment.md)


@day_admin.get("/decisions")
async def decisions(
    request: Request, svc: CommunityService = S, services: Services = _hub, _: Principal = _panel
) -> DecisionBoard:
    """Applicants waiting on this night's officers, and what was decided lately, with the officers' notes. Officers
    get the same link into each interview room that the applicant has."""
    board = svc.decisions(str(scope_of(request)))
    guild_id = services.settings.discord_guild_id
    for card in [*board.waiting, *board.decided]:
        card.application = with_room_url(card.application, guild_id)
    return board


@day_admin.post("/applications/{app_id}/notes", status_code=status.HTTP_201_CREATED)
async def add_note(
    request: Request, app_id: int, body: ApplicationNoteAdd, svc: CommunityService = S, p: Principal = _panel
) -> ApplicationNote:
    return svc.add_note(p.member_id, str(scope_of(request)), app_id, body.body)


@day_admin.post("/applications/{app_id}/decision")
async def decide(
    request: Request, app_id: int, body: ApplicationDecision, svc: CommunityService = S, p: Principal = _panel
) -> Application:
    return svc.decide(p.member_id, str(scope_of(request)), app_id, body.decision)


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
