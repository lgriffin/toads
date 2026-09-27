"""Clip links are reduced to (provider, id) from an allowlist; nothing else can reach an iframe on the hub."""

from __future__ import annotations

import re

import pytest
from hypothesis import given
from hypothesis import strategies as st
from toads_api.community.clips import ClipRef, parse_clip_url
from toads_api.community.recruitment import valid_logs_url
from toads_api.community.schemas import ClipProvider

YT, TW, SA = ClipProvider.YOUTUBE, ClipProvider.TWITCH, ClipProvider.STREAMABLE
SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,100}$")


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", ClipRef(YT, "dQw4w9WgXcQ")),
        ("https://youtube.com/watch?v=dQw4w9WgXcQ&t=42", ClipRef(YT, "dQw4w9WgXcQ")),
        ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", ClipRef(YT, "dQw4w9WgXcQ")),
        ("https://youtu.be/dQw4w9WgXcQ", ClipRef(YT, "dQw4w9WgXcQ")),
        ("https://www.youtube.com/shorts/dQw4w9WgXcQ", ClipRef(YT, "dQw4w9WgXcQ")),
        ("https://clips.twitch.tv/BraveTinyToadKappa", ClipRef(TW, "BraveTinyToadKappa")),
        ("https://www.twitch.tv/toadstream/clip/BraveTinyToad-abc_123", ClipRef(TW, "BraveTinyToad-abc_123")),
        ("https://streamable.com/abc123", ClipRef(SA, "abc123")),
    ],
)
def test_allowlisted_clips(url: str, expected: ClipRef) -> None:
    assert parse_clip_url(url) == expected


@pytest.mark.security
@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "http://youtu.be/dQw4w9WgXcQ",
        "//youtu.be/dQw4w9WgXcQ",
        "https://youtube.com.evil.example/watch?v=dQw4w9WgXcQ",
        "https://evil.example/youtube.com/watch?v=dQw4w9WgXcQ",
        "https://notyoutube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com@evil.example/watch?v=dQw4w9WgXcQ",
        "https://user:pw@youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com:8443/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=dQw4w9WgXc",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQQ",
        'https://youtu.be/dQw4w9WgX"Q',
        "https://youtu.be/dQw4w9<gXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "https://clips.twitch.tv/a/b",
        "https://clips.twitch.tv/" + "a" * 101,
        "https://twitch.tv/some channel/clip/x",
        "https://streamable.com/ABC123",
        "https://streamable.com/e/abc123",
        "https://youtu.be/dQw4w9WgXcQ\n",
        "https://youtu.be/\tdQw4w9WgXcQ",
        "https://[::1/",
        "https://youtube.com:notaport/watch?v=dQw4w9WgXcQ",
    ],
)
def test_everything_else_is_refused(url: str) -> None:
    assert parse_clip_url(url) is None


@pytest.mark.security
@given(st.text(max_size=400))
def test_fuzz_any_accepted_clip_has_a_safe_id(url: str) -> None:
    ref = parse_clip_url(url)
    if ref is not None:
        assert url.startswith("https://")
        assert SAFE_ID.match(ref.clip_id)


@pytest.mark.security
@given(st.from_regex(r"https://[a-z.]{1,30}/[A-Za-z0-9_/?=&.-]{0,40}", fullmatch=True))
def test_fuzz_unknown_hosts_never_match(url: str) -> None:
    host = url.split("/")[2]
    allowed = {
        "youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "clips.twitch.tv",
        "twitch.tv", "www.twitch.tv", "m.twitch.tv", "streamable.com", "www.streamable.com",
    }  # fmt: skip
    if host not in allowed:
        assert parse_clip_url(url) is None


@pytest.mark.parametrize(
    ("url", "ok"),
    [
        ("https://fresh.warcraftlogs.com/character/eu/spineshatter/mossbeard", True),
        ("https://classic.warcraftlogs.com/reports/abcdABCD12345678", True),
        ("http://fresh.warcraftlogs.com/x", False),
        ("https://warcraftlogs.com.evil.example/x", False),
        ("https://user@warcraftlogs.com/x", False),
        ("https://warcraftlogs.com:444/x", False),
        ("javascript:alert(1)", False),
        ("https://warcraftlogs.com/a b", False),
    ],
)
def test_logs_links(url: str, ok: bool) -> None:
    assert valid_logs_url(url) is ok
