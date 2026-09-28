"""A member's "Your performance" widget (REQ-HUB-HOME-007, REQ-HUB-HOME-008). No RBAC, web framework or storage imports.

The worker publishes the guild's last raid with every player's primary number against the guild median for their
role (toads_worker.jobs.performance). A member sees one entry: their main character's. The main character is, in
order: the approved character they chose to go by, any other character they hold an approved claim on, or the
character named like their server nickname (the rule claims auto-approve by) unless another member claims it. Nobody
is ever shown someone else's entry (REQ-HUB-PRIV-001).
"""

from __future__ import annotations

import enum
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from toads_api.home.repository import HomeRepository, MemberCharacters, StoredPerformance
from toads_api.home.service import HomeError, generated_at_ok

# The worker's PAGE_VERSION this hub understands.
PERFORMANCE_VERSION = 1


class MatchedBy(enum.StrEnum):
    CHOSEN = "chosen"
    CLAIM = "claim"
    NICKNAME = "nickname"


@dataclass(frozen=True)
class MyPerformance:
    # None until the worker has published a page.
    generated_at: str | None
    raid: dict[str, Any] | None
    # The member's main character's entry in the last raid, or None when none of their characters was in it.
    entry: dict[str, Any] | None
    matched_by: MatchedBy | None
    # The character names looked for, in order of preference, so the widget can say who was missing.
    looked_for: list[str]


def fold(name: str) -> str:
    """Case- and width-insensitive, as claims compare names; accents still count."""
    return unicodedata.normalize("NFKC", name).strip().casefold()


def candidates(chars: MemberCharacters) -> list[tuple[str, MatchedBy]]:
    """The member's possible main characters, best first, without repeats."""
    found: list[tuple[str, MatchedBy]] = []
    if chars.chosen:
        found.append((chars.chosen, MatchedBy.CHOSEN))
    found += [(name, MatchedBy.CLAIM) for name in chars.approved]
    if chars.nickname.strip() and fold(chars.nickname) not in chars.claimed_by_others:
        found.append((chars.nickname.strip(), MatchedBy.NICKNAME))
    seen: set[str] = set()
    out: list[tuple[str, MatchedBy]] = []
    for name, how in found:
        if fold(name) not in seen:
            seen.add(fold(name))
            out.append((name, how))
    return out


class PerformanceService:
    def __init__(self, repo: HomeRepository) -> None:
        self.repo = repo

    def publish(
        self, version: int, generated_at: str, raid: Mapping[str, Any] | None, players: Sequence[Mapping[str, Any]]
    ) -> int:
        """Keep the worker's latest page; returns how many players it holds. A delayed or retried build never
        replaces a newer one."""
        if version != PERFORMANCE_VERSION:
            raise HomeError(f"Unsupported performance page version {version}", status=422)
        if not generated_at_ok(generated_at):
            raise HomeError("generated_at must look like 2026-09-27 12:00:00", status=422)
        if raid is None and players:
            raise HomeError("Players need the raid they are from", status=422)
        if len({fold(str(p["name"])) for p in players}) != len(players):
            raise HomeError("A player can only appear once", status=422)
        current = self.repo.performance_page()
        if current is not None and generated_at < current.generated_at:
            raise HomeError("A newer performance page is already published", status=409)
        self.repo.save_performance_page(
            StoredPerformance(version, generated_at, dict(raid) if raid else None, [dict(p) for p in players])
        )
        return len(players)

    def mine(self, member_id: int) -> MyPerformance:
        chars = self.repo.member_characters(member_id)
        wanted = candidates(chars) if chars is not None else []
        names = [name for name, _ in wanted]
        page = self.repo.performance_page()
        if page is None:
            return MyPerformance(None, None, None, None, names)
        players = {fold(str(p["name"])): p for p in page.players}
        for name, how in wanted:
            entry = players.get(fold(name))
            if entry is not None:
                return MyPerformance(page.generated_at, page.raid, dict(entry), how, names)
        return MyPerformance(page.generated_at, page.raid, None, None, names)
