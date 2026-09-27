"""Picking the Warcraft Logs key for a request: the member's own when saved and working, else the guild's."""

from __future__ import annotations

import secrets
import uuid

import pytest
from hub_db import Base, CredentialCipher, Member, WclCredentialStatus
from hub_db.credentials import load_wcl_credentials, save_wcl_credentials
from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from toads_worker.settings import Settings
from toads_worker.wcl_keys import MemberKeys, client_for, key_for
from wcl_core.common.errors import AuthenticationError

KEY = CredentialCipher.generate_key()


def _settings() -> Settings:
    return Settings(
        database_url=SecretStr("sqlite://"),
        redis_url="redis://localhost:6379/0",
        wcl_client_id="guild-client-id",
        wcl_client_secret=SecretStr("replace-me"),
        wcl_guild_id=1,
        wcl_throttle_ms=500,
        wcl_max_retries=5,
        credentials_keys=SecretStr(KEY),
    )


@pytest.fixture
def db() -> sessionmaker[Session]:
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    maker = sessionmaker(engine, expire_on_commit=False)
    with maker.begin() as s:
        s.add(Member(id=1, discord_user_id=11, display_name="Hops"))
    return maker


def _save(db: sessionmaker[Session], cipher: CredentialCipher) -> str:
    cid = str(uuid.uuid4())
    with db.begin() as s:
        save_wcl_credentials(s, cipher, 1, cid, secrets.token_urlsafe(30))
    return cid


pytestmark = pytest.mark.security


class Tokens:
    error: str | None = None

    def __init__(self, client_id: str, client_secret: str | SecretStr) -> None:
        self.client_id = client_id

    def get_token(self) -> str:
        if Tokens.error and self.client_id != "guild-client-id":
            raise AuthenticationError(Tokens.error)
        return "token"


@pytest.fixture(autouse=True)
def _reset() -> None:
    Tokens.error = None


def _status(db: sessionmaker[Session], keys: CredentialCipher) -> WclCredentialStatus:
    with db() as s:
        stored = load_wcl_credentials(s, keys, 1)
        assert stored is not None
        return stored.status


def test_no_member_or_no_key_uses_guild_key(db: sessionmaker[Session]) -> None:
    keys = MemberKeys(db, CredentialCipher([KEY]))
    assert key_for(_settings(), None, keys).member_id is None
    assert key_for(_settings(), 1, keys).client_id == "guild-client-id"
    assert key_for(_settings(), 2, keys).client_id == "guild-client-id"


def test_member_key_is_used_and_marked_working(db: sessionmaker[Session]) -> None:
    cipher = CredentialCipher([KEY])
    cid = _save(db, cipher)
    client = client_for(_settings(), 1, keys=MemberKeys(db, cipher), tokens=Tokens)  # type: ignore[arg-type]
    assert client.token_manager.client_id == cid
    assert client.MIN_REQUEST_INTERVAL == 0.5 and client.MAX_RETRIES == 5 and client.cache_enabled is False
    assert _status(db, cipher) is WclCredentialStatus.WORKING


def test_refused_key_falls_back_and_is_marked(db: sessionmaker[Session]) -> None:
    cipher = CredentialCipher([KEY])
    _save(db, cipher)
    Tokens.error = "Authentication failed (HTTP 401)"
    client = client_for(_settings(), 1, keys=MemberKeys(db, cipher), tokens=Tokens)  # type: ignore[arg-type]
    assert client.token_manager.client_id == "guild-client-id"
    assert _status(db, cipher) is WclCredentialStatus.REJECTED
    # Once rejected, the member's key is not tried again until they save a new one.
    Tokens.error = None
    assert key_for(_settings(), 1, MemberKeys(db, cipher)).client_id == "guild-client-id"


def test_network_trouble_falls_back_without_blaming_the_key(db: sessionmaker[Session]) -> None:
    cipher = CredentialCipher([KEY])
    _save(db, cipher)
    Tokens.error = "Cannot reach WarcraftLogs — check your internet connection"
    client = client_for(_settings(), 1, keys=MemberKeys(db, cipher), tokens=Tokens)  # type: ignore[arg-type]
    assert client.token_manager.client_id == "guild-client-id"
    assert _status(db, cipher) is WclCredentialStatus.UNVERIFIED


def test_unreadable_key_uses_guild_key(db: sessionmaker[Session]) -> None:
    _save(db, CredentialCipher([CredentialCipher.generate_key()]))
    assert key_for(_settings(), 1, MemberKeys(db, CredentialCipher([KEY]))).client_id == "guild-client-id"


def test_check_on_a_key_replaced_meanwhile_leaves_the_new_key_unverified(db: sessionmaker[Session]) -> None:
    cipher = CredentialCipher([KEY])
    _save(db, cipher)

    class ReplacingTokens(Tokens):
        def get_token(self) -> str:
            # The member saves a new key while Warcraft Logs is refusing the old one.
            _save(db, cipher)
            raise AuthenticationError("Authentication failed (HTTP 401)")

    client_for(_settings(), 1, keys=MemberKeys(db, cipher), tokens=ReplacingTokens)  # type: ignore[arg-type]
    assert _status(db, cipher) is WclCredentialStatus.UNVERIFIED
