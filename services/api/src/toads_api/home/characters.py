"""A member's own raid performance on Me: their character's page (REQ-HUB-ME-*). No RBAC, web framework or storage
imports.

The worker builds a page for every name a member may go by (approved claims and server nicknames) with the
analyzer's CharacterPageService (wcl_app.character_pages in lgriffin/warcraftlogs_project, contract in its
guides/character_pages.md): each raid with the role's headline number against the raid's median, the character's
lineage, personal bests and a chart per role. A member sees only their own characters, picked as "Your performance"
picks them (toads_api.home.performance.candidates); nobody is ever shown someone else's page (REQ-HUB-PRIV-001).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from toads_api.home.charts import chart_problem
from toads_api.home.performance import MatchedBy, candidates
from toads_api.home.repository import HomeRepository, fold
from toads_api.home.service import HomeError, generated_at_ok

# The analyzer's CHARACTER_PAGE_VERSION this hub understands.
CHARACTER_PAGE_VERSION = 1


@dataclass(frozen=True)
class MyCharacterPage:
    # None until the worker has published pages.
    generated_at: str | None
    # The page of the character asked for, or of the member's main character; None when none of theirs has raided.
    page: dict[str, Any] | None
    matched_by: MatchedBy | None
    # The character names looked for, in order of preference.
    looked_for: list[str]
    # The member's characters that have a page, best first (their main leads), so Me can switch between them.
    characters: list[str]
    # Their main character's name, whether or not it has a page; None before they hold an approved claim.
    main: str | None = None


class CharacterPageService:
    def __init__(self, repo: HomeRepository) -> None:
        self.repo = repo

    def wanted(self) -> list[str]:
        """The names the worker builds pages for: every name a member may go by."""
        return self.repo.character_names()

    def publish(self, version: int, generated_at: str, pages: Sequence[Mapping[str, Any]]) -> int:
        """Replace every character page with the worker's latest build; returns how many it holds. A delayed or
        retried build never replaces a newer one."""
        if version != CHARACTER_PAGE_VERSION:
            raise HomeError(f"Unsupported character page version {version}", status=422)
        if not generated_at_ok(generated_at):
            raise HomeError("generated_at must look like 2026-09-27 12:00:00", status=422)
        if len({fold(str(p["name"])) for p in pages}) != len(pages):
            raise HomeError("A character can only appear once", status=422)
        for page in pages:
            for chart in page.get("charts", []):
                problem = chart_problem(chart)
                if problem:
                    raise HomeError(f"Character {page['name']}: {problem}", status=422)
        if not self.repo.save_character_pages(version, generated_at, [dict(p) for p in pages]):
            raise HomeError("Newer character pages are already published", status=409)
        return len(pages)

    def mine(self, member_id: int, name: str | None = None) -> MyCharacterPage:
        """The member's page for `name` when it is one of theirs, else their main character's."""
        chars = self.repo.member_characters(member_id)
        wanted = candidates(chars) if chars is not None else []
        main = chars.main if chars is not None else None
        looked_for = [n for n, _ in wanted]
        found = [(n, how, page) for n, how in wanted if (page := self.repo.character_page(n)) is not None]
        if not found:
            return MyCharacterPage(self.repo.character_pages_generated_at(), None, None, looked_for, [], main)
        names = [str(page.page["name"]) for _, _, page in found]
        chosen = next((f for f in found if name is not None and fold(f[0]) == fold(name)), found[0])
        _, how, page = chosen
        return MyCharacterPage(page.generated_at, dict(page.page), how, looked_for, names, main)
