"""Environment-only configuration. A missing variable stops startup before any port opens (REQ-DEV-CFG-001)."""

from __future__ import annotations

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TOADS_", extra="ignore")

    database_url: SecretStr
    redis_url: str
    discord_client_id: str
    discord_client_secret: SecretStr
    discord_guild_id: int
    public_base_url: str
    raid_days_config: Path = Path("config/raid_days.yaml")
    session_ttl_seconds: int = 7 * 24 * 3600
    role_refresh_seconds: int = 15 * 60
