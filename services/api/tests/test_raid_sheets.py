"""Raid sheet rules without HTTP: dates, raid-day matching, snapshots, and the worker's .xlsx reader."""

from __future__ import annotations

import io
from datetime import UTC, date, datetime

import pytest
from openpyxl import Workbook
from toads_api.raid_sheets.config import RaidSheetsConfig
from toads_api.raid_sheets.dates import find_date, raid_date_of, weekday_named
from toads_api.raid_sheets.repository import InMemorySheetRepository
from toads_api.raid_sheets.schemas import SheetImport, SheetTable
from toads_api.raid_sheets.service import RaidSheetService, UnknownSource
from toads_worker.jobs.sheets import cell_text, read_tables, spreadsheet_ids

SID = "1ua81-yeWdU1eW4ziHP2EF-1rxrSILbRWjmvZG9eLpkM"
SUN_ONLY = "1OTZF3PHYtx3h_ENlV5cN2aUylnIe7keS-SzFnun_CcU"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2026-09-24", date(2026, 9, 24)),
        ("Wed 24.09.2026", date(2026, 9, 24)),
        ("24.09.26 Kara", date(2026, 9, 24)),
        ("24th September 2026", date(2026, 9, 24)),
        ("Raid: Sept 24, 2026", date(2026, 9, 24)),
        ("31/02/2026", None),  # not a date
        ("Week 3", None),
        ("", None),
    ],
)
def test_find_date(text: str, expected: date | None) -> None:
    assert find_date(text) == expected


def test_raid_date_prefers_tab_name_then_first_rows() -> None:
    assert raid_date_of("2026-09-24", [["20/09/2026"]]) == date(2026, 9, 24)
    assert raid_date_of("Summary", [["Name"], ["Raid", "20/09/2026"]]) == date(2026, 9, 20)
    assert raid_date_of("Summary", [[""]] * 5 + [["20/09/2026"]]) is None


@pytest.mark.parametrize(
    ("name", "expected"), [("Wednesday", 2), ("Sunday raid", 6), ("Sun", 6), ("Wed/Sun", None), ("Main", None)]
)
def test_weekday_named(name: str, expected: int | None) -> None:
    assert weekday_named(name) == expected


def service() -> RaidSheetService:
    config = RaidSheetsConfig.model_validate(
        {
            "sources": [
                {"kind": "cba", "spreadsheet_id": SID},
                {"kind": "rpb", "spreadsheet_id": SUN_ONLY, "raid_day": "sun"},
            ]
        }
    )
    return RaidSheetService(repo=InMemorySheetRepository(), config=config, weekdays={"wed": 2, "sun": 6})


def imp(sid: str, *tabs: SheetTable, at: datetime = datetime(2026, 9, 25, tzinfo=UTC)) -> SheetImport:
    return SheetImport(spreadsheet_id=sid, fetched_at=at, tables=list(tabs))


def test_weekday_decides_the_raid_day_unless_the_source_names_one() -> None:
    svc = service()
    svc.record_import(imp(SID, SheetTable(tab="2026-09-23", headers=["a"], rows=[])))
    svc.record_import(imp(SUN_ONLY, SheetTable(tab="2026-09-23", headers=["a"], rows=[])))
    assert [s.kind for s in svc.for_raid("wed", date(2026, 9, 23)).sheets] == ["cba"]
    assert [s.kind for s in svc.for_raid("sun", date(2026, 9, 23)).sheets] == ["rpb"]


def test_a_date_on_no_raid_day_is_undated() -> None:
    result = service().record_import(imp(SID, SheetTable(tab="2026-09-21", headers=["a"], rows=[])))
    assert result.undated == ["2026-09-21"]


def test_unknown_spreadsheet_is_refused() -> None:
    with pytest.raises(UnknownSource):
        service().record_import(imp("9" * 44, SheetTable(tab="x", headers=["a"], rows=[])))


def test_newest_snapshot_wins_and_history_is_kept() -> None:
    svc = service()
    t = "2026-09-23"
    svc.record_import(imp(SID, SheetTable(tab=t, headers=["a"], rows=[["1"]])))
    svc.record_import(imp(SID, SheetTable(tab=t, headers=["a"], rows=[["2"]]), at=datetime(2026, 9, 26, tzinfo=UTC)))
    [link] = svc.for_raid("wed", date(2026, 9, 23)).sheets
    assert svc.snapshot("wed", link.snapshot_id).table.rows == [["2"]]
    repo = svc.repo
    assert isinstance(repo, InMemorySheetRepository)
    assert len(repo.snapshots) == 2


def test_cell_text() -> None:
    assert cell_text(None) == ""
    assert cell_text(3.0) == "3"
    assert cell_text(3.5) == "3.5"
    assert cell_text(datetime(2026, 9, 24)) == "2026-09-24"
    assert cell_text(date(2026, 9, 23)) == "2026-09-23"
    assert cell_text("x" * 900) == "x" * 500


def test_read_tables_uses_first_non_empty_row_as_headers() -> None:
    book = Workbook()
    sheet = book.active
    assert sheet is not None
    sheet.title = "Wed 24.09.2026"
    sheet.append([])
    sheet.append(["Player", "Score", None])
    sheet.append(["Hopscotch", 92.0])
    sheet.append([None, None])
    sheet.append(["Ribbit", 88.5])
    book.create_sheet("Empty")
    buf = io.BytesIO()
    book.save(buf)
    assert list(read_tables(buf.getvalue())) == [
        {"tab": "Wed 24.09.2026", "headers": ["Player", "Score"], "rows": [["Hopscotch", "92"], ["Ribbit", "88.5"]]}
    ]


def test_spreadsheet_ids_from_the_example_config() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    assert spreadsheet_ids(root / "config" / "raid_sheets.example.yaml") == [SID, SUN_ONLY]
    assert RaidSheetsConfig.load(root / "config" / "raid_sheets.example.yaml").source(SID) is not None
