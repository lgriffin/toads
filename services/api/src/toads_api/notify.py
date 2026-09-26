"""Outbound notifications. The API never talks to Discord channels itself: it appends to a Redis
outbox that the bot drains (the bot has no DB credentials). Consuming the outbox lands with the bot's
officer commands; until then entries simply queue up.
"""

from __future__ import annotations

import json
from typing import Any, Protocol

from redis.asyncio import Redis

OFFICERS_OUTBOX = "toads:outbox:officers"


class Notifier(Protocol):
    async def notify_officers(self, event: dict[str, Any]) -> None: ...


class RedisOutbox:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def notify_officers(self, event: dict[str, Any]) -> None:
        await self._redis.rpush(OFFICERS_OUTBOX, json.dumps(event))
