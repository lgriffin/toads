"""Builds the analyzer's home page (wcl_app.home, the same widgets as the desktop app's Home) from the guild's raids
in wcl-store and publishes it to the hub API, which serves it to members' hub homes.

The API decides which widgets it keeps; this job builds the analyzer widgets the hub places and posts them with the
service token. Run it after new raids are analysed: `toads-worker publish-home`, or enqueue `publish_home_page`.
"""

from __future__ import annotations

from typing import Any

import httpx
from wcl_app import HomeLayout, HomeService
from wcl_app.context import StorageFactory

from toads_worker import store
from toads_worker.settings import Settings

# The analyzer widgets the hub places (toads_api.home.service.CATALOGUE). The analyzer's quick actions and tracked
# players have no hub page, so they are not built.
HUB_WIDGETS = (
    "guild_snapshot",
    "last_raid",
    "recent_raids",
    "raid_activity",
    "healing_weekly",
    "healers_weekly",
    "top_damage",
    "top_healing",
    "attendance",
    "boss_kills",
    "class_mix",
    "interrupts",
    "consumables",
)


def build_page(storage: StorageFactory, healing_target: float | None = None) -> dict[str, Any]:
    """The page as JSON. A widget that fails to build carries its own `error`; the rest still build.
    `healing_target` is the guild's healing per raid the weekly healing chart measures each week against."""
    return HomeService(storage, healing_target=healing_target).page(HomeLayout.of(HUB_WIDGETS)).to_dict()


def publish_home_page(
    settings: Settings | None = None,
    *,
    storage: StorageFactory | None = None,
    hub: httpx.Client | None = None,
) -> dict[str, Any]:
    """Build the page and PUT it to the hub API. Returns the API's answer (how many widgets it kept)."""
    settings = settings or Settings()
    token = settings.hub_service_token.get_secret_value()
    if not token:
        raise RuntimeError("TOADS_HUB_SERVICE_TOKEN is not set; the hub API would refuse the page")
    page = build_page(storage or store.storage(settings), settings.healing_target_per_raid)
    hub = hub or httpx.Client(base_url=settings.hub_api_url, timeout=30.0)
    r = hub.put("/api/worker/home-page", json=page, headers={"Authorization": f"Bearer {token}"})
    r.raise_for_status()
    answer: dict[str, Any] = r.json()
    return answer
