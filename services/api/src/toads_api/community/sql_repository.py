"""CommunityRepository over the hub-db tables (Postgres in production, SQLite in tests).

Rows store member ids; display names are read from `members` on the way out, so a renamed member shows their
new name everywhere. Each call is its own transaction.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime

import hub_db
from sqlalchemy import ColumnElement, delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from toads_api.community.repository import AuditRecord, MemberCard, Payload
from toads_api.community.schemas import (
    Application,
    ApplicationEvent,
    ApplicationStatus,
    ClipProvider,
    Highlight,
    HighlightStatus,
    OutboxJob,
    OutboxKind,
    Post,
    PostOrigin,
    PostStatus,
    Priority,
    Progress,
    RecruitmentNeed,
    Role,
    Spotlight,
    SpotlightConsent,
    SpotlightStatus,
    Visibility,
)


def _utc(at: datetime) -> datetime:
    """SQLite hands back naive datetimes; every stored time is UTC."""
    return at if at.tzinfo is not None else at.replace(tzinfo=UTC)


def _utc_or_none(at: datetime | None) -> datetime | None:
    return None if at is None else _utc(at)


def _names(db: Session, ids: Iterable[int | None]) -> dict[int, str]:
    wanted = {i for i in ids if i is not None}
    if not wanted:
        return {}
    rows = db.execute(select(hub_db.Member.id, hub_db.Member.display_name).where(hub_db.Member.id.in_(wanted)))
    return {member_id: name for member_id, name in rows}


def _name(names: dict[int, str], member_id: int) -> str:
    return names.get(member_id, f"Member {member_id}")


@dataclass
class SqlCommunityRepository:
    db: sessionmaker[Session]
    # Zone progress comes from wcl-store once the analyzer publishes it; until then it is configured here.
    progression_list: list[Progress] = field(default_factory=list)

    def next_id(self) -> int:
        with self.db.begin() as db:
            row = hub_db.CommunityId()
            db.add(row)
            db.flush()
            return row.id

    def member(self, member_id: int) -> MemberCard | None:
        with self.db() as db:
            m = db.get(hub_db.Member, member_id)
            return None if m is None else MemberCard(display_name=m.display_name, discord_user_id=m.discord_user_id)

    # ------------------------------------------------------------------ posts

    def save_post(self, post: Post) -> None:
        with self.db.begin() as db:
            db.merge(
                hub_db.CommunityPost(
                    id=post.id,
                    title=post.title,
                    body=post.body,
                    author_member_id=post.author_id,
                    author_name=post.author_name,
                    origin=post.origin.value,
                    visibility=post.visibility.value,
                    raid_day_id=post.raid_day,
                    status=post.status.value,
                    pinned=post.pinned,
                    publish_to_discord=post.publish_to_discord,
                    discord_channel_id=post.discord_channel_id,
                    discord_message_id=post.discord_message_id,
                    edited_since_review=post.edited_since_review,
                    created_at=post.created_at,
                    published_at=post.published_at,
                )
            )

    @staticmethod
    def _post(row: hub_db.CommunityPost, names: dict[int, str]) -> Post:
        author = row.author_name if row.author_member_id is None else names.get(row.author_member_id, row.author_name)
        return Post(
            id=row.id,
            title=row.title,
            body=row.body,
            author_name=author,
            author_id=row.author_member_id,
            origin=PostOrigin(row.origin),
            visibility=Visibility(row.visibility),
            raid_day=row.raid_day_id,
            status=PostStatus(row.status),
            pinned=row.pinned,
            publish_to_discord=row.publish_to_discord,
            discord_channel_id=row.discord_channel_id,
            discord_message_id=row.discord_message_id,
            edited_since_review=row.edited_since_review,
            created_at=_utc(row.created_at),
            published_at=_utc_or_none(row.published_at),
        )

    def _posts_where(self, *where: ColumnElement[bool]) -> list[Post]:
        with self.db() as db:
            rows = db.scalars(select(hub_db.CommunityPost).where(*where).order_by(hub_db.CommunityPost.id)).all()
            names = _names(db, (r.author_member_id for r in rows))
            return [self._post(r, names) for r in rows]

    def get_post(self, post_id: int) -> Post | None:
        return next(iter(self._posts_where(hub_db.CommunityPost.id == post_id)), None)

    def post_for_discord_message(self, message_id: int) -> Post | None:
        return next(iter(self._posts_where(hub_db.CommunityPost.discord_message_id == message_id)), None)

    def posts(self) -> list[Post]:
        return self._posts_where()

    # ----------------------------------------------------------- applications

    def save_application(self, app: Application) -> None:
        with self.db.begin() as db:
            db.merge(
                hub_db.Application(
                    id=app.id,
                    member_id=app.member_id,
                    character_name=app.character_name,
                    class_name=app.class_name,
                    spec=app.spec,
                    role=app.role.value,
                    raid_days=list(app.raid_days),
                    experience=app.experience,
                    availability=app.availability,
                    logs_url=app.logs_url,
                    status=app.status.value,
                    interview_channel_id=app.interview_channel_id,
                    created_at=app.created_at,
                )
            )
            db.flush()
            # Events are append-only: store the ones this repository has not seen yet.
            stored = db.scalar(
                select(func.count())
                .select_from(hub_db.ApplicationEvent)
                .where(hub_db.ApplicationEvent.application_id == app.id)
            )
            for event in app.events[stored or 0 :]:
                db.add(
                    hub_db.ApplicationEvent(
                        application_id=app.id,
                        actor_member_id=event.actor_id,
                        from_status=None if event.from_status is None else event.from_status.value,
                        to_status=event.to_status.value,
                        note=event.note,
                        at=event.at,
                    )
                )

    def _applications_where(self, *where: ColumnElement[bool]) -> list[Application]:
        with self.db() as db:
            rows = db.scalars(select(hub_db.Application).where(*where).order_by(hub_db.Application.id)).all()
            events = db.scalars(
                select(hub_db.ApplicationEvent)
                .where(hub_db.ApplicationEvent.application_id.in_([r.id for r in rows]))
                .order_by(hub_db.ApplicationEvent.id)
            ).all()
            names = _names(db, [r.member_id for r in rows] + [e.actor_member_id for e in events])
            by_app: dict[int, list[ApplicationEvent]] = {}
            for e in events:
                by_app.setdefault(e.application_id, []).append(
                    ApplicationEvent(
                        at=_utc(e.at),
                        actor_id=e.actor_member_id,
                        actor_name=_name(names, e.actor_member_id),
                        from_status=None if e.from_status is None else ApplicationStatus(e.from_status),
                        to_status=ApplicationStatus(e.to_status),
                        note=e.note,
                    )
                )
            return [
                Application(
                    id=r.id,
                    member_id=r.member_id,
                    applicant_name=_name(names, r.member_id),
                    character_name=r.character_name,
                    class_name=r.class_name,
                    spec=r.spec,
                    role=Role(r.role),
                    raid_days=list(r.raid_days),
                    experience=r.experience,
                    availability=r.availability,
                    logs_url=r.logs_url,
                    status=ApplicationStatus(r.status),
                    interview_channel_id=r.interview_channel_id,
                    events=by_app.get(r.id, []),
                    created_at=_utc(r.created_at),
                )
                for r in rows
            ]

    def get_application(self, app_id: int) -> Application | None:
        return next(iter(self._applications_where(hub_db.Application.id == app_id)), None)

    def applications(self) -> list[Application]:
        return self._applications_where()

    # ------------------------------------------------------------- highlights

    def save_highlight(self, hl: Highlight) -> None:
        with self.db.begin() as db:
            db.merge(
                hub_db.Highlight(
                    id=hl.id,
                    title=hl.title,
                    provider=hl.provider.value,
                    clip_id=hl.clip_id,
                    submitted_by=hl.submitted_by_id,
                    raid_id=hl.raid_id,
                    boss=hl.boss,
                    visibility=hl.visibility.value,
                    status=hl.status.value,
                    created_at=hl.created_at,
                )
            )

    def _highlights_where(self, *where: ColumnElement[bool]) -> list[Highlight]:
        with self.db() as db:
            rows = db.scalars(select(hub_db.Highlight).where(*where).order_by(hub_db.Highlight.id)).all()
            names = _names(db, (r.submitted_by for r in rows))
            return [
                Highlight(
                    id=r.id,
                    title=r.title,
                    provider=ClipProvider(r.provider),
                    clip_id=r.clip_id,
                    submitted_by_id=r.submitted_by,
                    submitted_by=_name(names, r.submitted_by),
                    raid_id=r.raid_id,
                    boss=r.boss,
                    visibility=Visibility(r.visibility),
                    status=HighlightStatus(r.status),
                    created_at=_utc(r.created_at),
                )
                for r in rows
            ]

    def get_highlight(self, hl_id: int) -> Highlight | None:
        return next(iter(self._highlights_where(hub_db.Highlight.id == hl_id)), None)

    def highlights(self) -> list[Highlight]:
        return self._highlights_where()

    # ------------------------------------------------------------- spotlights

    def save_spotlight(self, sp: Spotlight) -> None:
        with self.db.begin() as db:
            db.merge(
                hub_db.Spotlight(
                    id=sp.id,
                    member_id=sp.member_id,
                    character_name=sp.character_name,
                    class_name=sp.class_name,
                    headline=sp.headline,
                    body=sp.body,
                    written_by=sp.written_by_id,
                    consent=sp.consent.value,
                    status=sp.status.value,
                    created_at=sp.created_at,
                )
            )

    def _spotlights_where(self, *where: ColumnElement[bool]) -> list[Spotlight]:
        with self.db() as db:
            rows = db.scalars(select(hub_db.Spotlight).where(*where).order_by(hub_db.Spotlight.id)).all()
            names = _names(db, [r.member_id for r in rows] + [r.written_by for r in rows])
            return [
                Spotlight(
                    id=r.id,
                    member_id=r.member_id,
                    member_name=_name(names, r.member_id),
                    character_name=r.character_name,
                    class_name=r.class_name,
                    headline=r.headline,
                    body=r.body,
                    written_by_id=r.written_by,
                    written_by=_name(names, r.written_by),
                    consent=SpotlightConsent(r.consent),
                    status=SpotlightStatus(r.status),
                    created_at=_utc(r.created_at),
                )
                for r in rows
            ]

    def get_spotlight(self, sp_id: int) -> Spotlight | None:
        return next(iter(self._spotlights_where(hub_db.Spotlight.id == sp_id)), None)

    def spotlights(self) -> list[Spotlight]:
        return self._spotlights_where()

    # --------------------------------------------------- recruitment, progress

    def needs(self) -> list[RecruitmentNeed]:
        with self.db() as db:
            rows = db.scalars(select(hub_db.RecruitmentNeed).order_by(hub_db.RecruitmentNeed.id)).all()
            return [
                RecruitmentNeed(
                    class_name=r.class_name,
                    spec=r.spec,
                    role=Role(r.role),
                    priority=Priority(r.priority),
                    raid_days=list(r.raid_days),
                )
                for r in rows
            ]

    def set_needs(self, needs: list[RecruitmentNeed]) -> None:
        with self.db.begin() as db:
            db.execute(delete(hub_db.RecruitmentNeed))
            db.add_all(
                hub_db.RecruitmentNeed(
                    class_name=n.class_name,
                    spec=n.spec,
                    role=n.role.value,
                    priority=n.priority.value,
                    raid_days=list(n.raid_days),
                )
                for n in needs
            )

    def progression(self) -> list[Progress]:
        return list(self.progression_list)

    # ---------------------------------------------------------------- outbox

    @staticmethod
    def _job(row: hub_db.BotOutbox) -> OutboxJob:
        return OutboxJob(
            id=row.id, kind=OutboxKind(row.kind), payload=row.payload, created_at=_utc(row.created_at), done=row.done
        )

    def enqueue(self, kind: OutboxKind, payload: Payload, at: datetime) -> OutboxJob:
        job = OutboxJob(id=self.next_id(), kind=kind, payload=payload, created_at=at)
        self.save_job(job)
        return job

    def get_job(self, job_id: int) -> OutboxJob | None:
        with self.db() as db:
            row = db.get(hub_db.BotOutbox, job_id)
            return None if row is None else self._job(row)

    def save_job(self, job: OutboxJob) -> None:
        with self.db.begin() as db:
            db.merge(
                hub_db.BotOutbox(
                    id=job.id, kind=job.kind.value, payload=dict(job.payload), done=job.done, created_at=job.created_at
                )
            )

    def jobs(self) -> list[OutboxJob]:
        with self.db() as db:
            return [self._job(r) for r in db.scalars(select(hub_db.BotOutbox).order_by(hub_db.BotOutbox.id))]

    # ----------------------------------------------------------------- audit

    def record_audit(self, record: AuditRecord) -> None:
        with self.db.begin() as db:
            db.add(
                hub_db.AuditEntry(
                    actor_member_id=record.actor_member_id,
                    action=record.action,
                    target=record.target[:200],
                    raid_day_id=record.raid_day,
                    at=record.at,
                )
            )

    def audit(self) -> list[AuditRecord]:
        with self.db() as db:
            rows = db.scalars(select(hub_db.AuditEntry).order_by(hub_db.AuditEntry.id)).all()
            return [AuditRecord(r.actor_member_id, r.action, r.target, r.raid_day_id, _utc(r.at)) for r in rows]
