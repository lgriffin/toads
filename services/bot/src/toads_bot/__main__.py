from __future__ import annotations

import discord
from discord.ext import commands

from toads_bot.cogs.community import Community
from toads_bot.hub import HubClient
from toads_bot.settings import Settings


def create_bot(settings: Settings) -> commands.Bot:
    intents = discord.Intents.default()
    intents.members = True
    intents.message_content = True  # mirrored announcement channels are read so officers can curate them
    bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)
    guild = discord.Object(id=settings.discord_guild_id)

    @bot.event
    async def setup_hook() -> None:
        # Single-guild sync so slash commands appear instantly. Cogs (/log, /me, /claim) land in H4.
        hub = HubClient(settings.hub_api_url, settings.hub_service_token)
        await bot.add_cog(
            Community(
                bot,
                hub,
                guild_id=settings.discord_guild_id,
                mirror_channel_ids=set(settings.mirror_channel_ids),
                post_to_channels=settings.post_to_channels,
            )
        )
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)

    return bot


def main() -> None:
    settings = Settings()  # fails fast on a missing variable
    create_bot(settings).run(settings.discord_bot_token.get_secret_value(), log_handler=None)


if __name__ == "__main__":
    main()
