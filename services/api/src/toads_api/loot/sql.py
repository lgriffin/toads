"""LootRepository over hub-db. Every change is an officer's action, so each is written to the audit log in the same
transaction."""

from __future__ import annotations

from datetime import datetime

from hub_db import LootItem, LootRecipient
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from toads_api import audit
from toads_api.loot.repository import InLine, LootEntry


def _target(entry_id: int) -> str:
    return f"loot_item:{entry_id}"


class SqlLootRepository:
    def __init__(self, db: sessionmaker[Session]) -> None:
        self._db = db

    def _entries(self, db: Session, rows: list[LootItem]) -> list[LootEntry]:
        lines: dict[int, list[InLine]] = {r.id: [] for r in rows}
        if rows:
            query = (
                select(LootRecipient)
                .where(LootRecipient.loot_item_id.in_(lines))
                .order_by(LootRecipient.loot_item_id, LootRecipient.rank)
            )
            for r in db.scalars(query):
                lines[r.loot_item_id].append(InLine(r.member_id, r.rank, r.received_at))
        return [
            LootEntry(
                id=r.id,
                raid_day=r.raid_day_id,
                item_id=r.item_id,
                item_name=r.item_name,
                note=r.note,
                recipients=tuple(lines[r.id]),
                created_by=r.created_by,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in rows
        ]

    def _row(self, db: Session, raid_day: str, entry_id: int) -> LootItem | None:
        row = db.get(LootItem, entry_id)
        return row if row is not None and row.raid_day_id == raid_day else None

    def _one(self, db: Session, row: LootItem) -> LootEntry:
        db.flush()
        return self._entries(db, [row])[0]

    def entries(self, raid_day: str) -> list[LootEntry]:
        query = select(LootItem).where(LootItem.raid_day_id == raid_day).order_by(LootItem.id)
        with self._db() as db:
            return self._entries(db, list(db.scalars(query)))

    def entry(self, raid_day: str, entry_id: int) -> LootEntry | None:
        with self._db() as db:
            row = self._row(db, raid_day, entry_id)
            return None if row is None else self._entries(db, [row])[0]

    def add(self, raid_day: str, item_id: int, item_name: str, note: str, by: int, at: datetime) -> LootEntry | None:
        try:
            with self._db.begin() as db:
                row = LootItem(
                    raid_day_id=raid_day,
                    item_id=item_id,
                    item_name=item_name,
                    note=note,
                    created_by=by,
                    created_at=at,
                    updated_at=at,
                )
                db.add(row)
                db.flush()
                audit.record(
                    db, actor=by, action="loot.add", target=_target(row.id), raid_day=raid_day, detail=item_name
                )
                return self._one(db, row)
        except IntegrityError:
            # (raid_day_id, item_id) is unique: the item is on the list already, perhaps added a moment ago.
            return None

    def set_note(self, raid_day: str, entry_id: int, note: str, by: int, at: datetime) -> LootEntry | None:
        with self._db.begin() as db:
            row = self._row(db, raid_day, entry_id)
            if row is None:
                return None
            row.note = note
            row.updated_at = at
            audit.record(db, actor=by, action="loot.note", target=_target(entry_id), raid_day=raid_day)
            return self._one(db, row)

    def set_line(self, raid_day: str, entry_id: int, member_ids: list[int], by: int, at: datetime) -> LootEntry | None:
        with self._db.begin() as db:
            row = self._row(db, raid_day, entry_id)
            if row is None:
                return None
            current = {
                r.member_id: r for r in db.scalars(select(LootRecipient).where(LootRecipient.loot_item_id == row.id))
            }
            keep = set(member_ids)
            gone = [m for m in current if m not in keep]
            if gone:
                db.execute(
                    delete(LootRecipient).where(LootRecipient.loot_item_id == row.id, LootRecipient.member_id.in_(gone))
                )
            for rank, member_id in enumerate(member_ids, start=1):
                existing = current.get(member_id)
                if existing is None:
                    db.add(LootRecipient(loot_item_id=row.id, member_id=member_id, rank=rank))
                else:
                    existing.rank = rank
            row.updated_at = at
            audit.record(
                db,
                actor=by,
                action="loot.line",
                target=_target(entry_id),
                raid_day=raid_day,
                detail=",".join(str(m) for m in member_ids),
            )
            return self._one(db, row)

    def mark(
        self, raid_day: str, entry_id: int, member_id: int, received_at: datetime | None, by: int
    ) -> LootEntry | None:
        with self._db.begin() as db:
            row = self._row(db, raid_day, entry_id)
            if row is None:
                return None
            line = db.scalar(
                select(LootRecipient).where(LootRecipient.loot_item_id == row.id, LootRecipient.member_id == member_id)
            )
            if line is None:
                return None
            line.received_at = received_at
            action = "loot.received" if received_at is not None else "loot.unreceived"
            audit.record(
                db, actor=by, action=action, target=_target(entry_id), raid_day=raid_day, detail=str(member_id)
            )
            return self._one(db, row)

    def remove(self, raid_day: str, entry_id: int, by: int) -> bool:
        with self._db.begin() as db:
            row = self._row(db, raid_day, entry_id)
            if row is None:
                return False
            audit.record(
                db, actor=by, action="loot.remove", target=_target(entry_id), raid_day=raid_day, detail=row.item_name
            )
            db.execute(delete(LootRecipient).where(LootRecipient.loot_item_id == entry_id))
            db.delete(row)
            return True
