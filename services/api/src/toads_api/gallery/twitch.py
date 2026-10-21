"""Twitch for `/stream`: read a channel out of a link, and (when the hub has a Twitch app) ask Twitch who is live.

Only the channel login is kept. The page builds the player URL from it itself (player.twitch.tv), so a member can
never get an arbitrary URL into an iframe on the hub, the same rule as highlight clips (community/clips.py).
"""

from __future__ import annotations

import re
import threading
import time
from collections.abc import Callable, Collection
from urllib.parse import urlsplit

import httpx
import structlog

log = structlog.get_logger(__name__)

_CHANNEL = re.compile(r"^[a-z0-9_]{3,25}$")
_HOSTS = frozenset({"twitch.tv", "www.twitch.tv", "m.twitch.tv"})
# Twitch's own pages, which look like a channel in the first path segment.
_RESERVED = frozenset(
    {
        "directory",
        "downloads",
        "friends",
        "inventory",
        "jobs",
        "login",
        "messages",
        "p",
        "search",
        "settings",
        "signup",
        "subscriptions",
        "turbo",
        "videos",
        "wallet",
    }
)


def parse_channel(link: str) -> str | None:
    """The Twitch login a link points at ("https://twitch.tv/Hopscotch" -> "hopscotch"), or None when the link is not a
    Twitch channel. A bare "twitch.tv/name" is accepted too, since that is how people paste it into Discord."""
    link = link.strip()
    if not link or len(link) > 200 or any(c.isspace() or ord(c) < 32 for c in link):
        return None
    if "://" not in link:
        link = f"https://{link}"
    try:
        parts = urlsplit(link)
        port = parts.port
    except ValueError:
        return None
    if parts.scheme not in {"https", "http"} or parts.username is not None or parts.password is not None or port:
        return None
    if (parts.hostname or "").lower() not in _HOSTS:
        return None
    segments = [s for s in parts.path.split("/") if s]
    if len(segments) != 1:
        return None
    channel = segments[0].lower()
    return channel if _CHANNEL.match(channel) and channel not in _RESERVED else None


class TwitchLive:
    """Which channels are live, from Twitch's Helix API with an app access token (client credentials).

    Answers are cached for `ttl` seconds so a busy page asks Twitch at most once a minute. When Twitch cannot be asked,
    `live` returns None and the page falls back to showing every stream that has not been ended or run out."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        ttl: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client_id = client_id
        self._secret = client_secret
        self._ttl = ttl
        self._clock = clock
        self._http = httpx.Client(timeout=5.0, transport=transport)
        self._token: str | None = None
        self._token_expires = 0.0
        self._cache: dict[frozenset[str], tuple[float, frozenset[str]]] = {}
        self._lock = threading.Lock()

    def _app_token(self) -> str:
        if self._token is None or self._clock() >= self._token_expires:
            r = self._http.post(
                "https://id.twitch.tv/oauth2/token",
                data={"client_id": self._client_id, "client_secret": self._secret, "grant_type": "client_credentials"},
            )
            r.raise_for_status()
            body = r.json()
            self._token = str(body["access_token"])
            self._token_expires = self._clock() + max(60.0, float(body.get("expires_in", 3600)) - 60.0)
        return self._token

    def _ask(self, channels: frozenset[str]) -> frozenset[str]:
        params = httpx.QueryParams([("user_login", c) for c in sorted(channels)[:100]])
        for attempt in range(2):
            headers = {"Client-Id": self._client_id, "Authorization": f"Bearer {self._app_token()}"}
            r = self._http.get("https://api.twitch.tv/helix/streams", params=params, headers=headers)
            if r.status_code == 401 and attempt == 0:
                self._token = None  # revoked or expired early: get a new one once
                continue
            r.raise_for_status()
            return frozenset(str(s["user_login"]).lower() for s in r.json().get("data", []) if s.get("type") == "live")
        return frozenset()

    def live(self, channels: Collection[str]) -> frozenset[str] | None:
        wanted = frozenset(channels)
        if not wanted:
            return frozenset()
        with self._lock:
            hit = self._cache.get(wanted)
            if hit is not None and self._clock() - hit[0] < self._ttl:
                return hit[1]
            try:
                answer = self._ask(wanted)
            except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                log.warning("twitch_live_check_failed", error=str(exc))
                return None
            self._cache = {wanted: (self._clock(), answer)}
            return answer
