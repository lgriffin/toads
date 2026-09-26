"""Dependencies for the community routes: the store, and the bot's service-token check."""

from __future__ import annotations

import hmac
from functools import lru_cache

from fastapi import Depends, Header, HTTPException, status

from toads_api.community.config import CommunityConfig
from toads_api.community.settings import CommunitySettings, get_community_settings
from toads_api.community.store import CommunityStore
from toads_api.rbac import RaidDaysConfig


@lru_cache(maxsize=1)
def get_store() -> CommunityStore:
    settings = get_community_settings()
    path = settings.raid_days_config
    raid_days = RaidDaysConfig.load(path) if path.exists() else RaidDaysConfig()
    return CommunityStore(config=CommunityConfig.load(settings.community_config), raid_days=raid_days)


async def require_service(
    authorization: str = Header(default=""),
    settings: CommunitySettings = Depends(get_community_settings),  # noqa: B008
) -> None:
    """The bot authenticates with `Authorization: Bearer <service token>`, compared in constant time."""
    scheme, _, token = authorization.partition(" ")
    expected = settings.hub_service_token.get_secret_value()
    if (
        scheme.lower() != "bearer"
        or not token
        or not expected
        or not hmac.compare_digest(token.encode(), expected.encode())
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not the bot")
