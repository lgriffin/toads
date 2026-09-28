"""Reference comparison jobs: wcl-app's ReferenceService on wcl-store storage, driven by requests in hub-db.

Storage is wcl-store's own SQLite ``PerformanceDB`` and hub-db is in-memory SQLite, so the job runs end to end with
no network; ``analyze_raid`` is replaced where a job would fetch a report.
"""

from __future__ import annotations

import secrets
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from hub_db import Base, CredentialCipher, Member, ReferenceComparison, ReferenceJob, ReferenceLogin, ReferencePage
from hub_db.reference import LOGIN_ROW, JobKind, LoginToken, create_job, load_login, save_comparison, save_login
from pydantic import SecretStr
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from toads_worker.jobs import reference
from toads_worker.settings import Settings
from wcl_core.client import WarcraftLogsClient
from wcl_core.models import (
    DPSPerformance,
    EncounterPerformance,
    EncounterSummary,
    HealerPerformance,
    PlayerIdentity,
    RaidAnalysis,
    RaidComposition,
    RaidMetadata,
)
from wcl_store.sqlite import PerformanceDB

OURS = "OursOursOursOurs"
THEIRS = "TheirsTheirsThei"
START = 1_790_000_000_000
KEY = CredentialCipher.generate_key()
# Built at runtime: token-looking literals trip the secret scanners.
FRESH_ACCESS, FRESH_REFRESH = secrets.token_urlsafe(8), secrets.token_urlsafe(8)


def _analysis(code: str, title: str, healing: int) -> RaidAnalysis:
    boss = EncounterSummary(
        1, "Gruul", START + 60_000, START + 300_000, 240_000, [EncounterPerformance("Croak", "Rogue", 3, "melee", 9, 9)]
    )
    return RaidAnalysis(
        metadata=RaidMetadata(code, title, "toad", START, START + 3_600_000, "Gruul's Lair"),
        composition=RaidComposition(
            healers=[PlayerIdentity("Lilypad", "Priest", 1, "healer")],
            melee=[PlayerIdentity("Croak", "Rogue", 3, "melee")],
        ),
        healers=[HealerPerformance("Lilypad", "Priest", 1, total_healing=healing, total_overhealing=healing // 10)],
        dps=[DPSPerformance("Croak", "Rogue", 3, "melee", total_damage=400_000)],
        encounters=[boss],
    )


def _settings() -> Settings:
    return Settings(
        database_url=SecretStr("sqlite://"),
        redis_url="redis://localhost:6379/0",
        wcl_client_id="client-id",
        wcl_client_secret=SecretStr(secrets.token_urlsafe(12)),
        wcl_guild_id=1,
        credentials_keys=SecretStr(KEY),
    )


@pytest.fixture
def hub_db() -> sessionmaker[Session]:
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    db = sessionmaker(engine, expire_on_commit=False)
    with db.begin() as s:
        s.add(Member(id=1, discord_user_id=11, display_name="Hopscotch"))
    return db


@pytest.fixture
def storage(tmp_path: Path) -> Callable[[], PerformanceDB]:
    path = str(tmp_path / "analyzer.db")
    with PerformanceDB(path) as db:
        db.initialize()
        db.import_raid(_analysis(OURS, "Toads Gruul", 900_000))
    return lambda: PerformanceDB(path)


def _connect(db: sessionmaker[Session], expires_at: float = 4_000_000_000.0) -> LoginToken:
    token = LoginToken(secrets.token_urlsafe(16), secrets.token_urlsafe(16), expires_at)
    with db.begin() as s:
        save_login(s, CredentialCipher([KEY]), token, member_id=1)
    return token


def _job(db: sessionmaker[Session], kind: JobKind, **params: Any) -> str:
    with db.begin() as s:
        return create_job(s, kind, "wed", 1, params).id


def _run(job_id: str, db: sessionmaker[Session], storage: Callable[[], PerformanceDB]) -> dict[str, Any]:
    return reference.run_reference_job(
        job_id, settings=_settings(), storage=storage, db=db, client=MagicMock(spec=WarcraftLogsClient)
    )


def _page(db: sessionmaker[Session]) -> ReferencePage:
    with db() as s:
        page = s.get(ReferencePage, 1)
        assert page is not None
        return page


def test_import_uses_the_dedicated_login(hub_db: sessionmaker[Session], storage: Callable[[], PerformanceDB]) -> None:
    _connect(hub_db)
    job = _job(hub_db, JobKind.IMPORT, report=THEIRS, label="World first")
    with patch("wcl_app.raids.analyze_raid", return_value=_analysis(THEIRS, "Best Gruul", 800_000)) as analyze:
        result = _run(job, hub_db, storage)

    assert result == {"job": job, "status": "done", "message": "Imported Best Gruul."}
    client = analyze.call_args.args[0]
    assert client.api_url == "https://fresh.warcraftlogs.com/api/v2/user" and client.cache_enabled is False
    page = _page(hub_db)
    assert [(r["report_id"], r["label"]) for r in page.references] == [(THEIRS, "World first")]
    assert [r["report_id"] for r in page.guild_raids] == [OURS]


def test_import_without_the_login_fails_the_job(
    hub_db: sessionmaker[Session], storage: Callable[[], PerformanceDB]
) -> None:
    job = _job(hub_db, JobKind.IMPORT, report=THEIRS, label=None)
    with patch("wcl_app.raids.analyze_raid") as analyze:
        result = _run(job, hub_db, storage)
    assert result["status"] == "failed" and result["message"] == reference.NO_LOGIN_MESSAGE
    analyze.assert_not_called()


def _token_response(status: int) -> MagicMock:
    response = MagicMock(status_code=status)
    response.json.return_value = {"access_token": FRESH_ACCESS, "refresh_token": FRESH_REFRESH, "expires_in": 3600}
    return response


def _uses_token(analysis: RaidAnalysis) -> Callable[..., RaidAnalysis]:
    def analyze(client: WarcraftLogsClient, *_: Any, **__: Any) -> RaidAnalysis:
        client.token_manager.get_token()
        return analysis

    return analyze


def test_an_expired_token_is_refreshed_and_kept(
    hub_db: sessionmaker[Session], storage: Callable[[], PerformanceDB]
) -> None:
    _connect(hub_db, expires_at=0)
    job = _job(hub_db, JobKind.IMPORT, report=THEIRS, label=None)
    with (
        patch("wcl_core.user_auth.requests.post", return_value=_token_response(200)) as post,
        patch("wcl_app.raids.analyze_raid", side_effect=_uses_token(_analysis(THEIRS, "Best Gruul", 1))),
    ):
        assert _run(job, hub_db, storage)["status"] == "done"
    assert post.call_args.kwargs["data"]["grant_type"] == "refresh_token"
    with hub_db() as s:
        token = load_login(s, CredentialCipher([KEY]))
        row = s.get(ReferenceLogin, LOGIN_ROW)
    assert token is not None and token.access_token == FRESH_ACCESS and token.refresh_token == FRESH_REFRESH
    assert row is not None and row.refreshed_at is not None


def test_a_refused_refresh_expires_the_login(
    hub_db: sessionmaker[Session], storage: Callable[[], PerformanceDB]
) -> None:
    _connect(hub_db, expires_at=0)
    job = _job(hub_db, JobKind.IMPORT, report=THEIRS, label=None)
    with (
        patch("wcl_core.user_auth.requests.post", return_value=_token_response(400)),
        patch("wcl_app.raids.analyze_raid", side_effect=_uses_token(_analysis(THEIRS, "x", 1))),
    ):
        result = _run(job, hub_db, storage)
    assert result["message"] == reference.EXPIRED_MESSAGE
    with hub_db() as s:
        row = s.get(ReferenceLogin, LOGIN_ROW)
        assert row is not None and row.status == "expired"
        assert load_login(s, CredentialCipher([KEY])) is None


def test_compare_label_and_delete(hub_db: sessionmaker[Session], storage: Callable[[], PerformanceDB]) -> None:
    with storage() as db:
        db.import_raid(_analysis(THEIRS, "Best Gruul", 800_000), source="reference")

    result = _run(_job(hub_db, JobKind.COMPARE, guild_report=OURS, reference_report=THEIRS), hub_db, storage)
    assert result["message"] == "Compared Toads Gruul with Best Gruul."
    with hub_db() as s:
        [row] = s.scalars(select(ReferenceComparison))
        assert row.payload["overview"][2]["key"] == "total_healing"
        assert row.payload["overview"][2]["delta_percent"] == 12.5
        assert (row.guild_title, row.reference_title) == ("Toads Gruul", "Best Gruul")

    assert _run(_job(hub_db, JobKind.LABEL, report=THEIRS, label="Best"), hub_db, storage)["status"] == "done"
    assert _page(hub_db).references[0]["label"] == "Best"

    result = _run(_job(hub_db, JobKind.DELETE, report=OURS), hub_db, storage)
    assert result["status"] == "failed" and "not a reference raid" in result["message"]

    assert _run(_job(hub_db, JobKind.DELETE, report=THEIRS), hub_db, storage)["message"] == "Reference deleted."
    assert _page(hub_db).references == []
    with hub_db() as s:
        assert list(s.scalars(select(ReferenceComparison))) == []


def test_a_storage_or_network_failure_is_reported_without_detail(
    hub_db: sessionmaker[Session], storage: Callable[[], PerformanceDB]
) -> None:
    _connect(hub_db)
    job = _job(hub_db, JobKind.IMPORT, report=THEIRS, label=None)
    with patch("wcl_app.raids.analyze_raid", side_effect=ConnectionError("secret detail")):
        result = _run(job, hub_db, storage)
    assert result["status"] == "failed" and "secret detail" not in result["message"]


def test_an_unknown_job_is_reported_missing(
    hub_db: sessionmaker[Session], storage: Callable[[], PerformanceDB]
) -> None:
    assert _run("nope", hub_db, storage) == {"job": "nope", "status": "missing"}


def test_publish_reference_page(
    hub_db: sessionmaker[Session], storage: Callable[[], PerformanceDB], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(reference, "hub_sessions", lambda _: hub_db)
    with hub_db.begin() as s:
        save_comparison(
            s, {"guild": {"report_id": OURS, "title": "a"}, "reference": {"report_id": THEIRS, "title": "b"}}, "t"
        )
    assert reference.publish_reference_page(_settings(), storage=storage) == {"references": 0, "guild_raids": 1}
    assert [r["report_id"] for r in _page(hub_db).guild_raids] == [OURS]


def test_an_unexpected_failure_still_ends_the_job(
    hub_db: sessionmaker[Session], storage: Callable[[], PerformanceDB]
) -> None:
    with storage() as db:
        db.import_raid(_analysis(THEIRS, "Best Gruul", 800_000), source="reference")
    job = _job(hub_db, JobKind.COMPARE, guild_report=OURS, reference_report=THEIRS)
    with (
        patch.object(reference, "save_comparison", side_effect=RuntimeError("hub-db down")),
        pytest.raises(RuntimeError),
    ):
        _run(job, hub_db, storage)
    with hub_db() as s:
        row = s.get(ReferenceJob, job)
        assert row is not None and row.status == "failed" and row.message == reference.UNEXPECTED_MESSAGE


def test_a_refresh_after_a_reconnect_leaves_the_new_login_alone(
    hub_db: sessionmaker[Session], storage: Callable[[], PerformanceDB]
) -> None:
    _connect(hub_db, expires_at=0)
    newer = LoginToken(secrets.token_urlsafe(16), secrets.token_urlsafe(16), 4_000_000_000.0)

    def reconnect_then_refresh(client: WarcraftLogsClient, *_: Any, **__: Any) -> RaidAnalysis:
        # An officer connects another account while this job still holds the first one's expired token.
        with hub_db.begin() as s:
            save_login(s, CredentialCipher([KEY]), newer, member_id=1)
        client.token_manager.get_token()
        return _analysis(THEIRS, "Best Gruul", 1)

    job = _job(hub_db, JobKind.IMPORT, report=THEIRS, label=None)
    with (
        patch("wcl_core.user_auth.requests.post", return_value=_token_response(400)),
        patch("wcl_app.raids.analyze_raid", side_effect=reconnect_then_refresh),
    ):
        assert _run(job, hub_db, storage)["message"] == reference.EXPIRED_MESSAGE
    with hub_db() as s:
        assert load_login(s, CredentialCipher([KEY])) == newer
