"""HomeRepository over hub-db."""

from __future__ import annotations

from datetime import UTC, datetime

from hub_db import AnalyzerHomePage, MemberHomeLayout
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from toads_api.home.repository import StoredPage, StoredWidget

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
