"""The officers' task board (docs/officer-board.md). Every route is scoped to the raid day in its path: that day's
officers, global officers and super admins only (MANAGE_OFFICER_BOARD), never a sibling day's officers.

- GET    /api/days/{day}/board                         the day's board: lanes, cards and who can be assigned
- POST   /api/days/{day}/board/cards                   add a card
- PUT    /api/days/{day}/board/cards/{card_id}         rewrite a card's title, notes, assignee and due date
- POST   /api/days/{day}/board/cards/{card_id}/move    move a card to a lane and a place in it
- DELETE /api/days/{day}/board/cards/{card_id}         take a card off the board
- GET    /api/days/{day}/links                         the links pinned to the night (strategy doc, role sheet)
- POST   /api/days/{day}/links                         pin a link
- DELETE /api/days/{day}/links/{link_id}               unpin a link
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

import anyio
import structlog
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Path, Request, Response, status
from pydantic import BaseModel, Field

from toads_api.officer_board.repository import NightLink
from toads_api.officer_board.service import (
    LANES,
    LINK_LABEL_LIMIT,
    LINK_URL_LIMIT,
    NOTES_LIMIT,
    TITLE_LIMIT,
    BoardError,
    CardView,
    Lane,
    OfficerBoardService,
)
from toads_api.rbac import Permission, Principal
from toads_api.rbac.deps import get_services, require
from toads_api.services import Services

log = structlog.get_logger(__name__)
router = APIRouter(tags=["officer-board"])


def get_board(request: Request) -> OfficerBoardService:
    return get_services(request).officer_board


Board = Annotated[OfficerBoardService, Depends(get_board)]
Hub = Annotated[Services, Depends(get_services)]
Officer = Annotated[Principal, Depends(require(Permission.MANAGE_OFFICER_BOARD, scoped=True))]
CardId = Annotated[int, Path(gt=0, lt=2**31)]
LANE = "^(" + "|".join(LANES) + ")$"


class CardOut(BaseModel):
    id: int
    lane: str
    title: str
    notes: str
    assignee_member_id: int | None
    assignee_name: str | None
    due_on: date | None
    overdue: bool
    updated_at: datetime


class LaneOut(BaseModel):
    id: str
    name: str
    cards: list[CardOut]


class AssigneeOut(BaseModel):
    member_id: int
    display_name: str


class BoardOut(BaseModel):
    raid_day: str
    lanes: list[LaneOut]
    # Everyone a card can be given to: every member who has signed in to the hub, by the name they chose.
    assignees: list[AssigneeOut]


class CardIn(BaseModel):
    title: str = Field(min_length=1, max_length=TITLE_LIMIT)
    notes: str = Field(default="", max_length=NOTES_LIMIT)
    assignee_member_id: int | None = Field(default=None, gt=0, lt=2**31)
    due_on: date | None = None


class NewCardIn(CardIn):
    lane: str = Field(default="todo", pattern=LANE)


class MoveIn(BaseModel):
    lane: str = Field(pattern=LANE)
    position: int = Field(ge=0, le=1000)


class LinkOut(BaseModel):
    id: int
    label: str
    url: str


class LinkIn(BaseModel):
    label: str = Field(min_length=1, max_length=LINK_LABEL_LIMIT)
    url: str = Field(min_length=1, max_length=LINK_URL_LIMIT)


def _link(x: NightLink) -> LinkOut:
    return LinkOut(id=x.id, label=x.label, url=x.url)


def _card(v: CardView) -> CardOut:
    c = v.card
    return CardOut(
        id=c.id,
        lane=c.lane,
        title=c.fields.title,
        notes=c.fields.notes,
        assignee_member_id=c.fields.assignee_member_id,
        assignee_name=v.assignee_name,
        due_on=c.fields.due_on,
        overdue=v.overdue,
        updated_at=c.updated_at,
    )


def _lanes(lanes: list[Lane]) -> list[LaneOut]:
    return [LaneOut(id=lane.id, name=lane.name, cards=[_card(v) for v in lane.cards]) for lane in lanes]


def _refused(exc: BoardError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.message)


def _whole_board(board: OfficerBoardService, services: Services, day: str) -> BoardOut:
    assignees = [AssigneeOut(member_id=e.member_id, display_name=e.shown_name) for e in services.account.directory()]
    return BoardOut(raid_day=day, lanes=_lanes(board.board(day)), assignees=assignees)


@router.get("/api/days/{day}/board")
async def officer_board(day: str, principal: Officer, board: Board, services: Hub) -> BoardOut:
    return await anyio.to_thread.run_sync(_whole_board, board, services, day)


@router.post("/api/days/{day}/board/cards", status_code=status.HTTP_201_CREATED)
async def add_card(day: str, body: NewCardIn, principal: Officer, board: Board) -> CardOut:
    try:
        view = await anyio.to_thread.run_sync(
            lambda: board.add(
                day,
                title=body.title,
                notes=body.notes,
                assignee=body.assignee_member_id,
                due_on=body.due_on,
                lane=body.lane,
                by=principal.member_id,
            )
        )
    except BoardError as exc:
        raise _refused(exc) from None
    log.info("board.card_added", by=principal.member_id, day=day, card=view.card.id)
    return _card(view)


@router.put("/api/days/{day}/board/cards/{card_id}")
async def edit_card(day: str, card_id: CardId, body: CardIn, principal: Officer, board: Board) -> CardOut:
    try:
        view = await anyio.to_thread.run_sync(
            lambda: board.edit(
                day,
                card_id,
                title=body.title,
                notes=body.notes,
                assignee=body.assignee_member_id,
                due_on=body.due_on,
                by=principal.member_id,
            )
        )
    except BoardError as exc:
        raise _refused(exc) from None
    return _card(view)


@router.post("/api/days/{day}/board/cards/{card_id}/move")
async def move_card(day: str, card_id: CardId, body: MoveIn, principal: Officer, board: Board) -> list[LaneOut]:
    try:
        lanes = await anyio.to_thread.run_sync(
            lambda: board.move(day, card_id, lane=body.lane, position=body.position, by=principal.member_id)
        )
    except BoardError as exc:
        raise _refused(exc) from None
    return _lanes(lanes)


@router.delete("/api/days/{day}/board/cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_card(day: str, card_id: CardId, principal: Officer, board: Board) -> Response:
    try:
        await anyio.to_thread.run_sync(board.remove, day, card_id, principal.member_id)
    except BoardError as exc:
        raise _refused(exc) from None
    log.info("board.card_removed", by=principal.member_id, day=day, card=card_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/api/days/{day}/links")
async def night_links(day: str, principal: Officer, board: Board) -> list[LinkOut]:
    return [_link(x) for x in await anyio.to_thread.run_sync(board.links, day)]


@router.post("/api/days/{day}/links", status_code=status.HTTP_201_CREATED)
async def pin_link(day: str, body: LinkIn, principal: Officer, board: Board) -> LinkOut:
    try:
        link = await anyio.to_thread.run_sync(
            lambda: board.add_link(day, label=body.label, url=body.url, by=principal.member_id)
        )
    except BoardError as exc:
        raise _refused(exc) from None
    log.info("board.link_pinned", by=principal.member_id, day=day, link=link.id)
    return _link(link)


@router.delete("/api/days/{day}/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unpin_link(day: str, link_id: CardId, principal: Officer, board: Board) -> Response:
    try:
        await anyio.to_thread.run_sync(board.remove_link, day, link_id, principal.member_id)
    except BoardError as exc:
        raise _refused(exc) from None
    log.info("board.link_unpinned", by=principal.member_id, day=day, link=link_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def include_officer_board(app: FastAPI) -> None:
    app.include_router(router)
