"""The bank's routes: the hub's face of toadsbank-api (docs/bank.md). Every member route declares its permission; the
hub decides who reaches a route and ToadsBank still applies a source's audience and its managers list.

- /api/bank/*                    members: sources, replica, inventory, their own requests (and the bot acting for one)
- /api/days/{day}/bank/*         that raid day's officers (and the global tier): imports and the request queue
- /api/admin/bank/*              the global tier only: registering and editing sources
- POST /api/bank/events          ToadsBank's worker, with the bank's service token

Mutating routes need an `Idempotency-Key` header. The hub never forwards it as sent: it derives the key it gives
ToadsBank from the member, the route and that header, so one member's key can never replay another's answer.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Annotated, Any, Literal

import structlog
from fastapi import APIRouter, Depends, FastAPI, Header, Path, Query, Request, status
from fastapi.responses import JSONResponse

from toads_api.bank.client import BankClient, BankError, BankIdentity, not_configured
from toads_api.bank.events import BankEvent
from toads_api.bank.schemas import (
    ID,
    BankMe,
    Decision,
    Delivery,
    EventAck,
    PartsIn,
    RequestCreate,
    Revision,
    SourceCreate,
    SourcePatch,
)
from toads_api.rbac.deps import get_services, require
from toads_api.rbac.permissions import HubRole, Permission, Principal
from toads_api.services import Services

log = structlog.get_logger(__name__)

# ToadsBank retries an event for up to 24 hours; remember ids for a week.
EVENT_MEMORY_SECONDS = 7 * 24 * 3600
# The hub's own refusal when an officer route's raid day does not own the bank it would touch.
NOT_THIS_DAY = "not_this_day"


async def _day(day: str = Path(pattern=r"^[a-z0-9_-]{1,32}$")) -> str:
    return day


member = APIRouter(prefix="/api/bank", tags=["bank"])
day_officer = APIRouter(prefix="/api/days/{day}/bank", tags=["bank", "raid-day officers"], dependencies=[Depends(_day)])
global_admin = APIRouter(prefix="/api/admin/bank", tags=["bank", "global officers"])
events = APIRouter(prefix="/api/bank", tags=["bank"])

_VIEW = require(Permission.VIEW_BANK)
_REQUEST = require(Permission.REQUEST_BANK_ITEMS)
_IMPORT = require(Permission.IMPORT_BANK_SNAPSHOT, scoped=True)
_MANAGE = require(Permission.MANAGE_BANK, scoped=True)
_ADMIN = require(Permission.MANAGE_BANK)

Live = Annotated[Services, Depends(get_services)]
Viewer = Annotated[Principal, Depends(_VIEW)]
Requester = Annotated[Principal, Depends(_REQUEST)]
Importer = Annotated[Principal, Depends(_IMPORT)]
Manager = Annotated[Principal, Depends(_MANAGE)]
Admin = Annotated[Principal, Depends(_ADMIN)]
Key = Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)]
Id = Annotated[str, Path(pattern=ID)]


# ------------------------------------------------------------------ adapters


def identity_of(principal: Principal) -> BankIdentity:
    """The X-Toads-* identity for a member: always `member`, `officer` when they hold officer powers anywhere, `admin`
    for the global tier."""
    if principal.discord_user_id is None:
        raise BankError(403, "forbidden", "Your hub session has no Discord identity; sign in again")
    roles = ["member"]
    if principal.is_officer:
        roles.append("officer")
    if principal.global_officer:
        roles.append("admin")
    return BankIdentity(principal.discord_user_id, principal.display_name, tuple(roles))


def bank_of(services: Services) -> BankClient:
    if services.bank is None:
        raise not_configured()
    return services.bank


def derive_key(who: BankIdentity, request: Request, key: str) -> str:
    """The idempotency key ToadsBank sees: the client's key, bound to the member and the route it was sent to."""
    material = f"{who.member}\n{request.method}\n{request.url.path}\n{key}".encode()
    return hashlib.sha256(material).hexdigest()


def officer_days(services: Services, principal: Principal) -> list[str]:
    return [
        d.id
        for d in services.raid_days.raid_days
        if principal.global_officer or principal.day_roles.get(d.id) is HubRole.OFFICER
    ]


async def day_sources(bank: BankClient, who: BankIdentity, day: str) -> set[str]:
    """The ids of the sources assigned to this raid day (a source's `raidDay`)."""
    rows = await bank.sources(who)
    return {str(s.get("id")) for s in rows or [] if isinstance(s, dict) and s.get("raidDay") == day}


async def bind_day(bank: BankClient, who: BankIdentity, principal: Principal, day: str, source_id: object) -> None:
    """A raid day's officers work only that day's banks. The URL's day only decides who reaches a route, so every
    officer route also checks that the source it touches belongs to that day. The global tier works every bank,
    including those with no raid day."""
    if principal.global_officer:
        return
    if source_id is None or str(source_id) not in await day_sources(bank, who, day):
        raise BankError(403, NOT_THIS_DAY, f"That bank does not belong to the {day} raid day")


async def _bind_import(bank: BankClient, who: BankIdentity, principal: Principal, day: str, shown: Any) -> None:
    matched = shown.get("matchedSource") if isinstance(shown, dict) else None
    await bind_day(bank, who, principal, day, matched.get("id") if isinstance(matched, dict) else None)


# -------------------------------------------------------------------- member


@member.get("/me")
async def me(principal: Viewer, live: Live) -> BankMe:
    return BankMe(
        configured=live.bank is not None,
        discord_user_id=str(principal.discord_user_id) if principal.discord_user_id is not None else None,
        display_name=principal.display_name,
        global_officer=principal.global_officer,
        officer_days=officer_days(live, principal),
    )


@member.get("/sources")
async def sources(principal: Viewer, live: Live) -> Any:
    return await bank_of(live).sources(identity_of(principal))


@member.get("/sources/{source_id}/replica")
async def replica(source_id: Id, principal: Viewer, live: Live) -> Any:
    return await bank_of(live).replica(identity_of(principal), source_id)


@member.get("/inventory")
async def inventory(
    principal: Viewer,
    live: Live,
    q: Annotated[str | None, Query(max_length=100)] = None,
    source_id: Annotated[str | None, Query(alias="sourceId", pattern=ID)] = None,
) -> Any:
    return await bank_of(live).inventory(identity_of(principal), q=q, source_id=source_id)


@member.get("/requests")
async def my_requests(
    principal: Viewer,
    live: Live,
    status_: Annotated[str | None, Query(alias="status", pattern=r"^[a-z]{1,20}$")] = None,
) -> Any:
    return await bank_of(live).requests(identity_of(principal), "mine", status_)


@member.post("/requests", status_code=status.HTTP_201_CREATED)
async def create_request(body: RequestCreate, request: Request, key: Key, principal: Requester, live: Live) -> Any:
    bank, who = bank_of(live), identity_of(principal)
    return await bank.create_request(who, body.model_dump(exclude_none=True), derive_key(who, request, key))


@member.post("/requests/{request_id}/cancel")
async def cancel(request_id: Id, body: Revision, request: Request, key: Key, principal: Requester, live: Live) -> Any:
    bank, who = bank_of(live), identity_of(principal)
    return await bank.act(who, request_id, "cancel", body.model_dump(), derive_key(who, request, key))


# ------------------------------------------------------- raid-day officers


@day_officer.post("/imports", status_code=status.HTTP_201_CREATED)
async def open_import(day: str, request: Request, key: Key, principal: Importer, live: Live) -> Any:
    bank, who = bank_of(live), identity_of(principal)
    return await bank.open_import(who, derive_key(who, request, key))


@day_officer.post("/imports/{import_id}/parts")
async def add_parts(
    day: str, import_id: Id, body: PartsIn, request: Request, key: Key, principal: Importer, live: Live
) -> Any:
    bank, who = bank_of(live), identity_of(principal)
    return await bank.add_parts(who, import_id, body.text, derive_key(who, request, key))


@day_officer.get("/imports/{import_id}/preview")
async def preview(day: str, import_id: Id, principal: Importer, live: Live) -> Any:
    bank, who = bank_of(live), identity_of(principal)
    shown = await bank.preview(who, import_id)
    await _bind_import(bank, who, principal, day, shown)
    return shown


@day_officer.post("/imports/{import_id}/accept")
async def accept(day: str, import_id: Id, request: Request, key: Key, principal: Importer, live: Live) -> Any:
    bank, who = bank_of(live), identity_of(principal)
    await _bind_import(bank, who, principal, day, await bank.preview(who, import_id))
    return await bank.accept(who, import_id, derive_key(who, request, key))


@day_officer.get("/requests")
async def queue(
    day: str,
    principal: Manager,
    live: Live,
    scope: Literal["queue", "all"] = "queue",
    status_: Annotated[str | None, Query(alias="status", pattern=r"^[a-z]{1,20}$")] = None,
) -> Any:
    bank, who = bank_of(live), identity_of(principal)
    rows = await bank.requests(who, scope, status_)
    if principal.global_officer or not isinstance(rows, list):
        return rows
    mine = await day_sources(bank, who, day)
    return [r for r in rows if isinstance(r, dict) and str(r.get("sourceId")) in mine]


async def _manage(
    live: Services, principal: Principal, request: Request, key: str, request_id: str, action: str, body: Any
) -> Any:
    bank, who = bank_of(live), identity_of(principal)
    day = request.path_params["day"]
    if not principal.global_officer:
        rows = await bank.requests(who, "all")
        target = next((r for r in rows or [] if isinstance(r, dict) and str(r.get("id")) == request_id), None)
        if target is None:
            raise BankError(404, "not_found", "No such request")
        await bind_day(bank, who, principal, day, target.get("sourceId"))
    return await bank.act(who, request_id, action, body.model_dump(exclude_none=True), derive_key(who, request, key))


@day_officer.post("/requests/{request_id}/approve")
async def approve(
    day: str, request_id: Id, body: Decision, request: Request, key: Key, principal: Manager, live: Live
) -> Any:
    return await _manage(live, principal, request, key, request_id, "approve", body)


@day_officer.post("/requests/{request_id}/reject")
async def reject(
    day: str, request_id: Id, body: Decision, request: Request, key: Key, principal: Manager, live: Live
) -> Any:
    return await _manage(live, principal, request, key, request_id, "reject", body)


@day_officer.post("/requests/{request_id}/deliveries")
async def deliver(
    day: str, request_id: Id, body: Delivery, request: Request, key: Key, principal: Manager, live: Live
) -> Any:
    return await _manage(live, principal, request, key, request_id, "deliveries", body)


# ------------------------------------------------------------- global tier


@global_admin.post("/sources", status_code=status.HTTP_201_CREATED)
async def create_source(body: SourceCreate, request: Request, key: Key, principal: Admin, live: Live) -> Any:
    bank, who = bank_of(live), identity_of(principal)
    return await bank.create_source(who, body.model_dump(), derive_key(who, request, key))


@global_admin.patch("/sources/{source_id}")
async def patch_source(
    source_id: Id, body: SourcePatch, request: Request, key: Key, principal: Admin, live: Live
) -> Any:
    bank, who = bank_of(live), identity_of(principal)
    return await bank.patch_source(who, source_id, body.model_dump(exclude_unset=True), derive_key(who, request, key))


# ------------------------------------------------------------------ events


async def require_bank_service(live: Live, authorization: str = Header(default="")) -> None:
    """ToadsBank's worker authenticates with the bank's service token, compared in constant time."""
    scheme, _, token = authorization.partition(" ")
    expected = live.settings.bank_service_token.get_secret_value()
    if (
        scheme.lower() != "bearer"
        or not token
        or not expected
        or not hmac.compare_digest(token.encode(), expected.encode())
    ):
        raise BankError(401, "unauthorised", "Not ToadsBank")


@events.post("/events", dependencies=[Depends(require_bank_service)])
async def receive_event(event: BankEvent, live: Live) -> EventAck:
    """At-least-once delivery: an id seen before is acknowledged and nothing is sent twice. If the hub cannot act on
    an event it forgets the id and answers 503, so ToadsBank retries it."""
    marker = f"bank:event:{event.id}"
    if not await live.redis.set(marker, "1", nx=True, ex=EVENT_MEMORY_SECONDS):
        return EventAck(duplicate=True)
    try:
        sent = live.bank_events.handle(event)
    except Exception:
        await live.redis.delete(marker)
        log.exception("bank.event_failed", event_type=event.type)
        raise BankError(503, "event_not_handled", "The hub could not act on this event yet; retry") from None
    log.info("bank.event", event_type=event.type, actions=len(sent))
    return EventAck(actions=len(sent))


# -------------------------------------------------------------------- wiring


async def _bank_error(_: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, BankError):
        raise exc
    return JSONResponse(status_code=exc.status, content=exc.body())


def include_bank(app: FastAPI) -> None:
    app.add_exception_handler(BankError, _bank_error)
    # The events route goes first so /api/bank/events is never read as a member route.
    for router in (events, member, day_officer, global_admin):
        app.include_router(router)
