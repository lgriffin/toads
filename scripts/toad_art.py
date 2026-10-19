"""Draw the toads that badge Discord roles and the super admin rank (docs/role-badges.md).

Each toad comes twice, like every toad under apps/web/static/logos/: a standalone toad and a badge, the toad in the
bronze ring with its name on the banner. The body is the member toad's; only the props and colours change. Banner
names are drawn as Cinzel outlines, so the badges need no font.

    uv run --with fonttools --with brotli python scripts/toad_art.py

Rerun after changing a toad here; the SVGs it writes are committed.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
LOGOS = ROOT / "apps/web/static/logos"
FONT = ROOT / "apps/web/node_modules/@fontsource/cinzel/files/cinzel-latin-600-normal.woff2"

INK, CREAM = "#1a1030", "#f7ecd2"
OUTLINE, BRONZE_DARK, GOLD = "#12303f", "#3a2410", "#f4dc9c"


@dataclass(frozen=True)
class ToadArt:
    file: str
    label: str
    # The badge disc's radial gradient, centre to edge.
    disc: tuple[str, str, str]
    banner: str
    banner_text: str
    # Drawn before the body (behind the toad) and after it (held or worn).
    behind: str
    front: str


def _star(cx: float, cy: float, r: float, fill: str) -> str:
    """A four-point twinkle."""
    q = r * 0.28
    return (
        f'<path d="M{cx} {cy - r} Q{cx + q} {cy - q} {cx + r} {cy} Q{cx + q} {cy + q} {cx} {cy + r} '
        f'Q{cx - q} {cy + q} {cx - r} {cy} Q{cx - q} {cy - q} {cx} {cy - r}Z" fill="{fill}"/>'
    )


def _rays(cx: float, cy: float, inner: float, outer: float, count: int, colour: str) -> str:
    out = []
    for i in range(count):
        a = math.pi + math.pi * (i + 0.5) / count
        x1, y1 = cx + inner * math.cos(a), cy + inner * math.sin(a)
        x2, y2 = cx + outer * math.cos(a), cy + outer * math.sin(a)
        out.append(f"M{x1:.1f} {y1:.1f} L{x2:.1f} {y2:.1f}")
    return f'<path d="{" ".join(out)}" stroke="{colour}" stroke-width="4" stroke-linecap="round"/>'


WEDNESDAY = ToadArt(
    file="days/wednesday-toad",
    label="WEDNESDAY",
    disc=("#8fb7ee", "#3a62b8", "#16245a"),
    banner="#3a62b8",
    banner_text=CREAM,
    # A crescent moon and the evening's first stars: Wednesday raids start at dusk.
    behind=(
        '<path d="M70 40 A22 22 0 1 0 92 74 A17 17 0 1 1 70 40Z" fill="#f4dc9c" stroke="#3a2410" '
        'stroke-width="2" stroke-linejoin="round"/>'
        + _star(118, 46, 6.5, "#f7ecd2")
        + _star(134, 62, 4, "#f4dc9c")
        + _star(104, 36, 3.2, "#c4c0ea")
    ),
    # A pond lantern on a reed, glowing amber.
    front=(
        '<path d="M146 66 L146 172" fill="none" stroke="#6b4a2a" stroke-width="4" stroke-linecap="round"/>'
        '<path d="M146 66 Q158 66 158 76" fill="none" stroke="#6b4a2a" stroke-width="3" stroke-linecap="round"/>'
        '<circle cx="158" cy="96" r="16" fill="#ffd27a" opacity=".28"/>'
        '<path d="M150 82 L166 82 L164 108 L152 108Z" fill="#ffcf6b" stroke="#12303f" stroke-width="2.2" '
        'stroke-linejoin="round"/>'
        '<path d="M148 80 L168 80 L164 76 L152 76Z M150 108 L166 108 L164 113 L152 113Z" fill="url(#bronze)" '
        'stroke="#3a2410" stroke-width="1.6" stroke-linejoin="round"/>'
        '<path d="M158 88 Q154 95 158 101 Q162 95 158 88Z" fill="#fff4d0"/>'
        '<path d="M88 152 Q100 160 112 152" fill="none" stroke="#3a62b8" stroke-width="3" stroke-linecap="round"/>'
    ),
)

SUNDAY = ToadArt(
    file="days/sunday-toad",
    label="SUNDAY",
    disc=("#ffd8a0", "#ef8a45", "#7a3420"),
    banner="#ef8a45",
    banner_text=INK,
    # The sun rising over the pond behind the toad's head.
    behind=(
        _rays(100, 70, 34, 50, 9, "#ffcf6b")
        + '<circle cx="100" cy="70" r="30" fill="#ffcf6b" stroke="#3a2410" stroke-width="2"/>'
        '<circle cx="100" cy="70" r="22" fill="#ffe7a8" opacity=".7"/>'
    ),
    # A pond daisy tucked behind the ear, and a sun-warmed smile.
    front=(
        "".join(
            f'<ellipse cx="{58 + dx}" cy="{84 + dy}" rx="6" ry="3.2" transform="rotate({rot} {58 + dx} {84 + dy})" '
            'fill="#fffaf0" stroke="#3a2410" stroke-width="1.1"/>'
            for dx, dy, rot in [
                (0, -7, 90),
                (7, 0, 0),
                (0, 7, 90),
                (-7, 0, 0),
                (5, -5, 45),
                (-5, 5, 45),
                (5, 5, -45),
                (-5, -5, -45),
            ]
        )
        + '<circle cx="58" cy="84" r="4" fill="#ffcf6b" stroke="#3a2410" stroke-width="1.1"/>'
        '<path d="M86 151 Q100 158 114 151" fill="none" stroke="#ef8a45" stroke-width="3" stroke-linecap="round"/>'
    ),
)

SUPER_ADMIN = ToadArt(
    file="ranks/super-admin",
    label="SUPER ADMIN",
    disc=("#f0a596", "#b8463e", "#4f1a22"),
    banner="#b8463e",
    banner_text=CREAM,
    behind=(
        # The hub's gear turning behind the toad: the super admin keeps the machinery.
        '<g transform="translate(100 64)"><circle r="26" fill="none" stroke="#c58f45" stroke-width="9" '
        'stroke-dasharray="7 6.6"/><circle r="20" fill="#7a4f23" stroke="#3a2410" stroke-width="2"/>'
        '<circle r="9" fill="#2b1a0c"/></g>'
    ),
    front=(
        # A circlet with a teal gem.
        '<path d="M70 80 Q100 70 130 80" fill="none" stroke="#3a2410" stroke-width="6" stroke-linecap="round"/>'
        '<path d="M70 80 Q100 70 130 80" fill="none" stroke="url(#bronze)" stroke-width="3.6" stroke-linecap="round"/>'
        '<path d="M100 64 L107 73 L100 82 L93 73Z" fill="#5fe6d6" stroke="#3a2410" stroke-width="1.6" '
        'stroke-linejoin="round"/><path d="M98 70 L100 67 L102 70" fill="none" stroke="#e9fffb" stroke-width="1.2"/>'
        # The keys to the hub, held up on the right.
        '<g transform="translate(-8 -4)">'
        '<path d="M158 82 L158 170" stroke="#3a2410" stroke-width="8" stroke-linecap="round"/>'
        '<path d="M158 82 L158 170" stroke="url(#bronze)" stroke-width="5" stroke-linecap="round"/>'
        '<path d="M158 152 L146 152 M158 162 L148 162" stroke="#3a2410" stroke-width="5" stroke-linecap="round"/>'
        '<path d="M158 152 L146 152 M158 162 L148 162" stroke="url(#bronze)" stroke-width="2.6" '
        'stroke-linecap="round"/>'
        '<circle cx="158" cy="72" r="14" fill="url(#bronze)" stroke="#3a2410" stroke-width="2.4"/>'
        '<circle cx="158" cy="72" r="6" fill="#4f1a22" stroke="#3a2410" stroke-width="1.6"/></g>'
    ),
)

ALL = (WEDNESDAY, SUNDAY, SUPER_ADMIN)


def _member_parts() -> tuple[str, str]:
    """The shared <defs> and the bare toad body, taken from the member toad."""
    member = (LOGOS / "ranks/member.svg").read_text(encoding="utf-8")
    defs = member[member.index("<defs>") : member.index("</defs>") + len("</defs>")]
    start = member.index('<path d="M52 150')
    warts = member.index("</g>", member.index('<g fill="#7d6e3c"')) + len("</g>")
    return defs, member[start:warts]


def _label_path(text: str, colour: str) -> str:
    """The banner's name as outlines, centred on the banner (x 100, baseline 220.2, caps 12.3 tall)."""
    font = TTFont(FONT)
    glyphs, cmap = font.getGlyphSet(), font.getBestCmap()
    cap_height = font["OS/2"].sCapHeight or 700
    scale = 12.3 / cap_height
    advance = sum(glyphs[cmap[ord(c)]].width for c in text) + 60 * (len(text) - 1)
    width = advance * scale
    if width > 150:
        scale *= 150 / width
        width = 150
    pen = SVGPathPen(glyphs)
    x = 0.0
    for c in text:
        name = cmap[ord(c)]
        tpen = TransformPen(pen, (scale, 0, 0, -scale, 100 - width / 2 + x * scale, 220.2))
        glyphs[name].draw(tpen)
        x += glyphs[name].width + 60
    d = re.sub(r"(\d+\.\d{2})\d+", r"\1", pen.getCommands())
    return f'<path d="{d}" fill="{colour}"/>'


def standalone(art: ToadArt, defs: str, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="4 12 192 168" width="192" height="168">\n'
        f"{defs}\n{art.behind}{body}{art.front}\n</svg>\n"
    )


def badge(art: ToadArt, defs: str, body: str) -> str:
    ticks = "".join(
        '<rect x="98" y="5" width="4" height="9" rx="1.5" fill="#4a2f14" opacity=".55" '
        f'transform="rotate({a} 100 100)"/>'
        for a in range(0, 360, 15)
    )
    a, b, c = art.disc
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 240" width="200" height="240">\n'
        f"{defs}\n"
        f'<radialGradient id="cls" cx=".5" cy=".42" r=".66"><stop offset="0" stop-color="{a}"/>'
        f'<stop offset=".55" stop-color="{b}"/><stop offset="1" stop-color="{c}"/></radialGradient>\n'
        '<circle cx="100" cy="100" r="97" fill="url(#bronze)"/>'
        '<circle cx="100" cy="100" r="97" fill="none" stroke="#4a2f14" stroke-width="1.5"/>\n'
        f"{ticks}\n"
        '<circle cx="100" cy="100" r="82" fill="#3a2410"/><circle cx="100" cy="100" r="79" fill="url(#bronze)"/>\n'
        '<circle cx="100" cy="100" r="74" fill="url(#cls)"/>\n'
        f'<g clip-path="url(#disc)">\n{art.behind}{body}{art.front}\n</g>\n'
        f'<path d="M10 198 H190 L180 214 L190 232 H10 L20 214Z" fill="{art.banner}" stroke="#3a2410" '
        'stroke-width="2.6" stroke-linejoin="round"/>'
        '<path d="M20 202 H180 M20 228 H180" stroke="#f4dc9c" stroke-width="1.4" opacity=".9"/>'
        f"{_label_path(art.label, art.banner_text)}\n</svg>\n"
    )


def main() -> None:
    defs, body = _member_parts()
    for art in ALL:
        out = LOGOS / f"{art.file}.svg"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(standalone(art, defs, body), encoding="utf-8")
        (LOGOS / f"{art.file}-badge.svg").write_text(badge(art, defs, body), encoding="utf-8")
        print(f"wrote {art.file}.svg and {art.file}-badge.svg")


if __name__ == "__main__":
    main()
