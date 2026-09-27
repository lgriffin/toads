"""The few Discord endpoints the API needs: OAuth2 token exchange, the caller's guild member, the guild's roles.

`DiscordAPI` is a protocol so tests and the dev stack can swap in the fake server
(`toads_api.testing.fake_discord`) through an httpx transport; nothing here reads the environment.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import httpx
from pydantic import SecretStr

# identify: who the user is; guilds.members.read: their nickname and roles in the Toads server.
SCOPES = "identify guilds.members.read"


class DiscordError(Exception):
    """Discord refused or failed a request. Messages never include tokens or response bodies."""


class DiscordAuthError(DiscordError):
    """The code, verifier or access token was rejected."""


@dataclass(frozen=True)
class GuildMember:
    user_id: int
    username: str
    global_name: str | None
    nick: str | None
    role_ids: frozenset[int]

    @property
    def server_name(self) -> str:
        """The name the member shows in the server: nickname, else global display name, else username."""
        return self.nick or self.global_name or self.username

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> GuildMember:
        user = data["user"]
        return cls(
            user_id=int(user["id"]),
            username=str(user["username"]),
            global_name=user.get("global_name"),
            nick=data.get("nick"),
            role_ids=frozenset(int(r) for r in data.get("roles", [])),
        )


class DiscordAPI(Protocol):
    async def exchange_code(self, code: str, code_verifier: str) -> str:
        """Trade an authorization code (plus PKCE verifier) for a user access token."""
        ...

    async def current_member(self, access_token: str) -> GuildMember | None:
        """The token owner's membership of the Toads server, or None when they are not in it."""
        ...

    async def guild_role_ids(self) -> set[int]:
        """Every role id that exists in the Toads server (bot token)."""
        ...


class HttpDiscord:
    def __init__(
        self,
        http: httpx.AsyncClient,
        *,
        api_base: str,
        client_id: str,
        client_secret: SecretStr,
        bot_token: SecretStr,
        redirect_uri: str,
        guild_id: int,
    ) -> None:
        self._http = http
        self._base = api_base.rstrip("/")
        self._client_id = client_id
        self._client_secret = client_secret
        self._bot_token = bot_token
        self._redirect_uri = redirect_uri
        self._guild_id = guild_id

    async def exchange_code(self, code: str, code_verifier: str) -> str:
        r = await self._http.post(
            f"{self._base}/oauth2/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self._redirect_uri,
                "code_verifier": code_verifier,
                "client_id": self._client_id,
                "client_secret": self._client_secret.get_secret_value(),
            },
        )
        if r.status_code in (400, 401):
            raise DiscordAuthError("Discord rejected the authorization code")
        if r.status_code != 200:
            raise DiscordError(f"Discord token exchange failed with HTTP {r.status_code}")
        token = r.json().get("access_token")
        if not isinstance(token, str) or not token:
            raise DiscordError("Discord token response had no access token")
        return token

    async def current_member(self, access_token: str) -> GuildMember | None:
        r = await self._http.get(
            f"{self._base}/users/@me/guilds/{self._guild_id}/member",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if r.status_code == 404:
            return None
        if r.status_code == 401:
            raise DiscordAuthError("Discord rejected the access token")
        if r.status_code != 200:
            raise DiscordError(f"Discord member lookup failed with HTTP {r.status_code}")
        return GuildMember.from_api(r.json())

    async def guild_role_ids(self) -> set[int]:
        r = await self._http.get(
            f"{self._base}/guilds/{self._guild_id}/roles",
            headers={"Authorization": f"Bot {self._bot_token.get_secret_value()}"},
        )
        if r.status_code != 200:
            raise DiscordError(f"Discord role listing failed with HTTP {r.status_code}")
        return {int(role["id"]) for role in r.json()}
