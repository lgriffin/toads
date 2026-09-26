from __future__ import annotations

import discord
from discord.ext import commands

from toads_bot.settings import Settings


def create_bot(settings: Settings) -> commands.Bot:
    intents = discord.Intents.default()
    intents.members = True
    bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)
    guild = discord.Object(id=settings.discord_guild_id)

    @bot.event
    async def setup_hook() -> None:
        # Single-guild sync so slash commands appear instantly. Cogs (/log, /me, /claim) land in H4.
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)

    return bot


def main() -> None:
    settings = Settings()  # fails fast on a missing variable
    create_bot(settings).run(settings.discord_bot_token.get_secret_value(), log_handler=None)


if __name__ == "__main__":
    main()
