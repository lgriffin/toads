"""Community-layer settings. Kept apart from the core Settings so auth work and this layer change independently."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class CommunitySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TOADS_", extra="ignore")

    # The bot's credential for the /api/bot/* routes. Shared with services/bot's TOADS_HUB_SERVICE_TOKEN.
    hub_service_token: SecretStr
    community_config: Path = Path("config/community.yaml")
    raid_days_config: Path = Path("config/raid_days.yaml")


@lru_cache(maxsize=1)
def get_community_settings() -> CommunitySettings:
    return CommunitySettings()  # values come from the environment
