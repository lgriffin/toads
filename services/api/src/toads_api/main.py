"""App factory. Services (Redis, Discord, DB) are built in the lifespan from the environment, or injected by tests."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import anyio
from fastapi import Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from toads_api import audit, auth, claims, members
from toads_api.rbac.deps import get_services, require
from toads_api.rbac.permissions import Permission, Principal
from toads_api.services import Services, build_services
from toads_api.settings import Settings


async def _validation_error(_: Request, exc: Exception) -> JSONResponse:
    # FastAPI's default handler echoes the offending input back; ours never echoes request bodies.
    if not isinstance(exc, RequestValidationError):
        raise exc
    errors = [{"loc": e.get("loc"), "msg": e.get("msg")} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})


def _record_sync(services: Services, principal: Principal, day: str) -> None:
    with services.db.begin() as db:
        audit.record(db, actor=principal.member_id, action="sync.trigger", target=f"raid day {day}", raid_day=day)


def create_app(services: Services | None = None) -> FastAPI:
    """Build the app. Without `services`, startup reads the environment and fails fast on anything missing
    (REQ-DEV-CFG-001) or on a configured Discord role the server does not have (REQ-HUB-DAY-022)."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        live = services if services is not None else build_services(Settings())
        try:
            await live.verify_discord_roles()
            app.state.services = live
            yield
        finally:
            await live.aclose()

    app = FastAPI(
        title="Toads Hub API", docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None, lifespan=lifespan
    )
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.include_router(auth.router)
    app.include_router(claims.router)
    app.include_router(members.router)

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/me")
    async def me(principal: Principal = Depends(require(Permission.VIEW_OWN_PERFORMANCE))) -> dict[str, Any]:  # noqa: B008
        return {"member_id": principal.member_id}

    @app.post("/api/days/{day}/admin/sync", status_code=status.HTTP_202_ACCEPTED)
    async def trigger_sync(
        day: str,
        principal: Principal = Depends(require(Permission.SYNC_LOGS, scoped=True)),  # noqa: B008
        live: Services = Depends(get_services),  # noqa: B008
    ) -> dict[str, str]:
        # Enqueueing lands with the worker's sync job; the officer action is audited now (REQ-HUB-AUDIT-001).
        await anyio.to_thread.run_sync(_record_sync, live, principal, day)
        return {"day": day, "status": "queued"}

    return app


app = create_app()
