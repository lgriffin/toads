"""Rules for members' specs and officers' comps. No RBAC, web framework or storage imports: the routes decide who may
call (and for which raid day), and the repository decides where things live."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime

from toads_api.comps.catalog import CLASSES, RAID_SIZES, SPECS
from toads_api.comps.repository import CompRecord, CompRepository, DuplicateCompError, Seat, SpecRecord

NAME_MAX = 80


class CompError(Exception):
    """A request the rules refuse. `status` is the HTTP code the adapter should answer with."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


@dataclass(frozen=True)
class PoolEntry:
    """A member on a raid day's roster, by the name they chose. No class means they have not set their specs yet."""

    member_id: int
    name: str
    wow_class: str | None
    primary: str | None
    secondary: str | None


@dataclass(frozen=True)
class SeatView:
    spec: str
    member_id: int | None
    # The member's chosen name, or None for a seat with no one in it (or someone no longer in the hub).
    member_name: str | None


@dataclass(frozen=True)
class CompView:
    id: int
    raid_day: str
    name: str
    size: int
    slots: list[SeatView | None]
    updated_by: str | None
    updated_at: datetime


def check_specs(wow_class: str, primary: str, secondary: str | None) -> None:
    """A known class, a primary of that class, and an optional, different secondary of the same class."""
    if wow_class not in CLASSES:
        raise CompError("Unknown class", status=422)
    for spec in (primary, secondary):
        if spec is not None and (spec not in SPECS or SPECS[spec].wow_class != wow_class):
            raise CompError(f"Choose a {CLASSES[wow_class]} spec", status=422)
    if secondary == primary:
        raise CompError("Your secondary spec must differ from your primary", status=422)


class CompService:
    def __init__(self, repo: CompRepository, shown_names: Callable[[Iterable[int]], Mapping[int, str]]) -> None:
        self.repo = repo
        self._names = shown_names

    # ---------------------------------------------------------------- specs

    def my_specs(self, member_id: int) -> SpecRecord | None:
        found = self.repo.specs([member_id])
        return found[0] if found else None

    def set_specs(self, member_id: int, wow_class: str, primary: str, secondary: str | None) -> SpecRecord:
        check_specs(wow_class, primary, secondary)
        record = SpecRecord(member_id, wow_class, primary, secondary)
        self.repo.set_specs(record)
        return record

    def clear_specs(self, member_id: int) -> None:
        self.repo.clear_specs(member_id)

    # ----------------------------------------------------------------- pool

    def pool(self, raid_day: str) -> list[PoolEntry]:
        """Everyone on the raid day, specs set or not, sorted by name."""
        ids = self.repo.members_on(raid_day)
        names = self._names(ids)
        specs = {r.member_id: r for r in self.repo.specs(ids)}
        entries = []
        for member_id in ids:
            if member_id not in names:
                continue
            s = specs.get(member_id)
            entries.append(
                PoolEntry(
                    member_id,
                    names[member_id],
                    s.wow_class if s else None,
                    s.primary if s else None,
                    s.secondary if s else None,
                )
            )
        return sorted(entries, key=lambda e: (e.name.casefold(), e.member_id))

    # ---------------------------------------------------------------- comps

    def _view(self, row: CompRecord, names: Mapping[int, str]) -> CompView:
        slots = [
            None if s is None else SeatView(s.spec, s.member_id, names.get(s.member_id) if s.member_id else None)
            for s in row.slots
        ]
        by = names.get(row.updated_by) if row.updated_by is not None else None
        return CompView(row.id, row.raid_day, row.name, row.size, slots, by, row.updated_at)

    def _views(self, rows: list[CompRecord]) -> list[CompView]:
        ids = {s.member_id for r in rows for s in r.slots if s is not None and s.member_id is not None}
        ids |= {r.updated_by for r in rows if r.updated_by is not None}
        names = self._names(ids)
        return [self._view(r, names) for r in rows]

    def comps(self, raid_day: str) -> list[CompView]:
        rows = sorted(self.repo.comps(raid_day), key=lambda r: (r.name.casefold(), r.id))
        return self._views(rows)

    def save_comp(
        self, raid_day: str, comp_id: int | None, name: str, size: int, slots: list[Seat | None], by: int
    ) -> CompView:
        name = " ".join(name.split())
        if not name or len(name) > NAME_MAX:
            raise CompError(f"Give the comp a name of up to {NAME_MAX} characters", status=422)
        if size not in RAID_SIZES:
            raise CompError("A comp seats 10, 20 or 40", status=422)
        if len(slots) != size:
            raise CompError(f"A comp of {size} has {size} seats", status=422)
        seated = [s.member_id for s in slots if s is not None and s.member_id is not None]
        if len(seated) != len(set(seated)):
            raise CompError("Each member can take one seat", status=422)
        if any(s is not None and s.spec not in SPECS for s in slots):
            raise CompError("Unknown spec", status=422)
        if set(seated) - set(self._names(seated)):
            raise CompError("Someone in the comp is not a hub member", status=422)
        # Officers may seat anyone in the hub (a fill-in from the other night) in any spec of their class, but never
        # as another class.
        classes = {r.member_id: r.wow_class for r in self.repo.specs(seated)}
        for s in slots:
            if s is not None and s.member_id in classes and SPECS[s.spec].wow_class != classes[s.member_id]:
                raise CompError(
                    f"{self._names([s.member_id])[s.member_id]} plays a {CLASSES[classes[s.member_id]]}", 422
                )
        try:
            row = self.repo.save_comp(raid_day, comp_id, name, size, slots, by)
        except DuplicateCompError:
            raise CompError(f"This raid day already has a comp called {name}", status=409) from None
        if row is None:
            raise CompError("No such comp", status=404)
        return self._views([row])[0]

    def delete_comp(self, raid_day: str, comp_id: int, by: int) -> None:
        if not self.repo.delete_comp(raid_day, comp_id, by):
            raise CompError("No such comp", status=404)
