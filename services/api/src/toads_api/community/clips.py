"""Highlight reels are links to clips on an allowlisted host, never raw embeds.

A submitted URL is reduced to (provider, clip id); the page rebuilds the embed URL from those two values, so a
member can never get an arbitrary URL into an iframe on the hub.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit

from toads_api.community.schemas import ClipProvider

_YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_TWITCH_SLUG = re.compile(r"^[A-Za-z0-9_-]{1,100}$")
_STREAMABLE_ID = re.compile(r"^[a-z0-9]{1,16}$")
_TWITCH_CHANNEL = re.compile(r"^[A-Za-z0-9_]{1,25}$")


@dataclass(frozen=True)
class ClipRef:
    provider: ClipProvider
    clip_id: str


def parse_clip_url(url: str) -> ClipRef | None:
    """Return the clip a URL points at, or None when it is not an https link to an allowlisted clip."""
    if len(url) > 300 or any(c.isspace() or ord(c) < 32 for c in url):
        return None
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    # Userinfo ("youtube.com@evil.example") and ports change where a URL really goes; refuse both.
    if parts.scheme != "https" or parts.username is not None or parts.password is not None:
        return None
    try:
        if parts.port is not None:
            return None
    except ValueError:
        return None
    host = (parts.hostname or "").lower()
    segments = [s for s in parts.path.split("/") if s]

    if host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        if segments == ["watch"]:
            return _match(ClipProvider.YOUTUBE, parse_qs(parts.query).get("v", [""])[0], _YOUTUBE_ID)
        if len(segments) == 2 and segments[0] == "shorts":
            return _match(ClipProvider.YOUTUBE, segments[1], _YOUTUBE_ID)
        return None
    if host == "youtu.be":
        return _match(ClipProvider.YOUTUBE, segments[0], _YOUTUBE_ID) if len(segments) == 1 else None
    if host == "clips.twitch.tv":
        return _match(ClipProvider.TWITCH, segments[0], _TWITCH_SLUG) if len(segments) == 1 else None
    if host in {"twitch.tv", "www.twitch.tv", "m.twitch.tv"}:
        if len(segments) == 3 and segments[1] == "clip" and _TWITCH_CHANNEL.match(segments[0]):
            return _match(ClipProvider.TWITCH, segments[2], _TWITCH_SLUG)
        return None
    if host in {"streamable.com", "www.streamable.com"}:
        return _match(ClipProvider.STREAMABLE, segments[0], _STREAMABLE_ID) if len(segments) == 1 else None
    return None


def _match(provider: ClipProvider, clip_id: str, pattern: re.Pattern[str]) -> ClipRef | None:
    return ClipRef(provider, clip_id) if pattern.match(clip_id) else None
