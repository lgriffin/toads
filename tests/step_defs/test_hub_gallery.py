"""REQ-HUB-GALLERY-*: the Highlights page's photos, photo of the week, streams and clips (docs/highlights.md).

Thin steps over the `hub` fixture (root conftest.py): the real API wired to the fake Discord server. The Toad Bot is
played by calls with the hub service token, acting for a member, as `/highlight`, `/stream` and `/clip` make them.
"""

from __future__ import annotations

import base64
import io
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from hub_db import AuditEntry
from PIL import Image
from pytest_bdd import given, parsers, scenarios, then, when
from sqlalchemy import select
from toads_api.gallery.service import GalleryService
from toads_api.gallery.sql import SqlGalleryRepository

from conftest import Hub

FEATURES = Path(__file__).resolve().parents[1] / "features"
scenarios(str(FEATURES / "hub_gallery.feature"))

BOT = {"authorization": "Bearer test-service-token"}
DAY = 24 * 3600


@pytest.fixture
def people() -> dict[str, Any]:
    return {}


def _as_bot(user_id: int) -> dict[str, str]:
    return {**BOT, "x-toads-acting-member": str(user_id)}


def _photo_bytes(colour: str = "green", gps: bool = False) -> bytes:
    exif = Image.Exif()
    if gps:
        exif[0x8825] = {1: "N", 2: (53.0, 20.0, 0.0)}
    out = io.BytesIO()
    Image.new("RGB", (320, 240), colour).save(out, format="JPEG", exif=exif)
    return out.getvalue()


def _bot_posts(hub: Hub, user_id: int, raw: bytes, caption: str = "") -> httpx.Response:
    body = {"caption": caption, "image_base64": base64.b64encode(raw).decode()}
    return hub.client.post("/api/gallery/photos", headers=_as_bot(user_id), json=body)


def _board(hub: Hub, sid: str) -> dict[str, Any]:
    r = hub.get("/api/gallery/board", sid)
    assert r.status_code == 200, r.text
    board: dict[str, Any] = r.json()
    return board


def _archive(hub: Hub, sid: str, query: str = "") -> dict[str, Any]:
    r = hub.get(f"/api/gallery/photos{query}", sid)
    assert r.status_code == 200, r.text
    page: dict[str, Any] = r.json()
    return page


def _audits(hub: Hub, action: str) -> int:
    with hub.db() as db:
        return len(db.scalars(select(AuditEntry).where(AuditEntry.action == action)).all())


# ------------------------------------------------------------------ people


@given(parsers.parse('a raider who goes by the nickname "{nick}"'))
def a_raider(hub: Hub, people: dict[str, Any], nick: str) -> None:
    people["raider_user"] = hub.user(("wed", "raider"), nick=nick)


@given("a guild member who signed in")
def a_member(hub: Hub, people: dict[str, Any]) -> None:
    people["member"] = hub.login(hub.user(nick="Lily"))


@given("a global officer")
def a_global_officer(hub: Hub, people: dict[str, Any]) -> None:
    people["global"] = hub.login(hub.user(("global", "officer"), nick="Croak"))


# ------------------------------------------------------------------ photos


@when(parsers.parse('the Toad Bot posts a phone photo with its location for the raider captioned "{caption}"'))
def bot_posts_phone_photo(hub: Hub, people: dict[str, Any], caption: str) -> None:
    r = _bot_posts(hub, people["raider_user"].user_id, _photo_bytes(gps=True), caption)
    assert r.status_code == 201, r.text


@given(parsers.parse("the raider has posted {n:d} photos a day apart"))
def raider_posted_photos(hub: Hub, people: dict[str, Any], n: int) -> None:
    people["photos"] = []
    for i in range(n):
        if i:
            hub.pass_time(DAY)
        r = _bot_posts(hub, people["raider_user"].user_id, _photo_bytes(), f"photo {i + 1}")
        assert r.status_code == 201, r.text
        people["photos"].append(r.json()["id"])


@then(parsers.parse('the member sees the photo in the carousel, captioned "{caption}" and posted by "{name}"'))
def member_sees_carousel(hub: Hub, people: dict[str, Any], caption: str, name: str) -> None:
    carousel = _board(hub, people["member"])["carousel"]
    assert [(p["caption"], p["uploader_name"], p["removable"]) for p in carousel] == [(caption, name, False)]
    people["photo_id"] = carousel[0]["id"]


@then("the stored photo is a WebP image with no EXIF data")
def stored_photo_is_clean(hub: Hub, people: dict[str, Any]) -> None:
    for kind in ("image", "thumbnail"):
        r = hub.get(f"/api/gallery/photos/{people['photo_id']}/{kind}", people["member"])
        assert r.status_code == 200, r.text
        assert r.headers["content-type"] == "image/webp"
        assert r.headers["x-content-type-options"] == "nosniff"
        img = Image.open(io.BytesIO(r.content))
        assert img.format == "WEBP" and not img.getexif()


@then("after 48 hours the photo has left the carousel")
def carousel_expires(hub: Hub, people: dict[str, Any]) -> None:
    hub.pass_time(2 * DAY + 1)
    assert _board(hub, people["member"])["carousel"] == []
    assert [p["id"] for p in _archive(hub, people["member"])["photos"]] == [people["photo_id"]]


@then(parsers.parse("the member sees all {n:d} photos in the archive, newest first"))
def archive_newest_first(hub: Hub, people: dict[str, Any], n: int) -> None:
    photos = _archive(hub, people["member"])["photos"]
    assert [p["caption"] for p in photos] == [f"photo {i}" for i in range(n, 0, -1)]


@then(parsers.parse("the archive pages through them {k:d} at a time"))
def archive_pages(hub: Hub, people: dict[str, Any], k: int) -> None:
    first = _archive(hub, people["member"], f"?limit={k}")
    assert len(first["photos"]) == k and first["next_before"] is not None
    rest = _archive(hub, people["member"], f"?limit={k}&before={first['next_before']}")
    assert [p["caption"] for p in rest["photos"]] == ["photo 1"] and rest["next_before"] is None


def _pick(hub: Hub, sid: str, photo_id: int) -> httpx.Response:
    return hub.post(f"/api/admin/gallery/photos/{photo_id}/photo-of-the-week", sid)


@when("the global officer picks the oldest photo as the photo of the week")
def pick_oldest(hub: Hub, people: dict[str, Any]) -> None:
    r = _pick(hub, people["global"], people["photos"][0])
    assert r.status_code == 200, r.text


@when("a day later picks the newest photo instead")
def pick_newest(hub: Hub, people: dict[str, Any]) -> None:
    hub.pass_time(DAY)
    r = _pick(hub, people["global"], people["photos"][-1])
    assert r.status_code == 200, r.text


@then("the member sees the newest photo as the photo of the week, picked by the global officer")
def member_sees_pick(hub: Hub, people: dict[str, Any]) -> None:
    pick = _board(hub, people["member"])["photo_of_the_week"]
    assert (pick["photo"]["id"], pick["chosen_by_name"]) == (people["photos"][-1], "Croak")
    ends = datetime.fromisoformat(pick["ends_at"]) - datetime.fromisoformat(pick["starts_at"])
    assert ends.days == 7


@then("both picks are listed among the photos of the week")
def picks_listed(hub: Hub, people: dict[str, Any]) -> None:
    r = hub.get("/api/gallery/photos-of-the-week", people["member"])
    assert [p["photo"]["id"] for p in r.json()] == [people["photos"][-1], people["photos"][0]]
    assert set(_archive(hub, people["member"])["picked"]) == {people["photos"][0], people["photos"][-1]}


@then(parsers.parse('the audit log records "{action}" twice'))
def audit_twice(hub: Hub, action: str) -> None:
    assert _audits(hub, action) == 2


@then("after seven days there is no photo of the week")
def pick_expires(hub: Hub, people: dict[str, Any]) -> None:
    hub.pass_time(7 * DAY)
    assert _board(hub, people["member"])["photo_of_the_week"] is None


@then("the member cannot take a photo down or pick the photo of the week")
def member_refused(hub: Hub, people: dict[str, Any]) -> None:
    photo = people["photos"][0]
    assert hub.delete(f"/api/gallery/photos/{photo}", people["member"]).status_code == 403
    assert _pick(hub, people["member"], photo).status_code == 403


@then("a Wednesday officer cannot pick the photo of the week")
def day_officer_refused(hub: Hub, people: dict[str, Any]) -> None:
    officer = hub.login(hub.user(("wed", "officer"), nick="Ribbit"))
    assert _pick(hub, officer, people["photos"][0]).status_code == 403


@then("the member cannot post a photo, and a visitor cannot see one")
def member_cannot_post(hub: Hub, people: dict[str, Any]) -> None:
    body = {"caption": "", "image_base64": base64.b64encode(_photo_bytes()).decode()}
    assert hub.post("/api/gallery/photos", people["member"], body).status_code == 403
    assert hub.get("/api/gallery/board", None).status_code == 401
    assert hub.get(f"/api/gallery/photos/{people['photos'][0]}/image", None).status_code == 401


@then(parsers.parse("the archive still holds {n:d} photos"))
def archive_holds(hub: Hub, people: dict[str, Any], n: int) -> None:
    assert len(_archive(hub, people["member"])["photos"]) == n


@when("the raider takes one of their photos down")
def raider_removes(hub: Hub, people: dict[str, Any]) -> None:
    raider = hub.login(people["raider_user"])
    assert _archive(hub, raider)["photos"][0]["removable"] is True
    assert hub.delete(f"/api/gallery/photos/{people['photos'][0]}", raider).status_code == 204


@when("the global officer takes another down")
def officer_removes(hub: Hub, people: dict[str, Any]) -> None:
    assert hub.delete(f"/api/gallery/photos/{people['photos'][1]}", people["global"]).status_code == 204


@then(parsers.parse('the archive holds {n:d} photo and the audit log records "{action}" for both'))
def archive_after_removal(hub: Hub, people: dict[str, Any], n: int, action: str) -> None:
    assert len(_archive(hub, people["member"])["photos"]) == n
    assert hub.get(f"/api/gallery/photos/{people['photos'][0]}/image", people["member"]).status_code == 404
    # The raider's own takedown is audited too: every removal is on the record.
    assert _audits(hub, action) == 2


@when("the Toad Bot posts a PDF for the raider")
def bot_posts_pdf(hub: Hub, people: dict[str, Any]) -> None:
    people["response"] = _bot_posts(hub, people["raider_user"].user_id, b"%PDF-1.7\n%not a photo")


@then("it is refused as not a photo and the archive is empty")
def pdf_refused(hub: Hub, people: dict[str, Any]) -> None:
    r = people["response"]
    assert r.status_code == 422 and "not a photo" in r.json()["detail"]
    assert _archive(hub, people["member"])["photos"] == []


# ----------------------------------------------------------------- streams


@when(parsers.parse('the Toad Bot starts a stream for the raider at "{link}" titled "{title}"'))
def bot_starts_stream(hub: Hub, people: dict[str, Any], link: str, title: str) -> None:
    body = {"link": link, "title": title}
    people["response"] = hub.client.post(
        "/api/gallery/streams", headers=_as_bot(people["raider_user"].user_id), json=body
    )


@when(parsers.parse('the Toad Bot starts a stream for the raider at "{link}" with no title'))
def bot_starts_untitled_stream(hub: Hub, people: dict[str, Any], link: str) -> None:
    bot_starts_stream(hub, people, link, "")


@then(parsers.parse('the member sees "{channel}" live, titled "{title}", streamed by "{name}"'))
def member_sees_stream(hub: Hub, people: dict[str, Any], channel: str, title: str, name: str) -> None:
    assert people["response"].status_code == 201, people["response"].text
    streams = _board(hub, people["member"])["streams"]
    assert [(s["channel"], s["title"], s["streamer_name"]) for s in streams] == [(channel, title, name)]


@when("the Toad Bot ends the raider's stream")
def bot_ends_stream(hub: Hub, people: dict[str, Any]) -> None:
    r = hub.client.post("/api/gallery/streams/end", headers=_as_bot(people["raider_user"].user_id))
    assert r.status_code == 200 and r.json() == {"ended": 1}, r.text


@when(parsers.parse("{hours:d} hours pass"))
def hours_pass(hub: Hub, hours: int) -> None:
    hub.pass_time(hours * 3600)


@when(parsers.parse("{minutes:d} minutes pass"))
def minutes_pass(hub: Hub, minutes: int) -> None:
    hub.pass_time(minutes * 60)


@then("no stream is live")
def no_stream(hub: Hub, people: dict[str, Any]) -> None:
    assert _board(hub, people["member"])["streams"] == []


@then("it is refused as not a Twitch channel and no stream is live")
def stream_refused(hub: Hub, people: dict[str, Any]) -> None:
    r = people["response"]
    assert r.status_code == 422 and "Twitch channel" in r.json()["detail"]
    no_stream(hub, people)


class _Twitch:
    def __init__(self, live: frozenset[str]) -> None:
        self.answer = live

    def live(self, channels: object) -> frozenset[str] | None:
        return self.answer


@given(parsers.parse('the hub asks Twitch who is live, and Twitch lists only "{channel}"'))
def twitch_lists(hub: Hub, channel: str) -> None:
    hub.services.gallery = GalleryService(
        SqlGalleryRepository(hub.db),
        clock=lambda: datetime.fromtimestamp(hub.now, UTC),
        live=_Twitch(frozenset({channel})),
    )


# ------------------------------------------------------------------- clips


@when(parsers.parse('the Toad Bot shares "{url}" for the raider titled "{title}"'))
def bot_shares_clip(hub: Hub, people: dict[str, Any], url: str, title: str) -> None:
    r = hub.client.post(
        "/api/highlights", headers=_as_bot(people["raider_user"].user_id), json={"title": title, "url": url}
    )
    assert r.status_code == 201, r.text
    people["clip_id"] = r.json()["id"]


@then("the member sees no clips yet and the global officer has one clip to review")
def clip_held(hub: Hub, people: dict[str, Any]) -> None:
    assert hub.get("/api/highlights", people["member"]).json() == []
    queue = hub.get("/api/admin/highlights", people["global"]).json()
    assert [h["id"] for h in queue] == [people["clip_id"]]


@when("the global officer publishes the clip to the guild")
def publish_clip(hub: Hub, people: dict[str, Any]) -> None:
    r = hub.post(f"/api/admin/highlights/{people['clip_id']}/review", people["global"], {"action": "publish_guild"})
    assert r.status_code == 200, r.text


@then(parsers.parse('the member sees the clip "{title}" from YouTube'))
def member_sees_clip(hub: Hub, people: dict[str, Any], title: str) -> None:
    clips = hub.get("/api/highlights", people["member"]).json()
    assert [(c["title"], c["provider"], c["clip_id"]) for c in clips] == [(title, "youtube", "dQw4w9WgXcQ")]
