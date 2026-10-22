"""FastAPI dependencies that enforce the permission table on every route."""

from __future__ import annotations

import hmac
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, replace

import anyio
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute
from starlette.routing import BaseRoute

from toads_api import audit
from toads_api.identity import DiscordUnavailableError, NotAMemberError, acting_principal, refresh
from toads_api.rbac.permissions import GRANTABLE, HubRole, Permission, Principal, ViewAs, can
from toads_api.services import Services
from toads_api.sessions import SESSION_COOKIE, SessionData
from toads_api.settings import Settings


def get_services(request: Request) -> Services:
    services: Services | None = getattr(request.app.state, "services", None)
    if services is None:
        raise RuntimeError("app services are not initialised; run the app through its lifespan")
    return services


ACTING_MEMBER_HEADER = "X-Toads-Acting-Member"
# The audit action every change made by the break-glass admin is recorded under (docs/admin.md).
BREAK_GLASS_ACTION = "break_glass"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
# The routes a bot may call on a member's behalf: the bank's for the bank bot (docs/bank.md), nothing else.
ACTING_PATHS = re.compile(r"^/api/(days/[a-z0-9_-]{1,32}/)?bank/(?!events$)")
# And the Toad Bot's `/raidhelper import` (docs/comps.md), `/bankrequest` (docs/bank-desk.md), and `/highlight`,
# `/stream` and `/clip` (docs/highlights.md), with the hub service token. Asking and posting only: answering a bank
# request, reviewing a clip or taking a photo down stays on the site.
TOAD_BOT_ACTING_PATHS = re.compile(
    r"^/api/(days/[a-z0-9_-]{1,32}/comps/raid-helper|bank-desk/requests|gallery/photos|gallery/streams(/end)?|highlights)$"
)


def _bearer_is(request: Request, secret: str) -> bool:
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    return (
        scheme.lower() == "bearer"
        and bool(token)
        and bool(secret)
        and hmac.compare_digest(token.encode(), secret.encode())
    )


def _is_bank_bot_token(request: Request, services: Services) -> bool:
    """The bank bot's own token (TOADS_BANK_BOT_TOKEN), never the shared hub service token."""
    return _bearer_is(request, services.settings.bank_bot_token.get_secret_value())


def _may_act(request: Request, services: Services) -> bool:
    path = request.url.path
    if ACTING_PATHS.match(path):
        return _is_bank_bot_token(request, services)
    if TOAD_BOT_ACTING_PATHS.match(path):
        return _bearer_is(request, services.settings.hub_service_token.get_secret_value())
    return False


async def _acting_member(request: Request, services: Services, raw: str) -> Principal:
    """A bot calling on behalf of the Discord member who used its command or button: the bank bot with its own token
    on the bank's routes, or the Toad Bot with the hub service token on its Raid-Helper import. The member's roles are
    read from Discord, so the bot gains no power the member does not have."""
    if not _may_act(request, services):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not signed in")
    if not raw.isdigit() or len(raw) > 20:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{ACTING_MEMBER_HEADER} must be a user id")
    try:
        return await acting_principal(services, int(raw))
    except NotAMemberError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of the guild") from None
    except DiscordUnavailableError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Discord is unavailable") from None


async def with_grants(services: Services, principal: Principal) -> Principal:
    """The member's bank grants, read from the database on every request and never cached with their roles, so a
    revoke takes effect on their next call, on the site and through the bank bot alike (docs/bank.md "Grants")."""
    if principal.discord_user_id is None or principal.viewing_as is not None:
        # Viewing the hub as a raider or officer shows that role's bank, not the super admin's own grants.
        return principal
    held = await anyio.to_thread.run_sync(services.bank_grants.held_by, principal.discord_user_id)
    if not held:
        return principal
    return replace(principal, grants=frozenset((Permission(p), day) for p, day in held))


def elevate(settings: Settings, principal: Principal) -> Principal:
    """Super admins come from configuration alone (docs/admin.md): TOADS_SUPER_ADMIN_IDS, and the break-glass admin
    TOADS_BREAK_GLASS_ADMIN_ID, who is a super admin whatever their roles or the list say, and is marked so."""
    user = principal.discord_user_id
    if user is None:
        return principal
    if settings.break_glass_admin_id is not None and user == settings.break_glass_admin_id:
        return replace(principal, global_officer=True, super_admin=True, break_glass=True)
    if user in settings.super_admins():
        return replace(principal, global_officer=True, super_admin=True)
    return principal


async def get_principal(request: Request) -> Principal:
    """Resolve the caller from their server-side session; roles come from Discord only (REQ-HUB-RBAC-001), super
    admins from configuration. Bank grants are added by the guards that can use them (Require, /api/bank/me)."""
    services = get_services(request)
    principal, view_as = await _session_principal(request, services)
    return viewing(services, elevate(services.settings, principal), view_as)


# The roles a super admin may view the hub as (docs/admin.md "View as"), by the name the session and URL use.
VIEW_AS_ROLES: dict[str, HubRole] = {"raider": HubRole.RAIDER, "officer": HubRole.OFFICER}
VIEW_AS_READ_ONLY = "You are viewing the hub as another role, which is read only. Go back to make changes."


def view_as_of(data: SessionData) -> ViewAs | None:
    role = VIEW_AS_ROLES.get(data.view_as_role)
    return ViewAs(role, data.view_as_day) if role is not None and data.view_as_day else None


def viewing(services: Services, principal: Principal, view_as: ViewAs | None) -> Principal:
    """docs/admin.md "View as": a super admin's requests carry one raid night's raider or officer standing and nothing
    else, still under their own identity. Anyone else's stored view is ignored (a super admin dropped from the
    configuration is simply themselves again), as is a raid day the configuration no longer has."""
    if view_as is None or not principal.super_admin or services.raid_days.day(view_as.raid_day) is None:
        return principal
    return Principal(
        member_id=principal.member_id,
        display_name=principal.display_name,
        day_roles={view_as.raid_day: view_as.role},
        discord_user_id=principal.discord_user_id,
        discord_username=principal.discord_username,
        discord_role_ids=principal.discord_role_ids,
        viewing_as=replace(view_as, break_glass=principal.break_glass),
    )


async def _session_principal(request: Request, services: Services) -> tuple[Principal, ViewAs | None]:
    acting = request.headers.get(ACTING_MEMBER_HEADER)
    if acting is not None:
        return await _acting_member(request, services, acting.strip()), None
    session_id = request.cookies.get(SESSION_COOKIE)
    data = await services.sessions.get(session_id) if session_id else None
    if session_id is None or data is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not signed in")
    if services.clock() - data.refreshed_at >= services.settings.role_refresh_seconds:
        try:
            refreshed = await refresh(services, session_id, data)
        except DiscordUnavailableError:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Discord is unavailable") from None
        if refreshed is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session ended; sign in again")
        data = refreshed
    # Off the event loop: the night badges' roles come from the database.
    principal = await anyio.to_thread.run_sync(
        services.principal_for,
        data.member_id,
        set(data.role_ids),
        data.display_name,
        data.discord_user_id,
        data.discord_username,
    )
    return principal, view_as_of(data)


def _record_break_glass(
    services: Services, principal: Principal, request: Request, raid_day: str | None, perm: str
) -> None:
    with services.db.begin() as db:
        audit.record(
            db,
            actor=principal.member_id,
            action=BREAK_GLASS_ACTION,
            target=f"{request.method} {request.url.path}",
            raid_day=raid_day,
            detail=perm,
        )


def _record_denial(services: Services, principal: Principal, request: Request, raid_day: str, perm: str) -> None:
    with services.db.begin() as db:
        audit.record(
            db,
            actor=principal.member_id,
            action="rbac.denied",
            target=f"{request.method} {request.url.path}",
            raid_day=raid_day,
            detail=perm,
        )


class Require:
    """Route guard. With scoped=True the raid day comes from the `day` path parameter only (REQ-HUB-DAY-023)."""

    def __init__(self, permission: Permission, *, scoped: bool = False) -> None:
        self.permission = permission
        self.scoped = scoped

    async def __call__(self, request: Request, principal: Principal = Depends(get_principal)) -> Principal:  # noqa: B008
        raid_day = request.path_params.get("day") if self.scoped else None
        if self.scoped:
            if raid_day is None:
                raise RuntimeError(f"route {request.url.path} is scoped but has no {{day}} path parameter")
            services = get_services(request)
            if services.raid_days.day(raid_day) is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown raid day")
        if self.scoped and self.permission in GRANTABLE:
            # Only raid-day bank routes can be opened by a grant, so only they read grants (one query per call).
            principal = await with_grants(get_services(request), principal)
        if not can(principal, self.permission, raid_day):
            if raid_day is not None and principal.is_officer:
                # REQ-HUB-DAY-011: an officer reaching into a sibling day's officer view is recorded.
                await anyio.to_thread.run_sync(
                    _record_denial, get_services(request), principal, request, raid_day, self.permission.value
                )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        if (
            principal.viewing_as is not None
            and request.method not in SAFE_METHODS
            and self.permission is not Permission.VIEW_AS
        ):
            # docs/admin.md "View as": read only, so nothing is done in a raider's or officer's name but going back.
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=VIEW_AS_READ_ONLY)
        glass = principal.break_glass or (principal.viewing_as is not None and principal.viewing_as.break_glass)
        if glass and request.method not in SAFE_METHODS:
            # docs/admin.md: every change made through the break-glass admin is on the audit log, marked as such.
            await anyio.to_thread.run_sync(
                _record_break_glass, get_services(request), principal, request, raid_day, self.permission.value
            )
        return principal


def require(permission: Permission, *, scoped: bool = False) -> Require:
    return Require(permission, scoped=scoped)


@dataclass(frozen=True)
class RouteRule:
    method: str
    path: str
    permission: Permission
    scoped: bool


def _find_require(dependant: Dependant) -> Require | None:
    for dep in dependant.dependencies:
        if isinstance(dep.call, Require):
            return dep.call
        found = _find_require(dep)
        if found is not None:
            return found
    return None


def _api_routes(routes: Iterable[BaseRoute]) -> Iterator[APIRoute]:
    for route in routes:
        if isinstance(route, APIRoute):
            yield route
            continue
        # Newer FastAPI keeps an included router as one branch route holding the original router.
        # The hub includes routers without a prefix, so the original routes' paths are the served paths.
        nested = getattr(route, "original_router", None)
        if nested is not None:
            yield from _api_routes(nested.routes)


def route_rules(app: FastAPI) -> tuple[list[RouteRule], list[str]]:
    """Every API route's guard, and the routes that have none (for the matrix test, REQ-HUB-DAY-021)."""
    rules: list[RouteRule] = []
    unguarded: list[str] = []
    for route in _api_routes(app.routes):
        guard = _find_require(route.dependant)
        for method in sorted(route.methods or ()):
            if guard is None:
                unguarded.append(f"{method} {route.path}")
            else:
                rules.append(RouteRule(method, route.path, guard.permission, guard.scoped))
    return rules, unguarded
