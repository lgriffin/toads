"""The bot's only door into the hub: the Hub API's /api/bot routes, authenticated with the service token."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx
from pydantic import SecretStr


class HubClient:
    def __init__(self, base_url: str, token: SecretStr, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {token.get_secret_value()}"},
            timeout=10.0,
            transport=transport,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def outbox(self) -> list[dict[str, Any]]:
        r = await self._http.get("/api/bot/outbox")
        r.raise_for_status()
        jobs: list[dict[str, Any]] = r.json()
        return jobs

    async def ack(self, job_id: int, *, channel_id: int | None = None, message_id: int | None = None) -> None:
        body = {k: v for k, v in {"channel_id": channel_id, "message_id": message_id}.items() if v is not None}
        (await self._http.post(f"/api/bot/outbox/{job_id}/ack", json=body)).raise_for_status()

    async def discord_message(
        self, *, channel_id: int, message_id: int, author_name: str, content: str, created_at: datetime
    ) -> None:
        body = {
            "channel_id": channel_id,
            "message_id": message_id,
            "author_name": author_name[:100],
            "content": content[:4000],
            "created_at": created_at.isoformat(),
        }
        (await self._http.post("/api/bot/discord-messages", json=body)).raise_for_status()

    async def discord_message_deleted(self, message_id: int) -> None:
        (await self._http.post(f"/api/bot/discord-messages/{message_id}/deleted")).raise_for_status()
