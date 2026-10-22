"""The Highlights page's photo and stream rules (docs/highlights.md), over the in-memory repository, plus the image
re-encoding and the Twitch link and live check."""

from __future__ import annotations

import io
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from PIL import Image
from toads_api.gallery import images
from toads_api.gallery.repository import InMemoryGalleryRepository, PhotoRecord, StreamRecord
from toads_api.gallery.service import DAILY_PHOTOS, GalleryError, GalleryService, Reviewer
from toads_api.gallery.twitch import TwitchLive, parse_channel

START = datetime(2026, 10, 21, 20, 0, tzinfo=UTC)


class Clock:
    def __init__(self) -> None:
        self.now = START

    def __call__(self) -> datetime:
        return self.now


class Live:
    def __init__(self, answer: frozenset[str] | None) -> None:
        self.answer = answer
        self.asked: list[set[str]] = []

    def live(self, channels: object) -> frozenset[str] | None:
        self.asked.append(set(channels))  # type: ignore[call-overload]
        return self.answer


def png(width: int = 64, height: int = 48, mode: str = "RGB") -> bytes:
    out = io.BytesIO()
    Image.new(mode, (width, height), (0, 128, 0, 128) if mode == "RGBA" else "green").save(out, format="PNG")
    return out.getvalue()


GLOBAL = Reviewer(1, every_night=True)
WED = Reviewer(2, nights=frozenset({"wed"}))
SUN = Reviewer(3, nights=frozenset({"sun"}))


def post(
    service: GalleryService, uid: int, name: str = "Hop", caption: str = "", source: str = "discord"
) -> PhotoRecord:
    """Post a photo and have a global officer approve it."""
    return service.approve_photo(service.post_photo(uid, name, caption, png(), source).id, GLOBAL)


def stream(service: GalleryService, uid: int, name: str, link: str, title: str = "") -> StreamRecord:
    """Start a stream and have a global officer approve its channel."""
    s = service.start_stream(uid, name, link, title)
    return s if s.approved_at is not None else service.approve_stream(s.id, GLOBAL)


def gallery(live: Live | None = None) -> tuple[GalleryService, InMemoryGalleryRepository, Clock]:
    repo, clock = InMemoryGalleryRepository(), Clock()
    return GalleryService(repo, clock, live), repo, clock


# ----------------------------------------------------------------- images


def test_a_photo_is_re_encoded_as_webp_and_loses_its_exif() -> None:
    exif = Image.Exif()
    exif[0x8825] = {2: (51.0, 30.0, 0.0)}  # GPS latitude
    exif[0x0112] = 6  # taken with the phone on its side
    out = io.BytesIO()
    Image.new("RGB", (40, 30), "blue").save(out, format="JPEG", exif=exif)
    done = images.process(out.getvalue())
    stored = Image.open(io.BytesIO(done.image))
    assert stored.format == "WEBP"
    assert (done.width, done.height) == (30, 40)  # turned the right way up
    assert not stored.getexif()
    assert done.media_type == "image/webp"


def test_big_photos_are_scaled_for_the_web_and_get_a_small_thumbnail() -> None:
    done = images.process(png(4000, 1000))
    assert (done.width, done.height) == (images.WEB_EDGE, 512)
    assert Image.open(io.BytesIO(done.thumbnail)).size == (images.THUMB_EDGE, 160)


def test_transparency_survives() -> None:
    done = images.process(png(10, 10, "RGBA"))
    assert Image.open(io.BytesIO(done.image)).mode == "RGBA"


def animated_gif() -> bytes:
    out = io.BytesIO()
    frames = [Image.new("RGB", (8, 8), colour) for colour in ("red", "blue")]
    frames[0].save(out, format="GIF", save_all=True, append_images=frames[1:])
    return out.getvalue()


@pytest.mark.parametrize(
    ("raw", "why"),
    [
        (b"", "empty"),
        (b"x" * (images.MAX_UPLOAD_BYTES + 1), "at most 10 MB"),
        (b"%PDF-1.7 not a photo", "not a photo"),
        (png()[:60], "could not be read"),
        (animated_gif(), "Animated"),
    ],
)
def test_what_is_not_a_photo_is_refused(raw: bytes, why: str) -> None:
    with pytest.raises(images.ImageRejected, match=why):
        images.process(raw)


def test_formats_outside_the_list_are_refused() -> None:
    out = io.BytesIO()
    Image.new("RGB", (8, 8)).save(out, format="BMP")
    with pytest.raises(images.ImageRejected, match="JPEG, PNG, WebP or GIF"):
        images.process(out.getvalue())


def test_decompression_bombs_are_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(images, "MAX_PIXELS", 100)
    with pytest.raises(images.ImageRejected, match="too large"):
        images.process(png(20, 20))


# ----------------------------------------------------------------- photos


def test_a_photo_shows_in_the_carousel_for_48_hours_and_in_the_archive_for_good() -> None:
    service, _, clock = gallery()
    first = post(service, 7, "  Hop\nscotch ", "  Gruul   down! ")
    assert (first.uploader_name, first.caption, first.source) == ("Hop scotch", "Gruul down!", "discord")
    clock.now += timedelta(hours=47, minutes=59)
    assert [p.id for p in service.board().carousel] == [first.id]
    clock.now += timedelta(minutes=2)
    second = post(service, 8, "Croak", source="site")
    assert [p.id for p in service.board().carousel] == [second.id]
    assert [p.id for p in service.archive().photos] == [second.id, first.id]


def test_the_archive_pages_newest_first() -> None:
    service, _, _ = gallery()
    ids = [post(service, i).id for i in range(5)]
    page = service.archive(limit=2)
    assert ([p.id for p in page.photos], page.next_before) == ([ids[4], ids[3]], ids[3])
    page = service.archive(before=ids[1], limit=2)
    assert ([p.id for p in page.photos], page.next_before) == ([ids[0]], None)


@pytest.mark.parametrize(
    ("caption", "source", "why", "status"),
    [("x" * 201, "discord", "at most 200", 422), ("", "carrier toad", "source", 422)],
)
def test_bad_posts_are_refused(caption: str, source: str, why: str, status: int) -> None:
    with pytest.raises(GalleryError, match=why) as exc:
        gallery()[0].post_photo(7, "Hop", caption, png(), source)
    assert exc.value.status == status


def test_a_post_that_is_not_a_photo_says_why() -> None:
    with pytest.raises(GalleryError, match="not a photo") as exc:
        gallery()[0].post_photo(7, "Hop", "", b"hello", "discord")
    assert exc.value.status == 422


def test_a_member_can_post_twenty_photos_a_day() -> None:
    service, _, clock = gallery()
    for _ in range(DAILY_PHOTOS):
        service.post_photo(7, "Hop", "", png(), "discord")
    with pytest.raises(GalleryError, match="tomorrow") as exc:
        service.post_photo(7, "Hop", "", png(), "discord")
    assert exc.value.status == 429
    service.post_photo(8, "Croak", "", png(), "discord")
    clock.now += timedelta(days=1, seconds=1)
    service.post_photo(7, "Hop", "", png(), "discord")


def test_a_photo_of_the_week_runs_seven_days_and_a_new_pick_replaces_it() -> None:
    service, repo, clock = gallery()
    a = post(service, 7)
    b = post(service, 8, "Croak")
    pick = service.pick_photo_of_the_week(a.id, 1, "  Lily ")
    assert (pick.photo.id, pick.pick.chosen_by_name, pick.pick.ends_at) == (a.id, "Lily", START + timedelta(days=7))
    clock.now += timedelta(days=3)
    service.pick_photo_of_the_week(b.id, 1, "Lily")
    board = service.board()
    assert board.photo_of_the_week is not None and board.photo_of_the_week.photo.id == b.id
    assert board.carousel == []  # three days on, both are out of the carousel but still there
    assert [p.photo.id for p in service.picks()] == [b.id, a.id]
    assert service.picks()[1].pick.ends_at == clock.now  # the first pick ended when the second began
    assert service.archive().picked == {a.id, b.id}
    clock.now += timedelta(days=7)
    assert service.board().photo_of_the_week is None
    assert [n.action for n in repo.audits if n.action != "gallery.approve_photo"] == ["gallery.photo_of_the_week"] * 2
    with pytest.raises(GalleryError, match="No such photo"):
        service.pick_photo_of_the_week(99, 1, "Lily")


def test_a_poster_or_a_global_officer_can_take_a_photo_down() -> None:
    service, repo, _ = gallery()
    a = post(service, 7)
    b = post(service, 8, "Croak")
    service.pick_photo_of_the_week(b.id, 1, "Lily")
    with pytest.raises(GalleryError, match="Only the member who posted") as exc:
        service.remove_photo(a.id, 2, 8, moderator=False)
    assert exc.value.status == 403
    service.remove_photo(a.id, 3, 7, moderator=False)
    service.remove_photo(b.id, 1, 1, moderator=True)
    assert service.archive().photos == []
    assert service.board().photo_of_the_week is None and service.picks() == []
    with pytest.raises(GalleryError, match="No such photo") as exc:
        service.photo_file(a.id, thumbnail=False)
    assert exc.value.status == 404
    assert [n.action for n in repo.audits][-2:] == ["gallery.remove_photo"] * 2
    with pytest.raises(GalleryError, match="No such photo"):
        service.remove_photo(a.id, 1, 1, moderator=True)


def test_photo_files_come_back_as_stored() -> None:
    service, _, _ = gallery()
    a = service.approve_photo(service.post_photo(7, "Hop", "", png(1000, 1000), "discord").id, GLOBAL)
    image, kind = service.photo_file(a.id, thumbnail=False)
    thumb, _ = service.photo_file(a.id, thumbnail=True)
    assert kind == "image/webp"
    assert Image.open(io.BytesIO(image)).size == (1000, 1000)
    assert Image.open(io.BytesIO(thumb)).size == (images.THUMB_EDGE, images.THUMB_EDGE)


# --------------------------------------------------------------- approval


def test_a_photo_waits_for_an_officer_before_anyone_else_sees_it() -> None:
    service, repo, clock = gallery()
    repo.nights[7] = frozenset({"wed"})
    waiting = service.post_photo(7, "Hop", "Gruul down!", png(), "discord")
    assert waiting.approved_at is None
    board = service.board(viewer_discord_id=8)
    assert (board.carousel, board.waiting_photos, service.archive().photos) == ([], [], [])
    assert [p.id for p in service.board(viewer_discord_id=7).waiting_photos] == [waiting.id]
    with pytest.raises(GalleryError, match="No such photo"):
        service.pick_photo_of_the_week(waiting.id, 1, "Lily")
    clock.now += timedelta(hours=30)  # approved late: still a full 48 hours in the carousel
    approved = service.approve_photo(waiting.id, WED)
    assert approved.approved_at == clock.now
    assert repo.audits[-1].action == "gallery.approve_photo" and repo.audits[-1].actor == WED.actor_id
    clock.now += timedelta(hours=47)
    assert [p.id for p in service.board().carousel] == [waiting.id]
    assert service.board(viewer_discord_id=7).waiting_photos == []


def test_a_nights_officers_decide_only_their_nights_posts_and_global_officers_decide_all() -> None:
    service, repo, _ = gallery()
    repo.nights.update({7: frozenset({"wed"}), 8: frozenset({"sun"})})
    wed = service.post_photo(7, "Hop", "", png(), "discord")
    sun = service.post_photo(8, "Croak", "", png(), "discord")
    nowhere = service.post_photo(9, "Lily", "", png(), "discord")
    queue = service.review_queue(WED)
    assert [(w.photo.id, w.nights) for w in queue.photos] == [(wed.id, frozenset({"wed"}))]
    assert [w.photo.id for w in service.review_queue(GLOBAL).photos] == [wed.id, sun.id, nowhere.id]
    for photo_id in (sun.id, nowhere.id):
        with pytest.raises(GalleryError, match="waiting for you") as exc:
            service.approve_photo(photo_id, WED)
        assert exc.value.status == 404
    service.approve_photo(nowhere.id, GLOBAL)
    with pytest.raises(GalleryError, match="waiting for you"):
        service.approve_photo(nowhere.id, GLOBAL)  # decided already


def test_a_rejected_photo_is_deleted_for_good() -> None:
    service, repo, _ = gallery()
    repo.nights[7] = frozenset({"sun"})
    photo = service.post_photo(7, "Hop", "", png(), "discord")
    with pytest.raises(GalleryError):
        service.reject_photo(photo.id, WED)
    service.reject_photo(photo.id, SUN)
    assert repo.audits[-1].action == "gallery.reject_photo"
    assert service.review_queue(GLOBAL).photos == [] and service.board(viewer_discord_id=7).waiting_photos == []
    with pytest.raises(GalleryError, match="No such photo"):
        service.photo_file(photo.id, thumbnail=False, viewer_discord_id=7)


def test_a_waiting_photos_bytes_are_for_its_poster_and_its_officers_only() -> None:
    service, repo, _ = gallery()
    repo.nights[7] = frozenset({"wed"})
    photo = service.post_photo(7, "Hop", "", png(), "discord")
    assert service.photo_file(photo.id, False, viewer_discord_id=7)[1] == "image/webp"
    assert service.photo_file(photo.id, True, viewer_discord_id=2, reviewer=WED)[1] == "image/webp"
    assert service.photo_file(photo.id, True, reviewer=GLOBAL)[1] == "image/webp"
    for viewer, reviewer in ((8, None), (3, SUN), (None, None)):
        with pytest.raises(GalleryError, match="No such photo"):
            service.photo_file(photo.id, False, viewer_discord_id=viewer, reviewer=reviewer)
    service.approve_photo(photo.id, WED)
    assert service.photo_file(photo.id, False, viewer_discord_id=8)[1] == "image/webp"


def test_a_stream_waits_until_an_officer_approves_its_channel_once() -> None:
    service, repo, clock = gallery()
    repo.nights[7] = frozenset({"wed"})
    s = service.start_stream(7, "Hop", "twitch.tv/hopscotch", "Sunday Gruul")
    assert s.approved_at is None and service.board().streams == []
    assert [x.id for x in service.board(viewer_discord_id=7).waiting_streams] == [s.id]
    assert [w.stream.id for w in service.review_queue(WED).streams] == [s.id]
    assert service.review_queue(SUN).streams == []
    with pytest.raises(GalleryError, match="waiting for you"):
        service.approve_stream(s.id, SUN)
    service.approve_stream(s.id, WED)
    assert [x.channel for x in service.board().streams] == ["hopscotch"]
    assert repo.audits[-1].action == "gallery.approve_stream"
    clock.now += timedelta(days=2)
    assert service.start_stream(7, "Hop", "twitch.tv/hopscotch", "").approved_at == clock.now  # trusted now
    other = service.start_stream(7, "Hop", "twitch.tv/hopscotch_alt", "")  # a new channel waits again
    assert other.approved_at is None and service.board().streams == []


def test_a_rejected_or_expired_stream_leaves_the_queue() -> None:
    service, repo, clock = gallery()
    s = service.start_stream(7, "Hop", "twitch.tv/hopscotch", "")
    service.reject_stream(s.id, GLOBAL)
    assert repo.audits[-1].action == "gallery.reject_stream"
    assert service.review_queue(GLOBAL).streams == [] and not repo.trusted(7, "hopscotch")
    t = service.start_stream(7, "Hop", "twitch.tv/hopscotch", "")
    clock.now += timedelta(hours=12)
    assert service.review_queue(GLOBAL).streams == []
    with pytest.raises(GalleryError, match="waiting for you"):
        service.approve_stream(t.id, GLOBAL)


# ---------------------------------------------------------------- streams


@pytest.mark.parametrize(
    ("link", "channel"),
    [
        ("https://www.twitch.tv/Hopscotch", "hopscotch"),
        ("twitch.tv/croak_tv", "croak_tv"),
        ("https://m.twitch.tv/lily/", "lily"),
        ("http://twitch.tv/lily", "lily"),
        ("https://twitch.tv/lily/clip/AbcDef", None),
        ("https://twitch.tv/directory", None),
        ("https://twitch.tv.evil.example/lily", None),
        ("https://twitch.tv@evil.example/lily", None),
        ("https://twitch.tv:444/lily", None),
        ("javascript:alert(1)", None),
        ("https://twitch.tv/no spaces", None),
        ("https://twitch.tv/x", None),
        ("https://youtube.com/@hop", None),
        ("", None),
    ],
)
def test_only_twitch_channel_links_are_streams(link: str, channel: str | None) -> None:
    assert parse_channel(link) == channel


def test_a_stream_shows_until_it_is_ended_or_twelve_hours_pass() -> None:
    service, _, clock = gallery()
    s = stream(service, 7, "Hop", "https://twitch.tv/Hopscotch", "  Sunday  Gruul ")
    assert (s.channel, s.title, s.ends_at) == ("hopscotch", "Sunday Gruul", START + timedelta(hours=12))
    stream(service, 8, "Croak", "twitch.tv/croak")
    assert [x.channel for x in service.board().streams] == ["croak", "hopscotch"]
    assert service.end_my_stream(8) == 1
    assert [x.channel for x in service.board().streams] == ["hopscotch"]
    clock.now += timedelta(hours=12)
    assert service.board().streams == []
    assert service.board().checked_live is False


def test_a_new_stream_replaces_the_members_last_one() -> None:
    service, _, _ = gallery()
    stream(service, 7, "Hop", "twitch.tv/hopscotch")
    stream(service, 7, "Hop", "twitch.tv/hopscotch_alt")
    assert [x.channel for x in service.board().streams] == ["hopscotch_alt"]


def test_bad_streams_are_refused() -> None:
    service, _, _ = gallery()
    with pytest.raises(GalleryError, match="Twitch channel's link") as exc:
        service.start_stream(7, "Hop", "https://youtube.com/watch?v=abc", "")
    assert exc.value.status == 422
    with pytest.raises(GalleryError, match="at most 120"):
        service.start_stream(7, "Hop", "twitch.tv/hopscotch", "x" * 121)


def test_with_twitch_asked_only_live_channels_show_after_a_grace_period() -> None:
    live = Live(frozenset({"hopscotch"}))
    service, _, clock = gallery(live)
    assert service.board().streams == [] and live.asked == []  # nothing to ask about
    stream(service, 7, "Hop", "twitch.tv/hopscotch")
    stream(service, 8, "Croak", "twitch.tv/croak")
    assert len(service.board().streams) == 2  # just started: Twitch may not list them yet
    clock.now += timedelta(minutes=6)
    board = service.board()
    assert ([x.channel for x in board.streams], board.checked_live) == (["hopscotch"], True)
    assert live.asked[-1] == {"hopscotch", "croak"}
    live.answer = None  # Twitch did not answer: show every open stream
    board = service.board()
    assert (len(board.streams), board.checked_live) == (2, False)


def test_a_streamer_or_a_global_officer_can_take_a_stream_down() -> None:
    service, repo, _ = gallery()
    s = stream(service, 7, "Hop", "twitch.tv/hopscotch")
    with pytest.raises(GalleryError, match="Only the streamer") as exc:
        service.remove_stream(s.id, 2, 8, moderator=False)
    assert exc.value.status == 403
    repo.audits.clear()
    service.remove_stream(s.id, 3, 7, moderator=False)
    assert service.board().streams == [] and repo.audits == []  # their own: nothing to audit
    assert service.start_stream(7, "Hop", "twitch.tv/hopscotch", "").approved_at is not None  # still trusted
    t = stream(service, 8, "Croak", "twitch.tv/croak")
    service.remove_stream(t.id, 1, 1, moderator=True)
    assert [n.action for n in repo.audits][-1] == "gallery.remove_stream"
    # An officer took it down, so the channel needs approving again.
    assert service.start_stream(8, "Croak", "twitch.tv/croak", "").approved_at is None
    with pytest.raises(GalleryError, match="No such stream"):
        service.remove_stream(99, 1, 1, moderator=True)


# ------------------------------------------------------------ Twitch API


class FakeTwitch:
    def __init__(self) -> None:
        self.tokens = 0
        self.asks: list[list[str]] = []
        self.reject_next = False
        self.down = False

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if self.down:
            return httpx.Response(500)
        if request.url.host == "id.twitch.tv":
            self.tokens += 1
            return httpx.Response(200, json={"access_token": f"t{self.tokens}", "expires_in": 3600})
        if self.reject_next:
            self.reject_next = False
            return httpx.Response(401)
        assert request.headers["Client-Id"] == "cid"
        self.asks.append(request.url.params.get_list("user_login"))
        return httpx.Response(200, json={"data": [{"user_login": "Hopscotch", "type": "live"}]})


def test_twitch_is_asked_once_a_minute_with_one_token() -> None:
    fake, now = FakeTwitch(), [0.0]
    live = TwitchLive("cid", "secret", clock=lambda: now[0], transport=httpx.MockTransport(fake))
    assert live.live([]) == frozenset()
    assert live.live(["hopscotch", "croak"]) == {"hopscotch"}
    assert live.live(["croak", "hopscotch"]) == {"hopscotch"}
    assert fake.asks == [["croak", "hopscotch"]]
    now[0] += 61
    fake.reject_next = True  # the token was revoked: get a new one and ask again
    assert live.live(["hopscotch"]) == {"hopscotch"}
    assert fake.tokens == 2
    fake.down = True
    now[0] += 61
    assert live.live(["hopscotch"]) is None
    fake.down = False
    asked = len(fake.asks)
    assert live.live(["hopscotch"]) is None  # a failure is remembered for a minute too
    assert len(fake.asks) == asked


def test_a_request_never_waits_behind_another_asking_twitch() -> None:
    fake, now = FakeTwitch(), [0.0]
    live = TwitchLive("cid", "secret", clock=lambda: now[0], transport=httpx.MockTransport(fake))
    assert live.live(["hopscotch"]) == {"hopscotch"}
    now[0] += 61
    live._lock.acquire()  # another board request is asking Twitch
    try:
        assert live.live(["hopscotch"]) == {"hopscotch"}  # the last answer, at once
        assert live.live(["croak"]) is None
    finally:
        live._lock.release()
