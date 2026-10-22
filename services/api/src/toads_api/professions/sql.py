"""ProfessionRepository over hub-db. Naming and un-naming a guild crafter are officer actions, so each is written to the
audit log in the same transaction."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

from hub_db import GuildCrafter, Member, MemberProfession
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from toads_api import audit
from toads_api.professions.repository import CrafterRecord, ProfessionRecord


def _crafter(row: GuildCrafter) -> CrafterRecord:
    return CrafterRecord(row.profession, row.member_id, row.note, row.designated_by, row.designated_at)


class SqlProfessionRepository:
    def __init__(self, db: sessionmaker[Session]) -> None:
        self._db = db

    def professions(self, member_ids: Iterable[int] | None = None) -> list[ProfessionRecord]:
        query = select(MemberProfession).order_by(MemberProfession.member_id, MemberProfession.profession)
        if member_ids is not None:
            query = query.where(MemberProfession.member_id.in_(list(member_ids)))
        with self._db() as db:
            return [ProfessionRecord(r.member_id, r.profession, r.skill, r.specialisation) for r in db.scalars(query)]

    def set_professions(self, member_id: int, records: list[ProfessionRecord]) -> list[str]:
        kept = [r.profession for r in records]
        now = datetime.now(UTC)
        with self._db.begin() as db:
            db.execute(delete(MemberProfession).where(MemberProfession.member_id == member_id))
            for r in records:
                db.add(
                    MemberProfession(
                        member_id=member_id,
                        profession=r.profession,
                        skill=r.skill,
                        specialisation=r.specialisation,
                        updated_at=now,
                    )
                )
            gone = list(
                db.scalars(
                    select(GuildCrafter.profession)
                    .where(GuildCrafter.member_id == member_id, GuildCrafter.profession.not_in(kept))
                    .order_by(GuildCrafter.profession)
                )
            )
            if gone:
                db.execute(
                    delete(GuildCrafter).where(GuildCrafter.member_id == member_id, GuildCrafter.profession.in_(gone))
                )
                # The member's own act, so they are the actor: the log shows why the naming ended.
                for profession in gone:
                    audit.record(
                        db,
                        actor=member_id,
                        action="crafter.unlisted",
                        target=f"member:{member_id} {profession}",
                        raid_day=None,
                    )
            return gone

    def crafters(self, member_ids: Iterable[int] | None = None) -> list[CrafterRecord]:
        query = select(GuildCrafter).order_by(GuildCrafter.profession, GuildCrafter.member_id)
        if member_ids is not None:
            query = query.where(GuildCrafter.member_id.in_(list(member_ids)))
        with self._db() as db:
            return [_crafter(r) for r in db.scalars(query)]

    def designate(
        self, profession: str, member_id: int, note: str | None, by: int, raid_day: str | None
    ) -> CrafterRecord:
        try:
            return self._designate(profession, member_id, note, by, raid_day)
        except IntegrityError:
            # Another officer named them in the same moment; the row exists now, so this write updates it.
            return self._designate(profession, member_id, note, by, raid_day)

    def _designate(
        self, profession: str, member_id: int, note: str | None, by: int, raid_day: str | None
    ) -> CrafterRecord:
        with self._db.begin() as db:
            row = db.get(GuildCrafter, (profession, member_id))
            if row is None:
                row = GuildCrafter(profession=profession, member_id=member_id)
                db.add(row)
            row.note, row.designated_by, row.designated_at = note, by, datetime.now(UTC)
            db.flush()
            audit.record(
                db, actor=by, action="crafter.name", target=f"member:{member_id} {profession}", raid_day=raid_day
            )
            return _crafter(row)

    def undesignate(self, profession: str, member_id: int, by: int, raid_day: str | None) -> bool:
        with self._db.begin() as db:
            row = db.get(GuildCrafter, (profession, member_id))
            if row is None:
                return False
            audit.record(
                db, actor=by, action="crafter.unname", target=f"member:{member_id} {profession}", raid_day=raid_day
            )
            db.delete(row)
            return True

    def members_on(self, raid_day: str) -> list[int]:
        # The guild is a few hundred members at most, so the JSON list is read here rather than queried per dialect.
        with self._db() as db:
            rows = db.execute(select(Member.id, Member.raid_days).where(Member.raid_days.is_not(None)))
            return [member_id for member_id, days in rows if isinstance(days, list) and raid_day in days]
