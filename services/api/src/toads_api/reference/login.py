"""The dedicated Warcraft Logs login: the OAuth authorization-code flow an officer completes in their browser.

POST /api/days/{day}/reference/login stores a random state in Redis (single use, short-lived, keyed by its SHA-256
so a Redis dump cannot be replayed) and answers with Warcraft Logs' authorize URL. Warcraft Logs sends the browser
back to /api/reference/login/callback, which takes the state, exchanges the code for the account's token and hands
it to ReferenceService. This token exchange is the API's only Warcraft Logs call, as the Discord sign-in is its only
Discord OAuth call; everything else goes through the worker.
"""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from redis.asyncio import Redis

from toads_api.reference.repository import UserToken
from toads_api.settings import Settings

CALLBACK_PATH = "/api/reference/login/callback"


class WclLoginError(Exception):
    """Warcraft Logs refused the code or could not be reached. The message is safe to show."""


@dataclass(frozen=True)
class PendingWclLogin:
    member_id: int
    raid_day: str


def _key(state: str) -> str:
    return f"toads:wcl_login:{hashlib.sha256(state.encode()).hexdigest()}"


class WclLogin:
    def __init__(self, settings: Settings, redis: Redis, http: httpx.AsyncClient | None) -> None:
        self._settings = settings
        self._redis = redis
        self._http = http

    @property
    def configured(self) -> bool:
        return bool(self._settings.wcl_client_id and self._settings.wcl_client_secret.get_secret_value())

    @property
    def redirect_uri(self) -> str:
        return self._settings.wcl_redirect_uri or f"{self._settings.public_base_url.rstrip('/')}{CALLBACK_PATH}"

    def _site(self) -> str:
        return self._settings.wcl_site_url.rstrip("/")

    async def begin(self, member_id: int, raid_day: str) -> str:
        """The URL to send the officer's browser to."""
        state = secrets.token_urlsafe(32)
        pending = json.dumps({"member_id": member_id, "raid_day": raid_day})
        await self._redis.set(_key(state), pending, ex=self._settings.login_ttl_seconds)
        query = urlencode(
            {
                "client_id": self._settings.wcl_client_id,
                "redirect_uri": self.redirect_uri,
                "response_type": "code",
                "state": state,
            }
        )
        return f"{self._site()}/oauth/authorize?{query}"

    async def take(self, state: str) -> PendingWclLogin | None:
        """The login this state started, once only."""
        raw = await self._redis.getdel(_key(state))
        if raw is None:
            return None
        data = json.loads(raw)
        return PendingWclLogin(int(data["member_id"]), str(data["raid_day"]))

    async def exchange(self, code: str, now: float) -> UserToken:
        http = self._http or httpx.AsyncClient(timeout=15.0)
        try:
            r = await http.post(
                f"{self._site()}/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                    "client_id": self._settings.wcl_client_id,
                    "client_secret": self._settings.wcl_client_secret.get_secret_value(),
                },
            )
        except httpx.HTTPError as exc:
            raise WclLoginError("Warcraft Logs is not answering; try again shortly.") from exc
        finally:
            if self._http is None:
                await http.aclose()
        if r.status_code != 200:
            raise WclLoginError("Warcraft Logs did not accept this sign-in.")
        try:
            data = r.json()
            access = str(data["access_token"])
            expires_in = float(data.get("expires_in", 3600))
        except (ValueError, KeyError, TypeError) as exc:
            raise WclLoginError("Warcraft Logs sent an unreadable answer.") from exc
        refresh = data.get("refresh_token")
        return UserToken(access, str(refresh) if refresh else None, now + expires_in - 60)
