from __future__ import annotations

from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TOADS_", extra="ignore")

    database_url: SecretStr
    redis_url: str
    wcl_client_id: str
    wcl_client_secret: SecretStr
    wcl_guild_id: int
    wcl_api_url: str = "https://fresh.warcraftlogs.com/api/v2/client"
    wcl_throttle_ms: int = 250
    wcl_max_retries: int = 3
    # Same value as the API's: decrypts members' own Warcraft Logs keys (comma-separated Fernet keys, newest first).
    credentials_keys: SecretStr
    # Raid sheets import (jobs/sheets.py): the API it posts to and the service token it posts with.
    hub_api_url: str = "http://api:8000"
    hub_service_token: SecretStr = SecretStr("")
    raid_sheets_config: Path = Path("config/raid_sheets.yaml")
    # `toads-worker schedule`: how often it rebuilds the hub's analyzer widgets and performance numbers, and imports
    # the raid sheets. 0 turns that job off.
    hub_refresh_minutes: int = Field(default=30, ge=0)
    sheets_refresh_minutes: int = Field(default=360, ge=0)
    # The guild-report sync (jobs/sync.py): minutes between runs (0 turns it off), the share of the guild key's hourly
    # Warcraft Logs points it leaves for everything else, and an optional cap on reports per run (0: the rate limit
    # alone decides).
    sync_refresh_minutes: int = Field(default=15, ge=0)
    sync_reserve_percent: int = Field(default=20, ge=0, le=90)
    sync_batch: int = Field(default=0, ge=0)
