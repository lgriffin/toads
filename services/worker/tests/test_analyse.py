from __future__ import annotations

from typing import Any

import pytest
from pydantic import SecretStr
from toads_worker.jobs import analyse
from toads_worker.reports import InvalidReportCodeError
from toads_worker.settings import Settings
from wcl_core.client import WarcraftLogsClient
from wcl_core.models import RaidAnalysis, RaidComposition, RaidMetadata

CODE = "aBcD1234eFgH5678"


def _settings() -> Settings:
    return Settings(
        database_url=SecretStr("postgresql+psycopg://u:p@localhost/db"),
        redis_url="redis://localhost:6379/0",
        wcl_client_id="client-id",
        wcl_client_secret=SecretStr("client-secret"),
        wcl_guild_id=1,
        wcl_api_url="https://fresh.warcraftlogs.com/api/v2/client",
        wcl_throttle_ms=500,
        wcl_max_retries=5,
        credentials_keys=SecretStr("unused"),
    )


def _analysis() -> RaidAnalysis:
    return RaidAnalysis(
        metadata=RaidMetadata(report_id=CODE, title="Karazhan", owner="toad", start_time=0, zone="Karazhan"),
        composition=RaidComposition(),
    )


def test_build_client_uses_worker_settings() -> None:
    settings = _settings()
    client = analyse.build_client(settings)
    assert client.api_url == "https://fresh.warcraftlogs.com/api/v2/client"
    assert client.cache_enabled is False
    assert client.MIN_REQUEST_INTERVAL == 0.5
    assert client.MAX_RETRIES == 5
    assert client.token_manager.client_secret.get_secret_value() == settings.wcl_client_secret.get_secret_value()


def test_analyse_report_runs_wcl_core(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    def fake_analyze(client: WarcraftLogsClient, code: str, progress_callback: Any = None) -> RaidAnalysis:
        seen.update(client=client, code=code, progress=progress_callback)
        return _analysis()

    monkeypatch.setattr(analyse, "analyze_raid", fake_analyze)
    client = analyse.build_client(_settings())
    messages: list[str] = []

    result = analyse.analyse_report(
        f"https://fresh.warcraftlogs.com/reports/{CODE}#fight=2", client=client, progress=messages.append
    )

    assert seen["client"] is client
    assert seen["code"] == CODE
    assert seen["progress"] == messages.append
    assert result["metadata"]["report_id"] == CODE
    assert result["metadata"]["title"] == "Karazhan"


@pytest.mark.security
def test_bad_code_is_refused_before_any_client_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    def no_client(_: Settings) -> WarcraftLogsClient:
        raise AssertionError("client built for an invalid code")

    monkeypatch.setattr(analyse, "build_client", no_client)
    with pytest.raises(InvalidReportCodeError):
        analyse.analyse_report('abc") { __schema', settings=_settings())
