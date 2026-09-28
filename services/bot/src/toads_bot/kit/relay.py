"""The example binding, and the smallest useful two-way bot: it relays text between the site and chosen channels.

- Site to Discord: a `say` action ({"channel_id": ..., "text": ...}) posts the text to one of the bot's channels.
- Discord to site: every member message in the bot's channels becomes a `message` event.
Nothing it posts can ping anyone.
"""

from __future__ import annotations

from typing import Any, ClassVar

import discord
from discord.ext import commands

from toads_bot.kit.binding import Binding, Refs
from toads_bot.kit.contract import SiteAction

NO_PINGS = discord.AllowedMentions.none()


class Relay(Binding):
    site_actions: ClassVar[dict[str, str]] = {"say": "say"}
    discord_events: ClassVar[tuple[str, ...]] = ("message",)

    async def say(self, action: SiteAction) -> Refs:
        channel_id = int(action.payload["channel_id"])
        channel = self.bot.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel | discord.Thread) or channel_id not in self.ctx.channel_ids:
            raise LookupError(f"channel {channel_id} is not one of this bot's channels")
        sent = await channel.send(str(action.payload["text"])[:2000], allowed_mentions=NO_PINGS)
        return {"channel_id": channel_id, "message_id": int(sent.id)}

    @commands.Cog.listener()
    async def on_message(self, message: Any) -> None:
        if message.author.bot or message.guild is None or message.guild.id != self.ctx.guild_id:
            return
        if message.channel.id not in self.ctx.channel_ids or not self.ctx.gate.allows(
            message.author.id, "relay.message"
        ):
            return
        await self.emit(
            "message",
            event_id=f"message:{message.id}",
            channel_id=message.channel.id,
            user_id=message.author.id,
            payload={
                "message_id": message.id,
                "author_name": str(message.author.display_name)[:100],
                "content": str(message.content)[:4000],
            },
        )
