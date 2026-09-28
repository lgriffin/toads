"""Reference comparison storage: the dedicated login encrypted at rest, jobs, and the worker's capped results."""

from __future__ import annotations

import secrets

import pytest
from hub_db import (
    Base,
    CredentialCipher,
    CredentialDecryptError,
    Member,
    ReferenceComparison,
    ReferenceJob,
    ReferenceLogin,
    ReferencePage,
)
from hub_db.credentials import save_wcl_credentials
from hub_db.reference import (
    LOGIN_ROW,
    MAX_COMPARISONS,
    MAX_JOBS,
    JobKind,
    JobStatus,
    LoginToken,
    create_job,
    delete_comparisons_of,
    delete_login,
    load_login,
    mark_login_expired,
    recent_jobs,
    save_comparison,
    save_login,
    save_page,
    store_refreshed_login,
    update_job,
)
from sqlalchemy import create_engine, func, select
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


@pytest.fixture
def cipher() -> CredentialCipher:
    return CredentialCipher([CredentialCipher.generate_key()])


def _token(expires_at: float = 5_000.0) -> LoginToken:
    return LoginToken(secrets.token_urlsafe(24), secrets.token_urlsafe(24), expires_at)


@pytest.mark.security
def test_login_is_encrypted_and_round_trips(db: Session, cipher: CredentialCipher) -> None:
    token = _token()
    save_login(db, cipher, token, member_id=1)
    row = db.get(ReferenceLogin, LOGIN_ROW)
    assert row is not None and row.connected_by == 1 and row.status == "working"
    assert token.access_token not in row.token_encrypted and token.refresh_token not in row.token_encrypted
    assert load_login(db, cipher) == token
    assert token.access_token not in repr(token)


@pytest.mark.security
def test_a_member_key_ciphertext_never_reads_as_the_login(db: Session, cipher: CredentialCipher) -> None:
    key = save_wcl_credentials(db, cipher, 1, "client", secrets.token_urlsafe(20))
    save_login(db, cipher, _token(), member_id=1)
    row = db.get(ReferenceLogin, LOGIN_ROW)
    assert row is not None
    row.token_encrypted = key.client_secret_encrypted
    with pytest.raises(CredentialDecryptError):
        load_login(db, cipher)


def test_reconnect_refresh_expire_and_delete(db: Session, cipher: CredentialCipher) -> None:
    assert load_login(db, cipher) is None
    save_login(db, cipher, _token(), member_id=1)
    second = _token(9_000.0)
    save_login(db, cipher, second, member_id=2)
    row = db.get(ReferenceLogin, LOGIN_ROW)
    assert row is not None and row.connected_by == 2
    assert load_login(db, cipher) == second

    refreshed = _token(12_000.0)
    store_refreshed_login(db, cipher, refreshed)
    assert load_login(db, cipher) == refreshed and row.refreshed_at is not None

    mark_login_expired(db)
    assert load_login(db, cipher) is None and row.status == "expired"
    save_login(db, cipher, _token(), member_id=1)
    assert row.status == "working"

    assert delete_login(db) is True
    assert delete_login(db) is False
    assert load_login(db, cipher) is None


def test_jobs_are_created_updated_and_capped(db: Session) -> None:
    job = create_job(db, JobKind.IMPORT, "wed", 1, {"report": "a" * 16, "label": None})
    assert job.status == "queued" and len(job.id) == 32
    update_job(db, job.id, JobStatus.FAILED, "x" * 900)
    assert job.status == "failed" and len(job.message) == 500
    assert update_job(db, "missing", JobStatus.DONE) is None

    for _ in range(MAX_JOBS + 5):
        create_job(db, JobKind.LABEL, "sun", None, {"report": "b" * 16})
    assert db.scalar(select(func.count()).select_from(ReferenceJob)) == MAX_JOBS
    assert len(recent_jobs(db, 10)) == 10


def _payload(guild: str, ref: str) -> dict[str, object]:
    return {"guild": {"report_id": guild, "title": "Ours"}, "reference": {"report_id": ref, "title": "Theirs"}}


def test_comparisons_replace_cap_and_follow_deletes(db: Session) -> None:
    save_comparison(db, _payload("g" * 16, "r" * 16), "2026-09-28 10:00:00")
    save_comparison(db, _payload("g" * 16, "r" * 16), "2026-09-28 11:00:00")
    rows = list(db.scalars(select(ReferenceComparison)))
    assert len(rows) == 1 and rows[0].generated_at == "2026-09-28 11:00:00"

    for i in range(MAX_COMPARISONS + 3):
        save_comparison(db, _payload(f"{i:016d}", "r" * 16), "2026-09-28 12:00:00")
    assert db.scalar(select(func.count()).select_from(ReferenceComparison)) == MAX_COMPARISONS

    delete_comparisons_of(db, "r" * 16)
    assert db.scalar(select(func.count()).select_from(ReferenceComparison)) == 0


def test_page_is_one_row(db: Session) -> None:
    save_page(db, "2026-09-28 10:00:00", [{"report_id": "r"}], [])
    save_page(db, "2026-09-28 11:00:00", [], [{"report_id": "g"}])
    db.flush()
    [page] = db.scalars(select(ReferencePage))
    assert (
        page.generated_at == "2026-09-28 11:00:00"
        and page.references == []
        and page.guild_raids == [{"report_id": "g"}]
    )
