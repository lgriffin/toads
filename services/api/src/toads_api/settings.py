"""Environment-only configuration. A missing variable stops startup before any port opens (REQ-DEV-CFG-001)."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TOADS_", extra="ignore")

    database_url: SecretStr
    redis_url: str
    discord_client_id: str
    discord_client_secret: SecretStr
    # Bot token: only used at startup to list the server's roles (REQ-HUB-DAY-022).
    discord_bot_token: SecretStr
    discord_guild_id: int
    # Must match a redirect registered on the Discord application exactly.
    discord_redirect_uri: str
    # Browser-facing authorize page and server-side API base; the dev stack points both at the fake Discord.
    discord_authorize_url: str = "https://discord.com/oauth2/authorize"
    discord_api_base: str = "https://discord.com/api/v10"
    public_base_url: str
    raid_days_config: Path = Path("config/raid_days.yaml")
    # The bot's credential for the /api/bot/* routes. Shared with services/bot's TOADS_HUB_SERVICE_TOKEN.
    hub_service_token: SecretStr
    community_config: Path = Path("config/community.yaml")
    # The CBA and RPB spreadsheets the worker imports (config/raid_sheets.example.yaml).
    raid_sheets_config: Path = Path("config/raid_sheets.yaml")
    session_ttl_seconds: int = Field(default=7 * 24 * 3600, gt=0)
    # REQ-HUB-RBAC-002: Discord roles are re-read at least this often.
    role_refresh_seconds: int = Field(default=15 * 60, gt=0, le=15 * 60)
    # How long a started login (state + PKCE verifier) stays usable.
    login_ttl_seconds: int = Field(default=600, gt=0)
