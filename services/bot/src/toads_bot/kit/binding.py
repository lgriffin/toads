"""A Binding is one feature of a bot, bound both ways to the hub.

- Site to Discord: `site_actions` maps each action kind the binding carries out to the name of an async method that
  takes the SiteAction and returns the Discord ids it made (or None). The runner calls it and reports the result.
- Discord to site: `discord_events` lists the event kinds the binding sends; its listeners call `emit`.

Both lists go into the bot's manifest, so the hub refuses actions and events a bot never declared.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, ClassVar

from discord.ext import commands
from pydantic import SecretStr

from toads_bot.kit.contract import BotManifest, DiscordEvent, EventReceipt, SiteAction
from toads_bot.kit.delivery import EventOutbox
from toads_bot.kit.gate import Gate
from toads_bot.kit.link import HubLink

Refs = dict[str, int | str]
ActionHandler = Callable[[SiteAction], Awaitable[Refs | None]]


@dataclass(frozen=True)
class BotContext:
    """What every binding of one bot shares."""

    manifest: BotManifest
    guild_id: int
    link: HubLink
    gate: Gate
    channel_ids: frozenset[int] = frozenset()
    outbox: EventOutbox = field(default_factory=EventOutbox)
    # For bindings that call the hub's member routes on a member's behalf (the bank's), beyond the bridge.
    hub_api_url: str = ""
    hub_service_token: SecretStr = field(default_factory=lambda: SecretStr(""))

    @property
    def name(self) -> str:
        return self.manifest.name


class Binding(commands.Cog):
    site_actions: ClassVar[Mapping[str, str]] = {}
    discord_events: ClassVar[tuple[str, ...]] = ()

    def __init__(self, bot: commands.Bot, ctx: BotContext) -> None:
        self.bot = bot
        self.ctx = ctx

    def handlers(self) -> dict[str, ActionHandler]:
        found: dict[str, ActionHandler] = {}
        for kind, method in self.site_actions.items():
            handler: Any = getattr(self, method)
            found[kind] = handler
        return found

    async def emit(
        self,
        kind: str,
        *,
        event_id: str,
        channel_id: int | None = None,
        user_id: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> EventReceipt | None:
        """Send an event to the hub. None when the hub could not take it yet (it is kept and resent) or refused it."""
        if kind not in self.discord_events:
            raise ValueError(f"{type(self).__name__} does not declare {kind!r} events")
        event = DiscordEvent(
            event_id=event_id,
            kind=kind,
            occurred_at=datetime.now(UTC),
            guild_id=self.ctx.guild_id,
            channel_id=channel_id,
            user_id=user_id,
            payload=payload or {},
        )
        return await self.ctx.outbox.deliver(self.ctx.link, self.ctx.manifest, event)
