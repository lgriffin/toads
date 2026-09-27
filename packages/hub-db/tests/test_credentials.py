"""Members' Warcraft Logs keys: encrypted at rest, bound to their member, rotatable."""

from __future__ import annotations

import secrets
import uuid
from pathlib import Path
from typing import Any

import pytest
from hub_db import Base, CredentialCipher, CredentialDecryptError, Member, WclCredential, WclCredentialStatus
from hub_db.credentials import (
    delete_wcl_credentials,
    load_wcl_credentials,
    mark_wcl_credentials,
    save_wcl_credentials,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = Session(engine)
    session.add_all(
        [Member(id=1, discord_user_id=11, display_name="A"), Member(id=2, discord_user_id=22, display_name="B")]
    )
    session.flush()
    return session


pytestmark = pytest.mark.security


def _key() -> tuple[str, str]:
    return str(uuid.uuid4()), secrets.token_urlsafe(30)


def test_round_trip_and_hint(db: Session) -> None:
    cipher = CredentialCipher([CredentialCipher.generate_key()])
    cid, secret = _key()
    row = save_wcl_credentials(db, cipher, 1, cid, secret)
    assert cid not in row.client_id_encrypted and secret not in row.client_secret_encrypted
    assert row.client_id_hint == cid[-4:]
    stored = load_wcl_credentials(db, cipher, 1)
    assert stored is not None
    assert (stored.client_id, stored.client_secret, stored.status) == (cid, secret, WclCredentialStatus.UNVERIFIED)
    assert secret not in repr(stored) and cid not in repr(stored)
    assert load_wcl_credentials(db, cipher, 2) is None


def test_saving_again_resets_status(db: Session) -> None:
    cipher = CredentialCipher([CredentialCipher.generate_key()])
    save_wcl_credentials(db, cipher, 1, *_key())
    stored = load_wcl_credentials(db, cipher, 1)
    assert stored is not None
    assert mark_wcl_credentials(db, 1, stored.revision, WclCredentialStatus.REJECTED) is True
    save_wcl_credentials(db, cipher, 1, *_key())
    row = db.get(WclCredential, 1)
    assert row is not None and row.status is WclCredentialStatus.UNVERIFIED and row.checked_at is None


def test_ciphertext_copied_to_another_member_does_not_decrypt(db: Session) -> None:
    cipher = CredentialCipher([CredentialCipher.generate_key()])
    save_wcl_credentials(db, cipher, 1, *_key())
    save_wcl_credentials(db, cipher, 2, *_key())
    one, two = db.get(WclCredential, 1), db.get(WclCredential, 2)
    assert one is not None and two is not None
    two.client_secret_encrypted = one.client_secret_encrypted
    with pytest.raises(CredentialDecryptError):
        load_wcl_credentials(db, cipher, 2)


def test_rotation_new_key_first_still_reads_old_rows(db: Session) -> None:
    old, new = CredentialCipher.generate_key(), CredentialCipher.generate_key()
    cid, secret = _key()
    save_wcl_credentials(db, CredentialCipher([old]), 1, cid, secret)
    stored = load_wcl_credentials(db, CredentialCipher.from_setting(f"{new},{old}"), 1)
    assert stored is not None and stored.client_secret == secret
    with pytest.raises(CredentialDecryptError):
        load_wcl_credentials(db, CredentialCipher([new]), 1)


def test_bad_key_setting_is_refused_without_echoing_it() -> None:
    with pytest.raises(ValueError, match="Fernet keys") as info:
        CredentialCipher.from_setting("replace-me")
    assert "replace-me" not in str(info.value)
    with pytest.raises(ValueError, match="at least one"):
        CredentialCipher.from_setting(" , ")


def test_delete(db: Session) -> None:
    cipher = CredentialCipher([CredentialCipher.generate_key()])
    save_wcl_credentials(db, cipher, 1, *_key())
    assert delete_wcl_credentials(db, 1) is True
    assert delete_wcl_credentials(db, 1) is False


def test_a_check_on_a_replaced_key_does_not_touch_the_new_one(db: Session) -> None:
    cipher = CredentialCipher([CredentialCipher.generate_key()])
    save_wcl_credentials(db, cipher, 1, *_key())
    old = load_wcl_credentials(db, cipher, 1)
    assert old is not None
    save_wcl_credentials(db, cipher, 1, *_key())
    assert mark_wcl_credentials(db, 1, old.revision, WclCredentialStatus.REJECTED) is False
    row = db.get(WclCredential, 1)
    assert row is not None and row.status is WclCredentialStatus.UNVERIFIED
    delete_wcl_credentials(db, 1)
    assert mark_wcl_credentials(db, 1, old.revision, WclCredentialStatus.WORKING) is False


def test_two_first_saves_at_once_both_succeed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'race.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as s, s.begin():
        s.add(Member(id=1, discord_user_id=11, display_name="A"))
    cipher = CredentialCipher([CredentialCipher.generate_key()])
    first, second = Session(engine), Session(engine)
    # The second save looked before the first committed, so it takes the insert path and hits the primary key.
    real_get = second.get
    looks: list[int] = []

    def stale_get(*args: Any, **kwargs: Any) -> Any:
        looks.append(1)
        return None if len(looks) == 1 else real_get(*args, **kwargs)

    monkeypatch.setattr(second, "get", stale_get)
    save_wcl_credentials(first, cipher, 1, *_key())
    first.commit()
    cid, secret = _key()
    save_wcl_credentials(second, cipher, 1, cid, secret)
    second.commit()
    assert len(looks) == 2
    with Session(engine) as check:
        stored = load_wcl_credentials(check, cipher, 1)
    assert stored is not None and stored.client_secret == secret
