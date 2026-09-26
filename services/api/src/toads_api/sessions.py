"""Server-side sessions and pending logins in Redis.

The browser only ever holds opaque random ids. Redis keys are SHA-256 digests of those ids, so a
Redis dump cannot be replayed as a cookie. Sessions expire after a fixed TTL from login.
"""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import asdict, dataclass

from redis.asyncio import Redis

SESSION_COOKIE = "toads_session"
LOGIN_COOKIE = "toads_login"


def _key(kind: str, token: str) -> str:
    return f"toads:{kind}:{hashlib.sha256(token.encode()).hexdigest()}"


@dataclass
class SessionData:
    member_id: int
    discord_user_id: int
    display_name: str
    role_ids: list[int]
    # Discord user token, kept server-side only, used to re-read roles (REQ-HUB-RBAC-002).
    access_token: str
    refreshed_at: float


@dataclass(frozen=True)
class PendingLogin:
    state: str
    code_verifier: str


class SessionStore:
    def __init__(self, redis: Redis, *, session_ttl: int, login_ttl: int) -> None:
        self._redis = redis
        self._session_ttl = session_ttl
        self._login_ttl = login_ttl

    async def begin_login(self, login: PendingLogin) -> str:
        login_id = secrets.token_urlsafe(32)
        await self._redis.set(_key("login", login_id), json.dumps(asdict(login)), ex=self._login_ttl)
        return login_id

    async def take_login(self, login_id: str) -> PendingLogin | None:
        """Return and delete the pending login atomically, so a state can be used once only."""
        raw = await self._redis.getdel(_key("login", login_id))
        if raw is None:
            return None
        return PendingLogin(**json.loads(raw))

    async def create(self, data: SessionData) -> str:
        session_id = secrets.token_urlsafe(32)
        await self._redis.set(_key("session", session_id), json.dumps(asdict(data)), ex=self._session_ttl)
        return session_id

    async def get(self, session_id: str) -> SessionData | None:
        raw = await self._redis.get(_key("session", session_id))
        if raw is None:
            return None
        return SessionData(**json.loads(raw))

    async def save(self, session_id: str, data: SessionData) -> None:
        # xx: never resurrect a session deleted meanwhile; keepttl: refreshing does not extend it.
        await self._redis.set(_key("session", session_id), json.dumps(asdict(data)), xx=True, keepttl=True)

    async def delete(self, session_id: str) -> None:
        await self._redis.delete(_key("session", session_id))
