"""The bot's only door into the hub: the Hub API's /api/bot routes, authenticated with the service token, and the
Raid-Helper import, bank desk request and Highlights posts, which it calls as the member who used `/raidhelper import`,
`/bankrequest`, `/highlight`, `/stream` or `/clip`."""

from __future__ import annotations

import base64
from datetime import datetime
from typing import Any
from urllib.parse import quote

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

    @property
    def base_url(self) -> str:
        return str(self._http.base_url)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def outbox(self) -> list[dict[str, Any]]:
        r = await self._http.get("/api/bot/outbox")
        r.raise_for_status()
        jobs: list[dict[str, Any]] = r.json()
        return jobs

    async def ack(
        self, job_id: int, *, channel_id: int | None = None, message_id: int | None = None, error: str | None = None
    ) -> None:
        """Mark a job done; `error` says why it could not be done, for jobs that retrying will not fix."""
        fields: dict[str, int | str | None] = {"channel_id": channel_id, "message_id": message_id, "error": error}
        body = {k: v for k, v in fields.items() if v is not None}
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

    async def raid_nights(self) -> list[dict[str, str]]:
        """The raid nights, as {id, name}, for the commands that ask which night."""
        r = await self._http.get("/api/public/raid-nights")
        r.raise_for_status()
        nights: list[dict[str, str]] = r.json()
        return nights

    async def import_raid_helper(self, day: str, discord_user_id: int, export: dict[str, Any]) -> httpx.Response:
        """Hand the hub a Raid-Helper export for a raid night, acting as the Discord member who sent it: the hub reads
        their roles from Discord and refuses anyone who is not that night's officer. The response is returned as is,
        refusals included, for the command to explain."""
        return await self._http.post(
            f"/api/days/{quote(day, safe='')}/comps/raid-helper",
            json=export,
            headers={"X-Toads-Acting-Member": str(discord_user_id)},
            timeout=30.0,
        )

    async def bank_request(self, discord_user_id: int, item: str, quantity: int) -> httpx.Response:
        """Ask the guild bank's request desk for an item, acting as the Discord member who used `/bankrequest`: the hub
        reads their roles from Discord, so only guild members can ask. Returned as is, refusals included."""
        return await self._http.post(
            "/api/bank-desk/requests",
            json={"item": item, "quantity": quantity},
            headers={"X-Toads-Acting-Member": str(discord_user_id)},
        )

    async def post_photo(self, discord_user_id: int, image: bytes, caption: str) -> httpx.Response:
        """Post a photo to the Highlights page, acting as the member who used `/highlight`: the hub reads their roles
        from Discord, so only raiders can post. Returned as is, refusals included."""
        return await self._http.post(
            "/api/gallery/photos",
            json={"caption": caption, "image_base64": base64.b64encode(image).decode("ascii")},
            headers={"X-Toads-Acting-Member": str(discord_user_id)},
            timeout=30.0,
        )

    async def start_stream(self, discord_user_id: int, link: str, title: str) -> httpx.Response:
        """Put the member's Twitch channel on the Highlights page (`/stream start`). Returned as is."""
        return await self._http.post(
            "/api/gallery/streams",
            json={"link": link, "title": title},
            headers={"X-Toads-Acting-Member": str(discord_user_id)},
        )

    async def end_stream(self, discord_user_id: int) -> httpx.Response:
        """Take the member's stream off the Highlights page (`/stream end`). Returned as is."""
        return await self._http.post(
            "/api/gallery/streams/end", headers={"X-Toads-Acting-Member": str(discord_user_id)}
        )

    async def share_clip(self, discord_user_id: int, url: str, title: str) -> httpx.Response:
        """Hand the hub a clip link for the officers to review (`/clip`). Returned as is."""
        return await self._http.post(
            "/api/highlights",
            json={"url": url, "title": title},
            headers={"X-Toads-Acting-Member": str(discord_user_id)},
        )
