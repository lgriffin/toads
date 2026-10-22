"""Rules for the Highlights page's photos and streams (docs/highlights.md). No RBAC, web framework or storage imports:
the routes decide who may call (raiders post, global officers pick the photo of the week and take anything down) and
pass it in as `moderator`; the repository decides where things live.

- A photo is in the carousel for 48 hours after it is posted, and in the archive for good.
- A global officer's photo-of-the-week pick runs for seven days, and replaces any pick still running.
- A stream shows until its member ends it, Twitch says the channel is offline, or 12 hours pass.
"""

from __future__ import annotations

from collections.abc import Callable, Collection
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from toads_api.gallery import images
from toads_api.gallery.repository import (
    AuditNote,
    GalleryRepository,
    NewPhoto,
    NewStream,
    PhotoRecord,
    PickRecord,
    StreamRecord,
)
from toads_api.gallery.twitch import parse_channel

CAROUSEL_WINDOW = timedelta(hours=48)
PHOTO_OF_THE_WEEK = timedelta(days=7)
STREAM_LIMIT = timedelta(hours=12)
# Twitch's API can take a couple of minutes to list a stream that just went live: show a new one regardless.
STREAM_GRACE = timedelta(minutes=5)
CAPTION_LIMIT = 200
TITLE_LIMIT = 120
NAME_LIMIT = 100
# A member can post this many photos a day: plenty for a raid night, not enough to flood the page.
DAILY_PHOTOS = 20
ARCHIVE_PAGE = 48
SOURCES = frozenset({"discord", "site"})


class GalleryError(Exception):
    """A request the rules refuse. `status` is the HTTP code the adapter should answer with."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


class LiveChecker(Protocol):
    def live(self, channels: Collection[str]) -> frozenset[str] | None:
        """The channels that are live now, or None when that cannot be known."""
        ...


@dataclass(frozen=True)
class Pick:
    photo: PhotoRecord
    pick: PickRecord


@dataclass(frozen=True)
class Board:
    """The top of the Highlights page."""

    carousel: list[PhotoRecord]
    photo_of_the_week: Pick | None
    streams: list[StreamRecord]
    # Whether Twitch was asked who is live (False: streams show until ended or run out).
    checked_live: bool


@dataclass(frozen=True)
class ArchivePage:
    photos: list[PhotoRecord]
    # Pass as `before` for the next page; None on the last page.
    next_before: int | None
    picked: frozenset[int]


def _clean(text: str) -> str:
    """One line of text: runs of whitespace (newlines included) become one space."""
    return " ".join(text.split())


class GalleryService:
    def __init__(self, repo: GalleryRepository, clock: Callable[[], datetime], live: LiveChecker | None = None) -> None:
        self._repo = repo
        self._clock = clock
        self._live = live

    # ---------------------------------------------------------------- photos

    def post_photo(self, discord_user_id: int, name: str, caption: str, raw: bytes, source: str) -> PhotoRecord:
        if source not in SOURCES:
            raise GalleryError("Unknown photo source", 422)
        caption = _clean(caption)
        if len(caption) > CAPTION_LIMIT:
            raise GalleryError(f"A caption is at most {CAPTION_LIMIT} characters", 422)
        now = self._clock()
        if self._repo.photos_posted_since(discord_user_id, now - timedelta(days=1)) >= DAILY_PHOTOS:
            raise GalleryError(f"You have posted {DAILY_PHOTOS} photos today already; try again tomorrow", 429)
        try:
            done = images.process(raw)
        except images.ImageRejected as exc:
            raise GalleryError(str(exc), 422) from None
        shown = _clean(name)[:NAME_LIMIT] or str(discord_user_id)
        return self._repo.add_photo(
            NewPhoto(
                discord_user_id=discord_user_id,
                uploader_name=shown,
                caption=caption,
                source=source,
                at=now,
                image=done.image,
                thumbnail=done.thumbnail,
                width=done.width,
                height=done.height,
                media_type=done.media_type,
            )
        )

    def board(self) -> Board:
        now = self._clock()
        streams, checked = self._streams(now)
        return Board(
            carousel=self._repo.photos(since=now - CAROUSEL_WINDOW),
            photo_of_the_week=self.photo_of_the_week(),
            streams=streams,
            checked_live=checked,
        )

    def photo_of_the_week(self) -> Pick | None:
        now = self._clock()
        for pick in self._repo.picks():
            if pick.starts_at <= now < pick.ends_at:
                photo = self._repo.get_photo(pick.photo_id)
                return None if photo is None else Pick(photo, pick)
        return None

    def archive(self, before: int | None = None, limit: int = ARCHIVE_PAGE) -> ArchivePage:
        """Every photo ever posted, newest first, a page at a time."""
        limit = max(1, min(limit, ARCHIVE_PAGE))
        found = self._repo.photos(before_id=before, limit=limit + 1)
        page = found[:limit]
        picked = frozenset(p.photo_id for p in self._repo.picks())
        return ArchivePage(page, page[-1].id if len(found) > limit else None, picked)

    def picks(self) -> list[Pick]:
        """Every photo of the week so far, newest first."""
        return [Pick(photo, p) for p in self._repo.picks() if (photo := self._repo.get_photo(p.photo_id)) is not None]

    def photo_file(self, photo_id: int, thumbnail: bool) -> tuple[bytes, str]:
        found = self._repo.photo_file(photo_id, thumbnail)
        if found is None:
            raise GalleryError("No such photo", 404)
        return found

    def remove_photo(self, photo_id: int, actor_id: int, actor_discord_id: int | None, moderator: bool) -> None:
        """Take a photo down for good: its poster, or a global officer."""
        photo = self._repo.get_photo(photo_id)
        if photo is None:
            raise GalleryError("No such photo", 404)
        if not moderator and photo.discord_user_id != actor_discord_id:
            raise GalleryError("Only the member who posted a photo, or a global officer, can take it down", 403)
        note = AuditNote(actor_id, "gallery.remove_photo", f"photo {photo_id} by discord user {photo.discord_user_id}")
        if not self._repo.delete_photo(photo_id, note):
            raise GalleryError("No such photo", 404)

    def pick_photo_of_the_week(self, photo_id: int, officer_id: int, officer_name: str) -> Pick:
        photo = self._repo.get_photo(photo_id)
        if photo is None:
            raise GalleryError("No such photo", 404)
        now = self._clock()
        name = _clean(officer_name)[:NAME_LIMIT] or "an officer"
        return Pick(photo, self._repo.pick(photo_id, officer_id, name, now, now + PHOTO_OF_THE_WEEK))

    # --------------------------------------------------------------- streams

    def start_stream(self, discord_user_id: int, name: str, link: str, title: str) -> StreamRecord:
        channel = parse_channel(link)
        if channel is None:
            raise GalleryError("Give your Twitch channel's link, like https://twitch.tv/yourname", 422)
        title = _clean(title)
        if len(title) > TITLE_LIMIT:
            raise GalleryError(f"A stream title is at most {TITLE_LIMIT} characters", 422)
        now = self._clock()
        shown = _clean(name)[:NAME_LIMIT] or str(discord_user_id)
        return self._repo.start_stream(NewStream(discord_user_id, shown, channel, title, now, now + STREAM_LIMIT))

    def end_my_stream(self, discord_user_id: int) -> int:
        return self._repo.end_streams_of(discord_user_id, self._clock())

    def remove_stream(self, stream_id: int, actor_id: int, actor_discord_id: int | None, moderator: bool) -> None:
        stream = self._repo.get_stream(stream_id)
        if stream is None:
            raise GalleryError("No such stream", 404)
        if not moderator and stream.discord_user_id != actor_discord_id:
            raise GalleryError("Only the streamer, or a global officer, can take a stream down", 403)
        audit = (
            None
            if stream.discord_user_id == actor_discord_id
            else AuditNote(actor_id, "gallery.remove_stream", f"stream {stream_id}: twitch.tv/{stream.channel}")
        )
        self._repo.end_stream(stream_id, self._clock(), audit)

    def _streams(self, now: datetime) -> tuple[list[StreamRecord], bool]:
        open_ = self._repo.open_streams(now)
        if self._live is None or not open_:
            return open_, self._live is not None
        live = self._live.live({s.channel for s in open_})
        if live is None:
            return open_, False
        return [s for s in open_ if s.channel in live or now - s.started_at < STREAM_GRACE], True
