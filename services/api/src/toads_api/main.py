"""App factory. Empty pages and health first (phase 2.0); routes arrive per milestone."""

from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from toads_api.rbac.deps import require
from toads_api.rbac.permissions import Permission, Principal


async def _validation_error(_: Request, exc: Exception) -> JSONResponse:
    # FastAPI's default handler echoes the offending input back; ours never echoes request bodies.
    if not isinstance(exc, RequestValidationError):
        raise exc
    errors = [{"loc": e.get("loc"), "msg": e.get("msg")} for e in exc.errors()]
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": errors})


def create_app() -> FastAPI:
    app = FastAPI(title="Toads Hub API", docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)
    app.add_exception_handler(RequestValidationError, _validation_error)

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
    ) -> dict[str, str]:
        # Enqueueing lands with the worker in phase 2.1.
        return {"day": day, "status": "queued"}

    return app


app = create_app()
