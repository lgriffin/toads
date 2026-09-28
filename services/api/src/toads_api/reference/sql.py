"""ReferenceRepository over hub-db."""

from __future__ import annotations

from typing import Any

from hub_db import CredentialCipher, Member, ReferenceComparison, ReferenceJob, ReferenceLogin, ReferencePage
from hub_db.reference import (
    LOGIN_ROW,
    PAGE_ROW,
    JobKind,
    JobStatus,
    LoginToken,
    create_job,
    delete_login,
    recent_jobs,
    save_login,
    update_job,
)
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from toads_api.reference.repository import (
    ComparisonSummary,
    Job,
    LoginInfo,
    StoredComparison,
    StoredPage,
    UserToken,
)


def _job(row: ReferenceJob) -> Job:
    return Job(
        id=row.id,
        kind=row.kind,
        status=row.status,
        raid_day=row.raid_day,
        params=dict(row.params),
        message=row.message,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlReferenceRepository:
    def __init__(self, db: sessionmaker[Session], cipher: CredentialCipher) -> None:
        self._db = db
        self._cipher = cipher

    def login_info(self) -> LoginInfo:
        with self._db() as db:
            row = db.get(ReferenceLogin, LOGIN_ROW)
            if row is None:
                return LoginInfo(connected=False)
            member = db.get(Member, row.connected_by) if row.connected_by is not None else None
            return LoginInfo(
                connected=True,
                status=row.status,
                connected_by=member.display_name if member is not None else None,
                connected_at=row.connected_at,
            )

    def save_login(self, token: UserToken, member_id: int) -> None:
        with self._db.begin() as db:
            save_login(
                db, self._cipher, LoginToken(token.access_token, token.refresh_token, token.expires_at), member_id
            )

    def delete_login(self) -> bool:
        with self._db.begin() as db:
            return delete_login(db)

    def create_job(self, kind: str, raid_day: str, member_id: int, params: dict[str, Any]) -> Job:
        with self._db.begin() as db:
            return _job(create_job(db, JobKind(kind), raid_day, member_id, params))

    def fail_job(self, job_id: str, message: str) -> None:
        with self._db.begin() as db:
            update_job(db, job_id, JobStatus.FAILED, message)

    def recent_jobs(self, limit: int) -> list[Job]:
        with self._db() as db:
            return [_job(r) for r in recent_jobs(db, limit)]

    def page(self) -> StoredPage | None:
        with self._db() as db:
            row = db.get(ReferencePage, PAGE_ROW)
            return None if row is None else StoredPage(row.generated_at, list(row.references), list(row.guild_raids))

    def comparisons(self) -> list[ComparisonSummary]:
        with self._db() as db:
            rows = db.scalars(select(ReferenceComparison).order_by(ReferenceComparison.updated_at.desc()))
            return [
                ComparisonSummary(r.guild_report, r.reference_report, r.guild_title, r.reference_title, r.generated_at)
                for r in rows
            ]

    def comparison(self, guild_report: str, reference_report: str) -> StoredComparison | None:
        with self._db() as db:
            row = db.scalar(
                select(ReferenceComparison).where(
                    ReferenceComparison.guild_report == guild_report,
                    ReferenceComparison.reference_report == reference_report,
                )
            )
            return None if row is None else StoredComparison(row.generated_at, dict(row.payload))
