"""Where the reference feature's state lives. ReferenceService only talks to the ReferenceRepository protocol; the
hub-db backed implementation is `sql.SqlReferenceRepository`."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class UserToken:
    """The dedicated login's Warcraft Logs token. repr hides it."""

    access_token: str
    refresh_token: str | None
    # Epoch seconds.
    expires_at: float

    def __repr__(self) -> str:
        return f"UserToken(expires_at={self.expires_at})"


@dataclass(frozen=True)
class LoginInfo:
    connected: bool
    # "working", or "expired" when Warcraft Logs refused to refresh it; None when not connected.
    status: str | None = None
    connected_by: str | None = None
    connected_at: datetime | None = None


@dataclass(frozen=True)
class Job:
    id: str
    kind: str
    status: str
    raid_day: str
    params: dict[str, Any]
    message: str
    created_at: datetime
    updated_at: datetime

    @property
    def report(self) -> str:
        """The raid the job is about: the reference for a comparison, else the report it names."""
        return str(self.params.get("reference_report") or self.params.get("report") or "")


@dataclass(frozen=True)
class StoredPage:
    generated_at: str
    references: list[dict[str, Any]]
    guild_raids: list[dict[str, Any]]


@dataclass(frozen=True)
class ComparisonSummary:
    guild_report: str
    reference_report: str
    guild_title: str
    reference_title: str
    generated_at: str


@dataclass(frozen=True)
class StoredComparison:
    generated_at: str
    payload: dict[str, Any]


class ReferenceRepository(Protocol):
    def login_info(self) -> LoginInfo: ...
    def save_login(self, token: UserToken, member_id: int) -> None: ...
    def delete_login(self) -> bool: ...

    def create_job(self, kind: str, raid_day: str, member_id: int, params: dict[str, Any]) -> Job: ...
    def fail_job(self, job_id: str, message: str) -> None: ...
    def recent_jobs(self, limit: int) -> list[Job]: ...

    def page(self) -> StoredPage | None: ...
    def comparisons(self) -> list[ComparisonSummary]: ...
    def comparison(self, guild_report: str, reference_report: str) -> StoredComparison | None: ...


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass
class InMemoryReferenceRepository:
    """For service tests."""

    token: UserToken | None = None
    connected_by: int | None = None
    expired: bool = False
    jobs: list[Job] = field(default_factory=list)
    stored_page: StoredPage | None = None
    stored: dict[tuple[str, str], StoredComparison] = field(default_factory=dict)

    def login_info(self) -> LoginInfo:
        if self.token is None:
            return LoginInfo(connected=False)
        return LoginInfo(True, "expired" if self.expired else "working", f"member {self.connected_by}", _now())

    def save_login(self, token: UserToken, member_id: int) -> None:
        self.token, self.connected_by, self.expired = token, member_id, False

    def delete_login(self) -> bool:
        had = self.token is not None
        self.token = None
        return had

    def create_job(self, kind: str, raid_day: str, member_id: int, params: dict[str, Any]) -> Job:
        job = Job(f"job{len(self.jobs) + 1}", kind, "queued", raid_day, dict(params), "", _now(), _now())
        self.jobs.append(job)
        return job

    def fail_job(self, job_id: str, message: str) -> None:
        self.jobs = [replace(j, status="failed", message=message) if j.id == job_id else j for j in self.jobs]

    def recent_jobs(self, limit: int) -> list[Job]:
        return list(reversed(self.jobs))[:limit]

    def page(self) -> StoredPage | None:
        return self.stored_page

    def comparisons(self) -> list[ComparisonSummary]:
        return [
            ComparisonSummary(g, r, c.payload["guild"]["title"], c.payload["reference"]["title"], c.generated_at)
            for (g, r), c in self.stored.items()
        ]

    def comparison(self, guild_report: str, reference_report: str) -> StoredComparison | None:
        return self.stored.get((guild_report, reference_report))
