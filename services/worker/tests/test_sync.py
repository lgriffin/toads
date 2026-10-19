"""The guild-report sync (REQ-DEV-OPS-004): new guild reports analysed in batches, newest first."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import requests
from pydantic import SecretStr
from pytest_bdd import given, parsers, scenario, then, when
from toads_worker.jobs import sync
from toads_worker.settings import Settings

FEATURES = Path(__file__).resolve().parents[3] / "tests" / "features"


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "database_url": SecretStr("postgresql+psycopg://u:p@localhost/db"),
        "redis_url": "redis://localhost",
        "wcl_client_id": "id",
        "wcl_client_secret": SecretStr("replace-me"),
        "wcl_guild_id": 1,
        "credentials_keys": SecretStr("replace-me"),
    }
    values.update(overrides)
    return Settings(**values)


class FakeRaids:
    """Stands in for wcl_app.RaidService: the guild's reports newest first, the stored codes and the analyses run.

    Each analysis spends `cost` points of the key's rate limit, which FakeBudget reads."""

    def __init__(self, remote: list[str], stored: set[str], broken: set[str] | None = None, cost: float = 0) -> None:
        self.remote = remote
        self.stored = set(stored)
        self.broken = broken or set()
        self.analysed: list[str] = []
        self.guilds: list[int] = []
        self.cost = cost
        self.spent = 0.0
        self.rate_limited: set[str] = set()

    def guild_reports(self, guild_id: int) -> list[dict[str, Any]]:
        self.guilds.append(guild_id)
        return [{"code": code} for code in self.remote]

    def imported_codes(self) -> set[str]:
        return set(self.stored)

    def analyze_and_save(self, report_id: str, *, progress: Any = None) -> object:
        self.analysed.append(report_id)
        self.spent += self.cost
        if report_id in self.rate_limited:
            raise requests.HTTPError("429 Too Many Requests", response=_response(429))
        if report_id in self.broken:
            raise RuntimeError(f"{report_id} has no fights")
        self.stored.add(report_id)
        return object()


def _response(status: int) -> requests.Response:
    response = requests.Response()
    response.status_code = status
    return response


class FakeBudget:
    """The key's rate limit: `limit` points an hour, of which the raids have spent theirs. None reads as unreadable."""

    def __init__(self, raids: FakeRaids, limit: float | None = 1000.0, start: float = 0.0) -> None:
        self.raids = raids
        self.limit = limit
        self.start = start
        self.readings = 0
        # From this reading on (counting from 1), the hour has reset; or the rate limit stops answering.
        self.reset_at: int | None = None
        self.unreadable_at: int | None = None

    def read(self) -> sync.RateLimit | None:
        self.readings += 1
        if self.limit is None or (self.unreadable_at is not None and self.readings >= self.unreadable_at):
            return None
        spent = self.start + self.raids.spent
        if self.reset_at is not None and self.readings >= self.reset_at:
            spent = 0.0
        return sync.RateLimit(self.limit, spent, 1800.0)


def _sync(settings: Settings, raids: FakeRaids, budget: FakeBudget | None = None) -> dict[str, Any]:
    return sync.sync_guild_reports(settings, raids=raids, budget=budget or FakeBudget(raids))


def test_new_report_codes_keep_the_order_given() -> None:
    assert sync.new_report_codes(["c", "b", "c", "a"], ["b"]) == ["c", "a"]


def test_sync_imports_everything_new_newest_first_when_it_fits_one_batch() -> None:
    raids = FakeRaids(["A", "B", "C"], stored=set(), cost=10)
    result = _sync(_settings(wcl_guild_id=42), raids)
    assert raids.analysed == ["A", "B", "C"]
    assert raids.guilds == [42]
    assert result == {"imported": ["A", "B", "C"], "failed": {}, "remaining": 0, "stopped": "done", "points_left": 770}


def test_reports_that_never_analyse_do_not_hold_back_older_ones() -> None:
    raids = FakeRaids(["A", "B", "C", "D"], stored=set(), broken={"A"})
    for _ in range(3):
        _sync(_settings(sync_batch=1), raids)
    assert raids.stored == {"B", "C", "D"}


def test_a_run_stops_after_twice_the_batch_in_attempts() -> None:
    raids = FakeRaids(["A", "B", "C", "D", "E"], stored=set(), broken={"A", "B", "C", "D", "E"})
    result = _sync(_settings(sync_batch=2), raids)
    assert raids.analysed == ["A", "B", "C", "D"]
    assert result["imported"] == [] and result["remaining"] == 5 and result["stopped"] == "batch"


def test_sync_with_nothing_new_analyses_nothing() -> None:
    raids = FakeRaids(["A"], stored={"A"})
    assert _sync(_settings(), raids) == {
        "imported": [],
        "failed": {},
        "remaining": 0,
        "stopped": "done",
        "points_left": 800,
    }
    assert raids.analysed == []


def test_sync_needs_a_guild_id() -> None:
    with pytest.raises(ValueError, match="TOADS_WCL_GUILD_ID"):
        _sync(_settings(wcl_guild_id=0), FakeRaids([], set()))


def _ops_scenario(number: int) -> Any:
    """Bind REQ-DEV-OPS-<nnn> from dev_ops.feature (the id is built, not written out)."""
    req_id = f"REQ-DEV-OPS-{number:03d}"
    for line in (FEATURES / "dev_ops.feature").read_text(encoding="utf-8").splitlines():
        m = re.match(rf"\s*Scenario: ({req_id} .*)$", line)
        if m:
            return scenario(str(FEATURES / "dev_ops.feature"), m.group(1))
    raise LookupError(req_id)


@_ops_scenario(4)
def test_ops_004() -> None:
    pass


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


@given(parsers.parse('the guild\'s reports on Warcraft Logs are "{codes}", newest first, and "{stored}" is stored'))
def guild_reports(ctx: dict[str, Any], codes: str, stored: str) -> None:
    ctx["raids"] = FakeRaids([c.strip() for c in codes.split(",")], stored={stored})


@given(parsers.parse('"{code}" fails to analyse'))
def broken_report(ctx: dict[str, Any], code: str) -> None:
    ctx["raids"].broken.add(code)


@when(parsers.parse("the sync runs with a batch of {batch:d}"))
def run_sync(ctx: dict[str, Any], batch: int) -> None:
    ctx["result"] = _sync(_settings(sync_batch=batch), ctx["raids"])


@then(parsers.parse('"{ok}" are stored, "{bad}" is listed as failed and {left:d} report is left for the next run'))
def sync_result(ctx: dict[str, Any], ok: str, bad: str, left: int) -> None:
    result, raids = ctx["result"], ctx["raids"]
    stored = [c.strip() for c in ok.split(",")]
    assert raids.analysed == [bad, *stored]  # newest first; the next older report took the failed one's place
    assert set(stored) <= raids.stored and bad not in raids.stored
    assert result["imported"] == stored
    assert list(result["failed"]) == [bad]
    assert result["remaining"] == left


@_ops_scenario(5)
def test_ops_005() -> None:
    pass


@given(
    parsers.parse(
        "the guild key may spend {limit:d} Warcraft Logs points an hour, {reserve:d} percent of them kept in reserve"
    )
)
def rate_limit(ctx: dict[str, Any], limit: int, reserve: int) -> None:
    ctx["limit"], ctx["reserve"] = limit, reserve


@given(parsers.parse("{count:d} new guild reports that cost {cost:d} points each"))
def costly_reports(ctx: dict[str, Any], count: int, cost: int) -> None:
    ctx["raids"] = FakeRaids([f"R{i}" for i in range(count)], stored=set(), cost=cost)


@when("the sync runs with no batch set")
def run_unbatched(ctx: dict[str, Any]) -> None:
    raids = ctx["raids"]
    settings = _settings(sync_reserve_percent=ctx["reserve"])
    ctx["result"] = _sync(settings, raids, FakeBudget(raids, limit=ctx["limit"]))


@then(parsers.parse("{count:d} reports are stored and the run stops on the rate-limit budget"))
def stopped_on_budget(ctx: dict[str, Any], count: int) -> None:
    assert len(ctx["raids"].stored) == count
    assert ctx["result"]["stopped"] == "rate_limit_budget"


def test_with_no_batch_the_rate_limit_alone_decides() -> None:
    raids = FakeRaids([f"R{i}" for i in range(40)], stored=set(), cost=20)
    result = _sync(_settings(), raids)
    # 800 points free: 39 reports at 20 bring it to 20 left, which no longer covers a 20-point report.
    assert len(result["imported"]) == 39 and result["stopped"] == "rate_limit_budget" and result["points_left"] == 20


def test_an_hour_already_spent_imports_nothing() -> None:
    raids = FakeRaids(["A"], stored=set(), cost=5)
    result = _sync(_settings(), raids, FakeBudget(raids, start=850))
    assert raids.analysed == [] and result["stopped"] == "rate_limit_budget" and result["remaining"] == 1


def test_a_set_batch_still_caps_the_run_under_the_budget() -> None:
    raids = FakeRaids(["A", "B", "C"], stored=set(), cost=1)
    assert _sync(_settings(sync_batch=2), raids)["imported"] == ["A", "B"]


def test_an_unreadable_rate_limit_falls_back_to_a_fixed_batch() -> None:
    raids = FakeRaids([f"R{i}" for i in range(15)], stored=set())
    result = _sync(_settings(), raids, FakeBudget(raids, limit=None))
    assert len(result["imported"]) == sync.FALLBACK_BATCH and result["stopped"] == "batch"
    assert result["points_left"] is None


def test_a_run_stops_when_the_rate_limit_stops_answering() -> None:
    raids = FakeRaids(["A", "B", "C"], stored=set(), cost=1)
    budget = FakeBudget(raids)
    budget.unreadable_at = 2
    result = _sync(_settings(), raids, budget)
    assert result["imported"] == ["A"] and result["stopped"] == "rate_limit_unknown"


def test_a_run_stops_when_the_hour_resets_so_the_publish_jobs_get_a_turn() -> None:
    raids = FakeRaids(["A", "B", "C"], stored=set(), cost=1)
    budget = FakeBudget(raids, start=500)
    budget.reset_at = 3
    result = _sync(_settings(), raids, budget)
    assert result["imported"] == ["A", "B"] and result["stopped"] == "rate_limit_reset"


def test_a_429_ends_the_run_without_marking_the_report_failed() -> None:
    raids = FakeRaids(["A", "B"], stored=set())
    raids.rate_limited.add("A")
    result = _sync(_settings(), raids)
    assert raids.analysed == ["A"] and result["failed"] == {} and result["stopped"] == "rate_limited"
    assert result["remaining"] == 2


class FakeClient:
    def __init__(self, answer: dict[str, Any] | Exception) -> None:
        self.answer = answer
        self.queries: list[tuple[str, bool]] = []

    def run_query(self, query: str, use_cache: bool = True, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        self.queries.append((query, use_cache))
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


def test_wcl_budget_reads_the_api_rate_limit_uncached() -> None:
    client = FakeClient(
        {"data": {"rateLimitData": {"limitPerHour": 18000, "pointsSpentThisHour": 12.5, "pointsResetIn": 900}}}
    )
    reading = sync.WclBudget(client).read()  # type: ignore[arg-type]
    assert reading == sync.RateLimit(18000.0, 12.5, 900.0)
    assert client.queries == [(sync.RATE_LIMIT_QUERY, False)]
    assert reading.allowance(20) == 14387.5


@pytest.mark.parametrize("answer", [requests.ConnectionError("down"), {"errors": [{"message": "no"}]}])
def test_wcl_budget_answers_none_when_it_cannot_read(answer: dict[str, Any] | Exception) -> None:
    assert sync.WclBudget(FakeClient(answer)).read() is None  # type: ignore[arg-type]


@_ops_scenario(6)
def test_ops_006() -> None:
    pass


class HourlyBudget(FakeBudget):
    """A rate limit whose hour resets each time the backfill sleeps."""

    def __init__(self, raids: FakeRaids, limit: float) -> None:
        super().__init__(raids, limit=limit)
        self.waits: list[float] = []

    def sleep(self, seconds: float) -> None:
        self.waits.append(seconds)
        self.start = -self.raids.spent


@given("the third oldest of them fails to analyse")
def third_oldest_broken(ctx: dict[str, Any]) -> None:
    raids = ctx["raids"]
    raids.remote.reverse()  # FullHistory lists oldest first; the fake lists in the order given
    raids.broken.add(raids.remote[2])


@when("the backfill runs")
def run_backfill(ctx: dict[str, Any]) -> None:
    raids = ctx["raids"]
    budget = HourlyBudget(raids, limit=ctx["limit"])
    settings = _settings(sync_reserve_percent=ctx["reserve"])
    ctx["budget"] = budget
    ctx["result"] = sync.backfill_guild_reports(settings, raids=raids, budget=budget, sleep=budget.sleep)


@then(
    parsers.parse(
        "the other {count:d} reports are stored, oldest first, "
        "after waiting for the rate limit to reset {waits:d} times"
    )
)
def backfilled(ctx: dict[str, Any], count: int, waits: int) -> None:
    raids, result = ctx["raids"], ctx["result"]
    broken = raids.remote[2]
    assert raids.stored == set(raids.remote) - {broken} and len(raids.stored) == count
    assert [c for c in raids.analysed if c != broken] == [c for c in raids.remote if c != broken]
    assert list(result["failed"]) == [broken] and result["remaining"] == 1 and result["imported"] == count
    assert ctx["budget"].waits == [1805.0] * waits


def test_backfill_waits_a_default_time_when_the_reset_is_unknown() -> None:
    raids = FakeRaids(["A", "B"], stored=set(), cost=1)
    budget = FakeBudget(raids)
    budget.unreadable_at = 2
    waits: list[float] = []

    def sleep(seconds: float) -> None:
        waits.append(seconds)
        budget.unreadable_at = None

    result = sync.backfill_guild_reports(_settings(), raids=raids, budget=budget, sleep=sleep)
    assert waits == [sync.UNKNOWN_RESET_WAIT_SECONDS] and result["imported"] == 2 and result["remaining"] == 0


def test_full_history_lists_every_report_oldest_first() -> None:
    class Client:
        def get_guild_reports(self, guild_id: int, total: int = 350) -> list[dict[str, Any]]:
            assert (guild_id, total) == (7, sync.ALL_REPORTS)
            return [{"code": "new"}, {"code": "old"}]

    service = FakeRaids([], stored={"x"})
    history = sync.FullHistory(service, Client())  # type: ignore[arg-type]
    assert [r["code"] for r in history.guild_reports(7)] == ["old", "new"]
    assert history.imported_codes() == {"x"}
    history.analyze_and_save("old")
    assert service.analysed == ["old"]


def test_raid_service_is_the_analyzers_on_the_guild_key() -> None:
    from wcl_app import RaidService

    assert isinstance(sync.raid_service(_settings()), RaidService)
