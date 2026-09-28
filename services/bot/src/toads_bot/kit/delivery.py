"""Getting Discord events to the hub when the hub is having a bad day.

An event the hub cannot take right now (network down, 5xx, a listener asking for a resend) waits in the bot's
EventOutbox and goes out again on the next action run, in order. A 409 means the hub forgot the bot (an API restart
empties its in-memory registry), so the bot registers again and resends at once. Any other 4xx is the hub refusing
the event for good, and it is dropped with a log line.
"""

from __future__ import annotations

import logging
from collections import deque

import httpx

from toads_bot.kit.contract import BotManifest, DiscordEvent, EventReceipt
from toads_bot.kit.link import HubLink

log = logging.getLogger(__name__)


def _retryable(exc: httpx.HTTPError) -> bool:
    return not isinstance(exc, httpx.HTTPStatusError) or exc.response.status_code >= 500


async def send_event(link: HubLink, manifest: BotManifest, event: DiscordEvent) -> EventReceipt:
    """Send one event, registering again first if the hub has forgotten this bot."""
    try:
        return await link.send_event(manifest.name, event)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code != 409:
            raise
    await link.register(manifest)
    return await link.send_event(manifest.name, event)


class EventOutbox:
    """Events waiting for the hub, oldest first. Bounded, so a long outage drops the oldest rather than the bot."""

    def __init__(self, limit: int = 1000) -> None:
        self._events: deque[DiscordEvent] = deque(maxlen=limit)

    def __len__(self) -> int:
        return len(self._events)

    async def deliver(self, link: HubLink, manifest: BotManifest, event: DiscordEvent) -> EventReceipt | None:
        """Send now, or keep the event for later if the hub cannot take it yet. None unless it went straight through."""
        if self._events:
            self._events.append(event)  # keep the order: older events go first
            await self.flush(link, manifest)
            return None
        try:
            return await send_event(link, manifest, event)
        except httpx.HTTPError as exc:
            if _retryable(exc):
                log.warning("hub could not take event %s; keeping it for later", event.event_id)
                self._events.append(event)
            else:
                log.warning("hub refused event %s", event.event_id, exc_info=True)
            return None

    async def flush(self, link: HubLink, manifest: BotManifest) -> int:
        """Send waiting events in order until the hub fails again; returns how many went out or were dropped."""
        done = 0
        while self._events:
            event = self._events[0]
            try:
                await send_event(link, manifest, event)
            except httpx.HTTPError as exc:
                if _retryable(exc):
                    return done
                log.warning("hub refused event %s", event.event_id, exc_info=True)
            self._events.popleft()
            done += 1
        return done
