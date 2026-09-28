"""The bot bridge's HTTP side (docs/bots.md). Every route takes the bots' service token only.

- GET  /api/bots                              the bots that have registered
- PUT  /api/bots/{bot}                        a bot registers its manifest at startup
- GET  /api/bots/{bot}/actions                site actions waiting for that bot
- POST /api/bots/{bot}/actions/{id}/result    the bot's answer to one action
- POST /api/bots/{bot}/events                 a Discord event the bot passes to the site
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Path, Query, Request, Response, status
from fastapi.responses import JSONResponse

from toads_api.bots.bridge import MAX_PULL, BotBridge, BridgeError
from toads_api.bots.models import NAME, ActionResult, BotManifest, DiscordEvent, EventReceipt, SiteAction
from toads_api.community.deps import require_service
from toads_api.rbac.deps import get_services

router = APIRouter(prefix="/api/bots", tags=["bots"], dependencies=[Depends(require_service)])


def get_bridge(request: Request) -> BotBridge:
    return get_services(request).bots


Bridge = Annotated[BotBridge, Depends(get_bridge)]
Bot = Annotated[str, Path(pattern=NAME)]


@router.get("")
async def list_bots(bridge: Bridge) -> list[BotManifest]:
    return bridge.bots()


@router.put("/{bot}")
async def register(bot: Bot, body: BotManifest, bridge: Bridge) -> BotManifest:
    if body.name != bot:
        raise BridgeError(422, "the manifest's name must match the path")
    return bridge.register(body)


@router.get("/{bot}/actions")
async def pending(
    bot: Bot, bridge: Bridge, limit: Annotated[int, Query(ge=1, le=MAX_PULL)] = MAX_PULL
) -> list[SiteAction]:
    return bridge.pending(bot, limit)


@router.post("/{bot}/actions/{action_id}/result", status_code=status.HTTP_204_NO_CONTENT)
async def result(bot: Bot, action_id: int, body: ActionResult, bridge: Bridge) -> Response:
    bridge.complete(bot, action_id, body)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{bot}/events", status_code=status.HTTP_202_ACCEPTED)
async def event(bot: Bot, body: DiscordEvent, bridge: Bridge) -> EventReceipt:
    return bridge.receive(bot, body)


async def _bridge_error(_: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, BridgeError):
        raise exc
    return JSONResponse(status_code=exc.status, content={"detail": str(exc)})


def include_bots(app: FastAPI) -> None:
    app.add_exception_handler(BridgeError, _bridge_error)
    app.include_router(router)
