from __future__ import annotations

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TOADS_", extra="ignore")

    discord_bot_token: SecretStr
    discord_guild_id: int
    hub_api_url: str
    hub_service_token: SecretStr
    post_to_channels: bool = False
