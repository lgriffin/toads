"""HomeRepository over hub-db."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from hub_db import (
    AnalyzerBadgePage,
    AnalyzerCharacterBuild,
    AnalyzerCharacterPage,
    AnalyzerHomePage,
    AnalyzerPerformancePage,
    CharacterClaim,
    ClaimStatus,
    Member,
    MemberHomeLayout,
    NightHomePage,
    main_claim,
)
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from toads_api.home.repository import (
    MemberCharacters,
    StoredBadges,
    StoredCharacterPage,
    StoredPage,
    StoredPerformance,
    StoredWidget,
    fold,
)

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

    def night_page(self, day: str) -> StoredPage | None:
        with self._db() as db:
            row = db.get(NightHomePage, day)
            return None if row is None else StoredPage(row.version, row.generated_at, list(row.widgets))

    def save_night_page(self, day: str, page: StoredPage) -> None:
        try:
            self._write_night(day, page)
        except IntegrityError:
            # The first two publications of this night raced to insert its row; update the one that won.
            self._write_night(day, page)

    def _write_night(self, day: str, page: StoredPage) -> None:
        with self._db.begin() as db:
            row = db.get(NightHomePage, day)
            if row is None:
                row = NightHomePage(raid_day_id=day)
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

    def save_badge_page(self, page: StoredBadges) -> bool:
        try:
            return self._write_badges(page)
        except IntegrityError:
            # The first two publications raced to insert the row; check against the one that won.
            return self._write_badges(page)

    def _write_badges(self, page: StoredBadges) -> bool:
        with self._db.begin() as db:
            # Locked until commit, so an overlapping older build cannot land after a newer one.
            row = db.get(AnalyzerBadgePage, _PAGE_ROW, with_for_update=True)
            if row is not None and page.generated_at < row.generated_at:
                return False
            if row is None:
                row = AnalyzerBadgePage(id=_PAGE_ROW)
                db.add(row)
            row.version = page.version
            row.generated_at = page.generated_at
            row.players = page.players
            row.updated_at = datetime.now(UTC)
            return True

    def member_characters(self, member_id: int) -> MemberCharacters | None:
        with self._db() as db:
            member = db.get(Member, member_id)
            if member is None:
                return None
            claims = db.scalars(select(CharacterClaim).where(CharacterClaim.status != ClaimStatus.REJECTED)).all()
            approved = [c for c in claims if c.member_id == member_id and c.status is ClaimStatus.APPROVED]
            main = main_claim(member.main_character_id, approved)
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
                nickname_shared=any(
                    fold(name) == fold(member.display_name)
                    for name in db.scalars(select(Member.display_name).where(Member.id != member_id))
                ),
                main=main.character_name if main else None,
            )

    def character_names(self) -> list[str]:
        with self._db() as db:
            claimed = db.scalars(
                select(CharacterClaim.character_name).where(CharacterClaim.status == ClaimStatus.APPROVED)
            ).all()
            nicknames = db.scalars(select(Member.display_name)).all()
        by_key = {fold(n): n.strip() for n in (*nicknames, *claimed) if n and n.strip()}
        return sorted(by_key.values(), key=str.casefold)

    def character_page(self, name: str) -> StoredCharacterPage | None:
        with self._db() as db:
            row = db.get(AnalyzerCharacterPage, fold(name))
            return None if row is None else StoredCharacterPage(row.version, row.generated_at, dict(row.page))

    def character_pages_generated_at(self) -> str | None:
        with self._db() as db:
            build = db.get(AnalyzerCharacterBuild, _PAGE_ROW)
            return None if build is None else build.generated_at

    def save_character_pages(self, version: int, generated_at: str, pages: list[dict[str, Any]]) -> bool:
        try:
            return self._write_character_pages(version, generated_at, pages)
        except IntegrityError:
            # The first two publications raced to insert the build row; the loser tries again behind the winner.
            return self._write_character_pages(version, generated_at, pages)

    def _write_character_pages(self, version: int, generated_at: str, pages: list[dict[str, Any]]) -> bool:
        with self._db.begin() as db:
            # The build row is locked for the whole transaction (on Postgres), so publications never interleave, and
            # it remembers the newest build even when it held no pages: a delayed or retried older one is refused.
            now = datetime.now(UTC)
            build = db.get(AnalyzerCharacterBuild, _PAGE_ROW, with_for_update=True)
            if build is None:
                build = AnalyzerCharacterBuild(id=_PAGE_ROW, version=version, generated_at=generated_at)
                db.add(build)
                db.flush()
            elif generated_at < build.generated_at:
                return False
            build.version, build.generated_at, build.updated_at = version, generated_at, now
            db.execute(delete(AnalyzerCharacterPage))
            for page in pages:
                db.add(
                    AnalyzerCharacterPage(
                        name_key=fold(str(page["name"])),
                        version=version,
                        generated_at=generated_at,
                        page=page,
                        updated_at=now,
                    )
                )
            return True
