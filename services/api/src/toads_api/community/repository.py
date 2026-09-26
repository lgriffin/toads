"""Where community state lives. CommunityService only talks to this protocol, so moving from memory to Postgres
(phase 2.1, tables in hub_db.community) replaces the repository and leaves the rules alone."""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from toads_api.community.schemas import (
    Application,
    Highlight,
    OutboxJob,
    OutboxKind,
    Post,
    Progress,
    RecruitmentNeed,
    Spotlight,
)


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


Payload = dict[str, str | int | list[int] | None]


class CommunityRepository(Protocol):
    def next_id(self) -> int: ...

    def member(self, member_id: int) -> MemberCard | None: ...

    def save_post(self, post: Post) -> None: ...
    def get_post(self, post_id: int) -> Post | None: ...
    def post_for_discord_message(self, message_id: int) -> Post | None: ...
    def posts(self) -> list[Post]: ...

    def save_application(self, app: Application) -> None: ...
    def get_application(self, app_id: int) -> Application | None: ...
    def applications(self) -> list[Application]: ...

    def save_highlight(self, hl: Highlight) -> None: ...
    def get_highlight(self, hl_id: int) -> Highlight | None: ...
    def highlights(self) -> list[Highlight]: ...

    def save_spotlight(self, sp: Spotlight) -> None: ...
    def get_spotlight(self, sp_id: int) -> Spotlight | None: ...
    def spotlights(self) -> list[Spotlight]: ...

    def needs(self) -> list[RecruitmentNeed]: ...
    def set_needs(self, needs: list[RecruitmentNeed]) -> None: ...
    def progression(self) -> list[Progress]: ...

    def enqueue(self, kind: OutboxKind, payload: Payload, at: datetime) -> OutboxJob: ...
    def get_job(self, job_id: int) -> OutboxJob | None: ...
    def save_job(self, job: OutboxJob) -> None: ...
    def jobs(self) -> list[OutboxJob]: ...

    def record_audit(self, record: AuditRecord) -> None: ...
    def audit(self) -> list[AuditRecord]: ...


@dataclass
class InMemoryCommunityRepository:
    """Process-local state for tests, local dev and the Pages-era API. Not durable across restarts."""

    members: dict[int, MemberCard] = field(default_factory=dict)
    needs_list: list[RecruitmentNeed] = field(default_factory=list)
    progression_list: list[Progress] = field(default_factory=list)
    _posts: dict[int, Post] = field(default_factory=dict)
    _applications: dict[int, Application] = field(default_factory=dict)
    _highlights: dict[int, Highlight] = field(default_factory=dict)
    _spotlights: dict[int, Spotlight] = field(default_factory=dict)
    _jobs: dict[int, OutboxJob] = field(default_factory=dict)
    _audit: list[AuditRecord] = field(default_factory=list)
    _ids: itertools.count[int] = field(default_factory=lambda: itertools.count(1))

    def next_id(self) -> int:
        return next(self._ids)

    def member(self, member_id: int) -> MemberCard | None:
        return self.members.get(member_id)

    def save_post(self, post: Post) -> None:
        self._posts[post.id] = post

    def get_post(self, post_id: int) -> Post | None:
        return self._posts.get(post_id)

    def post_for_discord_message(self, message_id: int) -> Post | None:
        return next((p for p in self._posts.values() if p.discord_message_id == message_id), None)

    def posts(self) -> list[Post]:
        return list(self._posts.values())

    def save_application(self, app: Application) -> None:
        self._applications[app.id] = app

    def get_application(self, app_id: int) -> Application | None:
        return self._applications.get(app_id)

    def applications(self) -> list[Application]:
        return list(self._applications.values())

    def save_highlight(self, hl: Highlight) -> None:
        self._highlights[hl.id] = hl

    def get_highlight(self, hl_id: int) -> Highlight | None:
        return self._highlights.get(hl_id)

    def highlights(self) -> list[Highlight]:
        return list(self._highlights.values())

    def save_spotlight(self, sp: Spotlight) -> None:
        self._spotlights[sp.id] = sp

    def get_spotlight(self, sp_id: int) -> Spotlight | None:
        return self._spotlights.get(sp_id)

    def spotlights(self) -> list[Spotlight]:
        return list(self._spotlights.values())

    def needs(self) -> list[RecruitmentNeed]:
        return list(self.needs_list)

    def set_needs(self, needs: list[RecruitmentNeed]) -> None:
        self.needs_list = list(needs)

    def progression(self) -> list[Progress]:
        return list(self.progression_list)

    def enqueue(self, kind: OutboxKind, payload: Payload, at: datetime) -> OutboxJob:
        job = OutboxJob(id=self.next_id(), kind=kind, payload=payload, created_at=at)
        self._jobs[job.id] = job
        return job

    def get_job(self, job_id: int) -> OutboxJob | None:
        return self._jobs.get(job_id)

    def save_job(self, job: OutboxJob) -> None:
        self._jobs[job.id] = job

    def jobs(self) -> list[OutboxJob]:
        return list(self._jobs.values())

    def record_audit(self, record: AuditRecord) -> None:
        self._audit.append(record)

    def audit(self) -> list[AuditRecord]:
        return list(self._audit)
