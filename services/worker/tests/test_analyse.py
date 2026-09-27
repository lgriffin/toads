"""The on-demand analysis job: wcl-app's RaidService with wcl-store storage (REQ-HUB-SYNC-006, REQ-CORE-SEC-002).

A Warcraft Logs client double serves one small raid, and storage is wcl-store's own SQLite ``PerformanceDB``, a
real ``RaidRepository``, so the job runs the analyzer's services layer end to end with no network. One test runs
against Postgres when TOADS_TEST_DATABASE_URL is set.
"""

from __future__ import annotations

import os
import re
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr
from pytest_bdd import given, parsers, scenario, then, when
from sqlalchemy import inspect, text
from toads_worker import store
from toads_worker.jobs import analyse
from toads_worker.reports import InvalidReportCodeError
from toads_worker.settings import Settings
from wcl_app.context import StorageFactory
from wcl_core.client import WarcraftLogsClient
from wcl_core.models import RaidMetadata
from wcl_store.sqlite import PerformanceDB

CODE = "aBcD1234eFgH5678"
FEATURES = Path(__file__).resolve().parents[3] / "tests" / "features"
# A priest who heals, a warrior who takes enough damage to be detected as a tank, and a rogue.
ACTORS = [
    {"name": "Lilypad", "id": 1, "type": "Player", "subType": "Priest"},
    {"name": "Tankard", "id": 2, "type": "Player", "subType": "Warrior"},
    {"name": "Croak", "id": 3, "type": "Player", "subType": "Rogue"},
]


def fake_wcl_client(code: str = CODE) -> Any:
    """A client double for ``analyze_raid``: every player heals, takes and deals the same amounts."""
    client = MagicMock(spec=WarcraftLogsClient)
    client.api_url = "https://fresh.warcraftlogs.test/api/v2/client"
    client.get_report_metadata.return_value = RaidMetadata(
        report_id=code, title="Karazhan", owner="toad", start_time=1_700_000_000_000, zone="Karazhan"
    )
    client.get_master_data.return_value = ACTORS
    client.get_fights.return_value = []
    client.get_healing_data.return_value = [
        {"type": "heal", "amount": 1_000_000, "overheal": 50_000, "abilityGameID": 2060}
    ]
    client.get_damage_taken_data.return_value = [
        {"type": "damage", "amount": 400_000, "mitigated": 500_000, "abilityGameID": 1}
    ]
    client.get_damage_done_data.return_value = [{"type": "damage", "amount": 150_000, "abilityGameID": 1}]
    client.run_query.return_value = {"data": {"reportData": {"report": {"table": {"data": {"entries": []}}}}}}
    client.get_buffs_table.return_value = {"data": {"auras": []}}
    client.get_cast_events_paginated.return_value = []
    client.get_cast_table.return_value = []
    client.get_damage_taken_table.return_value = []
    client.get_damage_done_table.return_value = []
    return client


@pytest.fixture
def wcl_client() -> Any:
    return fake_wcl_client()


@pytest.fixture
def sqlite_storage(tmp_path: Path) -> Callable[[], PerformanceDB]:
    """A wcl-store storage factory on a fresh SQLite file."""
    path = str(tmp_path / "analyzer.db")
    with PerformanceDB(path) as db:
        db.initialize()
    return lambda: PerformanceDB(path)


def _settings(database_url: str = "postgresql+psycopg://u:p@localhost/db") -> Settings:
    return Settings(
        database_url=SecretStr(database_url),
        redis_url="redis://localhost:6379/0",
        wcl_client_id="client-id",
        wcl_client_secret=SecretStr("client-secret"),
        wcl_guild_id=1,
        wcl_api_url="https://fresh.warcraftlogs.com/api/v2/client",
        wcl_throttle_ms=500,
        wcl_max_retries=5,
    )


def _roles(result: dict[str, Any]) -> dict[str, str]:
    comp = result["composition"]
    return {p["name"]: p["role"] for group in ("healers", "tanks", "melee", "ranged") for p in comp[group]}


def test_build_client_uses_worker_settings() -> None:
    settings = _settings()
    client = analyse.build_client(settings)
    assert client.api_url == "https://fresh.warcraftlogs.com/api/v2/client"
    assert client.cache_enabled is False
    assert client.MIN_REQUEST_INTERVAL == 0.5
    assert client.MAX_RETRIES == 5
    assert client.token_manager.client_secret.get_secret_value() == settings.wcl_client_secret.get_secret_value()


def test_analyse_report_runs_the_raid_service(wcl_client: Any, sqlite_storage: StorageFactory) -> None:
    messages: list[str] = []

    result = analyse.analyse_report(
        f"https://fresh.warcraftlogs.com/reports/{CODE}#fight=2",
        client=wcl_client,
        storage=sqlite_storage,
        progress=messages.append,
    )

    wcl_client.get_report_metadata.assert_called_with(CODE)
    assert "Fetching report metadata..." in messages
    assert result["metadata"]["report_id"] == CODE
    assert result["metadata"]["title"] == "Karazhan"
    assert _roles(result) == {"Lilypad": "healer", "Tankard": "tank", "Croak": "melee"}


def test_saved_role_override_changes_the_analysis(wcl_client: Any, sqlite_storage: Callable[[], PerformanceDB]) -> None:
    with sqlite_storage() as db:
        db.set_role_override("Tankard", "melee")

    result = analyse.analyse_report(CODE, client=wcl_client, storage=sqlite_storage)

    assert _roles(result)["Tankard"] == "melee"
    assert any("Tankard" in w for w in result["warnings"])


def test_analysis_is_stored(wcl_client: Any, sqlite_storage: Callable[[], PerformanceDB]) -> None:
    analyse.analyse_report(CODE, client=wcl_client, storage=sqlite_storage)

    with sqlite_storage() as db:
        assert CODE in db.get_imported_report_codes()
        stored = db.get_raid_analysis(CODE)
    assert stored is not None
    assert stored.metadata.title == "Karazhan"
    assert {p.name for p in stored.composition.all_players} == {"Lilypad", "Tankard", "Croak"}


def test_settings_supply_client_and_storage(
    monkeypatch: pytest.MonkeyPatch, wcl_client: Any, sqlite_storage: StorageFactory
) -> None:
    seen: list[Settings] = []

    def client_for(settings: Settings) -> Any:
        seen.append(settings)
        return wcl_client

    opened: list[str] = []

    def storage_for(settings: Settings) -> StorageFactory:
        opened.append(settings.database_url.get_secret_value())
        return sqlite_storage

    monkeypatch.setattr(analyse, "build_client", client_for)
    monkeypatch.setattr(analyse.store, "storage", storage_for)
    settings = _settings()

    result = analyse.analyse_report(CODE, settings=settings)

    assert seen == [settings]
    assert opened == [settings.database_url.get_secret_value()]
    assert result["metadata"]["report_id"] == CODE


@pytest.mark.security
def test_bad_code_is_refused_before_any_client_or_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    def no_client(_: Settings) -> Any:
        raise AssertionError("client built for an invalid code")

    def no_storage(_: Settings) -> StorageFactory:
        raise AssertionError("storage opened for an invalid code")

    monkeypatch.setattr(analyse, "build_client", no_client)
    monkeypatch.setattr(analyse.store, "storage", no_storage)
    with pytest.raises(InvalidReportCodeError):
        analyse.analyse_report('abc") { __schema', settings=_settings())


@pytest.mark.security
def test_bad_code_never_touches_a_passed_client_or_storage(wcl_client: Any) -> None:

    def storage() -> PerformanceDB:
        raise AssertionError("storage opened for an invalid code")

    with pytest.raises(InvalidReportCodeError):
        analyse.analyse_report(f"https://evil.example/reports/{CODE}", client=wcl_client, storage=storage)
    assert wcl_client.mock_calls == []


def test_storage_shares_one_engine_per_url() -> None:
    settings = _settings()
    try:
        assert store.engine_for("postgresql+psycopg://u:p@localhost/db") is store.engine_for(
            settings.database_url.get_secret_value()
        )
        with store.storage(settings)() as repo:
            assert repo._engine is store.engine_for(settings.database_url.get_secret_value())
    finally:
        store.engine_for.cache_clear()


def test_migrate_main_reads_only_the_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in list(os.environ):
        if name.startswith("TOADS_"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("TOADS_DATABASE_URL", "postgresql+psycopg://u:p@db/toads")
    urls: list[str] = []
    monkeypatch.setattr(store, "upgrade", urls.append)

    store.migrate_main()

    assert urls == ["postgresql+psycopg://u:p@db/toads"]


# ---------------------------------------------------------------- against a real Postgres

PG_URL = os.environ.get("TOADS_TEST_DATABASE_URL")


@pytest.fixture
def pg_url() -> Iterator[str]:
    """A fresh schema on TOADS_TEST_DATABASE_URL, selected through search_path and dropped afterwards."""
    if not PG_URL:
        pytest.skip("set TOADS_TEST_DATABASE_URL to run against Postgres")
    schema = f"toads_test_{uuid.uuid4().hex[:12]}"
    admin = store.make_engine(PG_URL)
    with admin.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    sep = "&" if "?" in PG_URL else "?"
    url = f"{PG_URL}{sep}options=-csearch_path%3D{schema}"
    try:
        yield url
    finally:
        store.engine_for(url).dispose()
        store.engine_for.cache_clear()
        with admin.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def test_analyse_report_on_postgres(pg_url: str, wcl_client: Any) -> None:
    store.migrate(pg_url)
    settings = _settings(pg_url)
    with store.storage(settings)() as repo:
        repo.set_role_override("Tankard", "melee")

    result = analyse.analyse_report(CODE, settings=settings, client=wcl_client)

    assert _roles(result)["Tankard"] == "melee"
    with store.storage(settings)() as repo:
        assert CODE in repo.get_imported_report_codes()
        stored = repo.get_raid_analysis(CODE)
    assert stored is not None
    assert {p.name: p.role for p in stored.composition.all_players}["Tankard"] == "melee"
    tables = set(inspect(store.engine_for(pg_url)).get_table_names())
    assert {"raids", "role_overrides", "wcl_store_alembic_version"} <= tables
    assert "alembic_version" not in tables  # hub-db's version table is left alone


# ---------------------------------------------------------------- REQ-HUB-SYNC-006


def _bind(feature: str, number: int) -> Any:
    """Bind the scenario REQ-<EPIC>-<nnn> from e.g. hub_sync.feature (the id is built, not written out)."""
    req_id = f"REQ-{feature.removesuffix('.feature').upper().replace('_', '-')}-{number:03d}"
    for line in (FEATURES / feature).read_text(encoding="utf-8").splitlines():
        m = re.match(rf"\s*Scenario(?: Outline)?: ({req_id} .*)$", line)
        if m:
            return scenario(str(FEATURES / feature), m.group(1))
    raise LookupError(req_id)


@_bind("hub_sync.feature", 6)
def test_sync_006() -> None:
    pass


@given(parsers.parse('a saved role override that pins "{name}" to {role}'))
def saved_override(sqlite_storage: Callable[[], PerformanceDB], name: str, role: str) -> None:
    with sqlite_storage() as db:
        db.set_role_override(name, role)


@when("the worker analyses the report", target_fixture="result")
def worker_analyses(wcl_client: Any, sqlite_storage: Callable[[], PerformanceDB]) -> dict[str, Any]:
    return analyse.analyse_report(CODE, client=wcl_client, storage=sqlite_storage)


@then(parsers.parse('"{name}" is analysed as {role}'))
def analysed_as(result: dict[str, Any], name: str, role: str) -> None:
    assert _roles(result)[name] == role


@then("the analysis is stored")
def stored(sqlite_storage: Callable[[], PerformanceDB], result: dict[str, Any]) -> None:
    with sqlite_storage() as db:
        assert CODE in db.get_imported_report_codes()
        saved = db.get_raid_analysis(CODE)
    assert saved is not None
    assert {p.name: p.role for p in saved.composition.all_players} == _roles(result)
