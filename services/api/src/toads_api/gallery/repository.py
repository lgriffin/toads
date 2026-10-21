"""Where Highlights photos, photo-of-the-week picks and live streams live. GalleryService only talks to the
GalleryRepository protocol; the hub-db backed implementation is `sql.SqlGalleryRepository`."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class AuditNote:
    """What the audit log records for an officer's change: who, the action and its target."""

    actor: int
    action: str
    target: str
    detail: str | None = None


@dataclass(frozen=True)
class NewPhoto:
    discord_user_id: int
    uploader_name: str
    caption: str
    source: str
    at: datetime
    image: bytes
    thumbnail: bytes
    width: int
    height: int
    media_type: str


@dataclass(frozen=True)
class PhotoRecord:
    id: int
    discord_user_id: int
    uploader_name: str
    caption: str
    width: int
    height: int
    media_type: str
    source: str
    created_at: datetime


@dataclass(frozen=True)
class PickRecord:
    """One photo-of-the-week pick."""

    id: int
    photo_id: int
    chosen_by_name: str
    starts_at: datetime
    ends_at: datetime


@dataclass(frozen=True)
class NewStream:
    discord_user_id: int
    streamer_name: str
    channel: str
    title: str
    at: datetime
    ends_at: datetime


@dataclass(frozen=True)
class StreamRecord:
    id: int
    discord_user_id: int
    streamer_name: str
    channel: str
    title: str
    started_at: datetime
    ends_at: datetime
    ended_at: datetime | None = None


class GalleryRepository(Protocol):
    def add_photo(self, photo: NewPhoto) -> PhotoRecord: ...

    def get_photo(self, photo_id: int) -> PhotoRecord | None: ...

    def photos(
        self, *, since: datetime | None = None, before_id: int | None = None, limit: int | None = None
    ) -> list[PhotoRecord]:
        """Photos newest first: those posted at or after `since`, those older than `before_id`, at most `limit`."""
        ...

    def photo_file(self, photo_id: int, thumbnail: bool) -> tuple[bytes, str] | None:
        """A photo's bytes (the web size, or its thumbnail) and media type."""
        ...

    def photos_posted_since(self, discord_user_id: int, since: datetime) -> int: ...

    def delete_photo(self, photo_id: int, note: AuditNote) -> bool:
        """Delete a photo, its bytes and any photo-of-the-week pick of it, and record who did. False when missing."""
        ...

    def pick(self, photo_id: int, chosen_by: int, chosen_by_name: str, at: datetime, ends_at: datetime) -> PickRecord:
        """Make a photo the photo of the week from `at` to `ends_at`, ending any pick still running at `at`."""
        ...

    def picks(self) -> list[PickRecord]:
        """Every photo-of-the-week pick, newest first."""
        ...

    def start_stream(self, stream: NewStream) -> StreamRecord:
        """Put a member's stream on the page, ending any stream of theirs still open."""
        ...

    def end_streams_of(self, discord_user_id: int, at: datetime) -> int:
        """End a member's open streams; how many were open."""
        ...

    def get_stream(self, stream_id: int) -> StreamRecord | None: ...

    def end_stream(self, stream_id: int, at: datetime, note: AuditNote | None = None) -> StreamRecord | None: ...

    def open_streams(self, at: datetime) -> list[StreamRecord]:
        """Streams not ended whose time has not run out at `at`, newest first."""
        ...


@dataclass
class InMemoryGalleryRepository:
    """For service tests; never use it outside tests."""

    rows: dict[int, PhotoRecord] = field(default_factory=dict)
    files: dict[int, tuple[bytes, bytes, str]] = field(default_factory=dict)
    pick_rows: list[PickRecord] = field(default_factory=list)
    streams: dict[int, StreamRecord] = field(default_factory=dict)
    audits: list[AuditNote] = field(default_factory=list)

    def add_photo(self, photo: NewPhoto) -> PhotoRecord:
        record = PhotoRecord(
            id=max(self.rows, default=0) + 1,
            discord_user_id=photo.discord_user_id,
            uploader_name=photo.uploader_name,
            caption=photo.caption,
            width=photo.width,
            height=photo.height,
            media_type=photo.media_type,
            source=photo.source,
            created_at=photo.at,
        )
        self.rows[record.id] = record
        self.files[record.id] = (photo.image, photo.thumbnail, photo.media_type)
        return record

    def get_photo(self, photo_id: int) -> PhotoRecord | None:
        return self.rows.get(photo_id)

    def photos(
        self, *, since: datetime | None = None, before_id: int | None = None, limit: int | None = None
    ) -> list[PhotoRecord]:
        found = [
            r
            for r in sorted(self.rows.values(), key=lambda r: r.id, reverse=True)
            if (since is None or r.created_at >= since) and (before_id is None or r.id < before_id)
        ]
        return found if limit is None else found[:limit]

    def photo_file(self, photo_id: int, thumbnail: bool) -> tuple[bytes, str] | None:
        stored = self.files.get(photo_id)
        if stored is None:
            return None
        return (stored[1] if thumbnail else stored[0]), stored[2]

    def photos_posted_since(self, discord_user_id: int, since: datetime) -> int:
        return sum(1 for r in self.rows.values() if r.discord_user_id == discord_user_id and r.created_at >= since)

    def delete_photo(self, photo_id: int, note: AuditNote) -> bool:
        if self.rows.pop(photo_id, None) is None:
            return False
        self.files.pop(photo_id, None)
        self.pick_rows = [p for p in self.pick_rows if p.photo_id != photo_id]
        self.audits.append(note)
        return True

    def pick(self, photo_id: int, chosen_by: int, chosen_by_name: str, at: datetime, ends_at: datetime) -> PickRecord:
        self.pick_rows = [replace(p, ends_at=at) if p.starts_at <= at < p.ends_at else p for p in self.pick_rows]
        record = PickRecord(len(self.pick_rows) + 1, photo_id, chosen_by_name, at, ends_at)
        self.pick_rows.append(record)
        self.audits.append(AuditNote(chosen_by, "gallery.photo_of_the_week", f"photo {photo_id}"))
        return record

    def picks(self) -> list[PickRecord]:
        return sorted(self.pick_rows, key=lambda p: p.id, reverse=True)

    def start_stream(self, stream: NewStream) -> StreamRecord:
        self.end_streams_of(stream.discord_user_id, stream.at)
        record = StreamRecord(
            id=max(self.streams, default=0) + 1,
            discord_user_id=stream.discord_user_id,
            streamer_name=stream.streamer_name,
            channel=stream.channel,
            title=stream.title,
            started_at=stream.at,
            ends_at=stream.ends_at,
        )
        self.streams[record.id] = record
        return record

    def end_streams_of(self, discord_user_id: int, at: datetime) -> int:
        open_ = [s for s in self.streams.values() if s.discord_user_id == discord_user_id and s.ended_at is None]
        for s in open_:
            self.streams[s.id] = replace(s, ended_at=at)
        return len(open_)

    def get_stream(self, stream_id: int) -> StreamRecord | None:
        return self.streams.get(stream_id)

    def end_stream(self, stream_id: int, at: datetime, note: AuditNote | None = None) -> StreamRecord | None:
        s = self.streams.get(stream_id)
        if s is None:
            return None
        if s.ended_at is None:
            s = self.streams[stream_id] = replace(s, ended_at=at)
        if note is not None:
            self.audits.append(note)
        return s

    def open_streams(self, at: datetime) -> list[StreamRecord]:
        return [
            s
            for s in sorted(self.streams.values(), key=lambda s: s.id, reverse=True)
            if s.ended_at is None and s.ends_at > at
        ]
