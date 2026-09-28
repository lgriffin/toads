"""A member's own Toads badges (REQ-HUB-HOME-011). No RBAC, web framework or storage imports.

The worker publishes every raider's badges as the analyzer builds them (wcl_app.badges in
lgriffin/warcraftlogs_project, contract in its guides/badges.md): raids attended and consumables used across the
guild's raids, each in tiers named after item quality. A member sees one player: their main character, picked as
"Your performance" picks it (toads_api.home.performance.candidates). Raid leaders see the last raid's roster through the
analyzer's officer-only `badges` home widget instead.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from toads_api.home.performance import MatchedBy, candidates, fold
from toads_api.home.repository import HomeRepository, StoredBadges
from toads_api.home.service import HomeError, generated_at_ok

# The analyzer's BADGES_SCHEMA_VERSION this hub understands.
BADGES_VERSION = 1


@dataclass(frozen=True)
class MyBadges:
    # None until the worker has published a page.
    generated_at: str | None
    # The member's main character's badges, earned or not, or None when none of their characters has raided.
    entry: dict[str, Any] | None
    matched_by: MatchedBy | None
    # The character names looked for, in order of preference.
    looked_for: list[str]


class BadgeService:
    def __init__(self, repo: HomeRepository) -> None:
        self.repo = repo

    def publish(self, version: int, generated_at: str, players: Sequence[Mapping[str, Any]]) -> int:
        """Keep the worker's latest page; returns how many players it holds. A delayed or retried build never
        replaces a newer one."""
        if version != BADGES_VERSION:
            raise HomeError(f"Unsupported badge page version {version}", status=422)
        if not generated_at_ok(generated_at):
            raise HomeError("generated_at must look like 2026-09-27 12:00:00", status=422)
        if len({fold(str(p["name"])) for p in players}) != len(players):
            raise HomeError("A player can only appear once", status=422)
        current = self.repo.badge_page()
        if current is not None and generated_at < current.generated_at:
            raise HomeError("A newer badge page is already published", status=409)
        self.repo.save_badge_page(StoredBadges(version, generated_at, [dict(p) for p in players]))
        return len(players)

    def mine(self, member_id: int) -> MyBadges:
        chars = self.repo.member_characters(member_id)
        wanted = candidates(chars) if chars is not None else []
        names = [name for name, _ in wanted]
        page = self.repo.badge_page()
        if page is None:
            return MyBadges(None, None, None, names)
        players = {fold(str(p["name"])): p for p in page.players}
        for name, how in wanted:
            entry = players.get(fold(name))
            if entry is not None:
                return MyBadges(page.generated_at, dict(entry), how, names)
        return MyBadges(page.generated_at, None, None, names)
