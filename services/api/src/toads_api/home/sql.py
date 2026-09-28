"""HomeRepository over hub-db."""

from __future__ import annotations

from datetime import UTC, datetime

from hub_db import (
    AnalyzerBadgePage,
    AnalyzerHomePage,
    AnalyzerPerformancePage,
    CharacterClaim,
    ClaimStatus,
    Member,
    MemberHomeLayout,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from toads_api.home.performance import fold
from toads_api.home.repository import MemberCharacters, StoredBadges, StoredPage, StoredPerformance, StoredWidget

# The analyzer's page is guild-wide: one row.
_PAGE_ROW = 1


class SqlHomeRepository:
    def __init__(self, db: sessionmaker[Session]) -> None:
        self._db = db

    def layout(self, member_id: int) -> list[StoredWidget] | None:
        with self._db() as db:
            row = db.get(MemberHomeLayout, member_id)
            if row is None:
                return None
            return [StoredWidget(str(w["id"]), bool(w["shown"])) for w in row.widgets]

    def save_layout(self, member_id: int, widgets: list[StoredWidget]) -> None:
        data: list[dict[str, object]] = [{"id": w.id, "shown": w.shown} for w in widgets]
        try:
            self._write_layout(member_id, data)
        except IntegrityError:
            # Two first saves raced to insert the member's row; the other one won, so this one updates it.
            self._write_layout(member_id, data)

    def _write_layout(self, member_id: int, data: list[dict[str, object]]) -> None:
        with self._db.begin() as db:
            row = db.get(MemberHomeLayout, member_id)
            if row is None:
                db.add(MemberHomeLayout(member_id=member_id, widgets=data, updated_at=datetime.now(UTC)))
            else:
                row.widgets = data
                row.updated_at = datetime.now(UTC)

    def delete_layout(self, member_id: int) -> bool:
        with self._db.begin() as db:
            row = db.get(MemberHomeLayout, member_id)
            if row is None:
                return False
            db.delete(row)
            return True

    def analyzer_page(self) -> StoredPage | None:
        with self._db() as db:
            row = db.get(AnalyzerHomePage, _PAGE_ROW)
            return None if row is None else StoredPage(row.version, row.generated_at, list(row.widgets))

    def save_analyzer_page(self, page: StoredPage) -> None:
        try:
            self._write_page(page)
        except IntegrityError:
            # The first two publications raced to insert the row; update the one that won.
            self._write_page(page)

    def _write_page(self, page: StoredPage) -> None:
        with self._db.begin() as db:
            row = db.get(AnalyzerHomePage, _PAGE_ROW)
            if row is None:
                row = AnalyzerHomePage(id=_PAGE_ROW)
                db.add(row)
            row.version = page.version
            row.generated_at = page.generated_at
            row.widgets = page.widgets
            row.updated_at = datetime.now(UTC)

    def performance_page(self) -> StoredPerformance | None:
        with self._db() as db:
            row = db.get(AnalyzerPerformancePage, _PAGE_ROW)
            if row is None:
                return None
            return StoredPerformance(
                row.version, row.generated_at, dict(row.raid) if row.raid else None, list(row.players)
            )

    def save_performance_page(self, page: StoredPerformance) -> None:
        try:
            self._write_performance(page)
        except IntegrityError:
            # The first two publications raced to insert the row; update the one that won.
            self._write_performance(page)

    def _write_performance(self, page: StoredPerformance) -> None:
        with self._db.begin() as db:
            row = db.get(AnalyzerPerformancePage, _PAGE_ROW)
            if row is None:
                row = AnalyzerPerformancePage(id=_PAGE_ROW)
                db.add(row)
            row.version = page.version
            row.generated_at = page.generated_at
            row.raid = page.raid
            row.players = page.players
            row.updated_at = datetime.now(UTC)

    def badge_page(self) -> StoredBadges | None:
        with self._db() as db:
            row = db.get(AnalyzerBadgePage, _PAGE_ROW)
            return None if row is None else StoredBadges(row.version, row.generated_at, list(row.players))

    def save_badge_page(self, page: StoredBadges) -> None:
        try:
            self._write_badges(page)
        except IntegrityError:
            # The first two publications raced to insert the row; update the one that won.
            self._write_badges(page)

    def _write_badges(self, page: StoredBadges) -> None:
        with self._db.begin() as db:
            row = db.get(AnalyzerBadgePage, _PAGE_ROW)
            if row is None:
                row = AnalyzerBadgePage(id=_PAGE_ROW)
                db.add(row)
            row.version = page.version
            row.generated_at = page.generated_at
            row.players = page.players
            row.updated_at = datetime.now(UTC)

    def member_characters(self, member_id: int) -> MemberCharacters | None:
        with self._db() as db:
            member = db.get(Member, member_id)
            if member is None:
                return None
            claims = db.scalars(select(CharacterClaim).where(CharacterClaim.status != ClaimStatus.REJECTED)).all()
            approved = [c for c in claims if c.member_id == member_id and c.status is ClaimStatus.APPROVED]
            chosen = next(
                (
                    c.character_name
                    for c in approved
                    if member.name_source == "character" and c.character_id == member.name_character_id
                ),
                None,
            )
            return MemberCharacters(
                nickname=member.display_name,
                chosen=chosen,
                approved=sorted((c.character_name for c in approved), key=str.casefold),
                claimed_by_others=frozenset(fold(c.character_name) for c in claims if c.member_id != member_id),
            )
