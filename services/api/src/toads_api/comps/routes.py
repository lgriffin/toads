"""Members' specs and the officers' comp builder (docs/comps.md).

- GET    /api/me/specs                     the caller's class and primary and secondary spec, or null
- PUT    /api/me/specs                     set them
- DELETE /api/me/specs                     clear them
- GET    /api/days/{day}/comps/pool        the raid day's roster with each member's specs (that day's officers), read
                                           from the Discord server's role holders at most every role refresh
- GET    /api/days/{day}/comps             the comps locked in for the raid day
- POST   /api/days/{day}/comps             lock in a new one
- PUT    /api/days/{day}/comps/{comp_id}   replace one
- DELETE /api/days/{day}/comps/{comp_id}   delete one
- POST   /api/days/{day}/comps/raid-helper pre-fill specs from a Raid-Helper export (that day's officers, or the Toad
                                           Bot acting for one: `/raidhelper import`)

The spec routes act on the caller's own member id, taken from the session, never from the request.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

import anyio
import structlog
from fastapi import APIRouter, Body, Depends, FastAPI, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from toads_api.comps import raid_helper
from toads_api.comps.repository import Seat, SpecRecord
from toads_api.comps.service import CompError, CompService, CompView, PoolEntry
from toads_api.discord_api import DiscordError
from toads_api.identity import member_ids_for, refresh_raid_rosters
from toads_api.rbac import Permission, Principal
from toads_api.rbac.deps import get_services, require

log = structlog.get_logger(__name__)
router = APIRouter(tags=["comps"])


def get_comps(request: Request) -> CompService:
    return get_services(request).comps


Comps = Annotated[CompService, Depends(get_comps)]
SignedIn = Annotated[Principal, Depends(require(Permission.VIEW_GUILD_RAIDS))]
DayOfficer = Annotated[Principal, Depends(require(Permission.BUILD_COMPS, scoped=True))]
SPEC_ID = r"^[a-z-]{1,32}$"


class SpecsIn(BaseModel):
    wow_class: str = Field(pattern=SPEC_ID)
    primary: str = Field(pattern=SPEC_ID)
    secondary: str | None = Field(default=None, pattern=SPEC_ID)


class SpecsOut(BaseModel):
    wow_class: str
    primary: str
    secondary: str | None
    # True while the specs are an officer's import (a Raid-Helper sign-up) the member has not confirmed or changed.
    imported: bool = False


class PoolEntryOut(BaseModel):
    member_id: int
    name: str
    wow_class: str | None
    primary: str | None
    secondary: str | None
    # False for a holder of the night's Discord role who has never signed in to the hub (so has no specs).
    signed_in: bool


class SeatIn(BaseModel):
    spec: str = Field(pattern=SPEC_ID)
    member_id: int | None = Field(default=None, gt=0)


class CompIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    size: int
    slots: list[SeatIn | None] = Field(max_length=40)


class SeatOut(BaseModel):
    spec: str
    member_id: int | None
    member_name: str | None


class CompOut(BaseModel):
    id: int
    raid_day: str
    name: str
    size: int
    slots: list[SeatOut | None]
    updated_by: str | None
    updated_at: datetime


class ImportRowOut(BaseModel):
    name: str
    # A string: Discord ids exceed JavaScript's safe integers. None for an open seat.
    discord_user_id: str | None
    wow_class: str | None
    spec: str | None
    # "added", "updated", "unchanged", "kept" (the member's own choice stays) or "skipped".
    outcome: str
    reason: str | None = None


class ImportOut(BaseModel):
    added: int
    updated: int
    unchanged: int
    kept: int
    skipped: int
    rows: list[ImportRowOut]


def _specs(r: SpecRecord | None) -> SpecsOut | None:
    if r is None:
        return None
    return SpecsOut(
        wow_class=r.wow_class, primary=r.primary, secondary=r.secondary, imported=r.imported_from is not None
    )


def _entry(e: PoolEntry) -> PoolEntryOut:
    return PoolEntryOut(
        member_id=e.member_id,
        name=e.name,
        wow_class=e.wow_class,
        primary=e.primary,
        secondary=e.secondary,
        signed_in=e.signed_in,
    )


def _comp(v: CompView) -> CompOut:
    return CompOut(
        id=v.id,
        raid_day=v.raid_day,
        name=v.name,
        size=v.size,
        slots=[
            None if s is None else SeatOut(spec=s.spec, member_id=s.member_id, member_name=s.member_name)
            for s in v.slots
        ],
        updated_by=v.updated_by,
        updated_at=v.updated_at,
    )


def _seats(body: CompIn) -> list[Seat | None]:
    return [None if s is None else Seat(s.spec, s.member_id) for s in body.slots]


def _refused(exc: CompError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.message)


@router.get("/api/me/specs")
async def my_specs(principal: SignedIn, comps: Comps) -> SpecsOut | None:
    return _specs(await anyio.to_thread.run_sync(comps.my_specs, principal.member_id))


@router.put("/api/me/specs")
async def set_my_specs(body: SpecsIn, principal: SignedIn, comps: Comps) -> SpecsOut | None:
    try:
        record = await anyio.to_thread.run_sync(
            comps.set_specs, principal.member_id, body.wow_class, body.primary, body.secondary
        )
    except CompError as exc:
        raise _refused(exc) from None
    return _specs(record)


@router.delete("/api/me/specs", status_code=status.HTTP_204_NO_CONTENT)
async def clear_my_specs(principal: SignedIn, comps: Comps) -> Response:
    await anyio.to_thread.run_sync(comps.clear_specs, principal.member_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/api/days/{day}/comps/pool")
async def comp_pool(day: str, principal: DayOfficer, comps: Comps, request: Request) -> list[PoolEntryOut]:
    # The night's role holders come from the server itself, so people who never signed in are listed too.
    await refresh_raid_rosters(get_services(request))
    return [_entry(e) for e in await anyio.to_thread.run_sync(comps.pool, day)]


@router.get("/api/days/{day}/comps")
async def list_comps(day: str, principal: DayOfficer, comps: Comps) -> list[CompOut]:
    return [_comp(v) for v in await anyio.to_thread.run_sync(comps.comps, day)]


async def _save(day: str, comp_id: int | None, body: CompIn, principal: Principal, comps: CompService) -> CompOut:
    try:
        view = await anyio.to_thread.run_sync(
            lambda: comps.save_comp(day, comp_id, body.name, body.size, _seats(body), principal.member_id)
        )
    except CompError as exc:
        raise _refused(exc) from None
    log.info("comp.saved", by=principal.member_id, raid_day=day, comp=view.id)
    return _comp(view)


@router.post("/api/days/{day}/comps", status_code=status.HTTP_201_CREATED)
async def create_comp(day: str, body: CompIn, principal: DayOfficer, comps: Comps) -> CompOut:
    return await _save(day, None, body, principal, comps)


@router.put("/api/days/{day}/comps/{comp_id}")
async def replace_comp(day: str, comp_id: int, body: CompIn, principal: DayOfficer, comps: Comps) -> CompOut:
    return await _save(day, comp_id, body, principal, comps)


@router.delete("/api/days/{day}/comps/{comp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comp(day: str, comp_id: int, principal: DayOfficer, comps: Comps) -> Response:
    try:
        await anyio.to_thread.run_sync(comps.delete_comp, day, comp_id, principal.member_id)
    except CompError as exc:
        raise _refused(exc) from None
    log.info("comp.deleted", by=principal.member_id, raid_day=day, comp=comp_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _skipped(s: raid_helper.Skipped) -> ImportRowOut:
    user = None if s.discord_user_id is None else str(s.discord_user_id)
    return ImportRowOut(
        name=s.name, discord_user_id=user, wow_class=None, spec=None, outcome="skipped", reason=s.reason
    )


@router.post("/api/days/{day}/comps/raid-helper")
async def import_raid_helper(
    day: str,
    export: Annotated[dict[str, Any], Body()],
    principal: DayOfficer,
    comps: Comps,
    request: Request,
) -> ImportOut:
    """Pre-fill the specs of everyone a Raid-Helper export seats (docs/comps.md "Importing from Raid-Helper"). Members
    are matched by Discord user id, so the names in the export do not matter, and anyone not in the server is
    skipped. Night membership and its badge stay with Discord roles."""
    try:
        signups, skipped = raid_helper.read_export(export)
    except raid_helper.ExportError as exc:
        raise HTTPException(422, detail=str(exc)) from None
    services = get_services(request)
    try:
        in_server = {m.user_id: m for m in await services.discord.guild_members()}
    except DiscordError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Discord is unavailable") from None
    found = [s for s in signups if s.discord_user_id in in_server]
    skipped += [
        raid_helper.Skipped(s.name, "Not in the Discord server", s.discord_user_id)
        for s in signups
        if s.discord_user_id not in in_server
    ]
    ids = await anyio.to_thread.run_sync(member_ids_for, services, [in_server[s.discord_user_id] for s in found])
    rows = [(ids[s.discord_user_id], s.name, s.wow_class, s.spec) for s in found]
    done = await anyio.to_thread.run_sync(
        lambda: comps.import_specs(rows, principal.member_id, day, raid_helper.SOURCE)
    )
    user_of = {member_id: user for user, member_id in ids.items()}
    out = [
        ImportRowOut(
            name=d.name,
            discord_user_id=str(user_of[d.member_id]),
            wow_class=d.wow_class,
            spec=d.spec,
            outcome=d.outcome,
            reason="They set their own specs on Me" if d.outcome == "kept" else None,
        )
        for d in done
    ] + [_skipped(s) for s in skipped]
    count = {k: sum(1 for d in done if d.outcome == k) for k in ("added", "updated", "unchanged", "kept")}
    log.info("comps.raid_helper_imported", by=principal.member_id, raid_day=day, skipped=len(skipped), **count)
    return ImportOut(**count, skipped=len(skipped), rows=out)


def include_comps(app: FastAPI) -> None:
    app.include_router(router)
