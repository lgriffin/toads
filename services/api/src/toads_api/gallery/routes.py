"""The Highlights page's photo and stream routes (docs/highlights.md).

- GET    /api/gallery/board                         members: the 48-hour carousel, the photo of the week, live streams
- GET    /api/gallery/photos?before=                members: the archive, every photo newest first, a page at a time
- GET    /api/gallery/photos-of-the-week            members: every photo of the week so far
- GET    /api/gallery/photos/{id}/image|thumbnail   members: a photo's bytes
- POST   /api/gallery/photos                        raiders: post a photo (the Toad Bot's `/highlight`, acting for them)
- DELETE /api/gallery/photos/{id}                   its poster, or a global officer: take it down
- POST   /api/admin/gallery/photos/{id}/photo-of-the-week   global officers: make it the photo of the week for 7 days
- POST   /api/gallery/streams                       raiders: put their Twitch channel on the page (`/stream start`)
- POST   /api/gallery/streams/end                   raiders: take their stream off (`/stream end`)
- DELETE /api/gallery/streams/{id}                  its streamer, or a global officer: take it off
- GET    /api/days/{day}/gallery/review             the night's officers: what its members posted that waits for them
- POST   /api/days/{day}/gallery/photos|streams/{id}/approve|reject   the night's officers: decide one
- GET    /api/admin/gallery/review                  global officers: everything waiting
- POST   /api/admin/gallery/photos|streams/{id}/approve|reject        global officers: decide any

Photos and streams are members-only: nothing here is on the public Story, and nothing shows until an officer approves
it. Who may remove what is worked out here (the poster, or anyone holding manage_highlights) and handed to the service
as `moderator`; who may approve what, as a `Reviewer` (the night in the path, or every night for the global tier).
"""

from __future__ import annotations

import base64
import binascii
from datetime import datetime
from typing import Annotated

import anyio
import structlog
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Path, Query, Request, Response, status
from pydantic import BaseModel, Field

from toads_api.gallery.images import MAX_UPLOAD_BYTES
from toads_api.gallery.repository import PhotoRecord, StreamRecord
from toads_api.gallery.service import (
    ARCHIVE_PAGE,
    CAPTION_LIMIT,
    CAROUSEL_WINDOW,
    TITLE_LIMIT,
    GalleryError,
    GalleryService,
    Pick,
    Reviewer,
    WaitingPhoto,
    WaitingStream,
)
from toads_api.rbac.deps import ACTING_MEMBER_HEADER, get_services, require
from toads_api.rbac.permissions import Permission, Principal, can
from toads_api.services import Services

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/gallery", tags=["highlights"])
# Guild-wide officer routes live under /api/admin (the global tier's alone).
curators = APIRouter(prefix="/api/admin/gallery", tags=["highlights", "global officers"])
# A raid night's officers approve what members of their night post; the night comes from the path alone.
night_officers = APIRouter(prefix="/api/days/{day}/gallery", tags=["highlights", "officers"])

Live = Annotated[Services, Depends(get_services)]
Viewer = Annotated[Principal, Depends(require(Permission.VIEW_GUILD_RAIDS))]
Poster = Annotated[Principal, Depends(require(Permission.UPLOAD_SCREENSHOTS))]
Streamer = Annotated[Principal, Depends(require(Permission.SUBMIT_HIGHLIGHT))]
Curator = Annotated[Principal, Depends(require(Permission.MANAGE_HIGHLIGHTS))]
NightOfficer = Annotated[Principal, Depends(require(Permission.MANAGE_HIGHLIGHTS, scoped=True))]
PhotoId = Annotated[int, Path(ge=1)]
StreamId = Annotated[int, Path(ge=1)]


def gallery_of(live: Live) -> GalleryService:
    return live.gallery


Gallery = Annotated[GalleryService, Depends(gallery_of)]


class PhotoIn(BaseModel):
    caption: str = Field(default="", max_length=CAPTION_LIMIT * 2)
    # The photo's bytes, base64: JSON keeps the Toad Bot's call and the site's the same shape.
    image_base64: str = Field(min_length=1, max_length=(MAX_UPLOAD_BYTES * 4) // 3 + 8)


class StreamIn(BaseModel):
    link: str = Field(min_length=1, max_length=200)
    title: str = Field(default="", max_length=TITLE_LIMIT * 2)


class PhotoOut(BaseModel):
    id: int
    uploader_name: str
    caption: str
    width: int
    height: int
    created_at: datetime
    # When it leaves the carousel; it stays in the archive.
    carousel_until: datetime
    image_url: str
    thumbnail_url: str
    # Whether the viewer may take it down: they posted it, or they are a global officer.
    removable: bool
    # Still waiting for an officer: only its poster and the officers who may approve it see it.
    waiting: bool = False


class PickOut(BaseModel):
    photo: PhotoOut
    chosen_by_name: str
    starts_at: datetime
    ends_at: datetime


class StreamOut(BaseModel):
    id: int
    streamer_name: str
    # The Twitch login; the page builds the player URL from it.
    channel: str
    title: str
    started_at: datetime
    ends_at: datetime
    removable: bool
    waiting: bool = False


class ReviewScopeOut(BaseModel):
    """Whose posts the viewer approves: every member's (global tier), or those of these raid nights' members."""

    every_night: bool
    nights: list[str]


class WaitingPhotoOut(PhotoOut):
    # The raid nights whose officers may decide it; empty means the global tier only.
    nights: list[str]


class WaitingStreamOut(StreamOut):
    nights: list[str]


class ReviewQueueOut(BaseModel):
    photos: list[WaitingPhotoOut]
    streams: list[WaitingStreamOut]


class BoardOut(BaseModel):
    carousel: list[PhotoOut]
    photo_of_the_week: PickOut | None
    streams: list[StreamOut]
    # True when Twitch is asked who is live; False when streams show until ended or 12 hours pass.
    checked_live: bool
    # The viewer may pick the photo of the week and take anything down.
    can_curate: bool
    can_post: bool
    # The viewer's own posts still waiting for an officer.
    waiting_photos: list[PhotoOut]
    waiting_streams: list[StreamOut]
    # Set when the viewer approves posts: whose, and so which review routes to call.
    review: ReviewScopeOut | None


class ArchiveOut(BaseModel):
    photos: list[PhotoOut]
    next_before: int | None
    # Ids on this page that have been a photo of the week.
    picked: list[int]


class StreamsEnded(BaseModel):
    ended: int


def _curator(p: Principal) -> bool:
    return can(p, Permission.MANAGE_HIGHLIGHTS)


def _photo(r: PhotoRecord, p: Principal) -> PhotoOut:
    return PhotoOut(**_photo_fields(r, p))


def _photo_fields(r: PhotoRecord, p: Principal) -> dict[str, object]:
    return {
        "id": r.id,
        "uploader_name": r.uploader_name,
        "caption": r.caption,
        "width": r.width,
        "height": r.height,
        "created_at": r.created_at,
        "carousel_until": (r.approved_at or r.created_at) + CAROUSEL_WINDOW,
        "image_url": f"/api/gallery/photos/{r.id}/image",
        "thumbnail_url": f"/api/gallery/photos/{r.id}/thumbnail",
        "removable": _curator(p) or (p.discord_user_id is not None and r.discord_user_id == p.discord_user_id),
        "waiting": r.approved_at is None,
    }


def _pick(pick: Pick, p: Principal) -> PickOut:
    return PickOut(
        photo=_photo(pick.photo, p),
        chosen_by_name=pick.pick.chosen_by_name,
        starts_at=pick.pick.starts_at,
        ends_at=pick.pick.ends_at,
    )


def _stream(s: StreamRecord, p: Principal) -> StreamOut:
    return StreamOut(**_stream_fields(s, p))


def _stream_fields(s: StreamRecord, p: Principal) -> dict[str, object]:
    return {
        "id": s.id,
        "streamer_name": s.streamer_name,
        "channel": s.channel,
        "title": s.title,
        "started_at": s.started_at,
        "ends_at": s.ends_at,
        "removable": _curator(p) or (p.discord_user_id is not None and s.discord_user_id == p.discord_user_id),
        "waiting": s.approved_at is None,
    }


def _waiting_photo(w: WaitingPhoto, p: Principal) -> WaitingPhotoOut:
    return WaitingPhotoOut(**_photo_fields(w.photo, p), nights=sorted(w.nights))


def _waiting_stream(w: WaitingStream, p: Principal) -> WaitingStreamOut:
    return WaitingStreamOut(**_stream_fields(w.stream, p), nights=sorted(w.nights))


def _reviewer_of(p: Principal, live: Services) -> Reviewer | None:
    """Whose posts this member approves, from their roles: every member's for the global tier, else their officer
    nights' members'. Only for reads (the board, a waiting photo's bytes); approving takes the night from the path."""
    if can(p, Permission.MANAGE_HIGHLIGHTS):
        return Reviewer(p.member_id, every_night=True)
    nights = frozenset(d.id for d in live.raid_days.raid_days if can(p, Permission.MANAGE_HIGHLIGHTS, d.id))
    return Reviewer(p.member_id, nights=nights) if nights else None


def _refuse(exc: GalleryError) -> HTTPException:
    return HTTPException(exc.status, detail=exc.message)


def _discord_id(principal: Principal) -> int:
    if principal.discord_user_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Your hub session has no Discord identity; sign in again")
    return principal.discord_user_id


# ---------------------------------------------------------------------- read


@router.get("/board")
async def board(principal: Viewer, gallery: Gallery, live: Live) -> BoardOut:
    b = await anyio.to_thread.run_sync(gallery.board, principal.discord_user_id)
    reviewer = _reviewer_of(principal, live)
    return BoardOut(
        carousel=[_photo(r, principal) for r in b.carousel],
        photo_of_the_week=None if b.photo_of_the_week is None else _pick(b.photo_of_the_week, principal),
        streams=[_stream(s, principal) for s in b.streams],
        checked_live=b.checked_live,
        can_curate=_curator(principal),
        can_post=can(principal, Permission.UPLOAD_SCREENSHOTS),
        waiting_photos=[_photo(r, principal) for r in b.waiting_photos],
        waiting_streams=[_stream(s, principal) for s in b.waiting_streams],
        review=None
        if reviewer is None
        else ReviewScopeOut(every_night=reviewer.every_night, nights=sorted(reviewer.nights)),
    )


@router.get("/photos")
async def archive(
    principal: Viewer,
    gallery: Gallery,
    before: Annotated[int | None, Query(ge=1)] = None,
    limit: Annotated[int, Query(ge=1, le=ARCHIVE_PAGE)] = ARCHIVE_PAGE,
) -> ArchiveOut:
    page = await anyio.to_thread.run_sync(gallery.archive, before, limit)
    return ArchiveOut(
        photos=[_photo(r, principal) for r in page.photos],
        next_before=page.next_before,
        picked=sorted(r.id for r in page.photos if r.id in page.picked),
    )


@router.get("/photos-of-the-week")
async def photos_of_the_week(principal: Viewer, gallery: Gallery) -> list[PickOut]:
    return [_pick(p, principal) for p in await anyio.to_thread.run_sync(gallery.picks)]


async def _file(gallery: GalleryService, photo_id: int, thumbnail: bool, p: Principal, live: Services) -> Response:
    try:
        data, media_type = await anyio.to_thread.run_sync(
            gallery.photo_file, photo_id, thumbnail, p.discord_user_id, _reviewer_of(p, live)
        )
    except GalleryError as exc:
        raise _refuse(exc) from None
    # Members-only and removable: browsers must ask again each time, so a taken-down photo stops showing at once.
    headers = {"Cache-Control": "private, no-cache", "X-Content-Type-Options": "nosniff"}
    return Response(content=data, media_type=media_type, headers=headers)


@router.get("/photos/{photo_id}/image")
async def photo_image(photo_id: PhotoId, principal: Viewer, gallery: Gallery, live: Live) -> Response:
    return await _file(gallery, photo_id, False, principal, live)


@router.get("/photos/{photo_id}/thumbnail")
async def photo_thumbnail(photo_id: PhotoId, principal: Viewer, gallery: Gallery, live: Live) -> Response:
    return await _file(gallery, photo_id, True, principal, live)


# --------------------------------------------------------------------- write


@router.post("/photos", status_code=status.HTTP_201_CREATED)
async def post_photo(body: PhotoIn, request: Request, principal: Poster, gallery: Gallery) -> PhotoOut:
    source = "discord" if request.headers.get(ACTING_MEMBER_HEADER) is not None else "site"
    try:
        raw = base64.b64decode(body.image_base64, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="The photo is not valid base64") from None
    try:
        record = await anyio.to_thread.run_sync(
            gallery.post_photo, _discord_id(principal), principal.display_name, body.caption, raw, source
        )
    except GalleryError as exc:
        raise _refuse(exc) from None
    log.info("gallery.photo_posted", photo_id=record.id, source=source)
    return _photo(record, principal)


@router.delete("/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_photo(photo_id: PhotoId, principal: Viewer, gallery: Gallery) -> Response:
    try:
        await anyio.to_thread.run_sync(
            gallery.remove_photo, photo_id, principal.member_id, principal.discord_user_id, _curator(principal)
        )
    except GalleryError as exc:
        raise _refuse(exc) from None
    log.info("gallery.photo_removed", photo_id=photo_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@curators.post("/photos/{photo_id}/photo-of-the-week")
async def pick_photo_of_the_week(photo_id: PhotoId, principal: Curator, gallery: Gallery) -> PickOut:
    try:
        pick = await anyio.to_thread.run_sync(
            gallery.pick_photo_of_the_week, photo_id, principal.member_id, principal.display_name
        )
    except GalleryError as exc:
        raise _refuse(exc) from None
    return _pick(pick, principal)


@router.post("/streams", status_code=status.HTTP_201_CREATED)
async def start_stream(body: StreamIn, principal: Streamer, gallery: Gallery) -> StreamOut:
    try:
        stream = await anyio.to_thread.run_sync(
            gallery.start_stream, _discord_id(principal), principal.display_name, body.link, body.title
        )
    except GalleryError as exc:
        raise _refuse(exc) from None
    log.info("gallery.stream_started", stream_id=stream.id, channel=stream.channel)
    return _stream(stream, principal)


@router.post("/streams/end")
async def end_my_stream(principal: Streamer, gallery: Gallery) -> StreamsEnded:
    if principal.discord_user_id is None:
        return StreamsEnded(ended=0)  # Streams are kept by Discord id; a session without one has started none.
    return StreamsEnded(ended=await anyio.to_thread.run_sync(gallery.end_my_stream, principal.discord_user_id))


@router.delete("/streams/{stream_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_stream(stream_id: StreamId, principal: Viewer, gallery: Gallery) -> Response:
    try:
        await anyio.to_thread.run_sync(
            gallery.remove_stream, stream_id, principal.member_id, principal.discord_user_id, _curator(principal)
        )
    except GalleryError as exc:
        raise _refuse(exc) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ------------------------------------------------------------------ approval


async def _queue(gallery: GalleryService, reviewer: Reviewer, p: Principal) -> ReviewQueueOut:
    q = await anyio.to_thread.run_sync(gallery.review_queue, reviewer)
    return ReviewQueueOut(
        photos=[_waiting_photo(w, p) for w in q.photos], streams=[_waiting_stream(w, p) for w in q.streams]
    )


async def _approve_photo(gallery: GalleryService, photo_id: int, reviewer: Reviewer, p: Principal) -> PhotoOut:
    try:
        photo = await anyio.to_thread.run_sync(gallery.approve_photo, photo_id, reviewer)
    except GalleryError as exc:
        raise _refuse(exc) from None
    log.info("gallery.photo_approved", photo_id=photo_id)
    return _photo(photo, p)


async def _reject_photo(gallery: GalleryService, photo_id: int, reviewer: Reviewer) -> Response:
    try:
        await anyio.to_thread.run_sync(gallery.reject_photo, photo_id, reviewer)
    except GalleryError as exc:
        raise _refuse(exc) from None
    log.info("gallery.photo_rejected", photo_id=photo_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def _approve_stream(gallery: GalleryService, stream_id: int, reviewer: Reviewer, p: Principal) -> StreamOut:
    try:
        stream = await anyio.to_thread.run_sync(gallery.approve_stream, stream_id, reviewer)
    except GalleryError as exc:
        raise _refuse(exc) from None
    log.info("gallery.stream_approved", stream_id=stream_id, channel=stream.channel)
    return _stream(stream, p)


async def _reject_stream(gallery: GalleryService, stream_id: int, reviewer: Reviewer) -> Response:
    try:
        await anyio.to_thread.run_sync(gallery.reject_stream, stream_id, reviewer)
    except GalleryError as exc:
        raise _refuse(exc) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _night(day: str, p: Principal) -> Reviewer:
    return Reviewer(p.member_id, nights=frozenset({day}))


def _every(p: Principal) -> Reviewer:
    return Reviewer(p.member_id, every_night=True)


@night_officers.get("/review")
async def night_queue(day: str, principal: NightOfficer, gallery: Gallery) -> ReviewQueueOut:
    """What members of this night posted that waits for an officer."""
    return await _queue(gallery, _night(day, principal), principal)


@night_officers.post("/photos/{photo_id}/approve")
async def night_approve_photo(day: str, photo_id: PhotoId, principal: NightOfficer, gallery: Gallery) -> PhotoOut:
    return await _approve_photo(gallery, photo_id, _night(day, principal), principal)


@night_officers.post("/photos/{photo_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def night_reject_photo(day: str, photo_id: PhotoId, principal: NightOfficer, gallery: Gallery) -> Response:
    return await _reject_photo(gallery, photo_id, _night(day, principal))


@night_officers.post("/streams/{stream_id}/approve")
async def night_approve_stream(day: str, stream_id: StreamId, principal: NightOfficer, gallery: Gallery) -> StreamOut:
    return await _approve_stream(gallery, stream_id, _night(day, principal), principal)


@night_officers.post("/streams/{stream_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def night_reject_stream(day: str, stream_id: StreamId, principal: NightOfficer, gallery: Gallery) -> Response:
    return await _reject_stream(gallery, stream_id, _night(day, principal))


@curators.get("/review")
async def every_queue(principal: Curator, gallery: Gallery) -> ReviewQueueOut:
    """Everything waiting for an officer, whichever night its poster is on."""
    return await _queue(gallery, _every(principal), principal)


@curators.post("/photos/{photo_id}/approve")
async def approve_photo(photo_id: PhotoId, principal: Curator, gallery: Gallery) -> PhotoOut:
    return await _approve_photo(gallery, photo_id, _every(principal), principal)


@curators.post("/photos/{photo_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def reject_photo(photo_id: PhotoId, principal: Curator, gallery: Gallery) -> Response:
    return await _reject_photo(gallery, photo_id, _every(principal))


@curators.post("/streams/{stream_id}/approve")
async def approve_stream(stream_id: StreamId, principal: Curator, gallery: Gallery) -> StreamOut:
    return await _approve_stream(gallery, stream_id, _every(principal), principal)


@curators.post("/streams/{stream_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def reject_stream(stream_id: StreamId, principal: Curator, gallery: Gallery) -> Response:
    return await _reject_stream(gallery, stream_id, _every(principal))


def include_gallery(app: FastAPI) -> None:
    for r in (router, curators, night_officers):
        app.include_router(r)
