"""Builds the analyzer's home page (wcl_app.home, the same widgets as the desktop app's Home) from the guild's raids
in wcl-store and publishes it to the hub API, which serves it to members' hub homes.

The API decides which widgets it keeps; this job builds the analyzer widgets the hub places and posts them with the
service token. `toads-worker schedule` runs it every TOADS_HUB_REFRESH_MINUTES; run it by hand after new raids are
analysed with `toads-worker publish-home`, or enqueue `publish_home_page`.
"""

from __future__ import annotations

from typing import Any

import httpx
from wcl_app import HomeLayout, HomeService
from wcl_app.context import StorageFactory

from toads_worker import hub_api, store
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
    # Officer-only on the hub: the last raid's roster with their badges.
    "badges",
    "boss_kills",
    "class_mix",
    "interrupts",
    "consumables",
    "flasks",
)


def build_page(storage: StorageFactory) -> dict[str, Any]:
    """The page as JSON. A widget that fails to build carries its own `error`; the rest still build."""
    return HomeService(storage).page(HomeLayout.of(HUB_WIDGETS)).to_dict()


def publish_home_page(
    settings: Settings | None = None,
    *,
    storage: StorageFactory | None = None,
    hub: httpx.Client | None = None,
) -> dict[str, Any]:
    """Build the page and PUT it to the hub API. Returns the API's answer (how many widgets it kept)."""
    settings = settings or Settings()
    hub_api.service_token(settings)
    return hub_api.put(settings, "/api/worker/home-page", build_page(storage or store.storage(settings)), hub)
