"""App factory. Services (Redis, Discord, DB) are built in the lifespan from the environment, or injected by tests."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import anyio
import structlog
from fastapi import Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from toads_api import audit, auth, claims, members
from toads_api.absences.routes import include_absences
from toads_api.account.routes import router as account_router
from toads_api.awards.routes import include_awards
from toads_api.bank.routes import include_bank
from toads_api.bank_grants.routes import include_bank_grants
from toads_api.bots.routes import include_bots
from toads_api.community.routes import include_community
from toads_api.comps.routes import include_comps
from toads_api.discord_api import DiscordAuthError, DiscordError, MismatchedDiscordApplicationError
from toads_api.home.routes import include_home
from toads_api.raid_sheets.routes import include_raid_sheets
from toads_api.rbac import UnknownDiscordRoleError
from toads_api.rbac.deps import get_services, require
from toads_api.rbac.permissions import Permission, Principal
from toads_api.reference.routes import include_reference
from toads_api.role_badges.routes import include_role_badges
from toads_api.services import Services, build_services
from toads_api.settings import Settings

log = structlog.get_logger(__name__)


async def _validation_error(_: Request, exc: Exception) -> JSONResponse:
    # FastAPI's default handler echoes the offending input back; ours never echoes request bodies.
    if not isinstance(exc, RequestValidationError):
        raise exc
    errors = [{"loc": e.get("loc"), "msg": e.get("msg")} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})


def _record_sync(services: Services, principal: Principal, day: str) -> None:
    with services.db.begin() as db:
        audit.record(db, actor=principal.member_id, action="sync.trigger", target=f"raid day {day}", raid_day=day)


# Toad Bot's invite, with the permissions ADMIN_GUIDE.md lists; the client id is the application id and is public.
BOT_INVITE = (
    "https://discord.com/oauth2/authorize?client_id={client_id}&permissions=268520464&integration_type=0"
    "&scope=bot+applications.commands"
)


async def _verify_discord(services: Services) -> None:
    """Check the Discord settings at startup without ever refusing to start: a change made in Discord (a reset bot
    token, a new application, a deleted role) must not take the whole site down, and nobody should need a shell on the
    server to see what is wrong. A rejected bot token or a client id and bot token from different applications
    (REQ-HUB-AUTH-003) and a configured role the server lacks (REQ-HUB-DAY-022) are errors in the log; Discord not
    answering, or a server the bot cannot read because it is not invited yet, is a warning (REQ-HUB-DAY-024).
    """
    invite = BOT_INVITE.format(client_id=services.settings.discord_client_id.strip())
    try:
        await services.verify_discord_application()
    except (DiscordAuthError, MismatchedDiscordApplicationError) as exc:
        log.error(
            "discord_application_misconfigured",
            error=str(exc),
            hint="set TOADS_DISCORD_CLIENT_ID and TOADS_DISCORD_BOT_TOKEN from the same Discord application",
        )
    except DiscordError as exc:
        log.warning("discord_application_unchecked", error=str(exc), hint="Discord did not answer; retried on restart")
    try:
        await services.verify_discord_roles()
    except UnknownDiscordRoleError as exc:
        log.error(
            "discord_role_missing",
            error=str(exc),
            hint="a role in the raid-day config was deleted or recreated in Discord; put its new id in the config",
        )
    except DiscordError as exc:
        log.warning(
            "discord_roles_unchecked",
            error=str(exc),
            hint=f"check TOADS_DISCORD_GUILD_ID and invite Toad Bot ({invite}); role checks, raid events and the bots "
            "read the server through it",
        )


def create_app(services: Services | None = None) -> FastAPI:
    """Build the app. Without `services`, startup reads the environment and fails fast on anything missing
    (REQ-DEV-CFG-001). Discord settings that do not match Discord are logged, never fatal (`_verify_discord`)."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        live = services if services is not None else build_services(Settings())
        try:
            await _verify_discord(live)
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
    app.include_router(account_router)
    include_awards(app)
    include_absences(app)
    include_role_badges(app)
    include_comps(app)
    include_home(app)
    include_reference(app)

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

    include_community(app)
    include_bots(app)
    include_bank(app)
    include_bank_grants(app)
    include_raid_sheets(app)
    return app


app = create_app()
