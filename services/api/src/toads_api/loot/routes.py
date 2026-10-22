"""Officers' loot priority (docs/loot.md). Every route is scoped to the raid day in its path: that day's officers,
global officers and super admins only (MANAGE_LOOT), never a sibling day's officers.

- GET    /api/days/{day}/loot                                       the night's loot list and its raid group
- GET    /api/days/{day}/loot/items?q=                              search the item catalogue by name
- POST   /api/days/{day}/loot                                       put an item on the list
- PUT    /api/days/{day}/loot/{entry_id}                            rewrite the item's note
- PUT    /api/days/{day}/loot/{entry_id}/line                       rank who is in line for it, first to last
- PUT    /api/days/{day}/loot/{entry_id}/line/{member_id}/received  mark one of them received, or not
- DELETE /api/days/{day}/loot/{entry_id}                            take the item off the list
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

import anyio
import structlog
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Path, Query, Request, Response, status
from pydantic import BaseModel, Field

from toads_api.identity import refresh_raid_rosters
from toads_api.loot.catalogue import MIN_QUERY, SEARCH_LIMIT, CatalogueItem
from toads_api.loot.service import LINE_LIMIT, NOTE_LIMIT, LootError, LootService, LootView
from toads_api.rbac import Permission, Principal
from toads_api.rbac.deps import get_services, require
from toads_api.services import Services

log = structlog.get_logger(__name__)
router = APIRouter(tags=["loot"])


def get_loot(request: Request) -> LootService:
    return get_services(request).loot


Loot = Annotated[LootService, Depends(get_loot)]
Hub = Annotated[Services, Depends(get_services)]
Officer = Annotated[Principal, Depends(require(Permission.MANAGE_LOOT, scoped=True))]
RowId = Annotated[int, Path(gt=0, lt=2**31)]


class ItemOut(BaseModel):
    id: int
    name: str
    quality: int
    item_level: int
    slot: str
    # "Forever", or "Vanilla" for an item only Classic's data has.
    flavour: str


class RecipientOut(BaseModel):
    member_id: int
    rank: int
    name: str
    received_at: datetime | None
    next_up: bool


class EntryOut(BaseModel):
    id: int
    item_id: int
    # The canonical name the item had when it was added.
    item_name: str
    # -1 when the catalogue no longer knows the item.
    quality: int
    item_level: int
    slot: str
    note: str
    recipients: list[RecipientOut]
    updated_at: datetime


class RosterOut(BaseModel):
    member_id: int
    name: str
    wow_class: str | None


class LootOut(BaseModel):
    raid_day: str
    items: list[EntryOut]
    # Who can be put in line: the night's raid group, by the name each chose.
    roster: list[RosterOut]
    # Where the item data comes from ("LibItemDB ItemDB-v1.7.0, Forever enUS: ...").
    catalogue: str


class AddIn(BaseModel):
    item_id: int = Field(gt=0, lt=2**31)
    note: str = Field(default="", max_length=NOTE_LIMIT)


class NoteIn(BaseModel):
    note: str = Field(default="", max_length=NOTE_LIMIT)


class LineIn(BaseModel):
    member_ids: list[Annotated[int, Field(gt=0, lt=2**31)]] = Field(max_length=LINE_LIMIT)


class ReceivedIn(BaseModel):
    received: bool


def _item(i: CatalogueItem) -> ItemOut:
    return ItemOut(id=i.id, name=i.name, quality=i.quality, item_level=i.item_level, slot=i.slot, flavour=i.flavour)


def _entry(v: LootView) -> EntryOut:
    e = v.entry
    return EntryOut(
        id=e.id,
        item_id=e.item_id,
        item_name=e.item_name,
        quality=v.item.quality if v.item else -1,
        item_level=v.item.item_level if v.item else -1,
        slot=v.item.slot if v.item else "",
        note=e.note,
        recipients=[
            RecipientOut(member_id=r.member_id, rank=r.rank, name=r.name, received_at=r.received_at, next_up=r.next_up)
            for r in v.recipients
        ],
        updated_at=e.updated_at,
    )


def _refused(exc: LootError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.message)


def _whole(loot: LootService, services: Services, day: str) -> LootOut:
    roster = [RosterOut(member_id=e.member_id, name=e.name, wow_class=e.wow_class) for e in services.comps.pool(day)]
    return LootOut(
        raid_day=day, items=[_entry(v) for v in loot.loot(day)], roster=roster, catalogue=loot.catalogue.source
    )


@router.get("/api/days/{day}/loot")
async def night_loot(day: str, principal: Officer, loot: Loot, services: Hub) -> LootOut:
    # The raid group is the night's Discord role holders; make sure members the hub has not met yet are on it.
    await refresh_raid_rosters(services)
    return await anyio.to_thread.run_sync(_whole, loot, services, day)


@router.get("/api/days/{day}/loot/items")
async def search_items(
    day: str,
    principal: Officer,
    loot: Loot,
    q: Annotated[str, Query(min_length=MIN_QUERY, max_length=80)],
    limit: Annotated[int, Query(ge=1, le=SEARCH_LIMIT)] = SEARCH_LIMIT,
) -> list[ItemOut]:
    return [_item(i) for i in await anyio.to_thread.run_sync(loot.search, q, limit)]


@router.post("/api/days/{day}/loot", status_code=status.HTTP_201_CREATED)
async def add_item(day: str, body: AddIn, principal: Officer, loot: Loot) -> EntryOut:
    try:
        view = await anyio.to_thread.run_sync(
            lambda: loot.add(day, item_id=body.item_id, note=body.note, by=principal.member_id)
        )
    except LootError as exc:
        raise _refused(exc) from None
    log.info("loot.item_added", by=principal.member_id, day=day, item=body.item_id)
    return _entry(view)


@router.put("/api/days/{day}/loot/{entry_id}")
async def edit_note(day: str, entry_id: RowId, body: NoteIn, principal: Officer, loot: Loot) -> EntryOut:
    try:
        view = await anyio.to_thread.run_sync(
            lambda: loot.set_note(day, entry_id, note=body.note, by=principal.member_id)
        )
    except LootError as exc:
        raise _refused(exc) from None
    return _entry(view)


@router.put("/api/days/{day}/loot/{entry_id}/line")
async def set_line(day: str, entry_id: RowId, body: LineIn, principal: Officer, loot: Loot) -> EntryOut:
    try:
        view = await anyio.to_thread.run_sync(
            lambda: loot.set_line(day, entry_id, member_ids=body.member_ids, by=principal.member_id)
        )
    except LootError as exc:
        raise _refused(exc) from None
    return _entry(view)


@router.put("/api/days/{day}/loot/{entry_id}/line/{member_id}/received")
async def mark_received(
    day: str, entry_id: RowId, member_id: RowId, body: ReceivedIn, principal: Officer, loot: Loot
) -> EntryOut:
    try:
        view = await anyio.to_thread.run_sync(
            lambda: loot.mark(day, entry_id, member_id, received=body.received, by=principal.member_id)
        )
    except LootError as exc:
        raise _refused(exc) from None
    log.info("loot.received", by=principal.member_id, day=day, entry=entry_id, member=member_id, received=body.received)
    return _entry(view)


@router.delete("/api/days/{day}/loot/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_item(day: str, entry_id: RowId, principal: Officer, loot: Loot) -> Response:
    try:
        await anyio.to_thread.run_sync(loot.remove, day, entry_id, principal.member_id)
    except LootError as exc:
        raise _refused(exc) from None
    log.info("loot.item_removed", by=principal.member_id, day=day, entry=entry_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def include_loot(app: FastAPI) -> None:
    app.include_router(router)
