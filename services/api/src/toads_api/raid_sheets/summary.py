"""Home page numbers from a raid's CBA and RPB tabs.

Both sheets are generated from one Warcraft Logs report by shariva's templates, so their layouts are fixed:
- CBA (Combat Log Analytics): "buff consumables" (uptime per player), "gear issues" (missing enchants and gems),
  "drums", "validate", and a title such as "BT / Hyjal (BT in 1:48:32, MH in 1:08:40)" on every tab.
- RPB (Role Performance Breakdown): "General" (consumables, interrupts, engineering) and one tab per role
  (Caster, Healer, Physical, Tank) with deaths and avoidable damage taken. Player names head the columns.

Rows and labels are found by their text, not their position, so a template update that adds a row does not shift
the numbers. Anything that is missing reads as None rather than failing the page. Pure functions over text tables.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

Grid = Sequence[Sequence[str]]

# Players under this share of consumable uptime are listed on the home page.
LOW_CONSUMABLES = 0.8
ROLES = ("tank", "healer", "caster", "physical")
# The headings that split RPB tabs into sections.
SECTIONS = (
    "consumables",
    "damage absorbed",
    "engineering etc",
    "interrupted spells",
    "stats and miscellanous",
    "trinkets and racials",
    "raw avoidable damage taken",
    "avoidable debuffs applied",
)

_CLEAR = re.compile(r"([A-Za-z][\w' ]*?)\s+in\s+(?:(\d+):)?(\d{1,2}):(\d{2})\b")
_INT = re.compile(r"-?\d+")
_DASHES = re.compile(r"^-+$")


@dataclass(frozen=True)
class ClearTime:
    zone: str  # as the sheet's title abbreviates it, e.g. "BT"
    seconds: int


@dataclass
class PlayerLine:
    name: str
    role: str | None = None
    consumables: float | None = None  # 0-1: average uptime of flask/elixirs, food and weapon buffs on bosses
    gear_issues: int | None = None
    drums: int | None = None
    potions: int | None = None
    interrupts: int | None = None
    deaths: int | None = None
    avoidable_damage: int | None = None


@dataclass
class RaidHeadline:
    """One raid's totals: a point on the home page's week-by-week trend."""

    raid_day: str
    raid_date: str  # ISO date
    title: str | None = None
    zone: str | None = None
    report_code: str | None = None
    log_valid: bool | None = None
    characters: int | None = None
    clear_times: list[ClearTime] = field(default_factory=list)
    consumables_avg: float | None = None
    low_consumables: list[str] = field(default_factory=list)
    gear_issues: int | None = None
    players_with_gear_issues: int | None = None
    drums: int | None = None
    potions: int | None = None
    interrupts: int | None = None
    deaths: int | None = None
    avoidable_damage: int | None = None


@dataclass
class RaidSummary:
    headline: RaidHeadline
    players: list[PlayerLine] = field(default_factory=list)


def _norm(text: str) -> str:
    return " ".join(text.lower().split())


def _cell(row: Sequence[str], i: int) -> str:
    return row[i].strip() if 0 <= i < len(row) else ""


def to_int(text: str) -> int | None:
    """The first whole number in a cell: "22 (⌀ 2.36)" -> 22, "6 (0)" -> 6, "274846.0" -> 274846."""
    text = text.strip().replace(",", "")
    try:
        return round(float(text))
    except ValueError:
        pass
    m = _INT.search(text)
    return int(m[0]) if m else None


def to_fraction(text: str) -> float | None:
    """0-1 from "0.94", "1", or "94%"; None for anything else, such as "-"."""
    text = text.strip()
    try:
        value = float(text[:-1]) / 100 if text.endswith("%") else float(text)
    except ValueError:
        return None
    return value if 0 <= value <= 1 else None


def label_value(grid: Grid, label: str) -> str | None:
    """The first non-empty cell right of the cell reading `label` ("title", "zone", "date")."""
    for row in grid:
        for i, cell in enumerate(row):
            if _norm(cell) == label:
                return next((c.strip() for c in row[i + 1 :] if c.strip()), None)
    return None


def clear_times(title: str) -> list[ClearTime]:
    """ "BT / Hyjal (BT in 1:48:32, MH in 1:08:40)" -> BT 6512s, MH 4120s."""
    inner = title[title.find("(") + 1 :] if "(" in title else title
    return [
        ClearTime(zone=m[1].strip(), seconds=int(m[2] or 0) * 3600 + int(m[3]) * 60 + int(m[4]))
        for m in _CLEAR.finditer(inner)
    ]


def _find(grid: Grid, header: str) -> tuple[int, int] | None:
    for r, row in enumerate(grid):
        for c, cell in enumerate(row):
            if _norm(cell) == header:
                return r, c
    return None


def consumables(grid: Grid) -> dict[str, float]:
    """CBA "buff consumables": each player's total average (excluding scrolls), right of their name."""
    at = _find(grid, "total average (excl. scrolls)")
    if at is None:
        return {}
    r0, c = at
    out: dict[str, float] = {}
    for row in grid[r0 + 1 :]:
        name, value = _cell(row, c - 1), to_fraction(_cell(row, c))
        if name and value is not None:
            out[name] = value
    return out


def gear_issues(grid: Grid) -> dict[str, int]:
    """CBA "gear issues": the "Item [Issue]" cells right of each player; a row of dashes means none."""
    header = next((r for r, row in enumerate(grid) if any(_norm(c) == "item [issue]" for c in row)), None)
    if header is None:
        return {}
    first = next(i for i, c in enumerate(grid[header]) if _norm(c) == "item [issue]")
    out: dict[str, int] = {}
    for row in grid[header + 1 :]:
        name = _cell(row, first - 1)
        if not name or name.startswith("<"):
            continue
        out[name] = sum(1 for c in row[first:] if c.strip() and not _DASHES.match(c.strip()))
    return out


def drums(grid: Grid) -> dict[str, int]:
    """CBA "drums": battle, war and restoration drums per player."""
    at = _find(grid, "# of battle drums")
    if at is None:
        return {}
    r0, c = at
    out: dict[str, int] = {}
    for row in grid[r0 + 1 :]:
        name = _cell(row, c - 1)
        if name:
            out[name] = sum(to_int(_cell(row, c + k)) or 0 for k in range(3))
    return out


def validate(grid: Grid) -> tuple[bool | None, int | None]:
    """CBA "validate": whether the log met the kill requirements, and how many characters took part."""
    valid: bool | None = None
    characters: int | None = None
    for row in grid:
        for i, cell in enumerate(row):
            text = _norm(cell)
            rest = [c.strip() for c in row[i + 1 :] if c.strip()]
            if text.startswith("is the log a valid log") and rest:
                valid = {"yes": True, "no": False}.get(rest[-1].lower())
            elif text.startswith("total number of characters used") and rest:
                characters = to_int(rest[0])
    return valid, characters


def player_columns(grid: Grid) -> tuple[int, dict[int, str]] | None:
    """RPB tabs: the first row whose cells after the label column are player names."""
    for r, row in enumerate(grid):
        names = {i: c.strip() for i, c in enumerate(row) if i > 0 and c.strip()}
        if names and not _cell(row, 0):
            return r, names
    return None


def per_player(grid: Grid, match: str, *, section: str | None = None) -> dict[str, int]:
    """Sum per player of the RPB rows whose label contains `match`, within `section` when given."""
    cols = player_columns(grid)
    if cols is None:
        return {}
    r0, names = cols
    out: dict[str, int] = {}
    inside = section is None
    for row in grid[r0 + 1 :]:
        label = _norm(_cell(row, 0))
        if section is not None and label.startswith(SECTIONS):
            inside = label.startswith(section)
            continue
        if not inside or match not in label:
            continue
        for i, name in names.items():
            if (value := to_int(_cell(row, i))) is not None:
                out[name] = out.get(name, 0) + value
    return out


def _total(values: Iterable[int]) -> int | None:
    values = list(values)
    return sum(values) if values else None


def _tab(tables: dict[str, Grid], name: str) -> Grid:
    """The tab called `name`, or one that starts with it (RPB can append the report title to tab names)."""
    if name in tables:
        return tables[name]
    return next((g for t, g in tables.items() if t.startswith(name) and "casts" not in t), [])


def summarise(
    raid_day: str,
    raid_date: str,
    cba: dict[str, Grid],
    rpb: dict[str, Grid],
    report_code: str | None = None,
) -> RaidSummary:
    """Totals and per-player lines from a raid's current CBA and RPB tabs, keyed by lower-case tab name."""
    head = RaidHeadline(raid_day=raid_day, raid_date=raid_date, report_code=report_code)
    for grid in [*cba.values(), *rpb.values()]:
        head.title = head.title or label_value(grid, "title")
        head.zone = head.zone or label_value(grid, "zone")
    head.clear_times = clear_times(head.title) if head.title else []
    head.log_valid, head.characters = validate(_tab(cba, "validate"))

    players: dict[str, PlayerLine] = {}

    def line(name: str) -> PlayerLine:
        return players.setdefault(name, PlayerLine(name=name))

    for name, value in consumables(_tab(cba, "buff consumables")).items():
        line(name).consumables = value
    for name, count in gear_issues(_tab(cba, "gear issues")).items():
        line(name).gear_issues = count
    for name, count in drums(_tab(cba, "drums")).items():
        line(name).drums = count

    general = _tab(rpb, "general")
    for name, count in per_player(general, "potion", section="consumables").items():
        line(name).potions = count
    for name, count in per_player(general, "# of interrupted spells").items():
        line(name).interrupts = count
    for role in ROLES:
        grid = _tab(rpb, role)
        cols = player_columns(grid)
        for name in cols[1].values() if cols else ():
            line(name).role = role
        for name, count in per_player(grid, "# of deaths in total").items():
            line(name).deaths = count
        for name, amount in per_player(grid, "total (partly) avoidable damage taken").items():
            line(name).avoidable_damage = amount

    ps = sorted(players.values(), key=lambda p: p.name.lower())
    uptimes = [p.consumables for p in ps if p.consumables is not None]
    head.consumables_avg = round(sum(uptimes) / len(uptimes), 4) if uptimes else None
    head.low_consumables = [p.name for p in ps if p.consumables is not None and p.consumables < LOW_CONSUMABLES]
    issues = [p.gear_issues for p in ps if p.gear_issues is not None]
    head.gear_issues = _total(issues)
    head.players_with_gear_issues = sum(1 for n in issues if n) if issues else None
    head.drums = _total(p.drums for p in ps if p.drums is not None)
    head.potions = _total(p.potions for p in ps if p.potions is not None)
    head.interrupts = _total(p.interrupts for p in ps if p.interrupts is not None)
    head.deaths = _total(p.deaths for p in ps if p.deaths is not None)
    head.avoidable_damage = _total(p.avoidable_damage for p in ps if p.avoidable_damage is not None)
    return RaidSummary(headline=head, players=ps)
