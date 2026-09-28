"""Rules for a member's hub home. No RBAC, web framework or storage imports: the routes decide which audience the
caller is in, and the repository decides where layouts live.

Widget ids are a contract shared with the web app (`apps/web/src/lib/home.ts`); add a widget in both places.
"""

from __future__ import annotations

import enum
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from toads_api.home.charts import chart_problem
from toads_api.home.repository import HomeRepository, StoredPage, StoredWidget


class Audience(enum.StrEnum):
    # Any signed-in member.
    MEMBER = "member"
    # Members with officer powers on at least one raid day, or global officers.
    OFFICER = "officer"


class Source(enum.StrEnum):
    # Drawn from the hub's own data (Discord events, posts, highlights, raid sheets, ...).
    HUB = "hub"
    # A widget of the analyzer's shared home page (wcl_app.home.HomeService in lgriffin/warcraftlogs_project,
    # contract in its guides/home_widgets.md). The worker builds the page and publishes it here; the id, title and
    # payload are the analyzer's, so the desktop app and the hub show the same numbers.
    ANALYZER = "analyzer"


@dataclass(frozen=True)
class Widget:
    id: str
    title: str
    description: str
    audience: Audience = Audience.MEMBER
    # Shown on a home the member has never customised.
    default_shown: bool = True
    source: Source = Source.HUB


def _analyzer(wid: str, title: str, description: str, *, default_shown: bool = True) -> Widget:
    return Widget(wid, title, description, default_shown=default_shown, source=Source.ANALYZER)


# In default display order. The analyzer's `quick_actions` (desktop commands) and `tracked_players` (the desktop's
# player pages) have no hub page yet, so they are left out; the hub's navigation covers the first.
CATALOGUE: tuple[Widget, ...] = (
    Widget("next_raid", "Next raid", "When the next raid starts and which roles still need signups."),
    Widget(
        "officer_desk",
        "Raid leader desk",
        "Applications, posts, highlights and spotlights waiting on officers.",
        Audience.OFFICER,
    ),
    _analyzer("guild_snapshot", "Guild at a glance", "Raids stored, active raiders, raids this month, last raid."),
    _analyzer("last_raid", "Last raid", "Date, duration, bosses killed, raid size, total damage and healing."),
    Widget("my_performance", "Your performance", "Your main character's last raid against the guild median."),
    Widget("raid_totals", "Raid totals", "Consumes, buffs and deaths per raid from the CBA and RPB sheets."),
    _analyzer("recent_raids", "Recent raids", "The newest guild raids."),
    _analyzer("raid_activity", "Raid activity", "Raids per week over the last eight weeks."),
    _analyzer(
        "healing_weekly",
        "Weekly healing",
        "Healing per raid each week, measured against the four-week average and the guild's target.",
    ),
    _analyzer("top_damage", "Top damage", "The top five damage dealers in the last raid."),
    _analyzer("top_healing", "Top healing", "The top five healers in the last raid, with overheal."),
    _analyzer("attendance", "Attendance", "Who attended most of the last ten raids."),
    Widget("posts", "Guild posts", "News and posts from officers and Discord."),
    Widget("highlights", "Recent highlights", "The newest highlight reels."),
    _analyzer("boss_kills", "Boss kills", "Bosses killed in the last raid, in kill order.", default_shown=False),
    _analyzer("class_mix", "Class mix", "Players per class in the last raid.", default_shown=False),
    _analyzer(
        "interrupts", "Interrupt casts", "The most interrupt abilities cast in the last raid.", default_shown=False
    ),
    _analyzer("consumables", "Consumables", "The top five consumable users in the last raid.", default_shown=False),
    _analyzer(
        "healers_weekly",
        "Healers week on week",
        "Each healer's healing per raid over the last twelve weeks.",
        default_shown=False,
    ),
    Widget("progression", "Progression", "Bosses killed in each raid zone.", default_shown=False),
    Widget("recruiting", "Recruiting", "The classes and specs the guild is looking for.", default_shown=False),
)
MAX_WIDGETS = len(CATALOGUE)
ANALYZER_IDS = frozenset(w.id for w in CATALOGUE if w.source is Source.ANALYZER)
# The analyzer's HOME_SCHEMA_VERSION this hub understands; it changes only when a payload field changes meaning.
ANALYZER_SCHEMA_VERSION = 1
# The analyzer has 15 widgets today; far more than this is a broken publisher.
MAX_ANALYZER_WIDGETS = 50
# Tiles, rows, items or bars in one widget: the analyzer sends at most a few dozen.
MAX_ENTRIES = 200
# The list fields each widget kind must carry (guides/home_widgets.md). `actions` is left out: the hub places none.
KIND_FIELDS: dict[str, tuple[str, ...]] = {
    "stats": ("tiles",),
    "table": ("columns", "rows"),
    "list": ("items",),
    "bars": ("bars",),
    # One chart payload rather than a list; checked by toads_api.home.charts.
    "chart": (),
}
# The analyzer's local time, "YYYY-MM-DD HH:MM:SS", which sorts as text.
_GENERATED_AT = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")


class HomeError(Exception):
    """A request the rules refuse. `status` is the HTTP code the adapter should answer with."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


@dataclass(frozen=True)
class WidgetChoice:
    widget: Widget
    shown: bool


@dataclass(frozen=True)
class AnalyzerPage:
    """The analyzer's home page as the worker last published it. `widgets` are its payloads, kept as JSON."""

    version: int
    generated_at: str
    widgets: list[dict[str, Any]]


@dataclass(frozen=True)
class HomeLayout:
    # Every widget the member may place, in display order, whether shown or not.
    widgets: list[WidgetChoice]
    # False while the member is on the default layout.
    customised: bool

    @property
    def shown(self) -> list[str]:
        return [c.widget.id for c in self.widgets if c.shown]


def catalogue_for(audience: Audience) -> list[Widget]:
    """Officers see every widget; members see the member ones."""
    return [w for w in CATALOGUE if audience is Audience.OFFICER or w.audience is Audience.MEMBER]


def default_layout(audience: Audience) -> list[WidgetChoice]:
    return [WidgetChoice(w, w.default_shown) for w in catalogue_for(audience)]


def merge(stored: Sequence[StoredWidget], audience: Audience) -> list[WidgetChoice]:
    """A saved layout read against today's catalogue. Unknown ids (retired widgets) and widgets the member may no
    longer see (an officer who stepped down) drop out; widgets added since the member saved are appended with their
    default. Keeping the saved entries lets an officer's hidden desk come back where it was if they return."""
    available = {w.id: w for w in catalogue_for(audience)}
    seen: set[str] = set()
    out: list[WidgetChoice] = []
    for entry in stored:
        widget = available.get(entry.id)
        if widget is None or entry.id in seen:
            continue
        seen.add(entry.id)
        out.append(WidgetChoice(widget, entry.shown))
    known = {e.id for e in stored}
    out += [WidgetChoice(w, w.default_shown) for w in available.values() if w.id not in known]
    return out


def malformed(widget: Mapping[str, Any]) -> str | None:
    """Why a widget the hub places does not match the analyzer's contract, or None when it does. The web draws the
    list fields directly, so each must be a bounded list of objects."""
    if not isinstance(widget.get("title"), str):
        return "title must be text"
    kind = str(widget.get("kind"))
    fields = KIND_FIELDS.get(kind)
    if fields is None:
        return f"unsupported kind {widget.get('kind')!r}"
    if kind == "chart":
        # A widget that failed to build carries its error and no chart.
        if widget.get("chart") is None and widget.get("error"):
            return None
        return chart_problem(widget.get("chart"))
    for name in fields:
        value = widget.get(name)
        if not isinstance(value, list) or not all(isinstance(e, dict) for e in value):
            return f"{name} must be a list of objects"
        if len(value) > MAX_ENTRIES:
            return f"{name} has more than {MAX_ENTRIES} entries"
    return None


class HomeService:
    def __init__(self, repo: HomeRepository) -> None:
        self.repo = repo

    def layout(self, member_id: int, audience: Audience) -> HomeLayout:
        stored = self.repo.layout(member_id)
        if stored is None:
            return HomeLayout(default_layout(audience), customised=False)
        return HomeLayout(merge(stored, audience), customised=True)

    def save(self, member_id: int, audience: Audience, shown: Sequence[str]) -> HomeLayout:
        """Show exactly `shown`, in that order; every other widget the member may place is kept, hidden, after them.
        Widgets the member cannot see now but saved earlier (officer ones, for a member who stepped down) keep their
        saved state."""
        if len(shown) > MAX_WIDGETS:
            raise HomeError("Too many widgets", status=422)
        if len(set(shown)) != len(shown):
            raise HomeError("A widget can only appear once", status=422)
        known = {w.id for w in CATALOGUE}
        unknown = [i for i in shown if i not in known]
        if unknown:
            raise HomeError(f"Unknown widget: {unknown[0]}", status=422)
        available = [w.id for w in catalogue_for(audience)]
        refused = [i for i in shown if i not in available]
        if refused:
            raise HomeError("That widget is for officers", status=403)

        current = [c.widget.id for c in self.layout(member_id, audience).widgets]
        entries = [StoredWidget(i, True) for i in shown]
        entries += [StoredWidget(i, False) for i in current if i not in shown]
        # Keep what the member cannot see right now exactly as it was saved.
        previous = self.repo.layout(member_id) or []
        entries += [e for e in previous if e.id in known and e.id not in available]
        self.repo.save_layout(member_id, entries)
        return self.layout(member_id, audience)

    def reset(self, member_id: int, audience: Audience) -> HomeLayout:
        self.repo.delete_layout(member_id)
        return self.layout(member_id, audience)

    # ------------------------------------------------------- analyzer page

    def publish_analyzer_page(self, version: int, generated_at: str, widgets: Sequence[Mapping[str, Any]]) -> int:
        """Keep the worker's latest build of the analyzer's home page; returns how many widgets were kept. Widgets
        the hub does not place (the analyzer's quick actions and tracked players, or ids newer than this hub) are
        dropped here rather than stored."""
        if version != ANALYZER_SCHEMA_VERSION:
            raise HomeError(f"Unsupported home page version {version}", status=422)
        if not _GENERATED_AT.fullmatch(generated_at):
            raise HomeError("generated_at must look like 2026-09-27 12:00:00", status=422)
        if len(widgets) > MAX_ANALYZER_WIDGETS:
            raise HomeError("Too many widgets", status=422)
        kept: dict[str, dict[str, Any]] = {}
        for w in widgets:
            wid = w.get("id")
            if not isinstance(wid, str) or wid not in ANALYZER_IDS or wid in kept:
                continue
            problem = malformed(w)
            if problem:
                raise HomeError(f"Widget {wid}: {problem}", status=422)
            kept[wid] = dict(w)
        current = self.repo.analyzer_page()
        if current is not None and generated_at < current.generated_at:
            # A delayed or retried build must not replace a newer one.
            raise HomeError("A newer home page is already published", status=409)
        self.repo.save_analyzer_page(StoredPage(version, generated_at, list(kept.values())))
        return len(kept)

    def analyzer_page(self) -> AnalyzerPage | None:
        page = self.repo.analyzer_page()
        if page is None:
            return None
        return AnalyzerPage(page.version, page.generated_at, [dict(w) for w in page.widgets])
