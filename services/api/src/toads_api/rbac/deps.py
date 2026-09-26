"""FastAPI dependencies that enforce the permission table on every route."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status

from toads_api.rbac.permissions import Permission, Principal, can


async def get_principal(request: Request) -> Principal:
    """Resolve the caller from their session. Discord OAuth lands in H2; until then nobody is signed in."""
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not signed in")


def require(permission: Permission, *, scoped: bool = False) -> Callable[..., object]:
    """Guard a route. With scoped=True the raid day comes from the `day` path parameter only (REQ-HUB-DAY-023)."""

    async def _check(request: Request, principal: Principal = Depends(get_principal)) -> Principal:  # noqa: B008
        raid_day = request.path_params.get("day") if scoped else None
        if scoped and raid_day is None:
            raise RuntimeError(f"route {request.url.path} is scoped but has no {{day}} path parameter")
        if not can(principal, permission, raid_day):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return principal

    return _check
