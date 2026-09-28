"""Reference comparison: the dedicated Warcraft Logs login, officers' queued requests, and what the worker built.

Officers compare one of the guild's raids with another guild's ("reference") raid. Reading another guild's report
needs a user-scoped Warcraft Logs token, so one officer connects a Warcraft Logs account for the whole guild: the
dedicated login. Its token is stored encrypted like members' own keys (MultiFernet, bound to a fixed owner id so a
ciphertext copied from a member's key never reads as the login).

The API writes the login and queues jobs; the worker (which owns every other Warcraft Logs call) runs the jobs with
wcl-app's ReferenceService, refreshes the token, and stores the lists and comparisons the API serves. The analyzer's
own tables (raids and their per-player rows) stay in wcl-store.
"""

from __future__ import annotations

import enum
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint, delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from hub_db.credentials import CredentialCipher
from hub_db.models import Base

# The login is guild-wide: one row, encrypted for this owner id (member ids start at 1).
LOGIN_ROW = 1
_LOGIN_OWNER = 0
PAGE_ROW = 1
# Comparisons and jobs are kept for the newest few only; older ones are rebuilt on request.
MAX_COMPARISONS = 30
MAX_JOBS = 100


def _now() -> datetime:
    return datetime.now(UTC)


class LoginStatus(enum.StrEnum):
    WORKING = "working"
    # Warcraft Logs refused to refresh the token: an officer must connect the account again.
    EXPIRED = "expired"


class JobKind(enum.StrEnum):
    IMPORT = "import"
    COMPARE = "compare"
    LABEL = "label"
    DELETE = "delete"


class JobStatus(enum.StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class ReferenceLogin(Base):
    __tablename__ = "reference_login"

    id: Mapped[int] = mapped_column(primary_key=True)
    token_encrypted: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default=LoginStatus.WORKING.value)
    connected_by: Mapped[int | None] = mapped_column(ForeignKey("members.id", ondelete="SET NULL"))
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    refreshed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReferenceJob(Base):
    """An officer's request the worker carries out: import, compare, label or delete."""

    __tablename__ = "reference_jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default=JobStatus.QUEUED.value)
    raid_day: Mapped[str] = mapped_column(String(32))
    requested_by: Mapped[int | None] = mapped_column(ForeignKey("members.id", ondelete="SET NULL"))
    params: Mapped[dict[str, Any]] = mapped_column(JSON)
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ReferencePage(Base):
    """The stored raids an officer picks from, as the worker last listed them: one row."""

    __tablename__ = "reference_pages"

    id: Mapped[int] = mapped_column(primary_key=True)
    generated_at: Mapped[str] = mapped_column(String(40))
    references: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    guild_raids: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ReferenceComparison(Base):
    """One built comparison: wcl-app's ReferenceComparison.to_dict(), stored as the worker built it."""

    __tablename__ = "reference_comparisons"
    __table_args__ = (UniqueConstraint("guild_report", "reference_report", name="uq_reference_comparisons_pair"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_report: Mapped[str] = mapped_column(String(32))
    reference_report: Mapped[str] = mapped_column(String(32))
    guild_title: Mapped[str] = mapped_column(String(200))
    reference_title: Mapped[str] = mapped_column(String(200))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    generated_at: Mapped[str] = mapped_column(String(40))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)


# ── The login ──


@dataclass(frozen=True)
class LoginToken:
    """The decrypted user token. repr hides it so it cannot reach a log line by accident."""

    access_token: str
    refresh_token: str | None
    # Epoch seconds.
    expires_at: float

    def __repr__(self) -> str:
        return f"LoginToken(expires_at={self.expires_at})"


def _encrypt(cipher: CredentialCipher, token: LoginToken) -> str:
    plain = {"access_token": token.access_token, "refresh_token": token.refresh_token, "expires_at": token.expires_at}
    return cipher.encrypt(_LOGIN_OWNER, json.dumps(plain))


def save_login(db: Session, cipher: CredentialCipher, token: LoginToken, member_id: int | None) -> None:
    """Connect (or reconnect) the account, recording which officer did it."""
    row = db.get(ReferenceLogin, LOGIN_ROW)
    if row is None:
        try:
            with db.begin_nested():
                db.add(ReferenceLogin(id=LOGIN_ROW, token_encrypted=_encrypt(cipher, token), connected_by=member_id))
            return
        except IntegrityError:
            row = db.get(ReferenceLogin, LOGIN_ROW, populate_existing=True)
            if row is None:
                raise
    row.token_encrypted = _encrypt(cipher, token)
    row.status = LoginStatus.WORKING.value
    row.connected_by = member_id
    row.connected_at = _now()
    row.refreshed_at = None
    db.flush()


def load_login(db: Session, cipher: CredentialCipher) -> LoginToken | None:
    """The token, or None when nobody has connected. Raises CredentialDecryptError when it cannot be read."""
    row = db.get(ReferenceLogin, LOGIN_ROW)
    if row is None or row.status == LoginStatus.EXPIRED.value:
        return None
    data = json.loads(cipher.decrypt(_LOGIN_OWNER, row.token_encrypted))
    return LoginToken(str(data["access_token"]), data.get("refresh_token"), float(data.get("expires_at", 0)))


def store_refreshed_login(db: Session, cipher: CredentialCipher, token: LoginToken) -> None:
    """Keep a token the worker refreshed; Warcraft Logs may have rotated the refresh token."""
    row = db.get(ReferenceLogin, LOGIN_ROW)
    if row is not None:
        row.token_encrypted = _encrypt(cipher, token)
        row.status = LoginStatus.WORKING.value
        row.refreshed_at = _now()


def mark_login_expired(db: Session) -> None:
    row = db.get(ReferenceLogin, LOGIN_ROW)
    if row is not None:
        row.status = LoginStatus.EXPIRED.value


def delete_login(db: Session) -> bool:
    row = db.get(ReferenceLogin, LOGIN_ROW)
    if row is None:
        return False
    db.delete(row)
    db.flush()
    return True


# ── Jobs ──


def create_job(
    db: Session, kind: JobKind, raid_day: str, member_id: int | None, params: dict[str, Any]
) -> ReferenceJob:
    job = ReferenceJob(
        id=uuid.uuid4().hex, kind=kind.value, raid_day=raid_day, requested_by=member_id, params=params, message=""
    )
    db.add(job)
    db.flush()
    _prune(db, ReferenceJob, ReferenceJob.created_at, MAX_JOBS)
    return job


def update_job(db: Session, job_id: str, status: JobStatus, message: str = "") -> ReferenceJob | None:
    job = db.get(ReferenceJob, job_id)
    if job is not None:
        job.status = status.value
        job.message = message[:500]
        job.updated_at = _now()
    return job


def recent_jobs(db: Session, limit: int = 10) -> list[ReferenceJob]:
    return list(db.scalars(select(ReferenceJob).order_by(ReferenceJob.created_at.desc()).limit(limit)))


# ── What the worker built ──


def save_page(
    db: Session, generated_at: str, references: list[dict[str, Any]], guild_raids: list[dict[str, Any]]
) -> None:
    row = db.get(ReferencePage, PAGE_ROW)
    if row is None:
        row = ReferencePage(id=PAGE_ROW)
        db.add(row)
    row.generated_at = generated_at
    row.references = references
    row.guild_raids = guild_raids
    row.updated_at = _now()


def save_comparison(db: Session, payload: dict[str, Any], generated_at: str) -> None:
    guild, ref = payload["guild"], payload["reference"]
    row = db.scalar(
        select(ReferenceComparison).where(
            ReferenceComparison.guild_report == guild["report_id"],
            ReferenceComparison.reference_report == ref["report_id"],
        )
    )
    if row is None:
        row = ReferenceComparison(guild_report=guild["report_id"], reference_report=ref["report_id"])
        db.add(row)
    row.guild_title = str(guild["title"])[:200]
    row.reference_title = str(ref["title"])[:200]
    row.payload = payload
    row.generated_at = generated_at
    row.updated_at = _now()
    db.flush()
    _prune(db, ReferenceComparison, ReferenceComparison.updated_at, MAX_COMPARISONS)


def delete_comparisons_of(db: Session, report_id: str) -> None:
    """Forget comparisons with a raid that was deleted."""
    db.execute(
        delete(ReferenceComparison).where(
            (ReferenceComparison.guild_report == report_id) | (ReferenceComparison.reference_report == report_id)
        )
    )


def _prune(db: Session, model: type[ReferenceJob] | type[ReferenceComparison], newest: Any, keep: int) -> None:
    stale = list(db.scalars(select(model).order_by(newest.desc()).offset(keep)))
    for row in stale:
        db.delete(row)
