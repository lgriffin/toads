"""Rules for raid strategy docs (docs/strategy.md). Officers add Google Docs to a raid, then each raid night pins the
docs its raiders see on their Raid page. No RBAC, web framework or storage imports: the routes decide who may call
(every officer adds docs, through one of their nights or guild-wide; a night's officers or the global tier pin that
night's docs) and the repository decides where rows live.
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


# The classic raids a doc can be added to, in the order the hub lists them. "tbd" holds a raid not listed yet.
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
# The docs a night pins for its raiders at most.
NIGHT_LIMIT = 10
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
    # Who added it, by the name they chose on the hub; None once they are gone.
    added_by: str | None


@dataclass(frozen=True)
class RaidDocs:
    raid: Raid
    # Newest first.
    docs: list[DocView]


@dataclass(frozen=True)
class NightDocView:
    raid: Raid
    doc: DocView


@dataclass(frozen=True)
class NightStrategy:
    """What a night's Raid page shows: the docs the night pins for its raiders, in order."""

    docs: list[NightDocView]


class StrategyService:
    def __init__(self, repo: StrategyRepository, shown_names: Callable[[Iterable[int]], dict[int, str]]) -> None:
        self.repo = repo
        self._shown_names = shown_names

    def _views(self, docs: list[StrategyDoc]) -> list[DocView]:
        names = self._shown_names({d.created_by for d in docs if d.created_by is not None})
        return [DocView(d, names.get(d.created_by) if d.created_by is not None else None) for d in docs]

    def library(self) -> list[RaidDocs]:
        """Every raid in order, with its docs, newest first; a doc for a raid no longer listed is left out."""
        views = self._views(self.repo.docs())
        return [RaidDocs(raid, [v for v in views if v.doc.raid == raid.id]) for raid in RAIDS.values()]

    def add(self, raid: str, *, url: str, by: int, title: str = "", through: str | None = None) -> DocView:
        """Add a Google Doc to a raid. It shows to raiders once a night pins it. `through`: the night the officer adds
        it through (None for the global tier), for the audit log."""
        known = RAIDS.get(raid)
        if known is None:
            raise StrategyError("Pick one of the raids", status=422)
        title = " ".join(title.split()) or f"{known.name} strategy"
        if len(title) > TITLE_LIMIT:
            raise StrategyError(f"Keep the name to {TITLE_LIMIT} characters", status=422)
        url = url.strip()
        if len(url) > URL_LIMIT or not google_link(url):
            raise StrategyError("Paste the doc's https://docs.google.com or drive.google.com link", status=422)
        return self._views([self.repo.add(raid, title, url, by, through)])[0]

    def remove(self, doc_id: int, by: int, *, through: str | None = None, nights: frozenset[str] | None = None) -> None:
        """Take a doc down, and off every night that pins it. With `nights` (the nights a night officer runs), a doc
        another night pins stays up for that night's officers or the global tier to decide."""
        outcome = self.repo.remove(doc_id, by, through, nights)
        if outcome == "pinned":
            raise StrategyError(
                "Another night pins this doc; its officers or a global officer can take it down", status=409
            )
        if outcome == "missing":
            raise StrategyError("No such strategy doc", status=404)

    def night_docs(self) -> dict[str, list[int]]:
        return self.repo.night_docs()

    def night(self, raid_day: str) -> NightStrategy:
        views = {v.doc.id: v for v in self._views(self.repo.docs())}
        out = []
        for doc_id in self.repo.night_docs().get(raid_day, []):
            view = views.get(doc_id)
            raid = RAIDS.get(view.doc.raid) if view else None
            if view is not None and raid is not None:
                out.append(NightDocView(raid, view))
        return NightStrategy(out)

    def set_night(self, raid_day: str, doc_ids: list[int], by: int) -> NightStrategy:
        """Pin docs for a night's raiders, in order, so its Raid page shows them; [] clears them. A doc taken down while
        this saves is left out, as if it had not been ticked."""
        known = {d.id for d in self.repo.docs()}
        chosen = list(dict.fromkeys(doc_ids))
        if any(i not in known for i in chosen):
            raise StrategyError("Pick from the docs listed; one may have been taken down", status=422)
        if len(chosen) > NIGHT_LIMIT:
            raise StrategyError(f"Pin up to {NIGHT_LIMIT} docs for a night", status=422)
        self.repo.set_night_docs(raid_day, chosen, by)
        return self.night(raid_day)
