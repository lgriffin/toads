"""Build the hub's item catalogue from LibItemDB (docs/loot.md "Item data").

    uv run python scripts/import_items.py path/to/ItemDB            # the unzipped addon folder
    uv run python scripts/import_items.py path/to/ItemDB --flavour Forever --flavour Vanilla --locale enUS

LibItemDB (https://www.curseforge.com/wow/addons/libitemdb, MIT, (c) Pimptasty) ships every item of a WoW flavour as
Lua tables: `Data/<flavour>/<locale>/Names.lua` maps an item id to its name, `Data/<flavour>/_core/*.lua` holds each
item's quality, subclass, equip slot and item level, and `_core/Hidden.lua` lists test and removed items. This reads
those files as text (it never runs Lua) and writes one gzipped TSV the API loads at startup:
`services/api/src/toads_api/loot/data/items.tsv.gz`. Stdlib only.

Flavours are read in the order given and the first one to name an item wins. The default is Forever, then Vanilla
(Classic Era): Forever's own data is a beta client walk that lacks much of the raid loot, and the two share item ids,
so Classic fills those gaps while Forever's names win where they differ.
"""

from __future__ import annotations

import argparse
import gzip
import io
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "services" / "api" / "src" / "toads_api" / "loot" / "data" / "items.tsv.gz"

# One table row: `[123]="..."` or `[123]=true`.
_ROW = re.compile(r'^\[(\d+)\]=(?:"((?:[^"\\]|\\.)*)"|(true))', re.MULTILINE)
_LOAD_CORE = re.compile(r"lib:LoadCore\((\d+),")
_VERSION = re.compile(r"^## Version:\s*(\S+)", re.MULTILINE)
_ESCAPE = re.compile(rb"\\(\d{1,3}|x[0-9A-Fa-f]{2}|.)", re.DOTALL)
_SIMPLE = {b"n": b"\n", b"t": b"\t", b"r": b"\r", b"a": b"\a", b"b": b"\b", b"f": b"\f", b"v": b"\v"}
_SEP = "\x1f"


@dataclass(frozen=True)
class Item:
    id: int
    name: str
    quality: int
    class_id: int
    subclass_id: int
    slot: str
    item_level: int
    # The LibItemDB flavour the item came from: "Forever" or "Vanilla".
    flavour: str


def unescape(s: str) -> str:
    """A Lua string literal's body as the string it means. Lua's numeric escapes are bytes, so a name written as
    `Caf\\195\\169` comes back as UTF-8 "Café"."""

    def one(m: re.Match[bytes]) -> bytes:
        e = m.group(1)
        if e.isdigit():
            return bytes([int(e) & 0xFF])
        if e[:1] == b"x" and len(e) == 3:
            return bytes([int(e[1:], 16)])
        return _SIMPLE.get(e, e)

    return _ESCAPE.sub(one, s.encode("utf-8")).decode("utf-8", errors="replace")


def names(path: Path) -> dict[int, str]:
    return {int(i): unescape(s) for i, s, flag in _ROW.findall(path.read_text(encoding="utf-8")) if not flag}


def hidden(path: Path) -> set[int]:
    if not path.exists():
        return set()
    return {int(i) for i, _, flag in _ROW.findall(path.read_text(encoding="utf-8")) if flag}


def core(folder: Path) -> dict[int, tuple[int, int, int, str, int]]:
    """Every item's (class id, quality, subclass id, equip slot, item level) from the `lib:LoadCore` files."""
    found: dict[int, tuple[int, int, int, str, int]] = {}
    for path in sorted(folder.glob("*.lua")):
        text = path.read_text(encoding="utf-8")
        load = _LOAD_CORE.search(text)
        if load is None:
            continue
        class_id = int(load.group(1))
        for i, packed, _ in _ROW.findall(text[load.end() :]):
            fields = unescape(packed).split(_SEP)
            if len(fields) < 4:
                continue
            quality, subclass, slot, level = fields[:4]
            found[int(i)] = (class_id, _int(quality), _int(subclass), slot, _int(level))
    return found


def _int(s: str) -> int:
    try:
        return int(s)
    except ValueError:
        return -1


def items(addon: Path, flavour: str, locale: str) -> list[Item]:
    """The flavour's items in id order, hidden ones left out. An item with a name but no core row keeps -1 fields."""
    data = addon / "Data" / flavour
    named = names(data / locale / "Names.lua")
    skip = hidden(data / "_core" / "Hidden.lua")
    facts = core(data / "_core")
    out = []
    for item_id in sorted(named):
        name = " ".join(named[item_id].split())
        if item_id in skip or not name:
            continue
        class_id, quality, subclass, slot, level = facts.get(item_id, (-1, -1, -1, "", -1))
        out.append(Item(item_id, name, quality, class_id, subclass, slot, level, flavour))
    return out


def merged(addon: Path, flavours: list[str], locale: str) -> list[Item]:
    """Every flavour's items in id order; where two name the same id, the earlier flavour's row wins."""
    found: dict[int, Item] = {}
    for flavour in flavours:
        for item in items(addon, flavour, locale):
            found.setdefault(item.id, item)
    return [found[i] for i in sorted(found)]


def version(addon: Path) -> str:
    for toc in sorted(addon.glob("*.toc")):
        m = _VERSION.search(toc.read_text(encoding="utf-8"))
        if m:
            return m.group(1)
    return "unknown"


def render(rows: list[Item], source: str) -> bytes:
    """The TSV, gzipped with a fixed timestamp so the same input always writes the same bytes."""
    text = io.StringIO()
    text.write(f"# {source}\n")
    text.write("# LibItemDB is MIT licensed, Copyright (c) 2026 Pimptasty. See NOTICE beside this file.\n")
    text.write("id\tname\tquality\tclass_id\tsubclass_id\tslot\titem_level\tflavour\n")
    for r in rows:
        fields = (r.id, r.name, r.quality, r.class_id, r.subclass_id, r.slot, r.item_level, r.flavour)
        text.write("\t".join(str(f) for f in fields) + "\n")
    return gzip.compress(text.getvalue().encode("utf-8"), mtime=0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("addon", type=Path, help="the unzipped ItemDB addon folder (holds Data/ and *.toc)")
    parser.add_argument(
        "--flavour", action="append", help="a Data/ folder to read; repeat it, first wins (default: Forever, Vanilla)"
    )
    parser.add_argument("--locale", default="enUS")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args(argv)
    flavours = args.flavour or ["Forever", "Vanilla"]
    for flavour in flavours:
        if not (args.addon / "Data" / flavour / args.locale / "Names.lua").is_file():
            print(f"No {flavour} {args.locale} names under {args.addon}/Data", file=sys.stderr)
            return 1
    rows = merged(args.addon, flavours, args.locale)
    counts = ", ".join(f"{sum(r.flavour == f for r in rows)} {f}" for f in flavours)
    source = f"LibItemDB {version(args.addon)}, {args.locale}: {len(rows)} items ({counts})"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(render(rows, source))
    print(f"Wrote {source} to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
