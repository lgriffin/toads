"""Turning a BotSpec into a running discord.py bot."""

from __future__ import annotations

from dataclasses import dataclass

import discord
from discord.ext import commands, tasks
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from toads_bot.kit.binding import ActionHandler, Binding, BotContext
from toads_bot.kit.contract import BotManifest
from toads_bot.kit.gate import Gate, OpenGate
from toads_bot.kit.link import HttpHubLink, HubLink
from toads_bot.kit.runner import ActionRunner


class KitSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TOADS_", extra="ignore")

    discord_bot_token: SecretStr
    discord_guild_id: int
    hub_api_url: str
    hub_service_token: SecretStr
    # Which spec in toads_bot.kit.specs.SPECS this process runs; one process per bot.
    bot_spec: str = "relay"
    # The channels this bot works in (JSON list, e.g. [111, 222]).
    bot_channel_ids: list[int] = []
    bot_poll_seconds: float = Field(default=15.0, ge=1.0)


@dataclass(frozen=True)
class BotSpec:
    name: str
    description: str
    bindings: tuple[type[Binding], ...]
    # Read message text (a privileged intent in the Discord developer portal); only bots that relay messages need it.
    message_content: bool = False
    members: bool = False

    def manifest(self) -> BotManifest:
        kinds = [kind for b in self.bindings for kind in b.site_actions]
        if len(kinds) != len(set(kinds)):
            raise ValueError(f"{self.name}: two bindings carry out the same action kind")
        events = sorted({kind for b in self.bindings for kind in b.discord_events})
        return BotManifest(name=self.name, description=self.description, actions=sorted(kinds), events=events)


def build_bot(
    spec: BotSpec, settings: KitSettings, *, link: HubLink | None = None, gate: Gate | None = None
) -> commands.Bot:
    """A discord.py bot for `spec`. Nothing connects until the bot runs: setup_hook registers the manifest with the
    hub, adds each binding as a cog, starts pulling site actions and syncs slash commands to the one guild."""
    manifest = spec.manifest()  # fails fast on clashing bindings
    intents = discord.Intents.default()
    intents.message_content = spec.message_content
    intents.members = spec.members
    bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)
    hub = link or HttpHubLink(settings.hub_api_url, settings.hub_service_token)
    ctx = BotContext(
        name=spec.name,
        guild_id=settings.discord_guild_id,
        link=hub,
        gate=gate or OpenGate(),
        channel_ids=frozenset(settings.bot_channel_ids),
    )

    @bot.event
    async def setup_hook() -> None:
        await hub.register(manifest)
        handlers: dict[str, ActionHandler] = {}
        for binding_type in spec.bindings:
            binding = binding_type(bot, ctx)
            await bot.add_cog(binding)
            handlers.update(binding.handlers())
        runner = ActionRunner(spec.name, hub, handlers)
        poll = tasks.loop(seconds=settings.bot_poll_seconds)(runner.run_once)
        poll.before_loop(bot.wait_until_ready)
        poll.start()
        guild = discord.Object(id=settings.discord_guild_id)
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)

    return bot
