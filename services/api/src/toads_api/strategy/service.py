"""Rules for raid strategy docs. No RBAC, web framework or storage imports: the routes decide who may call (the global
officers pin docs and say which raid their night is running) and the repository decides where rows live.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from urllib.parse import urlsplit

from toads_api.strategy.repository import StrategyDoc, StrategyRepository


@dataclass(frozen=True)
class Raid:
    id: str
    short: str
    name: str


# The classic raids a doc can be pinned to, in the order the hub lists them. "tbd" holds a raid not listed yet.
RAIDS: dict[str, Raid] = {
    r.id: r
    for r in (
        Raid("mc", "MC", "Molten Core"),
        Raid("bwl", "BWL", "Blackwing Lair"),
        Raid("zg", "ZG", "Zul'Gurub"),
        Raid("aq20", "AQ20", "Ruins of Ahn'Qiraj"),
        Raid("aq40", "AQ40", "Temple of Ahn'Qiraj"),
        Raid("naxx", "Naxx", "Naxxramas"),
        Raid("tbd", "TBD", "Another raid (to be decided)"),
    )
}
TITLE_LIMIT = 80
URL_LIMIT = 500
# The docs a raid keeps: its pinned doc and the ones it replaced, newest first. Older ones drop off.
KEEP = 6
# Officers keep strategy in Google Drive, so a pinned doc is a Google Docs, Sheets, Slides or Drive link.
GOOGLE_HOSTS = frozenset({"docs.google.com", "drive.google.com"})


def google_link(url: str) -> bool:
    """An https link to Google Docs or Drive, with no spaces and a well-formed port, so browsers open what we stored."""
    if any(c.isspace() for c in url):
        return False
    try:
        parts = urlsplit(url)
        host, _ = parts.hostname, parts.port
    except ValueError:
        return False
    return parts.scheme == "https" and host in GOOGLE_HOSTS and not parts.username and not parts.password


class StrategyError(Exception):
    """A request the rules refuse. `status` is the HTTP code the adapter should answer with."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


@dataclass(frozen=True)
class DocView:
    doc: StrategyDoc
    # Who pinned it, by the name they chose on the hub; None once they are gone.
    added_by: str | None


@dataclass(frozen=True)
class RaidStrategy:
    raid: Raid
    # The raid's authoritative doc: the newest pinned. None until one is.
    pinned: DocView | None
    # The docs it replaced, newest first.
    replaced: list[DocView]


@dataclass(frozen=True)
class NightStrategy:
    """What a night's Raid page shows: the raid the night is running and that raid's pinned doc."""

    raid: Raid | None
    pinned: DocView | None


class StrategyService:
    def __init__(self, repo: StrategyRepository, shown_names: Callable[[Iterable[int]], dict[int, str]]) -> None:
        self.repo = repo
        self._shown_names = shown_names

    def _views(self, docs: list[StrategyDoc]) -> list[DocView]:
        names = self._shown_names({d.created_by for d in docs if d.created_by is not None})
        return [DocView(d, names.get(d.created_by) if d.created_by is not None else None) for d in docs]

    def library(self) -> list[RaidStrategy]:
        """Every raid in order, with its pinned doc and the docs it replaced."""
        views = self._views(self.repo.docs())
        out = []
        for raid in RAIDS.values():
            mine = [v for v in views if v.doc.raid == raid.id]
            out.append(RaidStrategy(raid, mine[0] if mine else None, mine[1:]))
        return out

    def pin(self, raid: str, *, url: str, by: int, title: str = "", raid_day: str | None = None) -> DocView:
        """Pin a Google Doc to a raid. It becomes the raid's one authoritative doc, on every night running that raid;
        the one it replaces is kept below it until KEEP newer ones push it out. `raid_day` is the night whose officer
        pinned it (for the audit log); None for the global tier."""
        known = RAIDS.get(raid)
        if known is None:
            raise StrategyError("Pick one of the raids", status=422)
        title = " ".join(title.split()) or f"{known.name} strategy"
        if len(title) > TITLE_LIMIT:
            raise StrategyError(f"Keep the name to {TITLE_LIMIT} characters", status=422)
        url = url.strip()
        if len(url) > URL_LIMIT or not google_link(url):
            raise StrategyError("Paste the doc's https://docs.google.com or drive.google.com link", status=422)
        return self._views([self.repo.pin(raid, title, url, by, KEEP, raid_day)])[0]

    def remove(self, doc_id: int, by: int, raid_day: str | None = None) -> None:
        """Take a doc down. Taking down a raid's pinned doc pins the one it replaced again, if there is one."""
        if not self.repo.remove(doc_id, by, raid_day):
            raise StrategyError("No such strategy doc", status=404)

    def night_raids(self) -> dict[str, str]:
        return self.repo.night_raids()

    def night(self, raid_day: str) -> NightStrategy:
        raid = RAIDS.get(self.repo.night_raids().get(raid_day, ""))
        if raid is None:
            return NightStrategy(None, None)
        pinned = next((r.pinned for r in self.library() if r.raid.id == raid.id), None)
        return NightStrategy(raid, pinned)

    def set_night(self, raid_day: str, raid: str | None, by: int) -> NightStrategy:
        """Say which raid a night is running, so its Raid page shows that raid's pinned doc; None clears it."""
        if raid is not None and raid not in RAIDS:
            raise StrategyError("Pick one of the raids", status=422)
        self.repo.set_night_raid(raid_day, raid, by)
        return self.night(raid_day)
