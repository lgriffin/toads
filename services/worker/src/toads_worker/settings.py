from __future__ import annotations

from pydantic import SecretStr
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
