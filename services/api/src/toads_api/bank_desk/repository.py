"""Where bank desk requests live. BankDeskService only talks to the BankDeskRepository protocol; the hub-db backed
implementation is `sql.SqlBankDeskRepository`."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Protocol


class RequestStatus(enum.StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


class NoticeStatus(enum.StrEnum):
    """Whether the Toad Bot has DMed the member the officer's answer."""

    QUEUED = "queued"
    SENT = "sent"
    FAILED = "failed"


@dataclass(frozen=True)
class NewBankRequest:
    discord_user_id: int
    requester_name: str
    item: str
    quantity: int
    source: str
    at: datetime


@dataclass(frozen=True)
class Decision:
    status: RequestStatus
    message: str
    # The deciding officer's hub member id and name.
    decided_by: int
    decided_by_name: str
    at: datetime
    # The DM the Toad Bot sends the member.
    notice: str
    # The raid day whose officer route answered it, for the audit log.
    raid_day: str | None = None


@dataclass(frozen=True)
class BankRequestRecord:
    id: int
    discord_user_id: int
    requester_name: str
    item: str
    quantity: int
    source: str
    status: RequestStatus
    created_at: datetime
    officer_message: str | None = None
    decided_by_name: str | None = None
    decided_at: datetime | None = None
    # None until answered.
    notice: NoticeStatus | None = None
    notice_error: str | None = None


class BankDeskRepository(Protocol):
    def add(self, request: NewBankRequest) -> BankRequestRecord: ...

    def get(self, request_id: int) -> BankRequestRecord | None: ...

    def listed(
        self, status: RequestStatus | None = None, discord_user_id: int | None = None
    ) -> list[BankRequestRecord]:
        """Requests, newest first, optionally only those in one status or from one member."""
        ...

    def decide(self, request_id: int, decision: Decision) -> BankRequestRecord | None:
        """Answer a pending request and queue the Toad Bot's DM to the member, in one go. None when the request is no
        longer pending (another officer answered it first) or does not exist."""
        ...


@dataclass
class InMemoryBankDeskRepository:
    """For service tests; never use it outside tests."""

    rows: dict[int, BankRequestRecord] = field(default_factory=dict)
    notices: list[tuple[int, str]] = field(default_factory=list)

    def add(self, request: NewBankRequest) -> BankRequestRecord:
        record = BankRequestRecord(
            id=max(self.rows, default=0) + 1,
            discord_user_id=request.discord_user_id,
            requester_name=request.requester_name,
            item=request.item,
            quantity=request.quantity,
            source=request.source,
            status=RequestStatus.PENDING,
            created_at=request.at,
        )
        self.rows[record.id] = record
        return record

    def get(self, request_id: int) -> BankRequestRecord | None:
        return self.rows.get(request_id)

    def listed(
        self, status: RequestStatus | None = None, discord_user_id: int | None = None
    ) -> list[BankRequestRecord]:
        return [
            r
            for r in sorted(self.rows.values(), key=lambda r: r.id, reverse=True)
            if (status is None or r.status is status)
            and (discord_user_id is None or r.discord_user_id == discord_user_id)
        ]

    def decide(self, request_id: int, decision: Decision) -> BankRequestRecord | None:
        row = self.rows.get(request_id)
        if row is None or row.status is not RequestStatus.PENDING:
            return None
        self.notices.append((row.discord_user_id, decision.notice))
        decided = replace(
            row,
            status=decision.status,
            officer_message=decision.message or None,
            decided_by_name=decision.decided_by_name,
            decided_at=decision.at,
            notice=NoticeStatus.QUEUED,
        )
        self.rows[request_id] = decided
        return decided
