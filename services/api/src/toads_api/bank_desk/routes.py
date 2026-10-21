"""The bank request desk's routes (docs/bank-desk.md).

- POST /api/bank-desk/requests                                   any member: ask for an item (the site, or the Toad
                                                                 Bot's `/bankrequest` acting for them)
- GET  /api/bank-desk/requests/mine                              any member: their own requests and answers
- GET  /api/days/{day}/bank-desk/requests?status=                officers: every request, newest first
- GET  /api/days/{day}/bank-desk/members/{discord_user_id}/requests   officers: one member's history
- POST /api/days/{day}/bank-desk/requests/{id}/approve|deny      officers: answer with a message the Toad Bot DMs

Officer routes need manage_bank on the route's raid day: that day's officers, the global tier, or a member a super admin
granted the bank's upkeep (docs/bank.md "Grants"). Requests do not belong to a raid night yet, so every night's officers
work the same desk. Discord user ids travel as strings: they exceed JavaScript's safe integers.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

import anyio
import structlog
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Path, Query, Request, status
from pydantic import BaseModel, Field

from toads_api.bank_desk.repository import BankRequestRecord, RequestStatus
from toads_api.bank_desk.service import ITEM_LIMIT, MAX_QUANTITY, MESSAGE_LIMIT, BankDeskError, BankDeskService
from toads_api.rbac.deps import ACTING_MEMBER_HEADER, get_services, require
from toads_api.rbac.permissions import Permission, Principal
from toads_api.services import Services

log = structlog.get_logger(__name__)


async def _day(day: str = Path(pattern=r"^[a-z0-9_-]{1,32}$")) -> str:
    return day


member = APIRouter(prefix="/api/bank-desk", tags=["bank desk"])
day_officer = APIRouter(
    prefix="/api/days/{day}/bank-desk", tags=["bank desk", "raid-day officers"], dependencies=[Depends(_day)]
)

Live = Annotated[Services, Depends(get_services)]
Viewer = Annotated[Principal, Depends(require(Permission.VIEW_BANK))]
Requester = Annotated[Principal, Depends(require(Permission.REQUEST_BANK_ITEMS))]
Officer = Annotated[Principal, Depends(require(Permission.MANAGE_BANK, scoped=True))]


def desk_of(live: Live) -> BankDeskService:
    return live.bank_desk


Desk = Annotated[BankDeskService, Depends(desk_of)]


class BankRequestIn(BaseModel):
    item: str = Field(min_length=1, max_length=ITEM_LIMIT)
    quantity: int = Field(ge=1, le=MAX_QUANTITY)


class AnswerIn(BaseModel):
    message: str = Field(default="", max_length=MESSAGE_LIMIT)


class BankRequestOut(BaseModel):
    id: int
    discord_user_id: str
    requester_name: str
    item: str
    quantity: int
    source: str
    status: RequestStatus
    created_at: datetime
    officer_message: str | None
    decided_by_name: str | None
    decided_at: datetime | None
    # Whether the Toad Bot has DMed the member the answer: queued, sent or failed; None while pending.
    notice: str | None
    notice_error: str | None


def _out(r: BankRequestRecord) -> BankRequestOut:
    return BankRequestOut(
        id=r.id,
        discord_user_id=str(r.discord_user_id),
        requester_name=r.requester_name,
        item=r.item,
        quantity=r.quantity,
        source=r.source,
        status=r.status,
        created_at=r.created_at,
        officer_message=r.officer_message,
        decided_by_name=r.decided_by_name,
        decided_at=r.decided_at,
        notice=None if r.notice is None else r.notice.value,
        notice_error=r.notice_error,
    )


def _refuse(exc: BankDeskError) -> HTTPException:
    return HTTPException(exc.status, detail=exc.message)


def _discord_id(principal: Principal) -> int:
    if principal.discord_user_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Your hub session has no Discord identity; sign in again")
    return principal.discord_user_id


# -------------------------------------------------------------------- member


@member.post("/requests", status_code=status.HTTP_201_CREATED)
async def ask(body: BankRequestIn, request: Request, principal: Requester, desk: Desk) -> BankRequestOut:
    source = "discord" if request.headers.get(ACTING_MEMBER_HEADER) is not None else "site"
    try:
        record = await anyio.to_thread.run_sync(
            desk.ask, _discord_id(principal), principal.display_name, body.item, body.quantity, source
        )
    except BankDeskError as exc:
        raise _refuse(exc) from None
    log.info("bank_desk.ask", request_id=record.id, source=source)
    return _out(record)


@member.get("/requests/mine")
async def mine(principal: Viewer, desk: Desk) -> list[BankRequestOut]:
    if principal.discord_user_id is None:
        return []  # Requests are kept by Discord id; a session without one has asked for nothing.
    return [_out(r) for r in await anyio.to_thread.run_sync(desk.history, principal.discord_user_id)]


# ------------------------------------------------------------------ officers


@day_officer.get("/requests")
async def incoming(
    day: str, _: Officer, desk: Desk, status_: Annotated[RequestStatus | None, Query(alias="status")] = None
) -> list[BankRequestOut]:
    return [_out(r) for r in await anyio.to_thread.run_sync(desk.requests, status_)]


@day_officer.get("/members/{discord_user_id}/requests")
async def member_history(
    day: str, discord_user_id: Annotated[str, Path(pattern=r"^[1-9]\d{0,19}$")], _: Officer, desk: Desk
) -> list[BankRequestOut]:
    return [_out(r) for r in await anyio.to_thread.run_sync(desk.history, int(discord_user_id))]


@day_officer.post("/requests/{request_id}/{verdict}")
async def answer(
    day: str,
    request_id: Annotated[int, Path(ge=1)],
    verdict: Literal["approve", "deny"],
    body: AnswerIn,
    principal: Officer,
    desk: Desk,
) -> BankRequestOut:
    decided = RequestStatus.APPROVED if verdict == "approve" else RequestStatus.DENIED
    try:
        record = await anyio.to_thread.run_sync(
            desk.decide, request_id, decided, body.message, principal.member_id, principal.display_name, day
        )
    except BankDeskError as exc:
        raise _refuse(exc) from None
    log.info("bank_desk.answer", request_id=record.id, status=record.status.value)
    return _out(record)


def include_bank_desk(app: FastAPI) -> None:
    for router in (member, day_officer):
        app.include_router(router)
