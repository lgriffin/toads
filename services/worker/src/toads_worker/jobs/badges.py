"""Every raider's Toads badges (wcl_app.badges: raids attended and consumables used across the guild's raids),
published to the hub API so each member can see their own on /me (REQ-HUB-HOME-011).

Badges are worked out from wcl-store by the analyzer's BadgeService, as the desktop app's Player page shows them; the
last raid's roster reaches raid leaders through the analyzer's `badges` home widget (jobs/home.py) instead.
`toads-worker schedule` runs it every TOADS_HUB_REFRESH_MINUTES, or run `toads-worker publish-badges`.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

import httpx
from wcl_app import BadgeService
from wcl_app.badges import BADGES_SCHEMA_VERSION
from wcl_app.context import StorageFactory

from toads_worker import hub_api, store
from toads_worker.settings import Settings

# The hub API's MAX_BADGE_PLAYERS. `for_guild` ranks by tiers earned, so a longer history keeps its most decorated.
MAX_PLAYERS = 1000


def build_page(storage: StorageFactory, *, now: Callable[[], datetime] = datetime.now) -> dict[str, Any]:
    """The page as JSON: every character who has raided with the guild, each with every badge, earned or not."""
    players = BadgeService(storage).for_guild()[:MAX_PLAYERS]
    return {
        "version": BADGES_SCHEMA_VERSION,
        "generated_at": now().strftime("%Y-%m-%d %H:%M:%S"),
        "players": [p.to_dict() for p in players],
    }


def publish_badges(
    settings: Settings | None = None,
    *,
    storage: StorageFactory | None = None,
    hub: httpx.Client | None = None,
) -> dict[str, Any]:
    """Build the page and PUT it to the hub API. Returns the API's answer (how many players it kept)."""
    settings = settings or Settings()
    hub_api.service_token(settings)
    return hub_api.put(settings, "/api/worker/badges", build_page(storage or store.storage(settings)), hub)
