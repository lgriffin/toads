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
