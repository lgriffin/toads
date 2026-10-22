"""GalleryRepository over hub-db. Officers' changes are written with their audit entry in one transaction."""

from __future__ import annotations

from collections.abc import Collection
from datetime import UTC, datetime
from typing import Any, cast

from hub_db import GalleryPhoto, GalleryPhotoFile, LiveStream, Member, PhotoOfTheWeek, TrustedChannel
from sqlalchemy import CursorResult, delete, func, select, update
from sqlalchemy.orm import Session, sessionmaker

from toads_api import audit
from toads_api.gallery.repository import (
    AuditNote,
    NewPhoto,
    NewStream,
    PhotoRecord,
    PickRecord,
    StreamRecord,
)


def _aware(at: datetime) -> datetime:
    """SQLite hands back naive datetimes; every time stored here is UTC."""
    return at if at.tzinfo is not None else at.replace(tzinfo=UTC)


def _maybe(at: datetime | None) -> datetime | None:
    return None if at is None else _aware(at)


def _photo(row: GalleryPhoto) -> PhotoRecord:
    return PhotoRecord(
        id=row.id,
        discord_user_id=row.discord_user_id,
        uploader_name=row.uploader_name,
        caption=row.caption,
        width=row.width,
        height=row.height,
        media_type=row.media_type,
        source=row.source,
        created_at=_aware(row.created_at),
        approved_at=_maybe(row.approved_at),
    )


def _pick(row: PhotoOfTheWeek) -> PickRecord:
    return PickRecord(row.id, row.photo_id, row.chosen_by_name, _aware(row.starts_at), _aware(row.ends_at))


def _stream(row: LiveStream) -> StreamRecord:
    return StreamRecord(
        id=row.id,
        discord_user_id=row.discord_user_id,
        streamer_name=row.streamer_name,
        channel=row.channel,
        title=row.title,
        started_at=_aware(row.started_at),
        ends_at=_aware(row.ends_at),
        ended_at=_maybe(row.ended_at),
        approved_at=_maybe(row.approved_at),
    )


def _audit(db: Session, note: AuditNote) -> None:
    audit.record(db, actor=note.actor, action=note.action, target=note.target, raid_day=None, detail=note.detail)


class SqlGalleryRepository:
    def __init__(self, db: sessionmaker[Session]) -> None:
        self._db = db

    def add_photo(self, photo: NewPhoto) -> PhotoRecord:
        with self._db.begin() as db:
            row = GalleryPhoto(
                discord_user_id=photo.discord_user_id,
                uploader_name=photo.uploader_name,
                caption=photo.caption,
                width=photo.width,
                height=photo.height,
                media_type=photo.media_type,
                source=photo.source,
                created_at=photo.at,
            )
            db.add(row)
            db.flush()
            db.add(GalleryPhotoFile(photo_id=row.id, image=photo.image, thumbnail=photo.thumbnail))
            return _photo(row)

    def get_photo(self, photo_id: int) -> PhotoRecord | None:
        with self._db() as db:
            row = db.get(GalleryPhoto, photo_id)
            return None if row is None else _photo(row)

    def photos(
        self, *, since: datetime | None = None, before_id: int | None = None, limit: int | None = None
    ) -> list[PhotoRecord]:
        query = select(GalleryPhoto).where(GalleryPhoto.approved_at.is_not(None)).order_by(GalleryPhoto.id.desc())
        if since is not None:
            query = query.where(GalleryPhoto.approved_at >= since)
        if before_id is not None:
            query = query.where(GalleryPhoto.id < before_id)
        if limit is not None:
            query = query.limit(limit)
        with self._db() as db:
            return [_photo(r) for r in db.scalars(query)]

    def pending_photos(self, discord_user_id: int | None = None) -> list[PhotoRecord]:
        query = select(GalleryPhoto).where(GalleryPhoto.approved_at.is_(None)).order_by(GalleryPhoto.id)
        if discord_user_id is not None:
            query = query.where(GalleryPhoto.discord_user_id == discord_user_id)
        with self._db() as db:
            return [_photo(r) for r in db.scalars(query)]

    def approve_photo(self, photo_id: int, at: datetime, note: AuditNote) -> PhotoRecord | None:
        with self._db.begin() as db:
            row = db.get(GalleryPhoto, photo_id)
            if row is None:
                return None
            row.approved_at = at
            row.approved_by = note.actor
            _audit(db, note)
            db.flush()
            return _photo(row)

    def nights_of(self, discord_user_ids: Collection[int]) -> dict[int, frozenset[str]]:
        if not discord_user_ids:
            return {}
        query = select(Member.discord_user_id, Member.raid_days).where(
            Member.discord_user_id.in_(list(discord_user_ids))
        )
        with self._db() as db:
            return {int(i): frozenset(days) for i, days in db.execute(query) if days}

    def photo_file(self, photo_id: int, thumbnail: bool) -> tuple[bytes, str] | None:
        column = GalleryPhotoFile.thumbnail if thumbnail else GalleryPhotoFile.image
        query = (
            select(column, GalleryPhoto.media_type)
            .join(GalleryPhoto, GalleryPhoto.id == GalleryPhotoFile.photo_id)
            .where(GalleryPhotoFile.photo_id == photo_id)
        )
        with self._db() as db:
            found = db.execute(query).first()
            return None if found is None else (bytes(found[0]), str(found[1]))

    def photos_posted_since(self, discord_user_id: int, since: datetime) -> int:
        query = select(func.count(GalleryPhoto.id)).where(
            GalleryPhoto.discord_user_id == discord_user_id, GalleryPhoto.created_at >= since
        )
        with self._db() as db:
            return int(db.scalar(query) or 0)

    def delete_photo(self, photo_id: int, note: AuditNote) -> bool:
        with self._db.begin() as db:
            # Deleted explicitly rather than by cascade: SQLite only cascades with its foreign key pragma on.
            db.execute(delete(PhotoOfTheWeek).where(PhotoOfTheWeek.photo_id == photo_id))
            db.execute(delete(GalleryPhotoFile).where(GalleryPhotoFile.photo_id == photo_id))
            gone = cast(CursorResult[Any], db.execute(delete(GalleryPhoto).where(GalleryPhoto.id == photo_id))).rowcount
            if not gone:
                return False
            _audit(db, note)
            return True

    def pick(self, photo_id: int, chosen_by: int, chosen_by_name: str, at: datetime, ends_at: datetime) -> PickRecord:
        with self._db.begin() as db:
            db.execute(
                update(PhotoOfTheWeek)
                .where(PhotoOfTheWeek.starts_at <= at, PhotoOfTheWeek.ends_at > at)
                .values(ends_at=at)
            )
            row = PhotoOfTheWeek(
                photo_id=photo_id, chosen_by=chosen_by, chosen_by_name=chosen_by_name, starts_at=at, ends_at=ends_at
            )
            db.add(row)
            _audit(db, AuditNote(chosen_by, "gallery.photo_of_the_week", f"photo {photo_id}"))
            db.flush()
            return _pick(row)

    def picks(self) -> list[PickRecord]:
        with self._db() as db:
            return [_pick(r) for r in db.scalars(select(PhotoOfTheWeek).order_by(PhotoOfTheWeek.id.desc()))]

    def start_stream(self, stream: NewStream) -> StreamRecord:
        with self._db.begin() as db:
            self._end_open(db, stream.discord_user_id, stream.at)
            row = LiveStream(
                discord_user_id=stream.discord_user_id,
                streamer_name=stream.streamer_name,
                channel=stream.channel,
                title=stream.title,
                started_at=stream.at,
                ends_at=stream.ends_at,
                approved_at=stream.at if stream.approved else None,
            )
            db.add(row)
            db.flush()
            return _stream(row)

    def trusted(self, discord_user_id: int, channel: str) -> bool:
        with self._db() as db:
            return db.get(TrustedChannel, (discord_user_id, channel)) is not None

    def approve_stream(self, stream_id: int, at: datetime, approved_by: int, note: AuditNote) -> StreamRecord | None:
        with self._db.begin() as db:
            row = db.get(LiveStream, stream_id)
            if row is None:
                return None
            row.approved_at = at
            if db.get(TrustedChannel, (row.discord_user_id, row.channel)) is None:
                db.add(
                    TrustedChannel(
                        discord_user_id=row.discord_user_id,
                        channel=row.channel,
                        approved_by=approved_by,
                        approved_at=at,
                    )
                )
            _audit(db, note)
            db.flush()
            return _stream(row)

    def untrust(self, discord_user_id: int, channel: str) -> None:
        with self._db.begin() as db:
            db.execute(
                delete(TrustedChannel).where(
                    TrustedChannel.discord_user_id == discord_user_id, TrustedChannel.channel == channel
                )
            )

    @staticmethod
    def _end_open(db: Session, discord_user_id: int, at: datetime) -> int:
        result = cast(
            CursorResult[Any],
            db.execute(
                update(LiveStream)
                .where(LiveStream.discord_user_id == discord_user_id, LiveStream.ended_at.is_(None))
                .values(ended_at=at)
            ),
        )
        return int(result.rowcount or 0)

    def end_streams_of(self, discord_user_id: int, at: datetime) -> int:
        with self._db.begin() as db:
            return self._end_open(db, discord_user_id, at)

    def get_stream(self, stream_id: int) -> StreamRecord | None:
        with self._db() as db:
            row = db.get(LiveStream, stream_id)
            return None if row is None else _stream(row)

    def end_stream(self, stream_id: int, at: datetime, note: AuditNote | None = None) -> StreamRecord | None:
        with self._db.begin() as db:
            row = db.get(LiveStream, stream_id)
            if row is None:
                return None
            if row.ended_at is None:
                row.ended_at = at
            if note is not None:
                _audit(db, note)
            db.flush()
            return _stream(row)

    def open_streams(self, at: datetime) -> list[StreamRecord]:
        query = (
            select(LiveStream)
            .where(LiveStream.ended_at.is_(None), LiveStream.ends_at > at, LiveStream.approved_at.is_not(None))
            .order_by(LiveStream.id.desc())
        )
        with self._db() as db:
            return [_stream(r) for r in db.scalars(query)]

    def pending_streams(self, at: datetime) -> list[StreamRecord]:
        query = (
            select(LiveStream)
            .where(LiveStream.ended_at.is_(None), LiveStream.ends_at > at, LiveStream.approved_at.is_(None))
            .order_by(LiveStream.id)
        )
        with self._db() as db:
            return [_stream(r) for r in db.scalars(query)]
