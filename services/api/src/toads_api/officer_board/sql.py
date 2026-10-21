"""BoardRepository over hub-db. Every change is an officer's action, so each is written to the audit log in the same
transaction."""

from __future__ import annotations

from datetime import UTC, datetime

from hub_db import NightLink as NightLinkRow
from hub_db import OfficerBoardCard
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from toads_api import audit
from toads_api.officer_board.repository import Card, CardFields, NightLink


def _card(row: OfficerBoardCard) -> Card:
    return Card(
        id=row.id,
        raid_day=row.raid_day_id,
        lane=row.lane,
        position=row.position,
        fields=CardFields(row.title, row.notes, row.assignee_member_id, row.due_on),
        created_by=row.created_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _link(row: NightLinkRow) -> NightLink:
    return NightLink(row.id, row.raid_day_id, row.position, row.label, row.url, row.created_by, row.created_at)


def _target(card_id: int) -> str:
    return f"board_card:{card_id}"


class SqlBoardRepository:
    def __init__(self, db: sessionmaker[Session]) -> None:
        self._db = db

    def cards(self, raid_day: str) -> list[Card]:
        query = (
            select(OfficerBoardCard)
            .where(OfficerBoardCard.raid_day_id == raid_day)
            .order_by(OfficerBoardCard.lane, OfficerBoardCard.position, OfficerBoardCard.id)
        )
        with self._db() as db:
            return [_card(r) for r in db.scalars(query)]

    def _row(self, db: Session, raid_day: str, card_id: int) -> OfficerBoardCard | None:
        row = db.get(OfficerBoardCard, card_id)
        return row if row is not None and row.raid_day_id == raid_day else None

    def add(self, raid_day: str, lane: str, fields: CardFields, by: int) -> Card:
        last = select(func.max(OfficerBoardCard.position)).where(
            OfficerBoardCard.raid_day_id == raid_day, OfficerBoardCard.lane == lane
        )
        with self._db.begin() as db:
            top = db.scalar(last)
            row = OfficerBoardCard(
                raid_day_id=raid_day,
                lane=lane,
                position=0 if top is None else top + 1,
                title=fields.title,
                notes=fields.notes,
                assignee_member_id=fields.assignee_member_id,
                due_on=fields.due_on,
                created_by=by,
            )
            db.add(row)
            db.flush()
            audit.record(db, actor=by, action="board.add", target=_target(row.id), raid_day=raid_day)
            return _card(row)

    def edit(self, raid_day: str, card_id: int, fields: CardFields, by: int) -> Card | None:
        with self._db.begin() as db:
            row = self._row(db, raid_day, card_id)
            if row is None:
                return None
            row.title = fields.title
            row.notes = fields.notes
            row.assignee_member_id = fields.assignee_member_id
            row.due_on = fields.due_on
            row.updated_at = datetime.now(UTC)
            audit.record(db, actor=by, action="board.edit", target=_target(card_id), raid_day=raid_day)
            db.flush()
            return _card(row)

    def arrange(self, raid_day: str, card_id: int, lanes: dict[str, list[int]], by: int) -> bool:
        with self._db.begin() as db:
            if self._row(db, raid_day, card_id) is None:
                return False
            for lane, ids in lanes.items():
                for position, cid in enumerate(ids):
                    row = self._row(db, raid_day, cid)
                    if row is not None:
                        row.lane = lane
                        row.position = position
            moved = next(lane for lane, ids in lanes.items() if card_id in ids)
            row = self._row(db, raid_day, card_id)
            if row is not None:
                row.updated_at = datetime.now(UTC)
            audit.record(db, actor=by, action="board.move", target=_target(card_id), raid_day=raid_day, detail=moved)
            return True

    def remove(self, raid_day: str, card_id: int, by: int) -> bool:
        with self._db.begin() as db:
            row = self._row(db, raid_day, card_id)
            if row is None:
                return False
            audit.record(db, actor=by, action="board.remove", target=_target(card_id), raid_day=raid_day)
            db.delete(row)
            return True

    def links(self, raid_day: str) -> list[NightLink]:
        query = (
            select(NightLinkRow)
            .where(NightLinkRow.raid_day_id == raid_day)
            .order_by(NightLinkRow.position, NightLinkRow.id)
        )
        with self._db() as db:
            return [_link(r) for r in db.scalars(query)]

    def add_link(self, raid_day: str, label: str, url: str, by: int) -> NightLink:
        last = select(func.max(NightLinkRow.position)).where(NightLinkRow.raid_day_id == raid_day)
        with self._db.begin() as db:
            top = db.scalar(last)
            row = NightLinkRow(
                raid_day_id=raid_day, position=0 if top is None else top + 1, label=label, url=url, created_by=by
            )
            db.add(row)
            db.flush()
            audit.record(db, actor=by, action="board.link_add", target=f"night_link:{row.id}", raid_day=raid_day)
            return _link(row)

    def remove_link(self, raid_day: str, link_id: int, by: int) -> bool:
        with self._db.begin() as db:
            row = db.get(NightLinkRow, link_id)
            if row is None or row.raid_day_id != raid_day:
                return False
            audit.record(db, actor=by, action="board.link_remove", target=f"night_link:{link_id}", raid_day=raid_day)
            db.delete(row)
            return True
