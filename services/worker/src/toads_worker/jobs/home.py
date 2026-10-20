"""Builds the analyzer's home page (wcl_app.home, the same widgets as the desktop app's Home) from the guild's raids
in wcl-store and publishes it to the hub API, which serves it to members' hub homes.

The API decides which widgets it keeps; this job builds the analyzer widgets the hub places and posts them with the
service token. The API's answer names each raid night's weekday, and the job then builds the same widgets from that
night's raids only, one page per night, for the Logs page (docs/logs.md). `toads-worker schedule` runs it every
TOADS_HUB_REFRESH_MINUTES; run it by hand after new raids are analysed with `toads-worker publish-home`, or enqueue
`publish_home_page`.
"""

from __future__ import annotations

from typing import Any

import httpx
from wcl_app import HomeLayout, HomeService
from wcl_app.context import StorageFactory
from wcl_store import RaidScope

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


def build_page(storage: StorageFactory, weekday: int | None = None) -> dict[str, Any]:
    """The page as JSON, from every guild raid or only those raided on `weekday` (0 is Monday). A widget that fails
    to build carries its own `error`; the rest still build."""
    scope = RaidScope(weekdays=(weekday,)) if weekday is not None else None
    return HomeService(storage, scope=scope).page(HomeLayout.of(HUB_WIDGETS)).to_dict()


def publish_home_page(
    settings: Settings | None = None,
    *,
    storage: StorageFactory | None = None,
    hub: httpx.Client | None = None,
) -> dict[str, Any]:
    """Build the guild-wide page and PUT it to the hub API, then each raid night's page the API asked for. Returns
    the API's answer (how many widgets it kept, and the nights) with `night_widgets`, the widgets kept per night."""
    settings = settings or Settings()
    hub_api.service_token(settings)
    storage = storage or store.storage(settings)
    answer = hub_api.put(settings, "/api/worker/home-page", build_page(storage), hub)
    nights: dict[str, int] = answer.get("nights") or {}
    kept = {}
    for day, weekday in nights.items():
        night = hub_api.put(settings, f"/api/worker/home-page/nights/{day}", build_page(storage, weekday), hub)
        kept[day] = night["widgets"]
    return {**answer, "night_widgets": kept} if nights else answer
