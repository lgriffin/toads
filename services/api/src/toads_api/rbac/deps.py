"""FastAPI dependencies that enforce the permission table on every route."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass

import anyio
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute
from starlette.routing import BaseRoute

from toads_api import audit
from toads_api.identity import DiscordUnavailableError, refresh
from toads_api.rbac.permissions import Permission, Principal, can
from toads_api.services import Services
from toads_api.sessions import SESSION_COOKIE


def get_services(request: Request) -> Services:
    services: Services | None = getattr(request.app.state, "services", None)
    if services is None:
        raise RuntimeError("app services are not initialised; run the app through its lifespan")
    return services


async def get_principal(request: Request) -> Principal:
    """Resolve the caller from their server-side session; roles come from Discord only (REQ-HUB-RBAC-001)."""
    services = get_services(request)
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
    return services.raid_days.principal_for(data.member_id, set(data.role_ids), data.display_name)


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
        if not can(principal, self.permission, raid_day):
            if raid_day is not None and principal.is_officer:
                # REQ-HUB-DAY-011: an officer reaching into a sibling day's officer view is recorded.
                await anyio.to_thread.run_sync(
                    _record_denial, get_services(request), principal, request, raid_day, self.permission.value
                )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
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
