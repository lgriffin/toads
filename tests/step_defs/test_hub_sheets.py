"""REQ-HUB-SHEET: the CBA and RPB Google Sheets, imported read-only and attached to raids."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import Any

import pytest
from hub_db import RaidSheetSnapshot
from pytest_bdd import given, parsers, scenarios, then, when
from sqlalchemy import func, select
from toads_api.raid_sheets.config import RaidSheetsConfig
from toads_api.testing.raid_sheet_samples import REPORT, cba_tabs, rpb_tabs
from toads_worker.jobs import sheets as worker_sheets

from conftest import Hub

scenarios(str(Path(__file__).resolve().parent.parent / "features" / "hub_sheet.feature"))

CBA = "1ua81-yeWdU1eW4ziHP2EF-1rxrSILbRWjmvZG9eLpkM"
RPB = "1OTZF3PHYtx3h_ENlV5cN2aUylnIe7keS-SzFnun_CcU"
UNKNOWN = "1" + "x" * 43
TOKEN = "test-service-token"  # noqa: S105  (conftest.make_settings)
WORKER = {"Authorization": f"Bearer {TOKEN}"}
HEADERS = ["Player", "Class", "Score"]
ROWS = [["Hopscotch", "Druid", "92"], ["Ribbit", "Mage", "88"]]


def configure(hub: Hub) -> None:
    svc = hub.services.raid_sheets
    svc.config = RaidSheetsConfig.model_validate(
        {"sources": [{"kind": "cba", "spreadsheet_id": CBA}, {"kind": "rpb", "spreadsheet_id": RPB}]}
    )


def post_import(
    hub: Hub,
    sid: str,
    tabs: list[dict[str, Any]],
    headers: dict[str, str] | None = WORKER,
    fetched_at: str = "2026-09-25T09:00:00Z",
) -> Any:
    body = {"spreadsheet_id": sid, "fetched_at": fetched_at, "tables": tabs}
    return hub.client.post("/api/worker/raid-sheets", json=body, headers=headers or {})


def tab(name: str, rows: list[list[str]] = ROWS, headers: list[str] = HEADERS) -> dict[str, Any]:
    return {"tab": name, "headers": headers, "rows": rows}


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


@pytest.fixture
def member(hub: Hub) -> str:
    return hub.login(hub.user())


@given("the Toads raid sheets are configured")
def configured(hub: Hub) -> None:
    configure(hub)


@when(parsers.parse('the worker imports the CBA sheet with a tab named "{name}"'))
@given(parsers.parse('the worker imported the CBA sheet with a tab named "{name}"'))
def import_cba(hub: Hub, ctx: dict[str, Any], name: str) -> None:
    ctx["tab"] = name
    r = post_import(hub, CBA, [tab(name)])
    assert r.status_code == 200, r.text
    ctx["result"] = r.json()


@then(parsers.parse('the Wednesday raid on {when} shows the CBA tab "{name}"'))
def raid_shows(hub: Hub, member: str, ctx: dict[str, Any], when: str, name: str) -> None:
    r = hub.get(f"/api/days/wed/raids/{when}/sheets", member)
    assert r.status_code == 200, r.text
    [link] = r.json()["sheets"]
    assert (link["kind"], link["tab"]) == ("cba", name)
    ctx["link"] = link
    rows = hub.get(f"/api/days/wed/sheets/{link['snapshot_id']}", member).json()["table"]["rows"]
    assert rows == ROWS
    # Scoped to the day in the path: the same id is missing on Sunday.
    assert hub.get(f"/api/days/sun/sheets/{link['snapshot_id']}", member).status_code == 404


@then("the tab links to the CBA spreadsheet on Google Sheets")
def links_to_sheet(ctx: dict[str, Any]) -> None:
    assert ctx["link"]["url"] == f"https://docs.google.com/spreadsheets/d/{CBA}/edit"


@when("the worker imports the same tab again unchanged")
def import_again(hub: Hub, ctx: dict[str, Any]) -> None:
    ctx["result"] = post_import(hub, CBA, [tab(ctx["tab"])]).json()


@then("the import reports the tab as unchanged")
def reported_unchanged(ctx: dict[str, Any]) -> None:
    assert ctx["result"] == {"stored": [], "unchanged": [ctx["tab"]], "undated": [], "skipped": []}


@when("the worker imports the tab with one more row")
def import_changed(hub: Hub, ctx: dict[str, Any]) -> None:
    ctx["result"] = post_import(hub, CBA, [tab(ctx["tab"], [*ROWS, ["Croak", "Warrior", "75"]])]).json()


@then("the raid shows the newer version and both versions are stored")
def newest_shown(hub: Hub, member: str, ctx: dict[str, Any]) -> None:
    assert ctx["result"]["stored"] == [ctx["tab"]]
    [link] = hub.get("/api/days/wed/raids/2026-09-23/sheets", member).json()["sheets"]
    rows = hub.get(f"/api/days/wed/sheets/{link['snapshot_id']}", member).json()["table"]["rows"]
    assert rows[-1] == ["Croak", "Warrior", "75"]
    with hub.db() as db:
        assert db.scalar(select(func.count()).select_from(RaidSheetSnapshot)) == 2


@when(parsers.parse('the worker imports the RPB sheet with a tab named "{name}" and no dates'))
def import_undated(hub: Hub, ctx: dict[str, Any], name: str) -> None:
    ctx["result"] = post_import(hub, RPB, [tab(name)]).json()


@then(parsers.parse('the import reports "{name}" as undated'))
def reported_undated(ctx: dict[str, Any], name: str) -> None:
    assert ctx["result"]["undated"] == [name]


@then("no raid shows it")
def no_raid(hub: Hub, member: str) -> None:
    assert hub.get("/api/raid-sheets/recent", member).json() == []


@then("an import without the service token is refused with 401")
def refused_without_token(hub: Hub) -> None:
    assert post_import(hub, CBA, [tab("Wed 23/09/2026")], headers=None).status_code == 401
    bad = {"Authorization": "Bearer not-the-token"}
    assert post_import(hub, CBA, [tab("Wed 23/09/2026")], headers=bad).status_code == 401


@then("an import of an unconfigured spreadsheet is refused with 422")
def refused_unknown(hub: Hub) -> None:
    assert post_import(hub, UNKNOWN, [tab("Wed 23/09/2026")]).status_code == 422


@given("the worker imported sheets for the Sunday raid on 2026-09-20 and the Wednesday raid on 2026-09-23")
def two_raids(hub: Hub) -> None:
    # One tab dated by its name, one by a date cell in its first rows; the raid day follows from the weekday.
    assert post_import(hub, RPB, [tab("RPB", rows=[["Raid date", "20 Sep 2026"], *ROWS])]).status_code == 200
    assert post_import(hub, CBA, [tab("2026-09-23")]).status_code == 200


@then("a member sees the 2026-09-23 raid listed before the 2026-09-20 raid")
def listed_newest_first(hub: Hub, member: str) -> None:
    recent = hub.get("/api/raid-sheets/recent", member).json()
    assert [(r["raid_day"], r["raid_date"]) for r in recent] == [("wed", "2026-09-23"), ("sun", "2026-09-20")]
    assert [s["kind"] for s in recent[0]["sheets"]] == ["cba"]
    assert hub.get("/api/raid-sheets/recent", None).status_code == 401


@then("the raid sheet importer only reads from Google Sheets")
def importer_read_only() -> None:
    tree = ast.parse(inspect.getsource(worker_sheets))
    google_calls = [
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "http"
        and node.args
        and isinstance(node.args[0], ast.Constant)
    ]
    assert google_calls == ["GET"]
    assert worker_sheets.EXPORT_URL.startswith("https://docs.google.com/spreadsheets/d/")


# REQ-HUB-SHEET-007..009: the real sheets' layout (toads_api.testing.raid_sheet_samples).
SEP_23 = "September 23, 2026 19:32:26"


@given("the Toads raid sheets are configured with RPB following CBA")
def configured_following(hub: Hub) -> None:
    hub.services.raid_sheets.config = RaidSheetsConfig.model_validate(
        {
            "sources": [
                {"kind": "cba", "spreadsheet_id": CBA},
                {"kind": "rpb", "spreadsheet_id": RPB, "follows": "cba"},
            ]
        }
    )


@when("the worker imports the CBA sheet for the 2026-09-23 raid with its Instructions tab")
@given("the worker imported the CBA sheet for the 2026-09-23 raid")
def import_real_cba(hub: Hub, ctx: dict[str, Any]) -> None:
    r = post_import(hub, CBA, cba_tabs(SEP_23), fetched_at="2026-09-24T09:00:00Z")
    assert r.status_code == 200, r.text
    ctx["result"] = r.json()


@when("the worker imports the RPB sheet")
def import_real_rpb(hub: Hub, ctx: dict[str, Any]) -> None:
    r = post_import(hub, RPB, rpb_tabs(), fetched_at="2026-09-25T09:00:00Z")
    assert r.status_code == 200, r.text
    ctx["result"] = r.json()


@given("the worker imported the CBA and RPB sheets for the 2026-09-23 raid")
def import_both(hub: Hub, ctx: dict[str, Any]) -> None:
    import_real_cba(hub, ctx)
    import_real_rpb(hub, ctx)


@then("the import skips the Instructions tab")
def skips_instructions(ctx: dict[str, Any]) -> None:
    assert ctx["result"]["skipped"] == ["Instructions"]


@then("no stored tab holds the webhook or the e-mail address")
def nothing_secret(hub: Hub) -> None:
    with hub.db() as db:
        snaps = db.scalars(select(RaidSheetSnapshot)).all()
    cells = " ".join(c for s in snaps for row in [s.headers, *s.rows] for c in row)
    assert snaps and "Instructions" not in {s.tab for s in snaps}
    assert "discord.com/api/webhooks" not in cells and "runner@example.com" not in cells


@then("the 2026-09-23 raid names the Warcraft Logs report the CBA sheet was run for")
def names_report(hub: Hub, member: str) -> None:
    assert hub.get("/api/days/wed/raids/2026-09-23/sheets", member).json()["report_code"] == REPORT


@then("the 2026-09-23 raid shows both the CBA and the RPB tabs")
def shows_both(hub: Hub, member: str) -> None:
    sheets = hub.get("/api/days/wed/raids/2026-09-23/sheets", member).json()["sheets"]
    assert {s["kind"] for s in sheets} == {"cba", "rpb"}
    assert {s["tab"] for s in sheets if s["kind"] == "rpb"} == {"General", "Tank", "Caster", "Caster - casts"}


@then("a member sees the 2026-09-23 raid's clear times, consumable uptime, gear issues and deaths")
def sees_totals(hub: Hub, member: str, ctx: dict[str, Any]) -> None:
    r = hub.get("/api/days/wed/raids/2026-09-23/sheets/summary", member)
    assert r.status_code == 200, r.text
    ctx["summary"] = r.json()
    head = ctx["summary"]["headline"]
    assert head["clear_times"] == [{"zone": "BT", "seconds": 6512}, {"zone": "MH", "seconds": 4120}]
    assert head["low_consumables"] == ["Ribbit"]
    assert (head["gear_issues"], head["drums"], head["potions"], head["deaths"]) == (2, 25, 16, 9)
    assert head["report_code"] == REPORT
    # Scoped to the raid day in the path, like the sheets themselves.
    assert hub.get("/api/days/wed/raids/2026-09-23/sheets/summary", None).status_code == 401


@then("a member sees each player's line for the 2026-09-23 raid")
def sees_players(ctx: dict[str, Any]) -> None:
    players = {p["name"]: p for p in ctx["summary"]["players"]}
    assert set(players) == {"Hopscotch", "Ribbit"}
    assert (players["Hopscotch"]["role"], players["Hopscotch"]["avoidable_damage"]) == ("tank", 274846)


@then("a member sees the 2026-09-23 raid in the home page trend")
def sees_trend(hub: Hub, member: str) -> None:
    trend = hub.get("/api/raid-sheets/trend", member).json()
    assert [(t["raid_day"], t["raid_date"], t["interrupts"]) for t in trend] == [("wed", "2026-09-23", 4)]
