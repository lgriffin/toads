"""ToadsBank's events (delivered to POST /api/bank/events) turned into bank bot actions (docs/bank.md).

- request.assigned  -> bank.dm to each manager, with Approve / Reject / Record delivery buttons. A DM the bot finally
                       gives up on becomes a bank.post to the fallback channel (TB-BM-12).
- request.updated   -> bank.dm to the requester.
- snapshot.accepted -> bank.post to the bank channel: the source raid day's bank_requests channel, else the global one.
- request.created   -> nothing yet; the queue on the site reads ToadsBank directly.

Rules only: no FastAPI, RBAC or storage. Deduplication on the event id happens in the route, which owns Redis.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, Field

from toads_api.bank import messages
from toads_api.bots.bridge import BotBridge
from toads_api.bots.models import ActionResult, SiteAction

log = logging.getLogger(__name__)

BOT = "bank"
DM = "bank.dm"
POST = "bank.post"


class BankEvent(BaseModel):
    """One outbox event from ToadsBank's worker."""

    id: str = Field(min_length=1, max_length=200)
    type: str = Field(min_length=1, max_length=64)
    occurredAt: int = 0
    payload: dict[str, Any] = Field(default_factory=dict)


def _discord_id(value: object) -> str | None:
    text = str(value) if value is not None else ""
    return text if text.isdigit() and len(text) <= 20 else None


class BankEvents:
    def __init__(
        self,
        bridge: BotBridge,
        *,
        bank_channel: int | None = None,
        fallback_channel: int | None = None,
        day_channels: Mapping[str, int] | None = None,
    ) -> None:
        self._bridge = bridge
        self._bank_channel = bank_channel
        self._fallback_channel = fallback_channel or bank_channel
        self._day_channels = dict(day_channels or {})
        bridge.on_result(BOT, DM)(self._dm_answered)

    def handle(self, event: BankEvent) -> list[SiteAction]:
        """The bot actions one event asks for; an event type the hub does not act on gives none."""
        payload = event.payload
        if event.type == "request.assigned":
            return self._assigned(payload)
        if event.type == "request.updated":
            return self._updated(payload)
        if event.type == "snapshot.accepted":
            return self._snapshot(payload)
        return []

    def _channel_for(self, source: Mapping[str, Any]) -> int | None:
        day = source.get("raidDay")
        return self._day_channels.get(str(day)) if day else None

    def _assigned(self, payload: dict[str, Any]) -> list[SiteAction]:
        request = payload.get("request") or {}
        managers = payload.get("managers") or request.get("managers") or []
        content = messages.assigned(request)
        manage = {"request_id": str(request.get("id", "")), "revision": int(request.get("revision") or 0)}
        sent = []
        for manager in managers:
            user_id = _discord_id(manager)
            if user_id is None:
                continue
            sent.append(
                self._bridge.send(
                    BOT,
                    DM,
                    {"user_id": user_id, "content": content, "manage": manage, "fallback": messages.dm_failed(request)},
                )
            )
        return sent

    def _updated(self, payload: dict[str, Any]) -> list[SiteAction]:
        request = payload.get("request") or {}
        user_id = _discord_id(request.get("memberId"))
        if user_id is None:
            return []
        content = messages.updated(request, str(payload.get("change") or ""))
        return [self._bridge.send(BOT, DM, {"user_id": user_id, "content": content})]

    def _snapshot(self, payload: dict[str, Any]) -> list[SiteAction]:
        source = payload.get("source") or {}
        channel = self._channel_for(source) or self._bank_channel
        if channel is None:
            return []
        content = messages.snapshot_accepted(source, payload.get("receipt") or {}, payload.get("uploader"))
        return [self._bridge.send(BOT, POST, {"channel_id": str(channel), "content": content})]

    def _dm_answered(self, action: SiteAction, result: ActionResult) -> None:
        """The bot's final answer to a DM: after its retries, a DM that never went out goes to the fallback channel."""
        fallback = action.payload.get("fallback")
        if result.ok or not fallback or self._fallback_channel is None:
            return
        log.info("bank DM %s failed for good; posting to the fallback channel", action.id)
        self._bridge.send(BOT, POST, {"channel_id": str(self._fallback_channel), "content": str(fallback)})
