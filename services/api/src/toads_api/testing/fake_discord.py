"""A fake Discord OAuth2 + REST server for the dev stack and tests. No real credentials needed.

It implements just what the hub uses, with the same paths and shapes as Discord:

- GET  /oauth2/authorize                         signs in `login_as` (or `?login_as=<user id>`) at once
                                                 and redirects back with a code bound to the PKCE challenge
- POST /api/v10/oauth2/token                     authorization_code grant; checks client secret, redirect
                                                 URI and PKCE verifier; codes are single use
- GET  /api/v10/users/@me/guilds/{id}/member     the token owner's guild member, 404 when not in the server
- GET  /api/v10/guilds/{id}/roles                the server's roles (any `Bot` token)
- GET  /api/v10/guilds/{id}/scheduled-events     the server's scheduled events (any `Bot` token)

Tests drive it in-process (httpx.ASGITransport / TestClient) and edit `FakeDiscordState` directly.
The dev stack runs `uvicorn --factory toads_api.testing.fake_discord:app_from_env` (see infra/docker-compose.yml).
It is a development tool: it signs anyone in without a password.
"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlencode

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response


@dataclass
class FakeUser:
    user_id: int
    username: str
    global_name: str | None = None
    nick: str | None = None
    roles: set[int] = field(default_factory=set)
    in_guild: bool = True


@dataclass
class _Code:
    user_id: int
    redirect_uri: str
    challenge: str


@dataclass
class FakeDiscordState:
    client_id: str = "toads-dev"
    client_secret: str = "replace-me"  # noqa: S105 - the fake's own placeholder, not a credential
    guild_id: int = 1
    guild_roles: set[int] = field(default_factory=set)
    users: dict[int, FakeUser] = field(default_factory=dict)
    login_as: int | None = None
    codes: dict[str, _Code] = field(default_factory=dict)
    tokens: dict[str, int] = field(default_factory=dict)
    # Scheduled events exactly as Discord's API returns them (see `scheduled_event`).
    events: list[dict[str, Any]] = field(default_factory=list)
    # Tests set this to make the scheduled events listing fail as Discord does when it is down.
    events_down: bool = False

    def add_user(self, user: FakeUser) -> FakeUser:
        self.users[user.user_id] = user
        self.guild_roles |= user.roles
        return user

    def add_event(
        self, event_id: int, name: str, starts_at: datetime, *, status: int = 1, interested: int | None = 0
    ) -> dict[str, Any]:
        event = scheduled_event(self.guild_id, event_id, name, starts_at, status=status, interested=interested)
        self.events.append(event)
        return event

    def revoke_tokens(self, user_id: int) -> None:
        self.tokens = {t: u for t, u in self.tokens.items() if u != user_id}

    @classmethod
    def from_env(cls) -> FakeDiscordState:
        """Dev seed: one member, `FAKE_DISCORD_NICK`, holding the comma-separated `FAKE_DISCORD_ROLES`."""
        roles = {int(r) for r in os.environ.get("FAKE_DISCORD_ROLES", "").split(",") if r.strip()}
        extra = {int(r) for r in os.environ.get("FAKE_DISCORD_GUILD_ROLES", "").split(",") if r.strip()}
        state = cls(
            client_id=os.environ.get("FAKE_DISCORD_CLIENT_ID", "toads-dev"),
            client_secret=os.environ.get("FAKE_DISCORD_CLIENT_SECRET", "replace-me"),
            guild_id=int(os.environ.get("FAKE_DISCORD_GUILD_ID", "1")),
            guild_roles=extra,
        )
        user = state.add_user(
            FakeUser(1001, "hopscotch", global_name="Hopscotch", nick=os.environ.get("FAKE_DISCORD_NICK"), roles=roles)
        )
        state.login_as = user.user_id
        # One raid two days out, so the dev hub's Next raid widget has something to show.
        start = (datetime.now(UTC) + timedelta(days=2)).replace(hour=18, minute=30, second=0, microsecond=0)
        state.add_event(9001, "Karazhan", start, interested=17)
        return state


def scheduled_event(
    guild_id: int, event_id: int, name: str, starts_at: datetime, *, status: int = 1, interested: int | None = 0
) -> dict[str, Any]:
    """A scheduled event in Discord's shape (voice-channel raid events carry no end time)."""
    event: dict[str, Any] = {
        "id": str(event_id),
        "guild_id": str(guild_id),
        "name": name,
        "scheduled_start_time": starts_at.isoformat(),
        "scheduled_end_time": None,
        "status": status,
        "entity_type": 2,
    }
    if interested is not None:
        event["user_count"] = interested
    return event


def _s256(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")


def _oauth_error(error: str, status_code: int = 400) -> JSONResponse:
    return JSONResponse({"error": error}, status_code=status_code)


def create_fake_discord(state: FakeDiscordState) -> FastAPI:
    app = FastAPI(title="Fake Discord", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.fake = state

    def _bearer_user(request: Request) -> FakeUser:
        auth = request.headers.get("authorization", "")
        user_id = state.tokens.get(auth.removeprefix("Bearer ")) if auth.startswith("Bearer ") else None
        if user_id is None or user_id not in state.users:
            raise HTTPException(401, detail="401: Unauthorized")
        return state.users[user_id]

    @app.get("/oauth2/authorize")
    async def authorize(request: Request) -> Response:
        q = request.query_params
        if q.get("client_id") != state.client_id or q.get("response_type") != "code":
            return _oauth_error("invalid_request")
        if q.get("code_challenge_method") != "S256" or not q.get("code_challenge"):
            return _oauth_error("invalid_request")
        redirect_uri = q.get("redirect_uri", "")
        login_as = int(q["login_as"]) if q.get("login_as") else state.login_as
        if not redirect_uri or login_as is None or login_as not in state.users:
            return _oauth_error("access_denied")
        code = secrets.token_urlsafe(16)
        state.codes[code] = _Code(login_as, redirect_uri, q["code_challenge"])
        back = {"code": code, **({"state": q["state"]} if "state" in q else {})}
        return RedirectResponse(f"{redirect_uri}?{urlencode(back)}", status_code=302)

    @app.post("/api/v10/oauth2/token")
    async def token(request: Request) -> Response:
        form = {k: v[0] for k, v in parse_qs((await request.body()).decode()).items()}
        if form.get("client_id") != state.client_id or form.get("client_secret") != state.client_secret:
            return _oauth_error("invalid_client", 401)
        if form.get("grant_type") != "authorization_code":
            return _oauth_error("unsupported_grant_type")
        issued = state.codes.pop(form.get("code", ""), None)  # single use
        if issued is None or issued.redirect_uri != form.get("redirect_uri"):
            return _oauth_error("invalid_grant")
        verifier = form.get("code_verifier", "")
        if not verifier or _s256(verifier) != issued.challenge:
            return _oauth_error("invalid_grant")
        access = secrets.token_urlsafe(24)
        state.tokens[access] = issued.user_id
        return JSONResponse({"access_token": access, "token_type": "Bearer", "expires_in": 604800, "scope": "identify"})

    @app.get("/api/v10/users/@me/guilds/{guild_id}/member")
    async def my_member(guild_id: int, request: Request) -> dict[str, Any]:
        user = _bearer_user(request)
        if guild_id != state.guild_id or not user.in_guild:
            raise HTTPException(404, detail="Unknown Guild")
        return {
            "user": {"id": str(user.user_id), "username": user.username, "global_name": user.global_name},
            "nick": user.nick,
            "roles": [str(r) for r in sorted(user.roles)],
        }

    @app.get("/api/v10/guilds/{guild_id}/roles")
    async def roles(guild_id: int, request: Request) -> list[dict[str, str]]:
        if not request.headers.get("authorization", "").startswith("Bot ") or guild_id != state.guild_id:
            raise HTTPException(401, detail="401: Unauthorized")
        return [{"id": str(r), "name": f"role-{r}"} for r in sorted(state.guild_roles | {state.guild_id})]

    @app.get("/api/v10/guilds/{guild_id}/scheduled-events")
    async def scheduled_events(guild_id: int, request: Request) -> list[dict[str, Any]]:
        if not request.headers.get("authorization", "").startswith("Bot ") or guild_id != state.guild_id:
            raise HTTPException(401, detail="401: Unauthorized")
        if state.events_down:
            raise HTTPException(503, detail="503: Service Unavailable")
        with_count = request.query_params.get("with_user_count") == "true"
        return [e if with_count else {k: v for k, v in e.items() if k != "user_count"} for e in state.events]

    return app


def app_from_env() -> FastAPI:
    """Entry point for the dev compose stack. It signs anyone in, so it refuses to start without an explicit opt-in."""
    if os.environ.get("FAKE_DISCORD_I_AM_DEV") != "1":
        raise RuntimeError("fake Discord signs anyone in; set FAKE_DISCORD_I_AM_DEV=1, and only in the dev stack")
    return create_fake_discord(FakeDiscordState.from_env())
