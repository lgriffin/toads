"""Rules for the Highlights page's photos and streams (docs/highlights.md). No RBAC, web framework or storage imports:
the routes decide who may call (raiders post, officers approve, global officers pick the photo of the week and take
anything down) and pass it in as `moderator` or a `Reviewer`; the repository decides where things live.

- Nothing shows until an officer approves it. A raid night's officers approve what members of their night post; global
  officers approve anyone's. Rejecting a photo deletes it; rejecting a stream ends it.
- A photo is in the carousel for 48 hours after it is approved, and in the archive for good.
- Approving a stream trusts its Twitch channel for that member, so their later streams from it show at once. An
  officer taking one of its streams down withdraws that trust.
- A global officer's photo-of-the-week pick runs for seven days, and replaces any pick still running.
- A stream shows until its member ends it, Twitch says the channel is offline, or 12 hours pass.
"""

from __future__ import annotations

from collections.abc import Callable, Collection
from dataclasses import dataclass, field
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
class Reviewer:
    """An officer deciding what goes up: the raid nights whose members' posts they decide, or every one."""

    actor_id: int
    nights: frozenset[str] = frozenset()
    every_night: bool = False

    def covers(self, nights: Collection[str]) -> bool:
        """Whether they decide for a poster on these nights. A poster on no night is the global officers' alone."""
        return self.every_night or not self.nights.isdisjoint(nights)


@dataclass(frozen=True)
class WaitingPhoto:
    """A photo waiting for an officer, with the raid nights whose officers may decide it (none: global tier only)."""

    photo: PhotoRecord
    nights: frozenset[str]


@dataclass(frozen=True)
class WaitingStream:
    stream: StreamRecord
    nights: frozenset[str]


@dataclass(frozen=True)
class ReviewQueue:
    photos: list[WaitingPhoto]
    streams: list[WaitingStream]


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
    # The viewer's own posts still waiting for an officer.
    waiting_photos: list[PhotoRecord] = field(default_factory=list)
    waiting_streams: list[StreamRecord] = field(default_factory=list)


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

    def board(self, viewer_discord_id: int | None = None) -> Board:
        now = self._clock()
        streams, checked = self._streams(now)
        mine = viewer_discord_id is not None
        return Board(
            carousel=self._repo.photos(since=now - CAROUSEL_WINDOW),
            photo_of_the_week=self.photo_of_the_week(),
            streams=streams,
            checked_live=checked,
            waiting_photos=self._repo.pending_photos(viewer_discord_id) if mine else [],
            waiting_streams=[s for s in self._repo.pending_streams(now) if s.discord_user_id == viewer_discord_id],
        )

    def photo_of_the_week(self) -> Pick | None:
        now = self._clock()
        for pick in self._repo.picks():
            if pick.starts_at <= now < pick.ends_at:
                photo = self._repo.get_photo(pick.photo_id)
                return None if photo is None or photo.approved_at is None else Pick(photo, pick)
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

    def photo_file(
        self, photo_id: int, thumbnail: bool, viewer_discord_id: int | None = None, reviewer: Reviewer | None = None
    ) -> tuple[bytes, str]:
        """A photo's bytes. A waiting photo only for its poster and the officers who may decide it."""
        photo = self._repo.get_photo(photo_id)
        if photo is None or (
            photo.approved_at is None and not self._may_see_waiting(photo, viewer_discord_id, reviewer)
        ):
            raise GalleryError("No such photo", 404)
        found = self._repo.photo_file(photo_id, thumbnail)
        if found is None:
            raise GalleryError("No such photo", 404)
        return found

    def _may_see_waiting(self, photo: PhotoRecord, viewer_discord_id: int | None, reviewer: Reviewer | None) -> bool:
        if viewer_discord_id is not None and photo.discord_user_id == viewer_discord_id:
            return True
        return reviewer is not None and reviewer.covers(self._nights(photo.discord_user_id))

    def _nights(self, discord_user_id: int) -> frozenset[str]:
        return self._repo.nights_of([discord_user_id]).get(discord_user_id, frozenset())

    # -------------------------------------------------------------- approval

    def review_queue(self, reviewer: Reviewer) -> ReviewQueue:
        """What waits for this officer: posts from members of their nights (every post, for the global tier)."""
        photos = self._repo.pending_photos()
        streams = self._repo.pending_streams(self._clock())
        nights = self._repo.nights_of({p.discord_user_id for p in photos} | {s.discord_user_id for s in streams})

        def of(discord_user_id: int) -> frozenset[str]:
            return nights.get(discord_user_id, frozenset())

        return ReviewQueue(
            photos=[WaitingPhoto(p, of(p.discord_user_id)) for p in photos if reviewer.covers(of(p.discord_user_id))],
            streams=[
                WaitingStream(s, of(s.discord_user_id)) for s in streams if reviewer.covers(of(s.discord_user_id))
            ],
        )

    def _waiting_photo(self, photo_id: int, reviewer: Reviewer) -> PhotoRecord:
        photo = self._repo.get_photo(photo_id)
        if photo is None or photo.approved_at is not None or not reviewer.covers(self._nights(photo.discord_user_id)):
            raise GalleryError("No such photo waiting for you to approve", 404)
        return photo

    def approve_photo(self, photo_id: int, reviewer: Reviewer) -> PhotoRecord:
        photo = self._waiting_photo(photo_id, reviewer)
        note = AuditNote(
            reviewer.actor_id, "gallery.approve_photo", f"photo {photo_id} by discord user {photo.discord_user_id}"
        )
        approved = self._repo.approve_photo(photo_id, self._clock(), note)
        if approved is None:
            raise GalleryError("No such photo waiting for you to approve", 404)
        return approved

    def reject_photo(self, photo_id: int, reviewer: Reviewer) -> None:
        """Turn a waiting photo down: it and its bytes are deleted for good."""
        photo = self._waiting_photo(photo_id, reviewer)
        note = AuditNote(
            reviewer.actor_id, "gallery.reject_photo", f"photo {photo_id} by discord user {photo.discord_user_id}"
        )
        if not self._repo.delete_photo(photo_id, note):
            raise GalleryError("No such photo waiting for you to approve", 404)

    def _waiting_stream(self, stream_id: int, reviewer: Reviewer) -> StreamRecord:
        stream = self._repo.get_stream(stream_id)
        now = self._clock()
        if (
            stream is None
            or stream.approved_at is not None
            or stream.ended_at is not None
            or stream.ends_at <= now
            or not reviewer.covers(self._nights(stream.discord_user_id))
        ):
            raise GalleryError("No such stream waiting for you to approve", 404)
        return stream

    def approve_stream(self, stream_id: int, reviewer: Reviewer) -> StreamRecord:
        """Show a waiting stream, and trust its channel for its member from now on."""
        stream = self._waiting_stream(stream_id, reviewer)
        note = AuditNote(reviewer.actor_id, "gallery.approve_stream", f"stream {stream_id}: twitch.tv/{stream.channel}")
        approved = self._repo.approve_stream(stream_id, self._clock(), reviewer.actor_id, note)
        if approved is None:
            raise GalleryError("No such stream waiting for you to approve", 404)
        return approved

    def reject_stream(self, stream_id: int, reviewer: Reviewer) -> None:
        stream = self._waiting_stream(stream_id, reviewer)
        note = AuditNote(reviewer.actor_id, "gallery.reject_stream", f"stream {stream_id}: twitch.tv/{stream.channel}")
        self._repo.end_stream(stream_id, self._clock(), note)

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
        if photo is None or photo.approved_at is None:
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
        trusted = self._repo.trusted(discord_user_id, channel)
        return self._repo.start_stream(
            NewStream(discord_user_id, shown, channel, title, now, now + STREAM_LIMIT, approved=trusted)
        )

    def end_my_stream(self, discord_user_id: int) -> int:
        return self._repo.end_streams_of(discord_user_id, self._clock())

    def remove_stream(self, stream_id: int, actor_id: int, actor_discord_id: int | None, moderator: bool) -> None:
        stream = self._repo.get_stream(stream_id)
        if stream is None:
            raise GalleryError("No such stream", 404)
        if not moderator and stream.discord_user_id != actor_discord_id:
            raise GalleryError("Only the streamer, or a global officer, can take a stream down", 403)
        if stream.discord_user_id == actor_discord_id:
            self._repo.end_stream(stream_id, self._clock())
            return
        # An officer took it down: its channel needs approving again next time.
        self._repo.untrust(stream.discord_user_id, stream.channel)
        note = AuditNote(actor_id, "gallery.remove_stream", f"stream {stream_id}: twitch.tv/{stream.channel}")
        self._repo.end_stream(stream_id, self._clock(), note)

    def _streams(self, now: datetime) -> tuple[list[StreamRecord], bool]:
        open_ = self._repo.open_streams(now)
        if self._live is None or not open_:
            return open_, self._live is not None
        live = self._live.live({s.channel for s in open_})
        if live is None:
            return open_, False
        return [s for s in open_ if s.channel in live or now - s.started_at < STREAM_GRACE], True
