"""The Logs job: wcl_app.raid_pages over wcl-store, the list first, then each analysis the hub asks for."""

from __future__ import annotations

import importlib.util
import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from pydantic import SecretStr
from toads_worker.jobs import analyse, logs
from toads_worker.settings import Settings
from wcl_store.sqlite import PerformanceDB

# The analysis job's Warcraft Logs double, loaded by path (tests run with --import-mode=importlib).
_spec = importlib.util.spec_from_file_location("worker_test_analyse", Path(__file__).with_name("test_analyse.py"))
assert _spec and _spec.loader
_analyse_tests = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_analyse_tests)
CODE: str = _analyse_tests.CODE
fake_wcl_client = _analyse_tests.fake_wcl_client


@pytest.fixture
def sqlite_storage(tmp_path: Path) -> Callable[[], PerformanceDB]:
    path = str(tmp_path / "analyzer.db")
    with PerformanceDB(path) as db:
        db.initialize()
    return lambda: PerformanceDB(path)


def _settings(token: str = "test-service-token") -> Settings:  # noqa: S107
    return Settings(
        database_url=SecretStr("postgresql+psycopg://u:p@localhost/db"),
        redis_url="redis://localhost",
        wcl_client_id="id",
        wcl_client_secret=SecretStr("replace-me"),
        wcl_guild_id=1,
        credentials_keys=SecretStr("replace-me"),
        hub_api_url="http://hub.test",
        hub_service_token=SecretStr(token),
    )


def test_empty_storage_lists_nothing(sqlite_storage: Callable[[], PerformanceDB]) -> None:
    index = logs.build_index(logs.build_pages(sqlite_storage), now=lambda: datetime(2026, 10, 19, 8, 0, 0))
    assert index == {"version": 1, "generated_at": "2026-10-19 08:00:00", "raids": [], "bosses": [], "hashes": {}}


def test_a_stored_raid_is_listed_with_its_weekday_and_analysis(sqlite_storage: Callable[[], PerformanceDB]) -> None:
    analyse.analyse_report(CODE, client=fake_wcl_client(), storage=sqlite_storage)
    built = logs.build_pages(sqlite_storage)
    assert [p.summary.report_id for p in built.pages] == [CODE]
    index = logs.build_index(built)
    (raid,) = index["raids"]
    assert raid["report_id"] == CODE
    assert raid["weekday"] in range(7)
    assert index["hashes"] == {CODE: logs.page_hash(built.pages[0])}
    page = built.pages[0].to_dict()
    assert page["version"] == 1
    assert page["composition"]
    json.dumps(index)  # plain JSON, ready to send
    json.dumps(page)


def test_publish_sends_the_list_then_each_missing_raid(sqlite_storage: Callable[[], PerformanceDB]) -> None:
    analyse.analyse_report(CODE, client=fake_wcl_client(), storage=sqlite_storage)
    seen: list[tuple[str, str, str]] = []
    bodies: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path, request.headers["authorization"]))
        bodies[request.url.path] = json.loads(request.content)
        if request.url.path == "/api/worker/logs":
            # A raid the worker does not hold is skipped rather than failing the run.
            return httpx.Response(200, json={"raids": 1, "missing": [CODE, "gone"]})
        return httpx.Response(200, json={"report_id": CODE})

    hub = httpx.Client(base_url="http://hub.test", transport=httpx.MockTransport(handler))
    assert logs.publish_logs(_settings(), storage=sqlite_storage, hub=hub) == {"raids": 1, "sent": 1, "unreadable": 0}
    auth = "Bearer test-service-token"
    assert seen == [("PUT", "/api/worker/logs", auth), ("PUT", f"/api/worker/logs/{CODE}", auth)]
    assert bodies[f"/api/worker/logs/{CODE}"]["page"]["summary"]["report_id"] == CODE
    assert bodies[f"/api/worker/logs/{CODE}"]["hash"] == bodies["/api/worker/logs"]["hashes"][CODE]


def test_an_unreadable_raid_stays_listed_without_a_page(
    sqlite_storage: Callable[[], PerformanceDB], monkeypatch: pytest.MonkeyPatch
) -> None:
    analyse.analyse_report(CODE, client=fake_wcl_client(), storage=sqlite_storage)
    monkeypatch.setattr(logs.RaidPageService, "page", lambda *_: None)
    index = logs.build_index(logs.build_pages(sqlite_storage))
    # The hub keeps the analysis it already holds instead of dropping the raid.
    assert [r["report_id"] for r in index["raids"]] == [CODE]
    assert index["hashes"] == {}
    # The run counts it, so a by-hand run shows why its page says "not analysed".
    answer = httpx.Response(200, json={"raids": 1, "missing": []})
    hub = httpx.Client(base_url="http://hub.test", transport=httpx.MockTransport(lambda _: answer))
    assert logs.publish_logs(_settings(), storage=sqlite_storage, hub=hub)["unreadable"] == 1


@pytest.mark.parametrize("refused", ["list", "page"])
def test_a_newer_run_s_list_stops_this_one_quietly(sqlite_storage: Callable[[], PerformanceDB], refused: str) -> None:
    analyse.analyse_report(CODE, client=fake_wcl_client(), storage=sqlite_storage)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/worker/logs":
            if refused == "list":
                return httpx.Response(409, json={"detail": "A newer list is already stored"})
            return httpx.Response(200, json={"raids": 1, "missing": [CODE]})
        return httpx.Response(409, json={"detail": "A newer list wants another build of this raid"})

    hub = httpx.Client(base_url="http://hub.test", transport=httpx.MockTransport(handler))
    assert logs.publish_logs(_settings(), storage=sqlite_storage, hub=hub) == {"raids": 1, "sent": 0, "unreadable": 0}


def test_other_refusals_fail_the_run(sqlite_storage: Callable[[], PerformanceDB]) -> None:
    hub = httpx.Client(base_url="http://hub.test", transport=httpx.MockTransport(lambda _: httpx.Response(422)))
    with pytest.raises(httpx.HTTPStatusError):
        logs.publish_logs(_settings(), storage=sqlite_storage, hub=hub)


@pytest.mark.parametrize("failure", [httpx.Response(500), httpx.ReadTimeout("slow")])
def test_a_refused_raid_does_not_hold_back_the_next(
    sqlite_storage: Callable[[], PerformanceDB], failure: httpx.Response | Exception
) -> None:
    analyse.analyse_report(CODE, client=fake_wcl_client(), storage=sqlite_storage)
    pages: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/worker/logs":
            # The same raid twice stands in for two raids: the first upload fails, the second must still go.
            return httpx.Response(200, json={"raids": 1, "missing": [CODE, CODE]})
        pages.append(request.url.path)
        if len(pages) == 1:
            if isinstance(failure, Exception):
                raise failure
            return failure
        return httpx.Response(200, json={"report_id": CODE})

    hub = httpx.Client(base_url="http://hub.test", transport=httpx.MockTransport(handler))
    with pytest.raises(RuntimeError, match=f"1 raid\\(s\\): {CODE}"):
        logs.publish_logs(_settings(), storage=sqlite_storage, hub=hub)
    assert len(pages) == 2


def test_a_page_with_a_nan_is_sent_as_null() -> None:
    assert logs.plain({"a": [1.5, float("nan")], "b": (float("inf"), "x"), "c": {"d": -float("inf")}}) == {
        "a": [1.5, None],
        "b": [None, "x"],
        "c": {"d": None},
    }


def test_a_run_without_a_client_opens_and_closes_one(
    sqlite_storage: Callable[[], PerformanceDB], monkeypatch: pytest.MonkeyPatch
) -> None:
    opened: list[httpx.Client] = []
    real = httpx.Client

    def client(**kwargs: Any) -> httpx.Client:
        c = real(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"raids": 0, "missing": []})), **kwargs
        )
        opened.append(c)
        return c

    monkeypatch.setattr(logs.httpx, "Client", client)
    assert logs.publish_logs(_settings(), storage=sqlite_storage) == {"raids": 0, "sent": 0, "unreadable": 0}
    assert len(opened) == 1 and opened[0].is_closed


def test_publish_needs_a_service_token(sqlite_storage: Callable[[], PerformanceDB]) -> None:
    with pytest.raises(RuntimeError, match="HUB_SERVICE_TOKEN"):
        logs.publish_logs(_settings(token=""), storage=sqlite_storage)
