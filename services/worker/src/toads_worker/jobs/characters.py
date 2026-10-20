"""Each member's character pages (wcl_app.character_pages: their raids against the raid's median, lineage, personal
bests and a chart per role), published to the hub API for their Me page (REQ-HUB-ME-001).

The hub names the characters it wants, every name a member may go by, so the worker builds pages only for members and
never for the guild's whole history. Pages are built from wcl-store by the analyzer's CharacterPageService, as the
desktop app's character profile shows them. `toads-worker schedule` runs it every TOADS_HUB_REFRESH_MINUTES, or run
`toads-worker publish-characters`.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import datetime
from typing import Any

import httpx
import structlog
from wcl_app import CharacterPageService
from wcl_app.character_pages import CHARACTER_PAGE_VERSION
from wcl_app.context import StorageFactory

from toads_worker import hub_api, store
from toads_worker.settings import Settings

log = structlog.get_logger(__name__)

# The hub API's MAX_CHARACTER_PAGES.
MAX_PAGES = 2000


def build_pages(
    storage: StorageFactory, names: Iterable[str], *, now: Callable[[], datetime] = datetime.now
) -> dict[str, Any]:
    """The pages as JSON: one for each named character who has raided with the guild, each once."""
    pages: dict[str, dict[str, Any]] = {}
    # One storage session for the whole roster; each raid's analysis is read once.
    for page in CharacterPageService(storage).pages(list(names)):
        # Two names can lead to one character (a claim and a nickname differing in case); the hub stores it once.
        if page is not None and page.name.casefold() not in pages:
            pages[page.name.casefold()] = page.to_dict()
    if len(pages) > MAX_PAGES:
        log.warning("characters.pages_capped", pages=len(pages), kept=MAX_PAGES)
    return {
        "version": CHARACTER_PAGE_VERSION,
        "generated_at": now().strftime("%Y-%m-%d %H:%M:%S"),
        "pages": list(pages.values())[:MAX_PAGES],
    }


def publish_character_pages(
    settings: Settings | None = None,
    *,
    storage: StorageFactory | None = None,
    hub: httpx.Client | None = None,
) -> dict[str, Any]:
    """Ask the hub which characters it wants, build their pages and PUT them. Returns the API's answer (how many
    pages it kept)."""
    settings = settings or Settings()
    hub_api.service_token(settings)
    storage = storage or store.storage(settings)
    with hub_api.client(settings, hub) as client:
        wanted = hub_api.get(settings, "/api/worker/character-pages/wanted", client)
        body = build_pages(storage, [str(n) for n in wanted.get("names", [])])
        return hub_api.put(settings, "/api/worker/character-pages", body, client)
