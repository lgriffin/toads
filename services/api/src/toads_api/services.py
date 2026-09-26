"""Everything a request needs, built once at startup. Tests build their own with fakes."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

import httpx
from redis.asyncio import Redis
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from toads_api.characters import CharacterDirectory, NoCharacters
from toads_api.discord_api import DiscordAPI, HttpDiscord
from toads_api.notify import Notifier, RedisOutbox
from toads_api.rbac.config import RaidDaysConfig
from toads_api.sessions import SessionStore
from toads_api.settings import Settings


@dataclass
class Services:
    settings: Settings
    raid_days: RaidDaysConfig
    redis: Redis
    discord: DiscordAPI
    db: sessionmaker[Session]
    characters: CharacterDirectory
    notifier: Notifier
    clock: Callable[[], float] = time.time
    http: httpx.AsyncClient | None = None
    sessions: SessionStore = field(init=False)

    def __post_init__(self) -> None:
        self.sessions = SessionStore(
            self.redis, session_ttl=self.settings.session_ttl_seconds, login_ttl=self.settings.login_ttl_seconds
        )

    async def verify_discord_roles(self) -> None:
        """REQ-HUB-DAY-022: refuse to start when the raid-day config names a role the server lacks."""
        self.raid_days.check_roles_exist(await self.discord.guild_role_ids())

    async def aclose(self) -> None:
        if self.http is not None:
            await self.http.aclose()
        await self.redis.aclose()


def build_services(settings: Settings) -> Services:
    http = httpx.AsyncClient(timeout=10.0)
    redis = Redis.from_url(settings.redis_url)
    engine = create_engine(settings.database_url.get_secret_value(), pool_pre_ping=True)
    return Services(
        settings=settings,
        raid_days=RaidDaysConfig.load(settings.raid_days_config),
        redis=redis,
        discord=HttpDiscord(
            http,
            api_base=settings.discord_api_base,
            client_id=settings.discord_client_id,
            client_secret=settings.discord_client_secret,
            bot_token=settings.discord_bot_token,
            redirect_uri=settings.discord_redirect_uri,
            guild_id=settings.discord_guild_id,
        ),
        db=sessionmaker(engine, expire_on_commit=False),
        characters=NoCharacters(),
        notifier=RedisOutbox(redis),
        http=http,
    )
