"""The Highlights page's photos and live streams (docs/highlights.md).

Members post photos with the Toad Bot's `/highlight`; each shows in the carousel for 48 hours and stays in the archive
for good. A global officer can make one the photo of the week for seven days. `/stream` puts a member's Twitch channel
on the page while they are live. The image bytes live in their own table so listing photos never reads them.

Nothing shows until an officer approves it: a photo waits with no `approved_at`, and so does a stream from a Twitch
channel no officer has approved for that member yet (`gallery_trusted_channels`).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from hub_db.models import Base, _now


class GalleryPhoto(Base):
    __tablename__ = "gallery_photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Who posted it: their Discord user id and their server name at the time.
    discord_user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    uploader_name: Mapped[str] = mapped_column(String(100))
    caption: Mapped[str] = mapped_column(String(200), default="")
    # The stored (re-encoded) image's size in pixels and media type.
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    media_type: Mapped[str] = mapped_column(String(32))
    # Where it was posted from: "discord" or "site".
    source: Mapped[str] = mapped_column(String(16), default="discord")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    # When an officer approved it, and who: until then only its poster and the officers who may approve it see it.
    # The 48 hours in the carousel count from here.
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("members.id", ondelete="SET NULL"))


class GalleryPhotoFile(Base):
    """A photo's bytes: the web-sized image and its thumbnail, both re-encoded so no EXIF (phone GPS) survives."""

    __tablename__ = "gallery_photo_files"

    photo_id: Mapped[int] = mapped_column(ForeignKey("gallery_photos.id", ondelete="CASCADE"), primary_key=True)
    image: Mapped[bytes] = mapped_column(LargeBinary)
    thumbnail: Mapped[bytes] = mapped_column(LargeBinary)


class PhotoOfTheWeek(Base):
    """Each pick, kept after it ends, so the archive can show every past photo of the week."""

    __tablename__ = "photo_of_the_week"

    id: Mapped[int] = mapped_column(primary_key=True)
    photo_id: Mapped[int] = mapped_column(ForeignKey("gallery_photos.id", ondelete="CASCADE"), index=True)
    chosen_by: Mapped[int | None] = mapped_column(ForeignKey("members.id", ondelete="SET NULL"))
    chosen_by_name: Mapped[str] = mapped_column(String(100))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class LiveStream(Base):
    """A member's `/stream`: their Twitch channel, shown on the page until they end it, Twitch says they went
    offline, or `ends_at` passes."""

    __tablename__ = "live_streams"

    id: Mapped[int] = mapped_column(primary_key=True)
    discord_user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    streamer_name: Mapped[str] = mapped_column(String(100))
    # The Twitch login, lower case: the only part of the link the page uses.
    channel: Mapped[str] = mapped_column(String(25))
    title: Mapped[str] = mapped_column(String(120), default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    # None while it waits for an officer; set at once when the channel is trusted for this member.
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TrustedChannel(Base):
    """A Twitch channel an officer approved for one member: their later streams from it show without waiting. An
    officer taking one of its streams down withdraws the trust."""

    __tablename__ = "gallery_trusted_channels"

    discord_user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    channel: Mapped[str] = mapped_column(String(25), primary_key=True)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("members.id", ondelete="SET NULL"))
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
