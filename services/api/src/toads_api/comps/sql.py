"""CompRepository over hub-db. Saving and deleting a comp are officer actions, so each is written to the audit log in
the same transaction."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

from hub_db import Member, MemberSpec, RaidComp
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from toads_api import audit
from toads_api.comps.repository import CompRecord, DuplicateCompError, Seat, SpecRecord


def _seat(raw: object) -> Seat | None:
    if not isinstance(raw, dict) or not isinstance(raw.get("spec"), str):
        return None
    member = raw.get("member_id")
    return Seat(raw["spec"], member if isinstance(member, int) else None)


def _record(row: RaidComp) -> CompRecord:
    return CompRecord(
        id=row.id,
        raid_day=row.raid_day_id,
        name=row.name,
        size=row.size,
        slots=[_seat(s) for s in row.slots],
        updated_by=row.updated_by,
        updated_at=row.updated_at,
    )


def _slots(slots: list[Seat | None]) -> list[dict[str, object] | None]:
    return [None if s is None else {"spec": s.spec, "member_id": s.member_id} for s in slots]


class SqlCompRepository:
    def __init__(self, db: sessionmaker[Session]) -> None:
        self._db = db

    def specs(self, member_ids: Iterable[int] | None = None) -> list[SpecRecord]:
        query = select(MemberSpec).order_by(MemberSpec.member_id)
        if member_ids is not None:
            query = query.where(MemberSpec.member_id.in_(list(member_ids)))
        with self._db() as db:
            return [SpecRecord(r.member_id, r.wow_class, r.primary_spec, r.secondary_spec) for r in db.scalars(query)]

    def set_specs(self, record: SpecRecord) -> None:
        with self._db.begin() as db:
            row = db.get(MemberSpec, record.member_id)
            if row is None:
                row = MemberSpec(member_id=record.member_id)
                db.add(row)
            row.wow_class = record.wow_class
            row.primary_spec = record.primary
            row.secondary_spec = record.secondary
            row.updated_at = datetime.now(UTC)

    def clear_specs(self, member_id: int) -> bool:
        with self._db.begin() as db:
            row = db.get(MemberSpec, member_id)
            if row is None:
                return False
            db.delete(row)
            return True

    def members_on(self, raid_day: str) -> list[int]:
        # The guild is a few hundred members at most, so the JSON list is read here rather than queried per dialect.
        with self._db() as db:
            rows = db.execute(select(Member.id, Member.raid_days).where(Member.raid_days.is_not(None)))
            return [member_id for member_id, days in rows if isinstance(days, list) and raid_day in days]

    def signed_in(self, member_ids: Iterable[int]) -> set[int]:
        query = select(Member.id).where(Member.id.in_(list(member_ids)), Member.signed_in_at.is_not(None))
        with self._db() as db:
            return set(db.scalars(query))

    def comps(self, raid_day: str) -> list[CompRecord]:
        with self._db() as db:
            query = select(RaidComp).where(RaidComp.raid_day_id == raid_day).order_by(RaidComp.id)
            return [_record(r) for r in db.scalars(query)]

    def save_comp(
        self, raid_day: str, comp_id: int | None, name: str, size: int, slots: list[Seat | None], by: int
    ) -> CompRecord | None:
        try:
            with self._db.begin() as db:
                if comp_id is None:
                    row = RaidComp(raid_day_id=raid_day)
                    db.add(row)
                else:
                    found = db.get(RaidComp, comp_id)
                    if found is None or found.raid_day_id != raid_day:
                        return None
                    row = found
                row.name, row.size, row.slots, row.updated_by = name, size, _slots(slots), by
                row.updated_at = datetime.now(UTC)
                db.flush()
                audit.record(db, actor=by, action="comp.save", target=f"comp:{row.id} {name}", raid_day=raid_day)
                return _record(row)
        except IntegrityError:
            raise DuplicateCompError from None

    def delete_comp(self, raid_day: str, comp_id: int, by: int) -> bool:
        with self._db.begin() as db:
            row = db.get(RaidComp, comp_id)
            if row is None or row.raid_day_id != raid_day:
                return False
            audit.record(db, actor=by, action="comp.delete", target=f"comp:{row.id} {row.name}", raid_day=raid_day)
            db.delete(row)
            return True
