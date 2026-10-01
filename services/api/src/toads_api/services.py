"""Everything a request needs, built once at startup. Tests build their own with fakes."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo

import httpx
from hub_db import CredentialCipher
from redis.asyncio import Redis
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from toads_api.account.service import AccountService
from toads_api.account.sql import SqlAccountRepository
from toads_api.bank.client import BankClient
from toads_api.bank.events import BankEvents
from toads_api.bots.bridge import BotBridge, InMemoryBridgeStore
from toads_api.characters import CharacterDirectory, NoCharacters
from toads_api.community.config import CommunityConfig
from toads_api.community.service import CommunityService, RaidDayDirectory
from toads_api.community.sql_repository import SqlCommunityRepository
from toads_api.discord_api import DiscordAPI, HttpDiscord
from toads_api.home.badges import BadgeService
from toads_api.home.next_raid import NextRaidService, RaidSlot, parse_start
from toads_api.home.performance import PerformanceService
from toads_api.home.service import HomeService
from toads_api.home.sql import SqlHomeRepository
from toads_api.notify import Notifier, RedisOutbox
from toads_api.raid_sheets.config import RaidSheetsConfig
from toads_api.raid_sheets.dates import weekday_named
from toads_api.raid_sheets.service import RaidSheetService
from toads_api.raid_sheets.sql import SqlSheetRepository
from toads_api.rbac.config import RaidDaysConfig
from toads_api.reference.login import WclLogin
from toads_api.reference.queue import RqEnqueue
from toads_api.reference.service import ReferenceService
from toads_api.reference.sql import SqlReferenceRepository
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
    community: CommunityService = field(init=False)
    account: AccountService = field(init=False)
    home: HomeService = field(init=False)
    performance: PerformanceService = field(init=False)
    badges: BadgeService = field(init=False)
    next_raid: NextRaidService = field(init=False)
    raid_sheets: RaidSheetService = field(init=False)
    reference: ReferenceService = field(init=False)
    wcl_login: WclLogin = field(init=False)
    bots: BotBridge = field(init=False)
    # The guild bank (docs/bank.md): None until TOADS_BANK_URL and TOADS_BANK_SERVICE_TOKEN are set.
    bank: BankClient | None = field(init=False)
    bank_events: BankEvents = field(init=False)

    def __post_init__(self) -> None:
        # Two-way Discord bots (docs/bots.md). In memory until the bridge has a table: a restart drops queued actions.
        self.bots = BotBridge(InMemoryBridgeStore(), clock=lambda: self.clock())
        self.bank = None
        if self.settings.bank_url and self.settings.bank_service_token.get_secret_value():
            if self.http is None:
                self.http = httpx.AsyncClient(timeout=10.0)
            self.bank = BankClient(self.http, self.settings.bank_url, self.settings.bank_service_token)
        self.bank_events = BankEvents(
            self.bots,
            bank_channel=self.settings.bank_channel_id,
            fallback_channel=self.settings.bank_fallback_channel_id,
            day_channels={
                d.id: channel for d in self.raid_days.raid_days if (channel := d.channels.bank_requests) is not None
            },
        )
        cipher = CredentialCipher.from_setting(self.settings.credentials_keys.get_secret_value())
        self.account = AccountService(SqlAccountRepository(self.db, cipher))
        home_repo = SqlHomeRepository(self.db)
        self.home = HomeService(home_repo)
        self.performance = PerformanceService(home_repo)
        self.badges = BadgeService(home_repo)
        self.wcl_login = WclLogin(self.settings, self.redis, self.http)
        self.reference = ReferenceService(
            SqlReferenceRepository(self.db, cipher),
            RqEnqueue(self.settings.redis_url),
            configured=self.wcl_login.configured,
        )
        self.sessions = SessionStore(
            self.redis, session_ttl=self.settings.session_ttl_seconds, login_ttl=self.settings.login_ttl_seconds
        )
        self.community = CommunityService(
            repo=SqlCommunityRepository(self.db, shown_names=self.account.shown_names),
            config=CommunityConfig.load(self.settings.community_config),
            raid_days=RaidDayDirectory(
                day_ids=frozenset(d.id for d in self.raid_days.raid_days),
                global_officer_roles=tuple(self.raid_days.global_officer_roles),
                officer_roles={d.id: tuple(d.officer_roles) for d in self.raid_days.raid_days},
            ),
        )

        sheets_config = RaidSheetsConfig.load(self.settings.raid_sheets_config)
        weekdays = {
            d.id: day
            for d in self.raid_days.raid_days
            if (day := sheets_config.weekdays.get(d.id, weekday_named(d.name))) is not None
        }
        self.raid_sheets = RaidSheetService(repo=SqlSheetRepository(self.db), config=sheets_config, weekdays=weekdays)
        self.next_raid = NextRaidService(
            self.discord.scheduled_events,
            guild_id=self.settings.discord_guild_id,
            slots=[
                RaidSlot(d.id, d.name, weekdays[d.id], parse_start(d.start_time))
                for d in self.raid_days.raid_days
                if d.start_time is not None and d.id in weekdays
            ],
            timezone=ZoneInfo(self.raid_days.timezone),
            clock=lambda: self.clock(),
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
