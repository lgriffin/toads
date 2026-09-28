"""A bot's only door into the hub: the /api/bots routes, authenticated with the service token."""

from __future__ import annotations

from typing import Protocol

import httpx
from pydantic import SecretStr, TypeAdapter

from toads_bot.kit.contract import ActionResult, BotManifest, DiscordEvent, EventReceipt, SiteAction

_ACTIONS = TypeAdapter(list[SiteAction])


class HubLink(Protocol):
    async def register(self, manifest: BotManifest) -> None: ...
    async def pull(self, bot: str) -> list[SiteAction]: ...
    async def report(self, bot: str, action_id: int, result: ActionResult) -> None: ...
    async def send_event(self, bot: str, event: DiscordEvent) -> EventReceipt: ...


class HttpHubLink:
    def __init__(self, base_url: str, token: SecretStr, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {token.get_secret_value()}"},
            timeout=10.0,
            transport=transport,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def register(self, manifest: BotManifest) -> None:
        r = await self._http.put(f"/api/bots/{manifest.name}", json=manifest.model_dump(mode="json"))
        r.raise_for_status()

    async def pull(self, bot: str) -> list[SiteAction]:
        r = await self._http.get(f"/api/bots/{bot}/actions")
        r.raise_for_status()
        return _ACTIONS.validate_python(r.json())

    async def report(self, bot: str, action_id: int, result: ActionResult) -> None:
        r = await self._http.post(f"/api/bots/{bot}/actions/{action_id}/result", json=result.model_dump(mode="json"))
        r.raise_for_status()

    async def send_event(self, bot: str, event: DiscordEvent) -> EventReceipt:
        r = await self._http.post(f"/api/bots/{bot}/events", json=event.model_dump(mode="json"))
        r.raise_for_status()
        return EventReceipt.model_validate(r.json())
