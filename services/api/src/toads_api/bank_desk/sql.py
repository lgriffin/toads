"""BankDeskRepository over hub-db. Answering a request writes the answer, the Toad Bot's DM job (bot_outbox) and the
audit entry in one transaction, so a member is never told about an answer that was not kept, or left untold."""

from __future__ import annotations

from datetime import UTC, datetime

from hub_db import BankItemRequest, BotOutbox, CommunityId
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from toads_api import audit
from toads_api.bank_desk.repository import (
    BankRequestRecord,
    Decision,
    NewBankRequest,
    NoticeStatus,
    RequestStatus,
)

# The Toad Bot's outbox job that DMs a member (community OutboxKind.SEND_DM).
SEND_DM = "send_dm"


def _aware(at: datetime | None) -> datetime | None:
    """SQLite hands back naive datetimes; every time stored here is UTC."""
    return at if at is None or at.tzinfo is not None else at.replace(tzinfo=UTC)


def _notice(job: BotOutbox | None) -> tuple[NoticeStatus | None, str | None]:
    if job is None:
        return None, None
    if not job.done:
        return NoticeStatus.QUEUED, None
    error = job.payload.get("error") if isinstance(job.payload, dict) else None
    return (NoticeStatus.FAILED, str(error)) if error else (NoticeStatus.SENT, None)


def _record(row: BankItemRequest, job: BotOutbox | None) -> BankRequestRecord:
    notice, error = _notice(job)
    return BankRequestRecord(
        id=row.id,
        discord_user_id=row.discord_user_id,
        requester_name=row.requester_name,
        item=row.item,
        quantity=row.quantity,
        source=row.source,
        status=RequestStatus(row.status),
        created_at=_aware(row.created_at) or datetime.now(UTC),
        officer_message=row.officer_message,
        decided_by_name=row.decided_by_name,
        decided_at=_aware(row.decided_at),
        notice=notice,
        notice_error=error,
    )


class SqlBankDeskRepository:
    def __init__(self, db: sessionmaker[Session]) -> None:
        self._db = db

    def add(self, request: NewBankRequest) -> BankRequestRecord:
        with self._db.begin() as db:
            row = BankItemRequest(
                discord_user_id=request.discord_user_id,
                requester_name=request.requester_name,
                item=request.item,
                quantity=request.quantity,
                source=request.source,
                status=RequestStatus.PENDING.value,
                created_at=request.at,
            )
            db.add(row)
            db.flush()
            return _record(row, None)

    def get(self, request_id: int) -> BankRequestRecord | None:
        with self._db() as db:
            row = db.get(BankItemRequest, request_id)
            return None if row is None else self._with_job(db, row)

    @staticmethod
    def _with_job(db: Session, row: BankItemRequest) -> BankRequestRecord:
        return _record(row, db.get(BotOutbox, row.notice_job_id) if row.notice_job_id is not None else None)

    def listed(
        self, status: RequestStatus | None = None, discord_user_id: int | None = None
    ) -> list[BankRequestRecord]:
        query = select(BankItemRequest, BotOutbox).outerjoin(BotOutbox, BotOutbox.id == BankItemRequest.notice_job_id)
        if status is not None:
            query = query.where(BankItemRequest.status == status.value)
        if discord_user_id is not None:
            query = query.where(BankItemRequest.discord_user_id == discord_user_id)
        with self._db() as db:
            rows = db.execute(query.order_by(BankItemRequest.id.desc())).all()
            return [_record(row, job) for row, job in rows]

    def decide(self, request_id: int, decision: Decision) -> BankRequestRecord | None:
        with self._db.begin() as db:
            row = db.get(BankItemRequest, request_id, with_for_update=True)
            if row is None or row.status != RequestStatus.PENDING.value:
                return None
            # Job ids come from the community id sequence, as every other outbox job's do.
            job_id = CommunityId()
            db.add(job_id)
            db.flush()
            job = BotOutbox(
                id=job_id.id,
                kind=SEND_DM,
                payload={
                    "discord_user_id": str(row.discord_user_id),
                    "content": decision.notice,
                    "bank_request_id": row.id,
                },
                done=False,
                created_at=decision.at,
            )
            db.add(job)
            row.status = decision.status.value
            row.officer_message = decision.message or None
            row.decided_by = decision.decided_by
            row.decided_by_name = decision.decided_by_name
            row.decided_at = decision.at
            row.notice_job_id = job.id
            audit.record(
                db,
                actor=decision.decided_by,
                action=f"bank_desk.{'approve' if decision.status is RequestStatus.APPROVED else 'deny'}",
                target=f"bank request {row.id}: {row.quantity} x {row.item} for discord user {row.discord_user_id}",
                raid_day=decision.raid_day,
                detail=decision.message or None,
            )
            db.flush()
            return _record(row, job)
