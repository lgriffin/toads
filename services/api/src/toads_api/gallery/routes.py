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

Photos and streams are members-only: nothing here is on the public Story. Who may remove what is worked out here
(the poster, or anyone holding manage_highlights) and handed to the service as `moderator`.
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
)
from toads_api.rbac.deps import ACTING_MEMBER_HEADER, get_services, require
from toads_api.rbac.permissions import Permission, Principal, can
from toads_api.services import Services

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/gallery", tags=["highlights"])
# Guild-wide officer routes live under /api/admin (the global tier's alone).
curators = APIRouter(prefix="/api/admin/gallery", tags=["highlights", "global officers"])

Live = Annotated[Services, Depends(get_services)]
Viewer = Annotated[Principal, Depends(require(Permission.VIEW_GUILD_RAIDS))]
Poster = Annotated[Principal, Depends(require(Permission.UPLOAD_SCREENSHOTS))]
Streamer = Annotated[Principal, Depends(require(Permission.SUBMIT_HIGHLIGHT))]
Curator = Annotated[Principal, Depends(require(Permission.MANAGE_HIGHLIGHTS))]
PhotoId = Annotated[int, Path(ge=1)]


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


class BoardOut(BaseModel):
    carousel: list[PhotoOut]
    photo_of_the_week: PickOut | None
    streams: list[StreamOut]
    # True when Twitch is asked who is live; False when streams show until ended or 12 hours pass.
    checked_live: bool
    # The viewer may pick the photo of the week and take anything down.
    can_curate: bool
    can_post: bool


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
    return PhotoOut(
        id=r.id,
        uploader_name=r.uploader_name,
        caption=r.caption,
        width=r.width,
        height=r.height,
        created_at=r.created_at,
        carousel_until=r.created_at + CAROUSEL_WINDOW,
        image_url=f"/api/gallery/photos/{r.id}/image",
        thumbnail_url=f"/api/gallery/photos/{r.id}/thumbnail",
        removable=_curator(p) or (p.discord_user_id is not None and r.discord_user_id == p.discord_user_id),
    )


def _pick(pick: Pick, p: Principal) -> PickOut:
    return PickOut(
        photo=_photo(pick.photo, p),
        chosen_by_name=pick.pick.chosen_by_name,
        starts_at=pick.pick.starts_at,
        ends_at=pick.pick.ends_at,
    )


def _stream(s: StreamRecord, p: Principal) -> StreamOut:
    return StreamOut(
        id=s.id,
        streamer_name=s.streamer_name,
        channel=s.channel,
        title=s.title,
        started_at=s.started_at,
        ends_at=s.ends_at,
        removable=_curator(p) or (p.discord_user_id is not None and s.discord_user_id == p.discord_user_id),
    )


def _refuse(exc: GalleryError) -> HTTPException:
    return HTTPException(exc.status, detail=exc.message)


def _discord_id(principal: Principal) -> int:
    if principal.discord_user_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Your hub session has no Discord identity; sign in again")
    return principal.discord_user_id


# ---------------------------------------------------------------------- read


@router.get("/board")
async def board(principal: Viewer, gallery: Gallery) -> BoardOut:
    b = await anyio.to_thread.run_sync(gallery.board)
    return BoardOut(
        carousel=[_photo(r, principal) for r in b.carousel],
        photo_of_the_week=None if b.photo_of_the_week is None else _pick(b.photo_of_the_week, principal),
        streams=[_stream(s, principal) for s in b.streams],
        checked_live=b.checked_live,
        can_curate=_curator(principal),
        can_post=can(principal, Permission.UPLOAD_SCREENSHOTS),
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


async def _file(gallery: GalleryService, photo_id: int, thumbnail: bool) -> Response:
    try:
        data, media_type = await anyio.to_thread.run_sync(gallery.photo_file, photo_id, thumbnail)
    except GalleryError as exc:
        raise _refuse(exc) from None
    # A photo's bytes never change once posted, and only members may fetch them.
    headers = {"Cache-Control": "private, max-age=604800, immutable", "X-Content-Type-Options": "nosniff"}
    return Response(content=data, media_type=media_type, headers=headers)


@router.get("/photos/{photo_id}/image")
async def photo_image(photo_id: PhotoId, _: Viewer, gallery: Gallery) -> Response:
    return await _file(gallery, photo_id, thumbnail=False)


@router.get("/photos/{photo_id}/thumbnail")
async def photo_thumbnail(photo_id: PhotoId, _: Viewer, gallery: Gallery) -> Response:
    return await _file(gallery, photo_id, thumbnail=True)


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
async def remove_stream(stream_id: Annotated[int, Path(ge=1)], principal: Viewer, gallery: Gallery) -> Response:
    try:
        await anyio.to_thread.run_sync(
            gallery.remove_stream, stream_id, principal.member_id, principal.discord_user_id, _curator(principal)
        )
    except GalleryError as exc:
        raise _refuse(exc) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def include_gallery(app: FastAPI) -> None:
    for r in (router, curators):
        app.include_router(r)
