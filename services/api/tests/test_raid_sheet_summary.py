"""CBA and RPB numbers for the home page, secret scrubbing, and linking an undated RPB to its CBA raid."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import pytest
from toads_api.raid_sheets.config import RaidSheetsConfig
from toads_api.raid_sheets.repository import InMemorySheetRepository
from toads_api.raid_sheets.schemas import SheetImport
from toads_api.raid_sheets.service import RaidSheetService
from toads_api.raid_sheets.summary import ClearTime, clear_times, summarise, to_fraction, to_int
from toads_api.raid_sheets.tabs import REDACTED, keeps, redact, report_code
from toads_api.testing.raid_sheet_samples import REPORT, WEBHOOK, cba_tabs, rpb_tabs

CBA = "1ua81-yeWdU1eW4ziHP2EF-1rxrSILbRWjmvZG9eLpkM"
RPB = "1OTZF3PHYtx3h_ENlV5cN2aUylnIe7keS-SzFnun_CcU"


def grids(tabs: list[dict[str, Any]]) -> dict[str, list[list[str]]]:
    return {t["tab"].lower(): [t["headers"], *t["rows"]] for t in tabs}


@pytest.mark.parametrize(
    ("text", "expected"), [("22 (⌀ 2.36)", 22), ("6 (0)", 6), ("274846.0", 274846), ("1,204", 1204), ("-", None)]
)
def test_to_int(text: str, expected: int | None) -> None:
    assert to_int(text) == expected


@pytest.mark.parametrize(("text", "expected"), [("0.94", 0.94), ("1", 1.0), ("94%", 0.94), ("-", None), ("3", None)])
def test_to_fraction(text: str, expected: float | None) -> None:
    assert to_fraction(text) == expected


def test_clear_times_from_the_title() -> None:
    assert clear_times("BT / Hyjal (BT in 1:48:32, MH in 1:08:40)") == [ClearTime("BT", 6512), ClearTime("MH", 4120)]
    assert clear_times("Kara (Kara in 45:10)") == [ClearTime("Kara", 2710)]
    assert clear_times("Gruul's Lair") == []


def test_setup_tabs_are_dropped_unless_listed() -> None:
    assert not keeps("Instructions", None)
    assert not keeps("shadow resistance config", None)
    assert keeps("buff consumables", None)
    assert keeps("Caster - Sunday BT", ["caster*"])
    assert not keeps("Instructions", ["buff consumables"])


def test_webhooks_and_emails_are_blanked() -> None:
    assert redact(f"post to {WEBHOOK} please") == f"post to {REDACTED} please"
    assert redact("maag.lars+cla@gmail.com") == REDACTED
    assert redact("Rocket Boots Xtreme [no enchant]") == "Rocket Boots Xtreme [no enchant]"


def test_report_code_from_the_instructions_url() -> None:
    assert report_code(["", "https://fresh.warcraftlogs.com/reports/2bNJMG9AfDnmxKYh"]) == "2bNJMG9AfDnmxKYh"
    assert report_code(["https://classic.warcraftlogs.com/profile"]) is None


def test_summary_of_a_raid() -> None:
    s = summarise("wed", "2026-09-23", grids(cba_tabs()), grids(rpb_tabs()), REPORT)
    h = s.headline
    assert (h.title, h.zone, h.report_code) == ("BT / Hyjal (BT in 1:48:32, MH in 1:08:40)", "Black Temple", REPORT)
    assert (h.log_valid, h.characters) == (True, 25)
    assert [c.seconds for c in h.clear_times] == [6512, 4120]
    assert h.consumables_avg == pytest.approx((0.9433333333 + 0.74) / 2, abs=1e-4)
    assert h.low_consumables == ["Ribbit"]
    assert (h.gear_issues, h.players_with_gear_issues) == (2, 1)
    assert h.drums == 25
    # Haste and Super Mana potions, not drums or the shadow protection potion under "Damage absorbed".
    assert h.potions == 16
    assert (h.interrupts, h.deaths, h.avoidable_damage) == (4, 9, 354953)
    by_name = {p.name: p for p in s.players}
    assert list(by_name) == ["Hopscotch", "Ribbit"]  # Croak has no numbers anywhere
    hop, rib = by_name["Hopscotch"], by_name["Ribbit"]
    assert (hop.role, hop.gear_issues, hop.potions, hop.deaths, hop.avoidable_damage) == ("tank", 2, 9, 3, 274846)
    assert (rib.role, rib.gear_issues, rib.drums, rib.deaths) == ("caster", 0, 25, 6)


def test_summary_of_missing_tabs_is_empty_not_an_error() -> None:
    h = summarise("wed", "2026-09-23", {}, {}).headline
    assert (h.title, h.consumables_avg, h.gear_issues, h.deaths, h.clear_times) == (None, None, None, None, [])


def service() -> RaidSheetService:
    config = RaidSheetsConfig.model_validate(
        {
            "sources": [
                {"kind": "cba", "spreadsheet_id": CBA},
                {"kind": "rpb", "spreadsheet_id": RPB, "follows": "cba"},
            ]
        }
    )
    return RaidSheetService(repo=InMemorySheetRepository(), config=config, weekdays={"wed": 2, "sun": 6})


def imp(sid: str, tabs: list[dict[str, Any]], day: int) -> SheetImport:
    return SheetImport.model_validate(
        {"spreadsheet_id": sid, "fetched_at": datetime(2026, 9, day, 9, tzinfo=UTC), "tables": tabs}
    )


def test_import_drops_setup_tabs_and_keeps_the_report_code() -> None:
    svc = service()
    result = svc.record_import(imp(CBA, cba_tabs(), 24))
    assert result.skipped == ["Instructions"]
    assert sorted(result.stored) == ["buff consumables", "drums", "gear issues", "validate"]
    raid = svc.for_raid("wed", date(2026, 9, 23))
    assert raid.report_code == REPORT
    repo = svc.repo
    assert isinstance(repo, InMemorySheetRepository)
    stored = " ".join(c for s in repo.snapshots.values() for row in s.table.rows for c in row)
    assert "discord.com/api/webhooks" not in stored and "@example.com" not in stored


def test_an_undated_rpb_joins_the_latest_cba_raid() -> None:
    svc = service()
    svc.record_import(imp(CBA, cba_tabs(), 24))
    result = svc.record_import(imp(RPB, rpb_tabs(), 25))
    assert sorted(result.stored) == ["Caster", "Caster - casts", "General", "Tank"]
    raid = svc.for_raid("wed", date(2026, 9, 23))
    assert sorted({s.kind.value for s in raid.sheets}) == ["cba", "rpb"]
    # Downloaded again unchanged: still on the same raid, nothing new stored.
    assert svc.record_import(imp(RPB, rpb_tabs(), 26)).unchanged == ["General", "Tank", "Caster", "Caster - casts"]
    summary = svc.summary("wed", date(2026, 9, 23))
    assert (summary.headline.report_code, summary.headline.deaths) == (REPORT, 9)
    assert [h.raid_date for h in svc.trend()] == ["2026-09-23"]


def test_an_rpb_regenerated_before_its_cba_waits_for_it() -> None:
    svc = service()
    svc.record_import(imp(CBA, cba_tabs("September 16, 2026 19:30:00"), 17))
    svc.record_import(imp(RPB, rpb_tabs(), 18))
    # A new RPB arrives before the new CBA: the 16th already has an RPB, so it waits undated.
    result = svc.record_import(imp(RPB, rpb_tabs(extra_potion="7"), 24))
    assert result.undated == ["General"]
    assert svc.summary("wed", date(2026, 9, 16)).headline.potions == 16
    svc.record_import(imp(CBA, cba_tabs("September 23, 2026 19:30:00"), 25))
    assert svc.summary("wed", date(2026, 9, 23)).headline.potions == 23
    assert svc.summary("wed", date(2026, 9, 16)).headline.potions == 16
    assert [h.raid_date for h in svc.trend()] == ["2026-09-23", "2026-09-16"]


def test_an_rpb_long_after_the_last_cba_stays_undated() -> None:
    svc = service()
    svc.record_import(imp(CBA, cba_tabs("September 2, 2026 19:30:00"), 3))
    assert svc.record_import(imp(RPB, rpb_tabs(), 24)).undated == ["General", "Tank", "Caster", "Caster - casts"]
