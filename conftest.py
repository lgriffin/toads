"""Shared fixtures: a full hub API wired to the fake Discord server, fakeredis and in-memory SQLite.

No network and no real Discord credentials: the API's Discord client talks to
`toads_api.testing.fake_discord` through an httpx ASGI transport.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
from fakeredis import FakeAsyncRedis
from fastapi.testclient import TestClient
from hub_db import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from toads_api.characters import InMemoryCharacters
from toads_api.discord_api import HttpDiscord
from toads_api.main import create_app
from toads_api.notify import RedisOutbox
from toads_api.rbac.config import RaidDaysConfig
from toads_api.services import Services
from toads_api.sessions import SESSION_COOKIE
from toads_api.settings import Settings
from toads_api.testing.fake_discord import FakeDiscordState, FakeUser, create_fake_discord

HUB = "https://hub.test"
DISCORD = "https://discord.test"
GUILD_ID = 77

# Role ids: Wednesday trial/raider/officer 10/11/12, Sunday 20/21/22, global officer 900.
ROLES = {
    ("wed", "trial"): 10,
    ("wed", "raider"): 11,
    ("wed", "officer"): 12,
    ("sun", "trial"): 20,
    ("sun", "raider"): 21,
    ("sun", "officer"): 22,
    ("global", "officer"): 900,
}
RAID_DAYS = RaidDaysConfig.model_validate(
    {
        "global_officer_roles": [900],
        "raid_days": [
            {"id": "wed", "name": "Wednesday", "trial_roles": [10], "raider_roles": [11], "officer_roles": [12]},
            {"id": "sun", "name": "Sunday", "trial_roles": [20], "raider_roles": [21], "officer_roles": [22]},
        ],
    }
)


def make_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "database_url": "sqlite://",
        "redis_url": "redis://fake",
        "discord_client_id": "toads-dev",
        "discord_client_secret": "replace-me",
        "discord_bot_token": "replace-me",
        "discord_guild_id": GUILD_ID,
        "discord_redirect_uri": f"{HUB}/auth/callback",
        "discord_authorize_url": f"{DISCORD}/oauth2/authorize",
        "discord_api_base": f"{DISCORD}/api/v10",
        "public_base_url": HUB,
        "raid_days_config": Path("unused.yaml"),
    }
    values.update(overrides)
    return Settings(**values)


class Hub:
    """The API under test plus handles on every fake behind it."""

    def __init__(self, raid_days: RaidDaysConfig = RAID_DAYS) -> None:
        self.now = 1_000_000.0
        self.fake = FakeDiscordState(guild_id=GUILD_ID, guild_roles=set(ROLES.values()))
        self.fake_app = create_fake_discord(self.fake)
        self.discord = TestClient(self.fake_app, base_url=DISCORD)
        self.characters = InMemoryCharacters({1: "Hopscotch", 2: "Ribbit", 3: "Croak", 4: "Höpscotch"})
        self.engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.db: sessionmaker[Session] = sessionmaker(self.engine, expire_on_commit=False)
        self.redis = FakeAsyncRedis()
        settings = make_settings()
        http = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.fake_app))
        self.services = Services(
            settings=settings,
            raid_days=raid_days,
            redis=self.redis,
            discord=HttpDiscord(
                http,
                api_base=settings.discord_api_base,
                client_id=settings.discord_client_id,
                client_secret=settings.discord_client_secret,
                bot_token=settings.discord_bot_token,
                redirect_uri=settings.discord_redirect_uri,
                guild_id=GUILD_ID,
            ),
            db=self.db,
            characters=self.characters,
            notifier=RedisOutbox(self.redis),
            clock=lambda: self.now,
            http=http,
        )
        self.app = create_app(self.services)
        self.client = TestClient(self.app, base_url=HUB)
        self._next_user = 5000

    # --- people -----------------------------------------------------------------------------------

    def user(self, *roles: tuple[str, str], nick: str | None = None, in_guild: bool = True) -> FakeUser:
        self._next_user += 1
        return self.fake.add_user(
            FakeUser(
                self._next_user,
                f"user{self._next_user}",
                nick=nick,
                roles={ROLES[r] for r in roles},
                in_guild=in_guild,
            )
        )

    def start_login(self) -> httpx.Response:
        return self.client.get("/auth/login", follow_redirects=False)

    def authorize(self, login: httpx.Response, user: FakeUser) -> str:
        """Follow /auth/login's redirect through the fake Discord; returns the callback URL it sends back."""
        location = login.headers["location"]
        assert location.startswith(f"{DISCORD}/oauth2/authorize?")
        r = self.discord.get(f"{location.removeprefix(DISCORD)}&login_as={user.user_id}", follow_redirects=False)
        assert r.status_code == 302, r.text
        return r.headers["location"]

    def callback(self, url: str) -> httpx.Response:
        return self.client.get(url.removeprefix(HUB), follow_redirects=False)

    def login(self, user: FakeUser) -> str:
        """Full sign-in; returns the session id and leaves the client's cookie jar empty."""
        r = self.callback(self.authorize(self.start_login(), user))
        assert r.status_code == 303, r.text
        session_id = r.cookies[SESSION_COOKIE]
        self.client.cookies.clear()
        return session_id

    def as_(self, session_id: str | None) -> dict[str, str]:
        return {"cookie": f"{SESSION_COOKIE}={session_id}"} if session_id else {}

    def get(self, path: str, session_id: str | None) -> httpx.Response:
        return self.client.get(path, headers=self.as_(session_id))

    def post(self, path: str, session_id: str | None, json: object = None) -> httpx.Response:
        return self.client.post(path, headers=self.as_(session_id), json=json)

    def delete(self, path: str, session_id: str | None) -> httpx.Response:
        return self.client.delete(path, headers=self.as_(session_id))

    def pass_time(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def hub() -> Iterator[Hub]:
    h = Hub()
    with h.client:
        yield h
