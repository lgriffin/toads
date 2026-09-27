"""Which Warcraft Logs key a request uses.

Work done on a member's behalf (importing their report, analysing it for them) uses that member's own key when they
have saved one, so it spends their Warcraft Logs rate-limit budget rather than the guild's. Everything else (the
nightly guild sync, officer imports) and any member without a working key uses the guild key from the environment.

A member's key is tried once per client: if Warcraft Logs refuses it, the request falls back to the guild key and
the key is marked rejected so the member's settings page says so. Keys, secrets and tokens are never logged.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from functools import cache

import structlog
from hub_db import CredentialCipher, CredentialDecryptError, StoredWclCredentials, WclCredentialStatus
from hub_db.credentials import load_wcl_credentials, mark_wcl_credentials
from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from wcl_core.auth import TokenManager
from wcl_core.client import WarcraftLogsClient
from wcl_core.common.errors import AuthenticationError

from toads_worker.settings import Settings

log = structlog.get_logger(__name__)

# wcl_core reports a refused key as "Authentication failed (HTTP 4xx)"; network trouble reads differently.
_REFUSED = re.compile(r"\bHTTP 4\d\d\b")


@dataclass(frozen=True)
class WclKey:
    client_id: str
    client_secret: SecretStr
    # Whose key this is; None for the guild's.
    member_id: int | None = None
    # Which saved key it is (see StoredWclCredentials.revision); empty for the guild's.
    revision: str = ""


class MemberKeys:
    """Members' saved keys in hub-db, decrypted on read."""

    def __init__(self, db: sessionmaker[Session], cipher: CredentialCipher) -> None:
        self._db = db
        self._cipher = cipher

    def get(self, member_id: int) -> StoredWclCredentials | None:
        with self._db() as db:
            try:
                return load_wcl_credentials(db, self._cipher, member_id)
            except CredentialDecryptError:
                # Rotated-away encryption key or a tampered row: treat as no key, and say so without any detail.
                log.warning("wcl_key.unreadable", member_id=member_id)
                return None

    def mark(self, member_id: int, revision: str, status: WclCredentialStatus) -> None:
        with self._db.begin() as db:
            mark_wcl_credentials(db, member_id, revision, status)


@cache
def _member_keys(database_url: str, credentials_keys: str) -> MemberKeys:
    engine = create_engine(database_url, pool_pre_ping=True)
    return MemberKeys(sessionmaker(engine, expire_on_commit=False), CredentialCipher.from_setting(credentials_keys))


def member_keys(settings: Settings) -> MemberKeys:
    return _member_keys(settings.database_url.get_secret_value(), settings.credentials_keys.get_secret_value())


def guild_key(settings: Settings) -> WclKey:
    return WclKey(settings.wcl_client_id, settings.wcl_client_secret)


def key_for(settings: Settings, member_id: int | None, keys: MemberKeys) -> WclKey:
    """The member's own key when they saved one that Warcraft Logs has not refused; otherwise the guild's."""
    if member_id is None:
        return guild_key(settings)
    stored = keys.get(member_id)
    if stored is None or stored.status is WclCredentialStatus.REJECTED:
        return guild_key(settings)
    return WclKey(stored.client_id, SecretStr(stored.client_secret), member_id, stored.revision)


def _client(settings: Settings, tokens: TokenManager) -> WarcraftLogsClient:
    """The on-disk response cache is off: the worker runs in a read-only container, and raw responses will be
    cached in object storage instead (phase 2.1)."""
    client = WarcraftLogsClient(tokens, cache_enabled=False, api_url=settings.wcl_api_url)
    client.MIN_REQUEST_INTERVAL = settings.wcl_throttle_ms / 1000
    client.MAX_RETRIES = settings.wcl_max_retries
    return client


TokenFactory = Callable[[str, SecretStr], TokenManager]


def client_for(
    settings: Settings,
    member_id: int | None = None,
    *,
    keys: MemberKeys | None = None,
    tokens: TokenFactory = TokenManager,
) -> WarcraftLogsClient:
    """A Warcraft Logs client for work done on `member_id`'s behalf (None: the guild's own work).

    A member's key is checked up front by fetching its token, which the client then reuses, so a refused key costs
    one token request and never a failed job.
    """
    if member_id is None:
        return _client(settings, tokens(settings.wcl_client_id, settings.wcl_client_secret))
    keys = keys or member_keys(settings)
    key = key_for(settings, member_id, keys)
    manager = tokens(key.client_id, key.client_secret)
    if key.member_id is None:
        return _client(settings, manager)
    try:
        manager.get_token()
    except AuthenticationError as exc:
        refused = bool(_REFUSED.search(str(exc)))
        if refused:
            keys.mark(member_id, key.revision, WclCredentialStatus.REJECTED)
        log.warning("wcl_key.fallback_to_guild", member_id=member_id, refused=refused)
        return _client(settings, tokens(settings.wcl_client_id, settings.wcl_client_secret))
    keys.mark(member_id, key.revision, WclCredentialStatus.WORKING)
    return _client(settings, manager)
