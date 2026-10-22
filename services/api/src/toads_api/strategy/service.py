"""Rules for raid strategy docs (docs/strategy.md). No RBAC, web framework or storage imports: the routes decide who
may call (every officer pins docs, for their own nights or every night; the global tier for any; a night's officers or
the global tier say which raids the night is running) and the repository decides where rows live.
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
# The docs a raid keeps for each night and for every night: its pinned doc and the ones it replaced, newest first.
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
class Slot:
    """A raid's docs for one raid night, or for every night (`raid_day` None)."""

    raid_day: str | None
    # The newest doc pinned here.
    pinned: DocView
    # The docs it replaced, newest first.
    replaced: list[DocView]


@dataclass(frozen=True)
class RaidStrategy:
    raid: Raid
    # Every night's doc first, then each night's own, in the order asked for; only the places a doc is pinned.
    slots: list[Slot]


@dataclass(frozen=True)
class NightRaidDoc:
    raid: Raid
    # The night's own doc for the raid, else the raid's every-night doc; None while neither is pinned.
    pinned: DocView | None


@dataclass(frozen=True)
class NightStrategy:
    """What a night's Raid page shows: each raid the night is running, in order, with its doc."""

    raids: list[NightRaidDoc]


class StrategyService:
    def __init__(self, repo: StrategyRepository, shown_names: Callable[[Iterable[int]], dict[int, str]]) -> None:
        self.repo = repo
        self._shown_names = shown_names

    def _views(self, docs: list[StrategyDoc]) -> list[DocView]:
        names = self._shown_names({d.created_by for d in docs if d.created_by is not None})
        return [DocView(d, names.get(d.created_by) if d.created_by is not None else None) for d in docs]

    def library(self, nights: Iterable[str] = ()) -> list[RaidStrategy]:
        """Every raid in order, with its docs for every night and for each night that pinned its own. `nights` orders
        the nights' slots (the raid days' config order); a night it leaves out comes after them."""
        order = {day: i for i, day in enumerate(nights)}
        views = self._views(self.repo.docs())
        out = []
        for raid in RAIDS.values():
            places: dict[str | None, list[DocView]] = {}
            for v in views:
                if v.doc.raid == raid.id:
                    places.setdefault(v.doc.raid_day, []).append(v)
            ranked = sorted(places, key=lambda d: (d is not None, order.get(d or "", len(order)), d or ""))
            out.append(RaidStrategy(raid, [Slot(d, places[d][0], places[d][1:]) for d in ranked]))
        return out

    def pin(self, raid: str, *, url: str, by: int, title: str = "", raid_day: str | None = None) -> DocView:
        """Pin a Google Doc to a raid for one night (`raid_day`) or every night (None). It becomes the doc for that
        raid there at once; the one it replaces is kept below it until KEEP newer ones push it out. A doc pinned for
        one night also adds the raid to the raids that night is running, so its Raid page shows it straight away."""
        known = RAIDS.get(raid)
        if known is None:
            raise StrategyError("Pick one of the raids", status=422)
        title = " ".join(title.split()) or f"{known.name} strategy"
        if len(title) > TITLE_LIMIT:
            raise StrategyError(f"Keep the name to {TITLE_LIMIT} characters", status=422)
        url = url.strip()
        if len(url) > URL_LIMIT or not google_link(url):
            raise StrategyError("Paste the doc's https://docs.google.com or drive.google.com link", status=422)
        doc = self.repo.pin(raid, raid_day, title, url, by, KEEP)
        if raid_day is not None:
            running = self.repo.night_raids().get(raid_day, [])
            if raid not in running:
                self.repo.set_night_raids(raid_day, [*running, raid], by)
        return self._views([doc])[0]

    def remove(self, doc_id: int, by: int, nights: frozenset[str | None] | None = None) -> None:
        """Take a doc down. Taking down a pinned doc pins the one it replaced again, if there is one. With `nights`,
        only a doc pinned for one of them (None standing for every night)."""
        if not self.repo.remove(doc_id, by, nights):
            raise StrategyError("No such strategy doc", status=404)

    def night_raids(self) -> dict[str, list[str]]:
        return self.repo.night_raids()

    def night(self, raid_day: str) -> NightStrategy:
        docs = self._views(self.repo.docs())
        out = []
        for raid_id in self.repo.night_raids().get(raid_day, []):
            raid = RAIDS.get(raid_id)
            if raid is None:
                continue
            own = next((v for v in docs if (v.doc.raid, v.doc.raid_day) == (raid.id, raid_day)), None)
            every = next((v for v in docs if (v.doc.raid, v.doc.raid_day) == (raid.id, None)), None)
            out.append(NightRaidDoc(raid, own or every))
        return NightStrategy(out)

    def set_night(self, raid_day: str, raids: list[str], by: int) -> NightStrategy:
        """Say which raids a night is running, in order, so its Raid page shows each raid's doc; [] clears them."""
        if any(r not in RAIDS for r in raids):
            raise StrategyError("Pick from the raids listed", status=422)
        self.repo.set_night_raids(raid_day, list(dict.fromkeys(raids)), by)
        return self.night(raid_day)
