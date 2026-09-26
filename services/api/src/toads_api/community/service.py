"""Community rules: what may change and how. Who may ask is decided before this, in the route dependencies.

Arguments named `scope` are the raid day a route is working in (None for guild-wide routes). Items outside that
scope are reported as missing so ids do not leak across raid days. Audiences are passed in as data (the raid days
a viewer belongs to), never as a Principal, so this module has no view of roles or permissions.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from toads_api.community import recruitment
from toads_api.community.clips import parse_clip_url
from toads_api.community.config import CommunityConfig
from toads_api.community.repository import AuditRecord, CommunityRepository, Payload
from toads_api.community.schemas import (
    Application,
    ApplicationCreate,
    ApplicationEvent,
    ApplicationStatus,
    CurationAction,
    DeskSummary,
    DiscordMessageIn,
    Highlight,
    HighlightAction,
    HighlightCreate,
    HighlightStatus,
    OutboxAck,
    OutboxJob,
    OutboxKind,
    Post,
    PostCreate,
    PostOrigin,
    PostStatus,
    PublicStory,
    RecruitmentNeed,
    Spotlight,
    SpotlightConsent,
    SpotlightCreate,
    SpotlightStatus,
    Visibility,
)


class CommunityError(Exception):
    status_code = 400


class NotFound(CommunityError):
    status_code = 404


class Conflict(CommunityError):
    status_code = 409


class Invalid(CommunityError):
    status_code = 422


class Forbidden(CommunityError):
    """Refusals decided in the route layer (tier checks) use this too, so every refusal has one shape."""

    status_code = 403


@dataclass(frozen=True)
class RaidDayDirectory:
    """The raid days and the Discord roles that run them: the only guild structure the rules need."""

    day_ids: frozenset[str] = frozenset()
    global_officer_roles: tuple[int, ...] = ()
    officer_roles: dict[str, tuple[int, ...]] = field(default_factory=dict)

    def officer_role_ids(self, days: list[str]) -> list[int]:
        """Roles that may see an interview room: the global tier plus the officers of the days applied for."""
        ids = set(self.global_officer_roles)
        for day, roles in self.officer_roles.items():
            if not days or day in days:
                ids.update(roles)
        return sorted(ids)


@dataclass(frozen=True)
class Audience:
    """Who is reading: signed in or not, and which raid days' content they may see (None: every day)."""

    signed_in: bool
    days: frozenset[str] | None = frozenset()

    def sees_day(self, day: str | None) -> bool:
        return self.days is None or day in self.days


PUBLIC_AUDIENCE = Audience(signed_in=False)

_MENTION = re.compile(r"@(everyone|here)", re.IGNORECASE)
ACTIVE = frozenset({ApplicationStatus.APPLIED, ApplicationStatus.INTERVIEWING, ApplicationStatus.TRIAL_OFFERED})
HIGHLIGHT_QUEUE_CAP = 5


def defang_mentions(text: str) -> str:
    """Break @everyone / @here so mirrored text can never ping the server, whatever the bot's mention settings."""
    return _MENTION.sub(lambda m: "@​" + m.group(1), text)


def _now() -> datetime:
    return datetime.now(UTC)


def _title_from(content: str) -> str:
    first = content.strip().splitlines()[0].strip().lstrip("#").strip() or "Post from Discord"
    return (first[:117] + "...") if len(first) > 120 else first


@dataclass
class CommunityService:
    repo: CommunityRepository
    config: CommunityConfig = field(default_factory=CommunityConfig)
    raid_days: RaidDayDirectory = field(default_factory=RaidDayDirectory)
    clock: Callable[[], datetime] = _now

    # ----------------------------------------------------------------- helpers

    def name_of(self, member_id: int) -> str:
        card = self.repo.member(member_id)
        return card.display_name if card else f"Member {member_id}"

    def _audit(self, actor_id: int, action: str, target: str, scope: str | None) -> None:
        self.repo.record_audit(AuditRecord(actor_id, action, target, scope, self.clock()))

    def _enqueue(self, kind: OutboxKind, payload: Payload) -> OutboxJob:
        return self.repo.enqueue(kind, payload, self.clock())

    # ------------------------------------------------------------------- posts

    def can_see_post(self, post: Post, audience: Audience) -> bool:
        if post.status is not PostStatus.PUBLISHED:
            return False
        if post.visibility is Visibility.PUBLIC:
            return True
        if not audience.signed_in:
            return False
        return post.visibility is Visibility.GUILD or audience.sees_day(post.raid_day)

    def feed(self, audience: Audience) -> list[Post]:
        visible = [p for p in self.repo.posts() if self.can_see_post(p, audience)]
        visible.sort(key=lambda p: p.published_at or p.created_at, reverse=True)
        visible.sort(key=lambda p: not p.pinned)  # stable: pinned first, newest first within each group
        return visible

    def create_post(self, actor_id: int, scope: str | None, data: PostCreate) -> Post:
        if scope is None and data.visibility is Visibility.RAID_DAY:
            raise Invalid("A raid-day post is written from that raid day's officer page")
        now = self.clock()
        post = Post(
            id=self.repo.next_id(),
            title=data.title,
            body=data.body,
            author_name=self.name_of(actor_id),
            origin=PostOrigin.HUB,
            visibility=Visibility.RAID_DAY if scope is not None else data.visibility,
            raid_day=scope,
            status=PostStatus.PUBLISHED,
            pinned=data.pinned,
            publish_to_discord=data.publish_to_discord,
            created_at=now,
            published_at=now,
        )
        if data.publish_to_discord:
            channel = self.config.post_channels.get(scope or "guild")
            if channel is not None:
                post.discord_channel_id = channel
                self._enqueue(OutboxKind.POST_MESSAGE, {"post_id": post.id, "channel_id": channel})
        self.repo.save_post(post)
        self._audit(actor_id, "post.create", f"post:{post.id}", scope)
        return post

    def update_post(self, actor_id: int, scope: str | None, post_id: int, data: PostCreate) -> Post:
        post = self._post_in_scope(post_id, scope)
        if post.origin is not PostOrigin.HUB:
            raise Conflict("Posts mirrored from Discord are edited in Discord")
        if scope is None:
            if data.visibility is Visibility.RAID_DAY:
                raise Invalid("A raid-day post is written from that raid day's officer page")
            post.visibility = data.visibility
        post.title, post.body, post.pinned = data.title, data.body, data.pinned
        self.repo.save_post(post)
        self._audit(actor_id, "post.update", f"post:{post.id}", scope)
        if post.discord_message_id is not None and post.discord_channel_id is not None:
            self._enqueue(
                OutboxKind.EDIT_MESSAGE,
                {"post_id": post.id, "channel_id": post.discord_channel_id, "message_id": post.discord_message_id},
            )
        return post

    def _post_in_scope(self, post_id: int, scope: str | None) -> Post:
        post = self.repo.get_post(post_id)
        if post is None or post.raid_day != scope:
            raise NotFound("No such post")
        return post

    def ingest_discord_message(self, msg: DiscordMessageIn) -> Post | None:
        """Offer a Discord message to the hub. It waits for an officer; nothing from Discord publishes by itself."""
        channel = self.config.mirrored(msg.channel_id)
        if channel is None:
            raise Forbidden("That channel is not mirrored")
        content = defang_mentions(msg.content.strip())
        existing = self.repo.post_for_discord_message(msg.message_id)
        if existing is not None:
            if not content:
                return existing
            existing.title, existing.body = _title_from(content), content
            if existing.status is PostStatus.PUBLISHED:
                existing.edited_since_review = True
                # An edit after review must not reach the outside world unseen.
                if existing.visibility is Visibility.PUBLIC:
                    existing.status = PostStatus.PENDING_REVIEW
            self.repo.save_post(existing)
            return existing
        if not content:
            return None
        post = Post(
            id=self.repo.next_id(),
            title=_title_from(content),
            body=content,
            author_name=msg.author_name,
            origin=PostOrigin.DISCORD,
            visibility=Visibility.RAID_DAY if channel.raid_day else Visibility.GUILD,
            raid_day=channel.raid_day,
            status=PostStatus.PENDING_REVIEW,
            discord_channel_id=msg.channel_id,
            discord_message_id=msg.message_id,
            created_at=msg.created_at,
        )
        self.repo.save_post(post)
        return post

    def discord_message_deleted(self, message_id: int) -> None:
        """Deleting in Discord takes the post down from the hub too."""
        post = self.repo.post_for_discord_message(message_id)
        if post is not None and post.origin is PostOrigin.DISCORD:
            post.status = PostStatus.HIDDEN
            self.repo.save_post(post)

    def curation_queue(self, scope: str | None) -> list[Post]:
        return sorted(
            (p for p in self.repo.posts() if p.status is PostStatus.PENDING_REVIEW and p.raid_day == scope),
            key=lambda p: p.created_at,
        )

    def curate(
        self,
        actor_id: int,
        scope: str | None,
        post_id: int,
        action: CurationAction,
        visibility: Visibility | None = None,
    ) -> Post:
        post = self._post_in_scope(post_id, scope)
        if post.status is not PostStatus.PENDING_REVIEW:
            raise Conflict("That post is not waiting for review")
        if action is CurationAction.HIDE:
            post.status = PostStatus.HIDDEN
        else:
            visibility = visibility or post.visibility
            if scope is None and visibility is Visibility.RAID_DAY:
                raise Invalid("Guild-wide posts are public or guild")
            post.visibility = visibility
            post.status = PostStatus.PUBLISHED
            post.edited_since_review = False
            post.published_at = self.clock()
        self.repo.save_post(post)
        self._audit(actor_id, f"post.curate.{action.value}", f"post:{post.id}", scope)
        return post

    # ------------------------------------------------------------ applications

    def apply(self, member_id: int, data: ApplicationCreate) -> Application:
        mine = [a for a in self.repo.applications() if a.member_id == member_id]
        if any(a.status in recruitment.OPEN for a in mine):
            raise Conflict("You already have an open application")
        cutoff = self.clock() - timedelta(days=recruitment.REAPPLY_COOLDOWN_DAYS)
        if any(a.status is ApplicationStatus.DECLINED and a.events[-1].at > cutoff for a in mine):
            raise Conflict(f"You can apply again {recruitment.REAPPLY_COOLDOWN_DAYS} days after a decision")
        if set(data.raid_days) - self.raid_days.day_ids:
            raise Invalid("Unknown raid day")
        if data.logs_url is not None and not recruitment.valid_logs_url(data.logs_url):
            raise Invalid("Logs link must be an https link to warcraftlogs.com")
        now = self.clock()
        name = self.name_of(member_id)
        app = Application(
            id=self.repo.next_id(),
            member_id=member_id,
            applicant_name=name,
            character_name=data.character_name,
            class_name=data.class_name,
            spec=data.spec,
            role=data.role,
            raid_days=sorted(set(data.raid_days)),
            experience=data.experience,
            availability=data.availability,
            logs_url=data.logs_url,
            status=ApplicationStatus.APPLIED,
            events=[ApplicationEvent(at=now, actor_name=name, from_status=None, to_status=ApplicationStatus.APPLIED)],
            created_at=now,
        )
        self.repo.save_application(app)
        return app

    def my_applications(self, member_id: int) -> list[Application]:
        mine = [a for a in self.repo.applications() if a.member_id == member_id]
        return sorted(mine, key=lambda a: a.created_at, reverse=True)

    def applications_for(self, scope: str | None) -> list[Application]:
        """A raid day's applications are those for that day or for any day; None is every application."""
        return sorted(
            (a for a in self.repo.applications() if scope is None or not a.raid_days or scope in a.raid_days),
            key=lambda a: a.created_at,
        )

    def _application_in_scope(self, app_id: int, scope: str | None) -> Application:
        app = self.repo.get_application(app_id)
        if app is None or (scope is not None and app.raid_days and scope not in app.raid_days):
            raise NotFound("No such application")
        return app

    def _move(self, app: Application, to: ApplicationStatus, actor_name: str, note: str) -> None:
        if not recruitment.can_transition(app.status, to):
            raise Conflict(f"An application that is {app.status.value} cannot become {to.value}")
        app.events.append(
            ApplicationEvent(at=self.clock(), actor_name=actor_name, from_status=app.status, to_status=to, note=note)
        )
        app.status = to
        self.repo.save_application(app)
        if to in recruitment.FINAL and app.interview_channel_id is not None:
            self._enqueue(
                OutboxKind.LOCK_INTERVIEW_ROOM,
                {
                    "application_id": app.id,
                    "channel_id": app.interview_channel_id,
                    "discord_user_id": self._discord_id(app),
                },
            )

    def _discord_id(self, app: Application) -> int:
        card = self.repo.member(app.member_id)
        if card is None:
            raise Conflict("The applicant has not logged in to the hub")
        return card.discord_user_id

    def transition(
        self, actor_id: int, scope: str | None, app_id: int, to: ApplicationStatus, note: str
    ) -> Application:
        app = self._application_in_scope(app_id, scope)
        self._move(app, to, self.name_of(actor_id), note)
        self._audit(actor_id, f"application.{to.value}", f"application:{app.id}", scope)
        return app

    def withdraw(self, member_id: int, app_id: int) -> Application:
        app = self.repo.get_application(app_id)
        if app is None or app.member_id != member_id:
            raise NotFound("No such application")
        self._move(app, ApplicationStatus.WITHDRAWN, self.name_of(member_id), "")
        return app

    def open_interview_room(self, actor_id: int, scope: str | None, app_id: int) -> Application:
        """Ask the bot for a private channel with the applicant and the officers who will decide."""
        app = self._application_in_scope(app_id, scope)
        pending = any(
            j.kind is OutboxKind.CREATE_INTERVIEW_ROOM and j.payload.get("application_id") == app.id and not j.done
            for j in self.repo.jobs()
        )
        if app.interview_channel_id is not None or pending:
            raise Conflict("An interview room is already open or on its way")
        if app.status is ApplicationStatus.APPLIED:
            self._move(app, ApplicationStatus.INTERVIEWING, self.name_of(actor_id), "Interview room opened")
        elif app.status is not ApplicationStatus.INTERVIEWING:
            raise Conflict("Interview rooms are for applications being interviewed")
        self._enqueue(
            OutboxKind.CREATE_INTERVIEW_ROOM,
            {
                "application_id": app.id,
                "discord_user_id": self._discord_id(app),
                "character_name": app.character_name,
                "category_id": self.config.interview_category_id,
                "officer_role_ids": self.raid_days.officer_role_ids(app.raid_days),
            },
        )
        self._audit(actor_id, "application.interview_room", f"application:{app.id}", scope)
        return app

    # ------------------------------------------------------------------ outbox

    def pending_jobs(self) -> list[OutboxJob]:
        return [j for j in self.repo.jobs() if not j.done]

    def ack(self, job_id: int, ack: OutboxAck) -> OutboxJob:
        job = self.repo.get_job(job_id)
        if job is None:
            raise NotFound("No such job")
        if job.done:
            return job  # acks are idempotent: a bot that reconnects may ack twice
        job.done = True
        self.repo.save_job(job)
        if job.kind is OutboxKind.CREATE_INTERVIEW_ROOM and ack.channel_id is not None:
            app = self.repo.get_application(int(str(job.payload["application_id"])))
            if app is not None:
                app.interview_channel_id = ack.channel_id
                self.repo.save_application(app)
        elif job.kind is OutboxKind.POST_MESSAGE and ack.message_id is not None:
            post = self.repo.get_post(int(str(job.payload["post_id"])))
            if post is not None:
                post.discord_message_id = ack.message_id
                self.repo.save_post(post)
        return job

    def post_for_job(self, job: OutboxJob) -> Post | None:
        post_id = job.payload.get("post_id")
        return self.repo.get_post(int(str(post_id))) if post_id is not None else None

    # -------------------------------------------------------------- highlights

    def submit_highlight(self, member_id: int, data: HighlightCreate) -> Highlight:
        ref = parse_clip_url(data.url)
        if ref is None:
            raise Invalid("Clips must be https links to YouTube, a Twitch clip or Streamable")
        name = self.name_of(member_id)
        waiting = sum(
            1 for h in self.repo.highlights() if h.status is HighlightStatus.SUBMITTED and h.submitted_by == name
        )
        if waiting >= HIGHLIGHT_QUEUE_CAP:
            raise Conflict(f"You have {HIGHLIGHT_QUEUE_CAP} clips waiting for review already")
        hl = Highlight(
            id=self.repo.next_id(),
            title=data.title,
            provider=ref.provider,
            clip_id=ref.clip_id,
            submitted_by=name,
            raid_id=data.raid_id,
            boss=data.boss,
            visibility=Visibility.GUILD,
            status=HighlightStatus.SUBMITTED,
            created_at=self.clock(),
        )
        self.repo.save_highlight(hl)
        return hl

    def highlights_to_review(self) -> list[Highlight]:
        return [h for h in self.repo.highlights() if h.status is HighlightStatus.SUBMITTED]

    def review_highlight(self, actor_id: int, hl_id: int, action: HighlightAction) -> Highlight:
        hl = self.repo.get_highlight(hl_id)
        if hl is None:
            raise NotFound("No such highlight")
        if action is HighlightAction.REJECT:
            hl.status = HighlightStatus.REJECTED
        else:
            hl.status = HighlightStatus.PUBLISHED
            hl.visibility = Visibility.PUBLIC if action is HighlightAction.PUBLISH_PUBLIC else Visibility.GUILD
        self.repo.save_highlight(hl)
        self._audit(actor_id, f"highlight.{action.value}", f"highlight:{hl.id}", None)
        return hl

    def highlights_for(self, audience: Audience) -> list[Highlight]:
        shown = [
            h
            for h in self.repo.highlights()
            if h.status is HighlightStatus.PUBLISHED and (h.visibility is Visibility.PUBLIC or audience.signed_in)
        ]
        return sorted(shown, key=lambda h: h.created_at, reverse=True)

    # -------------------------------------------------------------- spotlights

    def create_spotlight(self, actor_id: int, data: SpotlightCreate) -> Spotlight:
        if self.repo.member(data.member_id) is None:
            raise Invalid("Spotlights are about members who have logged in to the hub, so they can consent")
        sp = Spotlight(
            id=self.repo.next_id(),
            member_id=data.member_id,
            member_name=self.name_of(data.member_id),
            character_name=data.character_name,
            class_name=data.class_name,
            headline=data.headline,
            body=data.body,
            written_by=self.name_of(actor_id),
            consent=SpotlightConsent.PENDING,
            status=SpotlightStatus.DRAFT,
            created_at=self.clock(),
        )
        self.repo.save_spotlight(sp)
        self._audit(actor_id, "spotlight.create", f"spotlight:{sp.id}", None)
        return sp

    def all_spotlights(self) -> list[Spotlight]:
        return self.repo.spotlights()

    def spotlights_about(self, member_id: int) -> list[Spotlight]:
        return [s for s in self.repo.spotlights() if s.member_id == member_id]

    def decide_consent(self, member_id: int, sp_id: int, grant: bool) -> Spotlight:
        sp = self.repo.get_spotlight(sp_id)
        if sp is None or sp.member_id != member_id:
            raise NotFound("No such spotlight")
        sp.consent = SpotlightConsent.GRANTED if grant else SpotlightConsent.DECLINED
        if not grant and sp.status is SpotlightStatus.PUBLISHED:
            sp.status = SpotlightStatus.RETIRED  # withdrawing consent takes it down at once
        self.repo.save_spotlight(sp)
        return sp

    def publish_spotlight(self, actor_id: int, sp_id: int) -> Spotlight:
        sp = self.repo.get_spotlight(sp_id)
        if sp is None:
            raise NotFound("No such spotlight")
        if sp.consent is not SpotlightConsent.GRANTED:
            raise Conflict("A spotlight goes live only after its member agrees to it")
        if sp.status is not SpotlightStatus.DRAFT:
            raise Conflict("Only a draft spotlight can be published")
        sp.status = SpotlightStatus.PUBLISHED
        self.repo.save_spotlight(sp)
        self._audit(actor_id, "spotlight.publish", f"spotlight:{sp.id}", None)
        return sp

    def retire_spotlight(self, actor_id: int, sp_id: int) -> Spotlight:
        sp = self.repo.get_spotlight(sp_id)
        if sp is None:
            raise NotFound("No such spotlight")
        sp.status = SpotlightStatus.RETIRED
        self.repo.save_spotlight(sp)
        self._audit(actor_id, "spotlight.retire", f"spotlight:{sp.id}", None)
        return sp

    def published_spotlights(self) -> list[Spotlight]:
        return [
            s
            for s in self.repo.spotlights()
            if s.status is SpotlightStatus.PUBLISHED and s.consent is SpotlightConsent.GRANTED
        ]

    # ------------------------------------------------------------ recruitment

    def needs(self) -> list[RecruitmentNeed]:
        return self.repo.needs()

    def set_needs(self, actor_id: int, needs: list[RecruitmentNeed]) -> list[RecruitmentNeed]:
        if {d for n in needs for d in n.raid_days} - self.raid_days.day_ids:
            raise Invalid("Unknown raid day")
        self.repo.set_needs(needs)
        self._audit(actor_id, "recruitment.needs", f"{len(needs)} needs", None)
        return self.repo.needs()

    # ------------------------------------------------------------------ views

    def public_story(self) -> PublicStory:
        return PublicStory(
            guild=self.config.guild,
            realm=self.config.realm,
            tagline=self.config.tagline,
            story=self.config.story,
            discord_invite=self.config.discord_invite,
            progression=self.repo.progression(),
            needs=self.repo.needs(),
            posts=self.feed(PUBLIC_AUDIENCE),
            highlights=self.highlights_for(PUBLIC_AUDIENCE),
            spotlights=self.published_spotlights(),
        )

    def desk(self, scopes: list[str | None]) -> DeskSummary:
        """What waits on an officer across the scopes they lead. [None] is the global tier's whole-guild view."""
        whole_guild = None in scopes
        apps = {a.id for s in scopes for a in self.applications_for(s) if a.status in ACTIVE}
        if whole_guild:
            curate = sum(1 for p in self.repo.posts() if p.status is PostStatus.PENDING_REVIEW)
        else:
            curate = sum(len(self.curation_queue(s)) for s in scopes)
        return DeskSummary(
            applications_waiting=len(apps),
            posts_to_curate=curate,
            highlights_to_review=len(self.highlights_to_review()) if whole_guild else 0,
            spotlights_awaiting_consent=sum(
                1
                for s in self.repo.spotlights()
                if s.status is SpotlightStatus.DRAFT and s.consent is SpotlightConsent.PENDING
            )
            if whole_guild
            else 0,
        )
