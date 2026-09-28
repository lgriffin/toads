"""Every raider's primary number in the guild's last raid against the guild median for the same role, published to the
hub API for members' "Your performance" widget (REQ-HUB-HOME-007).

Raids are read through the analyzer's services layer (wcl_app.RaidService), as the desktop app reads them. The page
holds the whole raid; the API hands each member only their own character's entry (REQ-HUB-PRIV-001).
`toads-worker schedule` runs it every TOADS_HUB_REFRESH_MINUTES, or run `toads-worker publish-performance`.
"""

from __future__ import annotations

import statistics
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx
from wcl_app import AppContext, RaidService
from wcl_app.context import StorageFactory
from wcl_core.models import RaidAnalysis

from toads_worker import hub_api, store
from toads_worker.settings import Settings

# The hub API's PERFORMANCE_VERSION; bump both together when a field changes meaning.
PAGE_VERSION = 1
# The last raid and the ones before it, for each character's recent trend.
RECENT_RAIDS = 5
# Each role's primary metric: what the widget compares against the role's median. Tanks are compared on mitigation
# rather than damage taken, which depends more on the pulls than on the tank.
METRICS: dict[str, tuple[str, str]] = {
    "tank": ("Mitigation", "percent"),
    "healer": ("Healing", "amount"),
    "melee": ("Damage", "amount"),
    "ranged": ("Damage", "amount"),
}


@dataclass(frozen=True)
class Score:
    name: str
    player_class: str
    role: str
    value: float


@dataclass(frozen=True)
class Standing:
    score: Score
    median: float
    rank: int
    of: int


def scores(analysis: RaidAnalysis) -> list[Score]:
    """One score per player in the role the analyzer gave them. A name seen twice keeps its first role."""
    found: dict[str, Score] = {}
    candidates = (
        [Score(t.name, t.player_class, "tank", t.mitigation_percent) for t in analysis.tanks]
        + [Score(h.name, h.player_class, "healer", h.total_healing) for h in analysis.healers]
        + [
            Score(d.name, d.player_class, "melee" if d.role == "melee" else "ranged", d.total_damage)
            for d in analysis.dps
        ]
    )
    for s in candidates:
        found.setdefault(s.name.casefold(), s)
    return list(found.values())


def standings(analysis: RaidAnalysis) -> dict[str, Standing]:
    """Each player's place in their role, keyed by case-folded name. The median is over the same role only
    (REQ-HUB-ME-002), so a healer is never measured against the damage dealers."""
    by_role: dict[str, list[Score]] = {}
    for s in scores(analysis):
        by_role.setdefault(s.role, []).append(s)
    out: dict[str, Standing] = {}
    for players in by_role.values():
        median = round(float(statistics.median(p.value for p in players)), 1)
        ranked = sorted(players, key=lambda p: p.value, reverse=True)
        for rank, p in enumerate(ranked, 1):
            out[p.name.casefold()] = Standing(p, median, rank, len(ranked))
    return out


def _raid(listed: dict[str, Any], analysis: RaidAnalysis) -> dict[str, Any]:
    return {
        "report_id": analysis.metadata.report_id,
        "title": listed.get("title") or analysis.metadata.title,
        "date": str(listed.get("raid_date") or "")[:10],
    }


def page_from(analysed: list[tuple[dict[str, Any], RaidAnalysis]], generated_at: str) -> dict[str, Any]:
    """The page for these raids (newest first, as `RaidService.list_raids` lists them): the newest raid and one entry
    per player in it, with up to RECENT_RAIDS of their raids in the same role (oldest first) for a trend. `raid` is
    null and `players` empty when there are no raids."""
    page: dict[str, Any] = {"version": PAGE_VERSION, "generated_at": generated_at, "raid": None, "players": []}
    if not analysed:
        return page
    boards = [(_raid(listed, analysis), standings(analysis)) for listed, analysis in analysed]
    last_raid, last_board = boards[0]
    page["raid"] = last_raid
    for key, st in sorted(last_board.items(), key=lambda item: (item[1].score.role, item[1].rank)):
        metric, unit = METRICS[st.score.role]
        recent = [
            {"date": raid["date"], "value": other.score.value, "median": other.median}
            for raid, board in reversed(boards)
            if (other := board.get(key)) is not None and other.score.role == st.score.role
        ]
        page["players"].append(
            {
                "name": st.score.name,
                "class": st.score.player_class,
                "role": st.score.role,
                "metric": metric,
                "unit": unit,
                "value": st.score.value,
                "median": st.median,
                "rank": st.rank,
                "of": st.of,
                "recent": recent,
            }
        )
    return page


def build_page(storage: StorageFactory, *, now: Callable[[], datetime] = datetime.now) -> dict[str, Any]:
    """The page as JSON, from the newest RECENT_RAIDS analysed raids in wcl-store."""
    raids = RaidService(AppContext(config={}, storage=storage))
    analysed = [
        (listed, analysis)
        for listed in raids.list_raids(limit=RECENT_RAIDS)
        if (analysis := raids.get_raid(str(listed["report_id"]))) is not None
    ]
    return page_from(analysed, now().strftime("%Y-%m-%d %H:%M:%S"))


def publish_performance(
    settings: Settings | None = None,
    *,
    storage: StorageFactory | None = None,
    hub: httpx.Client | None = None,
) -> dict[str, Any]:
    """Build the page and PUT it to the hub API. Returns the API's answer (how many players it kept)."""
    settings = settings or Settings()
    hub_api.service_token(settings)
    return hub_api.put(settings, "/api/worker/performance", build_page(storage or store.storage(settings)), hub)
