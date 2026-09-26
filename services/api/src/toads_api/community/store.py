"""Community state and the rules that change it.

In-memory until the hub's Alembic migrations land with the data plane (phase 2.1); the matching tables are already
in hub-db. Routes only call the methods here, so swapping in a Postgres repository does not touch them.
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from toads_api.community import recruitment
from toads_api.community.clips import parse_clip_url
from toads_api.community.config import CommunityConfig
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
    Progress,
    PublicStory,
    RecruitmentNeed,
    Spotlight,
    SpotlightConsent,
    SpotlightCreate,
    SpotlightStatus,
    Visibility,
)
from toads_api.rbac import HubRole, Principal, RaidDaysConfig


class CommunityError(Exception):
    status_code = 400


class NotFound(CommunityError):
    status_code = 404


class Conflict(CommunityError):
    status_code = 409


class Invalid(CommunityError):
    status_code = 422


class Forbidden(CommunityError):
    status_code = 403


@dataclass(frozen=True)
class MemberCard:
    display_name: str
    discord_user_id: int


@dataclass(frozen=True)
class AuditRecord:
    actor_member_id: int
    action: str
    target: str
    raid_day: str | None
    at: datetime


_MENTION = re.compile(r"@(everyone|here)", re.IGNORECASE)


def defang_mentions(text: str) -> str:
    """Break @everyone / @here so mirrored text can never ping the server, whatever the bot's mention settings."""
    return _MENTION.sub(lambda m: "@​" + m.group(1), text)


def _now() -> datetime:
    return datetime.now(UTC)


def member_days(principal: Principal) -> set[str]:
    return {d for d, role in principal.day_roles.items() if role > HubRole.MEMBER}


@dataclass
class CommunityStore:
    config: CommunityConfig = field(default_factory=CommunityConfig)
    raid_days: RaidDaysConfig = field(default_factory=RaidDaysConfig)
    clock: Callable[[], datetime] = _now
    members: dict[int, MemberCard] = field(default_factory=dict)
    posts: dict[int, Post] = field(default_factory=dict)
    applications: dict[int, Application] = field(default_factory=dict)
    highlights: dict[int, Highlight] = field(default_factory=dict)
    spotlights: dict[int, Spotlight] = field(default_factory=dict)
    needs: list[RecruitmentNeed] = field(default_factory=list)
    progression: list[Progress] = field(default_factory=list)
    outbox: dict[int, OutboxJob] = field(default_factory=dict)
    audit: list[AuditRecord] = field(default_factory=list)
    _ids: itertools.count[int] = field(default_factory=lambda: itertools.count(1))

    # ----------------------------------------------------------------- helpers

    def _next_id(self) -> int:
        return next(self._ids)

    def name_of(self, member_id: int) -> str:
        card = self.members.get(member_id)
        return card.display_name if card else f"Member {member_id}"

    def _audit(self, actor: Principal, action: str, target: str, raid_day: str | None) -> None:
        self.audit.append(AuditRecord(actor.member_id, action, target, raid_day, self.clock()))

    def _enqueue(self, kind: OutboxKind, payload: dict[str, str | int | list[int] | None]) -> OutboxJob:
        job = OutboxJob(id=self._next_id(), kind=kind, payload=payload, created_at=self.clock())
        self.outbox[job.id] = job
        return job

    def _day_ids(self) -> set[str]:
        return {d.id for d in self.raid_days.raid_days}

    def _officer_role_ids(self, days: list[str]) -> list[int]:
        """Roles that may see an interview room: the global tier plus the officers of the days applied for."""
        ids = set(self.raid_days.global_officer_roles)
        for day in self.raid_days.raid_days:
            if not days or day.id in days:
                ids.update(day.officer_roles)
        return sorted(ids)

    # ------------------------------------------------------------------- posts

    def can_see_post(self, post: Post, viewer: Principal | None) -> bool:
        if post.status is not PostStatus.PUBLISHED:
            return False
        if post.visibility is Visibility.PUBLIC:
            return True
        if viewer is None:
            return False
        if post.visibility is Visibility.GUILD:
            return True
        return viewer.global_officer or post.raid_day in member_days(viewer)

    def feed(self, viewer: Principal | None) -> list[Post]:
        visible = [p for p in self.posts.values() if self.can_see_post(p, viewer)]
        visible.sort(key=lambda p: p.published_at or p.created_at, reverse=True)
        visible.sort(key=lambda p: not p.pinned)  # stable: pinned first, newest first within each group
        return visible

    def create_post(self, actor: Principal, raid_day: str | None, data: PostCreate) -> Post:
        if raid_day is None and data.visibility is Visibility.RAID_DAY:
            raise Invalid("A raid-day post is written from that raid day's officer page")
        if raid_day is not None and data.visibility is Visibility.PUBLIC:
            raise Forbidden("Only the global tier posts to the public story")
        visibility = Visibility.RAID_DAY if raid_day is not None else data.visibility
        now = self.clock()
        post = Post(
            id=self._next_id(),
            title=data.title,
            body=data.body,
            author_name=self.name_of(actor.member_id),
            origin=PostOrigin.HUB,
            visibility=visibility,
            raid_day=raid_day,
            status=PostStatus.PUBLISHED,
            pinned=data.pinned,
            publish_to_discord=data.publish_to_discord,
            created_at=now,
            published_at=now,
        )
        self.posts[post.id] = post
        self._audit(actor, "post.create", f"post:{post.id}", raid_day)
        if data.publish_to_discord:
            channel = self.config.post_channels.get(raid_day or "guild")
            if channel is not None:
                post.discord_channel_id = channel
                self._enqueue(OutboxKind.POST_MESSAGE, {"post_id": post.id, "channel_id": channel})
        return post

    def update_post(self, actor: Principal, raid_day: str | None, post_id: int, data: PostCreate) -> Post:
        post = self._post_in_scope(post_id, raid_day)
        if post.origin is not PostOrigin.HUB:
            raise Conflict("Posts mirrored from Discord are edited in Discord")
        if raid_day is not None and data.visibility is Visibility.PUBLIC:
            raise Forbidden("Only the global tier posts to the public story")
        post.title, post.body, post.pinned = data.title, data.body, data.pinned
        if raid_day is None:
            if data.visibility is Visibility.RAID_DAY:
                raise Invalid("A raid-day post is written from that raid day's officer page")
            post.visibility = data.visibility
        self._audit(actor, "post.update", f"post:{post.id}", raid_day)
        if post.discord_message_id is not None and post.discord_channel_id is not None:
            self._enqueue(
                OutboxKind.EDIT_MESSAGE,
                {"post_id": post.id, "channel_id": post.discord_channel_id, "message_id": post.discord_message_id},
            )
        return post

    def _post_in_scope(self, post_id: int, raid_day: str | None) -> Post:
        post = self.posts.get(post_id)
        # A post outside the caller's scope is reported as missing, so ids do not leak across raid days.
        if post is None or post.raid_day != raid_day:
            raise NotFound("No such post")
        return post

    def ingest_discord_message(self, msg: DiscordMessageIn) -> Post | None:
        """Offer a Discord message to the hub. It waits for an officer; nothing from Discord publishes by itself."""
        channel = self.config.mirrored(msg.channel_id)
        if channel is None:
            raise Forbidden("That channel is not mirrored")
        content = defang_mentions(msg.content.strip())
        existing = next((p for p in self.posts.values() if p.discord_message_id == msg.message_id), None)
        if existing is not None:
            if not content:
                return existing
            existing.title, existing.body = _title_from(content), content
            if existing.status is PostStatus.PUBLISHED:
                existing.edited_since_review = True
                # An edit after review must not reach the outside world unseen.
                if existing.visibility is Visibility.PUBLIC:
                    existing.status = PostStatus.PENDING_REVIEW
            return existing
        if not content:
            return None
        post = Post(
            id=self._next_id(),
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
        self.posts[post.id] = post
        return post

    def discord_message_deleted(self, message_id: int) -> None:
        """Deleting in Discord takes the post down from the hub too."""
        for post in self.posts.values():
            if post.discord_message_id == message_id and post.origin is PostOrigin.DISCORD:
                post.status = PostStatus.HIDDEN

    def curation_queue(self, raid_day: str | None) -> list[Post]:
        return sorted(
            (p for p in self.posts.values() if p.status is PostStatus.PENDING_REVIEW and p.raid_day == raid_day),
            key=lambda p: p.created_at,
        )

    def curate(
        self,
        actor: Principal,
        raid_day: str | None,
        post_id: int,
        action: CurationAction,
        visibility: Visibility | None = None,
    ) -> Post:
        post = self._post_in_scope(post_id, raid_day)
        if post.status is not PostStatus.PENDING_REVIEW:
            raise Conflict("That post is not waiting for review")
        if action is CurationAction.HIDE:
            post.status = PostStatus.HIDDEN
        else:
            visibility = visibility or post.visibility
            if raid_day is not None and visibility is Visibility.PUBLIC:
                raise Forbidden("Only the global tier posts to the public story")
            if raid_day is None and visibility is Visibility.RAID_DAY:
                raise Invalid("Guild-wide posts are public or guild")
            post.visibility = visibility
            post.status = PostStatus.PUBLISHED
            post.edited_since_review = False
            post.published_at = self.clock()
        self._audit(actor, f"post.curate.{action.value}", f"post:{post.id}", raid_day)
        return post

    # ------------------------------------------------------------ applications

    def apply(self, member_id: int, data: ApplicationCreate) -> Application:
        mine = [a for a in self.applications.values() if a.member_id == member_id]
        if any(a.status in recruitment.OPEN for a in mine):
            raise Conflict("You already have an open application")
        cutoff = self.clock() - timedelta(days=recruitment.REAPPLY_COOLDOWN_DAYS)
        if any(a.status is ApplicationStatus.DECLINED and a.events[-1].at > cutoff for a in mine):
            raise Conflict(f"You can apply again {recruitment.REAPPLY_COOLDOWN_DAYS} days after a decision")
        unknown = set(data.raid_days) - self._day_ids()
        if unknown:
            raise Invalid("Unknown raid day")
        if data.logs_url is not None and not recruitment.valid_logs_url(data.logs_url):
            raise Invalid("Logs link must be an https link to warcraftlogs.com")
        now = self.clock()
        app = Application(
            id=self._next_id(),
            member_id=member_id,
            applicant_name=self.name_of(member_id),
            character_name=data.character_name,
            class_name=data.class_name,
            spec=data.spec,
            role=data.role,
            raid_days=sorted(set(data.raid_days)),
            experience=data.experience,
            availability=data.availability,
            logs_url=data.logs_url,
            status=ApplicationStatus.APPLIED,
            events=[
                ApplicationEvent(
                    at=now, actor_name=self.name_of(member_id), from_status=None, to_status=ApplicationStatus.APPLIED
                )
            ],
            created_at=now,
        )
        self.applications[app.id] = app
        return app

    def my_applications(self, member_id: int) -> list[Application]:
        return sorted(
            (a for a in self.applications.values() if a.member_id == member_id),
            key=lambda a: a.created_at,
            reverse=True,
        )

    def applications_for(self, raid_day: str | None) -> list[Application]:
        """A raid day's officers see applications for their day or for any day; None is the global tier's view."""
        return sorted(
            (a for a in self.applications.values() if raid_day is None or not a.raid_days or raid_day in a.raid_days),
            key=lambda a: a.created_at,
        )

    def _application_in_scope(self, app_id: int, raid_day: str | None) -> Application:
        app = self.applications.get(app_id)
        if app is None or (raid_day is not None and app.raid_days and raid_day not in app.raid_days):
            raise NotFound("No such application")
        return app

    def _move(self, app: Application, to: ApplicationStatus, actor_name: str, note: str) -> None:
        if not recruitment.can_transition(app.status, to):
            raise Conflict(f"An application that is {app.status.value} cannot become {to.value}")
        app.events.append(
            ApplicationEvent(at=self.clock(), actor_name=actor_name, from_status=app.status, to_status=to, note=note)
        )
        app.status = to
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
        card = self.members.get(app.member_id)
        if card is None:
            raise Conflict("The applicant has not logged in to the hub")
        return card.discord_user_id

    def transition(
        self, actor: Principal, raid_day: str | None, app_id: int, to: ApplicationStatus, note: str
    ) -> Application:
        app = self._application_in_scope(app_id, raid_day)
        if to in recruitment.APPLICANT_ONLY:
            raise Forbidden("Only the applicant can withdraw")
        self._move(app, to, self.name_of(actor.member_id), note)
        self._audit(actor, f"application.{to.value}", f"application:{app.id}", raid_day)
        return app

    def withdraw(self, member_id: int, app_id: int) -> Application:
        app = self.applications.get(app_id)
        if app is None or app.member_id != member_id:
            raise NotFound("No such application")
        self._move(app, ApplicationStatus.WITHDRAWN, self.name_of(member_id), "")
        return app

    def open_interview_room(self, actor: Principal, raid_day: str | None, app_id: int) -> Application:
        """Ask the bot for a private channel with the applicant and the officers who will decide."""
        app = self._application_in_scope(app_id, raid_day)
        if app.interview_channel_id is not None or any(
            j.kind is OutboxKind.CREATE_INTERVIEW_ROOM and j.payload.get("application_id") == app.id and not j.done
            for j in self.outbox.values()
        ):
            raise Conflict("An interview room is already open or on its way")
        if app.status is ApplicationStatus.APPLIED:
            self._move(app, ApplicationStatus.INTERVIEWING, self.name_of(actor.member_id), "Interview room opened")
        elif app.status is not ApplicationStatus.INTERVIEWING:
            raise Conflict("Interview rooms are for applications being interviewed")
        self._enqueue(
            OutboxKind.CREATE_INTERVIEW_ROOM,
            {
                "application_id": app.id,
                "discord_user_id": self._discord_id(app),
                "character_name": app.character_name,
                "category_id": self.config.interview_category_id,
                "officer_role_ids": self._officer_role_ids(app.raid_days),
            },
        )
        self._audit(actor, "application.interview_room", f"application:{app.id}", raid_day)
        return app

    # ------------------------------------------------------------------ outbox

    def pending_jobs(self) -> list[OutboxJob]:
        return [j for j in self.outbox.values() if not j.done]

    def ack(self, job_id: int, ack: OutboxAck) -> OutboxJob:
        job = self.outbox.get(job_id)
        if job is None:
            raise NotFound("No such job")
        if job.done:
            return job  # acks are idempotent: a bot that reconnects may ack twice
        job.done = True
        if job.kind is OutboxKind.CREATE_INTERVIEW_ROOM and ack.channel_id is not None:
            app = self.applications.get(int(str(job.payload["application_id"])))
            if app is not None:
                app.interview_channel_id = ack.channel_id
        elif job.kind is OutboxKind.POST_MESSAGE and ack.message_id is not None:
            post = self.posts.get(int(str(job.payload["post_id"])))
            if post is not None:
                post.discord_message_id = ack.message_id
        return job

    def post_for_job(self, job: OutboxJob) -> Post | None:
        post_id = job.payload.get("post_id")
        return self.posts.get(int(str(post_id))) if post_id is not None else None

    # -------------------------------------------------------------- highlights

    def submit_highlight(self, member_id: int, data: HighlightCreate) -> Highlight:
        ref = parse_clip_url(data.url)
        if ref is None:
            raise Invalid("Clips must be https links to YouTube, a Twitch clip or Streamable")
        pending = sum(
            1
            for h in self.highlights.values()
            if h.status is HighlightStatus.SUBMITTED and h.submitted_by == self.name_of(member_id)
        )
        if pending >= 5:
            raise Conflict("You have five clips waiting for review already")
        hl = Highlight(
            id=self._next_id(),
            title=data.title,
            provider=ref.provider,
            clip_id=ref.clip_id,
            submitted_by=self.name_of(member_id),
            raid_id=data.raid_id,
            boss=data.boss,
            visibility=Visibility.GUILD,
            status=HighlightStatus.SUBMITTED,
            created_at=self.clock(),
        )
        self.highlights[hl.id] = hl
        return hl

    def review_highlight(self, actor: Principal, hl_id: int, action: HighlightAction) -> Highlight:
        hl = self.highlights.get(hl_id)
        if hl is None:
            raise NotFound("No such highlight")
        if action is HighlightAction.REJECT:
            hl.status = HighlightStatus.REJECTED
        else:
            hl.status = HighlightStatus.PUBLISHED
            hl.visibility = Visibility.PUBLIC if action is HighlightAction.PUBLISH_PUBLIC else Visibility.GUILD
        self._audit(actor, f"highlight.{action.value}", f"highlight:{hl.id}", None)
        return hl

    def highlights_for(self, viewer: Principal | None) -> list[Highlight]:
        shown = [
            h
            for h in self.highlights.values()
            if h.status is HighlightStatus.PUBLISHED and (h.visibility is Visibility.PUBLIC or viewer is not None)
        ]
        return sorted(shown, key=lambda h: h.created_at, reverse=True)

    # -------------------------------------------------------------- spotlights

    def create_spotlight(self, actor: Principal, data: SpotlightCreate) -> Spotlight:
        if data.member_id not in self.members:
            raise Invalid("Spotlights are about members who have logged in to the hub, so they can consent")
        sp = Spotlight(
            id=self._next_id(),
            member_id=data.member_id,
            member_name=self.name_of(data.member_id),
            character_name=data.character_name,
            class_name=data.class_name,
            headline=data.headline,
            body=data.body,
            written_by=self.name_of(actor.member_id),
            consent=SpotlightConsent.PENDING,
            status=SpotlightStatus.DRAFT,
            created_at=self.clock(),
        )
        self.spotlights[sp.id] = sp
        self._audit(actor, "spotlight.create", f"spotlight:{sp.id}", None)
        return sp

    def spotlights_about(self, member_id: int) -> list[Spotlight]:
        return [s for s in self.spotlights.values() if s.member_id == member_id]

    def decide_consent(self, member_id: int, sp_id: int, grant: bool) -> Spotlight:
        sp = self.spotlights.get(sp_id)
        if sp is None or sp.member_id != member_id:
            raise NotFound("No such spotlight")
        sp.consent = SpotlightConsent.GRANTED if grant else SpotlightConsent.DECLINED
        if not grant and sp.status is SpotlightStatus.PUBLISHED:
            sp.status = SpotlightStatus.RETIRED  # withdrawing consent takes it down at once
        return sp

    def publish_spotlight(self, actor: Principal, sp_id: int) -> Spotlight:
        sp = self.spotlights.get(sp_id)
        if sp is None:
            raise NotFound("No such spotlight")
        if sp.consent is not SpotlightConsent.GRANTED:
            raise Conflict("A spotlight goes live only after its member agrees to it")
        if sp.status is not SpotlightStatus.DRAFT:
            raise Conflict("Only a draft spotlight can be published")
        sp.status = SpotlightStatus.PUBLISHED
        self._audit(actor, "spotlight.publish", f"spotlight:{sp.id}", None)
        return sp

    def retire_spotlight(self, actor: Principal, sp_id: int) -> Spotlight:
        sp = self.spotlights.get(sp_id)
        if sp is None:
            raise NotFound("No such spotlight")
        sp.status = SpotlightStatus.RETIRED
        self._audit(actor, "spotlight.retire", f"spotlight:{sp.id}", None)
        return sp

    def published_spotlights(self) -> list[Spotlight]:
        return [
            s
            for s in self.spotlights.values()
            if s.status is SpotlightStatus.PUBLISHED and s.consent is SpotlightConsent.GRANTED
        ]

    # ------------------------------------------------------------ recruitment

    def set_needs(self, actor: Principal, needs: list[RecruitmentNeed]) -> list[RecruitmentNeed]:
        unknown = {d for n in needs for d in n.raid_days} - self._day_ids()
        if unknown:
            raise Invalid("Unknown raid day")
        self.needs = list(needs)
        self._audit(actor, "recruitment.needs", f"{len(needs)} needs", None)
        return self.needs

    # ------------------------------------------------------------------ views

    def public_story(self) -> PublicStory:
        return PublicStory(
            guild=self.config.guild,
            realm=self.config.realm,
            tagline=self.config.tagline,
            story=self.config.story,
            discord_invite=self.config.discord_invite,
            progression=self.progression,
            needs=self.needs,
            posts=self.feed(None),
            highlights=self.highlights_for(None),
            spotlights=self.published_spotlights(),
        )

    def desk(self, viewer: Principal) -> DeskSummary:
        """Counts of what waits on this officer. A raid-day officer counts only their own days."""
        if viewer.global_officer:
            scopes: list[str | None] = [None]
        else:
            scopes = [d for d, role in viewer.day_roles.items() if role is HubRole.OFFICER]
        apps = {
            a.id
            for s in scopes
            for a in self.applications_for(s)
            if a.status in {ApplicationStatus.APPLIED, ApplicationStatus.INTERVIEWING, ApplicationStatus.TRIAL_OFFERED}
        }
        if viewer.global_officer:
            curate = sum(1 for p in self.posts.values() if p.status is PostStatus.PENDING_REVIEW)
        else:
            curate = sum(len(self.curation_queue(s)) for s in scopes)
        return DeskSummary(
            applications_waiting=len(apps),
            posts_to_curate=curate,
            highlights_to_review=sum(1 for h in self.highlights.values() if h.status is HighlightStatus.SUBMITTED)
            if viewer.global_officer
            else 0,
            spotlights_awaiting_consent=sum(
                1
                for s in self.spotlights.values()
                if s.status is SpotlightStatus.DRAFT and s.consent is SpotlightConsent.PENDING
            )
            if viewer.global_officer
            else 0,
        )


def _title_from(content: str) -> str:
    first = content.strip().splitlines()[0].strip().lstrip("#").strip() or "Post from Discord"
    return (first[:117] + "...") if len(first) > 120 else first
