"""scripts/import_items.py: LibItemDB's Lua tables into the API's item catalogue (docs/loot.md "Item data")."""

from __future__ import annotations

import gzip
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("import_items", ROOT / "scripts" / "import_items.py")
assert _spec and _spec.loader
import_items = importlib.util.module_from_spec(_spec)
sys.modules["import_items"] = import_items
_spec.loader.exec_module(import_items)

NAMES = """-- LibItemDB names - WoW {flavour}, enUS
if GetLocale() ~= "enUS" then return end
lib:LoadNames({{
{rows}
}})
"""


def _addon(tmp_path: Path) -> Path:
    addon = tmp_path / "ItemDB"
    for flavour, names, core, hidden in (
        (
            "Forever",
            '[19019]="Thunderfury, Blessed Blade of the Windseeker",\n[3041]="\\"Mage-Eye\\" Blunderbuss",\n'
            '[77]="Deprecated Outfitter Cloth Armor",\n[2454]="Elixir of Minor Strength",\n[9]="  Odd   spacing ",',
            'lib:SetBuild(16001)\nlib:LoadCore(2, {\n[19019]="5\\0317\\031INVTYPE_WEAPON\\03180\\031X=1",\n'
            '[3041]="2\\0313\\031INVTYPE_RANGEDRIGHT\\03131\\031",\n[5]="bad",\n})\n',
            "lib:LoadHidden({\n[77]=true,\n})\n",
        ),
        (
            "Vanilla",
            '[17076]="Bonereaver\'s Edge",\n[2454]="Elixir of Lion\'s Strength",\n[10]="Caf\\195\\169 \\x41",',
            'lib:LoadCore(2, {\n[17076]="4\\0318\\031INVTYPE_2HWEAPON\\03177\\031",\n'
            '[2454]="1\\0310\\031\\031x\\031",\n})\n',
            None,
        ),
    ):
        names_dir = addon / "Data" / flavour / "enUS"
        names_dir.mkdir(parents=True)
        (names_dir / "Names.lua").write_text(NAMES.format(flavour=flavour, rows=names), encoding="utf-8")
        core_dir = addon / "Data" / flavour / "_core"
        core_dir.mkdir()
        (core_dir / "Weapon.lua").write_text(core, encoding="utf-8")
        (core_dir / "Talents.lua").write_text("lib:LoadTalents({})\n", encoding="utf-8")
        if hidden:
            (core_dir / "Hidden.lua").write_text(hidden, encoding="utf-8")
    (addon / "ItemDB.toc").write_text("## Interface: 11508\n## Version: ItemDB-v9.9.9\n", encoding="utf-8")
    return addon


def test_unescape_reads_lua_string_escapes() -> None:
    assert import_items.unescape(r"a\"b\\c\nd\031e\x41") == 'a"b\\c\nd\x1feA'
    assert import_items.unescape(r"\q") == "q"


def test_items_merge_flavours_first_wins_and_leave_out_hidden(tmp_path: Path) -> None:
    rows = {i.id: i for i in import_items.merged(_addon(tmp_path), ["Forever", "Vanilla"], "enUS")}
    assert sorted(rows) == [9, 10, 2454, 3041, 17076, 19019]
    assert rows[19019] == import_items.Item(
        19019, "Thunderfury, Blessed Blade of the Windseeker", 5, 2, 7, "INVTYPE_WEAPON", 80, "Forever"
    )
    assert rows[3041].name == '"Mage-Eye" Blunderbuss'
    # Forever's name wins where both have the item; Classic fills what Forever lacks.
    assert (rows[2454].name, rows[2454].flavour, rows[2454].quality) == ("Elixir of Minor Strength", "Forever", -1)
    assert (rows[17076].name, rows[17076].flavour, rows[17076].item_level) == ("Bonereaver's Edge", "Vanilla", 77)
    assert rows[9].name == "Odd spacing"
    assert rows[10].name == "Caf\u00e9 A"


def test_main_writes_a_reproducible_gzipped_tsv(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    addon, out = _addon(tmp_path), tmp_path / "out" / "items.tsv.gz"
    assert import_items.main([str(addon), "--out", str(out)]) == 0
    first = out.read_bytes()
    assert import_items.main([str(addon), "--out", str(out)]) == 0
    assert out.read_bytes() == first
    lines = gzip.decompress(first).decode("utf-8").splitlines()
    assert lines[0] == "# LibItemDB ItemDB-v9.9.9, enUS: 6 items (4 Forever, 2 Vanilla)"
    assert "Pimptasty" in lines[1]
    assert lines[2].split("\t") == [
        "id", "name", "quality", "class_id", "subclass_id", "slot", "item_level", "flavour"
    ]  # fmt: skip
    assert lines[-1] == "19019\tThunderfury, Blessed Blade of the Windseeker\t5\t2\t7\tINVTYPE_WEAPON\t80\tForever"
    assert "Wrote LibItemDB" in capsys.readouterr().out


def test_main_refuses_a_folder_without_the_flavour(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert import_items.main([str(_addon(tmp_path)), "--flavour", "Mists", "--out", str(tmp_path / "x")]) == 1
    assert "No Mists enUS names" in capsys.readouterr().err
    assert import_items.version(tmp_path) == "unknown"
    assert import_items.hidden(tmp_path / "missing.lua") == set()
