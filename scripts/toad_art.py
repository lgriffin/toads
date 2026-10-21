"""Draw the toads that badge Discord roles (docs/role-badges.md) and the super admin rank, the Horde race toads, and the
weekly honours officers give (docs/awards.md): Raider of the Week and the pond's piss-takes.

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
    # Race toads recolour the member toad: the skin gradient (top, bottom) and any body colour swapped for another.
    skin: tuple[str, str] | None = None
    recolour: tuple[tuple[str, str], ...] = ()
    # A transform for the whole toad (the Floor Inspector lies down), and what is drawn on its face, moving with it.
    pose: str = ""
    face: str = ""


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

THURSDAY = ToadArt(
    file="days/thursday-toad",
    label="THURSDAY",
    disc=("#c9b8f4", "#6a4fc0", "#241650"),
    banner="#6a4fc0",
    banner_text=CREAM,
    # Thor's day: a storm cloud over the pond, its bolt striking off to the side.
    behind=(
        '<path d="M52 60 L38 84 L48 84 L32 110 L62 76 L52 76 L62 60Z" fill="#ffd96b" stroke="#3a2410" '
        'stroke-width="2" stroke-linejoin="round"/>'
        '<path d="M50 62 Q44 46 62 44 Q64 28 84 32 Q96 16 114 28 Q134 22 138 40 Q156 42 150 60 Q146 66 136 64 '
        'L62 64 Q52 66 50 62Z" fill="#d9d2f2" stroke="#3a2410" stroke-width="2" stroke-linejoin="round"/>'
        '<path d="M66 54 Q80 58 94 52 M104 48 Q118 54 132 50" fill="none" stroke="#a99ad6" stroke-width="2.4" '
        'stroke-linecap="round"/>'
        + "".join(
            f'<path d="M{x} {y} q-3 6 0 8 q3 -2 0 -8Z" fill="#8fd3f0" stroke="#12303f" stroke-width="1"/>'
            for x, y in [(120, 70), (134, 74)]
        )
    ),
    # A little bronze warhammer, held up on the right, and a stormy grin.
    front=(
        '<g transform="translate(-6 0)">'
        '<path d="M158 96 L158 168" stroke="#3a2410" stroke-width="8" stroke-linecap="round"/>'
        '<path d="M158 96 L158 168" stroke="#7a4f23" stroke-width="5" stroke-linecap="round"/>'
        '<rect x="141" y="80" width="34" height="20" rx="3" fill="url(#bronze)" stroke="#3a2410" stroke-width="2.4"/>'
        '<path d="M147 84 L147 96 M169 84 L169 96" stroke="#3a2410" stroke-width="1.6" opacity=".6"/>'
        '<path d="M156 86 L161 86 L158 92Z" fill="#ffd96b" stroke="#3a2410" stroke-width="1"/></g>'
        '<path d="M86 151 Q100 159 114 151" fill="none" stroke="#6a4fc0" stroke-width="3" stroke-linecap="round"/>'
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

# ---------------------------------------------------------------- weekly honours (docs/awards.md)
# Raider of the Week and the pond's weekly piss-takes, given after each raid week.

IVORY, STEEL = "#f3ead0", "#b8c2cc"


def _crown(cx: float, cy: float, scale: float = 1.0, tilt: float = 0) -> str:
    """A gold crown, its band centred on (cx, cy)."""
    return (
        f'<g transform="translate({cx} {cy}) rotate({tilt}) scale({scale})">'
        '<path d="M-22 6 L-26 -22 L-12 -10 L0 -28 L12 -10 L26 -22 L22 6Z" fill="#ffd25a" stroke="#3a2410" '
        'stroke-width="2.4" stroke-linejoin="round"/>'
        '<path d="M-22 0 L22 0 L22 7 L-22 7Z" fill="url(#bronze)" stroke="#3a2410" stroke-width="2" '
        'stroke-linejoin="round"/>'
        '<circle cx="0" cy="-12" r="3.6" fill="#e0402e" stroke="#3a2410" stroke-width="1.4"/>'
        '<circle cx="-12" cy="3.5" r="2.4" fill="#5fe6d6" stroke="#3a2410" stroke-width="1"/>'
        '<circle cx="12" cy="3.5" r="2.4" fill="#5fe6d6" stroke="#3a2410" stroke-width="1"/>'
        '<circle cx="-26" cy="-22" r="2.6" fill="#fff4d0" stroke="#3a2410" stroke-width="1"/>'
        '<circle cx="26" cy="-22" r="2.6" fill="#fff4d0" stroke="#3a2410" stroke-width="1"/>'
        '<circle cx="0" cy="-28" r="2.8" fill="#fff4d0" stroke="#3a2410" stroke-width="1"/></g>'
    )


def _bang(x: float, y: float, colour: str = "#ffd25a") -> str:
    """An aggro exclamation mark, its dot at (x, y)."""
    return (
        f'<path d="M{x - 4} {y - 30} L{x + 4} {y - 30} L{x + 2.4} {y - 8} L{x - 2.4} {y - 8}Z" fill="{colour}" '
        'stroke="#3a2410" stroke-width="2" stroke-linejoin="round"/>'
        f'<circle cx="{x}" cy="{y}" r="3.6" fill="{colour}" stroke="#3a2410" stroke-width="2"/>'
    )


def _flame(cx: float, base: float, h: float, w: float) -> str:
    """A two-tone flame standing on `base`."""

    def tongue(cx: float, base: float, h: float, w: float, fill: str) -> str:
        return (
            f'<path d="M{cx} {base - h} C{cx + w * 0.25} {base - h * 0.62} {cx + w} {base - h * 0.55} '
            f"{cx + w * 0.7} {base} L{cx - w * 0.7} {base} C{cx - w} {base - h * 0.5} {cx - w * 0.3} "
            f'{base - h * 0.6} {cx} {base - h}Z" fill="{fill}" stroke="#7a2410" stroke-width="1.6" '
            'stroke-linejoin="round"/>'
        )

    return tongue(cx, base, h, w, "#ff7a1a") + tongue(cx, base, h * 0.55, w * 0.55, "#ffd25a")


def _drop(x: float, y: float, fill: str = "#8fd3f0") -> str:
    """A sweat drop (or a mana drop) hanging from (x, y)."""
    return (
        f'<path d="M{x} {y} Q{x - 6} {y + 9} {x} {y + 12} Q{x + 6} {y + 9} {x} {y}Z" fill="{fill}" '
        'stroke="#12303f" stroke-width="1.2"/>'
    )


def _z(x: float, y: float, s: float) -> str:
    return (
        f'<path d="M{x} {y} h{s} l{-s} {s * 1.1} h{s}" fill="none" stroke="#f7ecd2" stroke-width="{s / 4:.1f}" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
    )


RAIDER_OF_THE_WEEK = ToadArt(
    file="honours/raider-of-the-week",
    label="RAIDER OF THE WEEK",
    disc=("#c8f5d2", "#3fae6a", "#123d27"),
    banner="#2f8f57",
    banner_text=CREAM,
    # The pond's sunrise behind a crowned head: best toad on the pad this week.
    behind=_rays(100, 70, 36, 56, 11, "#f4dc9c") + _star(40, 70, 6, "#fff4d0") + _star(160, 64, 5, "#fff4d0"),
    front=(
        _crown(100, 80, 0.95)
        # A foam "number one" hand, held high.
        + '<g transform="rotate(10 160 110)">'
        '<rect x="155" y="58" width="13" height="40" rx="6.5" fill="#ffd25a" stroke="#3a2410" stroke-width="2.4"/>'
        '<rect x="145" y="92" width="32" height="34" rx="10" fill="#ffd25a" stroke="#3a2410" stroke-width="2.4"/>'
        '<path d="M151 100 h20 M151 108 h20" stroke="#c58f45" stroke-width="2" stroke-linecap="round"/>'
        '<rect x="148" y="124" width="26" height="12" rx="3" fill="#2f8f57" stroke="#3a2410" stroke-width="2"/></g>'
    ),
)

SUNDER_KING = ToadArt(
    file="honours/sunder-king",
    label="SUNDER KING",
    disc=("#f2b8a8", "#a8382e", "#3d1210"),
    banner="#a8382e",
    banner_text=CREAM,
    # A breastplate with five cracks in it: five stacks, before the rogues had even opened.
    behind=(
        '<path d="M62 30 Q100 18 138 30 L134 76 Q100 92 66 76Z" fill="#b8c2cc" stroke="#12303f" stroke-width="2.4" '
        'stroke-linejoin="round"/>'
        '<path d="M100 22 L100 86" stroke="#7d8894" stroke-width="2"/>'
        '<path d="M74 34 L80 44 L74 50 L82 60 M90 28 L94 40 L88 48 M108 28 L104 38 L112 46 L106 56 '
        'M124 32 L120 42 L128 50 M130 52 L122 60 L128 68" fill="none" stroke="#12303f" stroke-width="2.2" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
    ),
    # A crown that does not quite fit, and a sword that has sundered a great deal.
    front=(
        _crown(76, 76, 0.7, -16) + '<g transform="rotate(14 160 120)">'
        '<path d="M156 44 L164 44 L164 118 L160 126 L156 118Z" fill="#dfe6ec" stroke="#12303f" stroke-width="2.2" '
        'stroke-linejoin="round"/><path d="M160 48 L160 116" stroke="#9aa6b2" stroke-width="1.6"/>'
        '<rect x="146" y="122" width="28" height="7" rx="3" fill="url(#bronze)" stroke="#3a2410" stroke-width="2"/>'
        '<rect x="156" y="129" width="8" height="22" rx="3" fill="#7a4f23" stroke="#3a2410" stroke-width="2"/></g>'
    ),
)

BEST_INTERRUPT = ToadArt(
    file="honours/best-interrupt",
    label="BEST INTERRUPT",
    disc=("#fff4b0", "#d8b83a", "#4f3f0c"),
    banner="#d8b83a",
    banner_text=INK,
    # The boss's spell bubble, kicked mid-sentence.
    behind=(
        '<g transform="translate(132 46) scale(.78) translate(-137 -40)">'
        '<path d="M108 30 Q108 16 136 16 Q166 16 166 36 Q166 56 138 56 L126 56 L114 68 L118 54 Q108 50 108 30Z" '
        'fill="#fffaf0" stroke="#12303f" stroke-width="2.2" stroke-linejoin="round"/>'
        '<path d="M118 36 Q124 26 130 36 T142 36 T154 36" fill="none" stroke="#8a5ad6" stroke-width="3" '
        'stroke-linecap="round"/>'
        '<path d="M116 48 L158 22" stroke="#e0402e" stroke-width="4.5" stroke-linecap="round"/></g>'
    ),
    # A rogue's boot, mid-kick, with the impact still ringing.
    front=(
        '<g transform="translate(8 4)">'
        '<path d="M22 60 L30 60 M18 70 L32 70 M24 80 L34 80" stroke="#f7ecd2" stroke-width="3" '
        'stroke-linecap="round"/>'
        '<path d="M38 50 L58 50 L60 64 L86 66 Q96 68 94 76 L92 82 L40 82 Q34 82 36 74Z" fill="#7a4f23" '
        'stroke="#2b1a0c" stroke-width="2.4" stroke-linejoin="round"/>'
        '<path d="M36 50 L60 50 L60 58 L36 58Z" fill="#c58f45" stroke="#2b1a0c" stroke-width="2"/>'
        '<path d="M40 82 L92 82" stroke="#2b1a0c" stroke-width="5" stroke-linecap="round"/></g>'
        + _star(108, 64, 9, "#fff4d0")
    ),
)

FLOOR_INSPECTOR = ToadArt(
    file="honours/floor-inspector",
    label="FLOOR INSPECTOR",
    disc=("#d6dbe8", "#6a7896", "#1d2438"),
    banner="#6a7896",
    banner_text=CREAM,
    # Floorboards: the toad spent most of the raid examining them closely.
    behind=(
        '<path d="M0 150 H200 V200 H0Z" fill="#8a5a32"/>'
        '<path d="M0 150 H200 M0 166 H200 M60 150 V166 M140 150 V166 M100 166 V200" stroke="#4a2f14" '
        'stroke-width="2"/>'
    ),
    pose="translate(104 114) rotate(-82) scale(.8) translate(-100 -124)",
    # Crossed-out eyes and a tongue out.
    face=(
        '<circle cx="76" cy="90" r="10" fill="url(#skin)"/><circle cx="124" cy="90" r="10" fill="url(#skin)"/>'
        '<path d="M69 83 L83 97 M83 83 L69 97 M117 83 L131 97 M131 83 L117 97" stroke="#12303f" stroke-width="3.6" '
        'stroke-linecap="round"/>'
        '<path d="M106 135 Q114 150 104 154 Q96 150 100 137Z" fill="#f28a9a" stroke="#7a2f4f" stroke-width="1.6"/>'
    ),
    # Stars circling the head, and the magnifying glass they brought for the job.
    front=(
        _star(44, 84, 7, "#ffd25a")
        + _star(64, 66, 5, "#fff4d0")
        + _star(40, 108, 4.5, "#fff4d0")
        + '<circle cx="152" cy="132" r="13" fill="#bfe8ff" fill-opacity=".45" stroke="url(#bronze)" stroke-width="5"/>'
        '<circle cx="152" cy="132" r="13" fill="none" stroke="#3a2410" stroke-width="1.2"/>'
        '<path d="M162 141 L178 148" stroke="#3a2410" stroke-width="6" stroke-linecap="round"/>'
    ),
)

STOOD_IN_FIRE = ToadArt(
    file="honours/stood-in-fire",
    label="STOOD IN FIRE",
    disc=("#ffd0a0", "#e0581e", "#4a140a"),
    banner="#e0581e",
    banner_text=INK,
    # The fire. It was always there. Everyone else moved.
    behind=_flame(46, 160, 70, 22) + _flame(156, 160, 78, 24) + _flame(100, 120, 60, 26),
    # More of it at their feet, smoke off the top and a brave little sweat drop.
    front=(
        _flame(70, 178, 34, 14)
        + _flame(130, 178, 30, 13)
        + _flame(100, 182, 26, 12)
        + '<path d="M96 70 Q88 60 96 52 Q90 42 100 36 Q112 40 108 50 Q118 56 110 66 Q104 72 96 70Z" '
        'fill="#6a6f7a" fill-opacity=".85" stroke="#2b2f38" stroke-width="1.6"/>' + _drop(144, 74)
    ),
)

JUMPED_THE_GUN = ToadArt(
    file="honours/jumped-the-gun",
    label="JUMPED THE GUN",
    disc=("#ffe0a0", "#d8862a", "#4a2a0a"),
    banner="#d8862a",
    banner_text=INK,
    # The pull timer, still on three.
    behind=(
        '<rect x="132" y="20" width="12" height="8" rx="2" fill="url(#bronze)" stroke="#3a2410" stroke-width="1.8"/>'
        '<circle cx="138" cy="52" r="24" fill="url(#bronze)" stroke="#3a2410" stroke-width="2.4"/>'
        '<circle cx="138" cy="52" r="19" fill="#fffaf0" stroke="#3a2410" stroke-width="1.6"/>'
        '<path d="M138 52 L138 33 A19 19 0 0 1 154.5 42.5Z" fill="#e0402e" fill-opacity=".55"/>'
        '<path d="M131 43 Q138 37 144 42 Q146 49 138 51 Q146 53 144 59 Q138 65 131 60" fill="none" '
        'stroke="#12303f" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'
        # Speed lines: they were already gone.
        '<path d="M28 96 L48 96 M22 112 L46 112 M28 128 L48 128" stroke="#fff4d0" stroke-width="3.4" '
        'stroke-linecap="round"/>'
    ),
    front=_drop(98, 62) + _drop(146, 92) + _bang(62, 66, "#e0402e"),
)

BREW_BREAK = ToadArt(
    file="honours/brew-break",
    label="BREW BREAK",
    disc=("#f6e2c4", "#b07a4a", "#3f2410"),
    banner="#b07a4a",
    banner_text=CREAM,
    # Away from keyboard. The pull went without them.
    behind=_z(110, 50, 11) + _z(128, 42, 8) + _z(144, 54, 6),
    # Heavy eyelids, a proper cup of tea and its steam.
    face=(
        '<path d="M66.5 90 A9.5 9.5 0 0 1 85.5 90Z M114.5 90 A9.5 9.5 0 0 1 133.5 90Z" fill="url(#skin)" '
        'stroke="#12303f" stroke-width="2"/>'
    ),
    front=(
        '<path d="M150 112 Q144 102 150 94 Q156 86 150 76 M162 110 Q156 100 162 92 Q168 84 162 74" fill="none" '
        'stroke="#fffaf0" stroke-width="3" stroke-linecap="round" opacity=".8"/>'
        '<ellipse cx="156" cy="146" rx="26" ry="6" fill="#fffaf0" stroke="#12303f" stroke-width="2"/>'
        '<path d="M138 118 L174 118 Q172 142 156 144 Q140 142 138 118Z" fill="#fffaf0" stroke="#12303f" '
        'stroke-width="2.2" stroke-linejoin="round"/>'
        '<ellipse cx="156" cy="119" rx="17" ry="3.6" fill="#a0602a" stroke="#12303f" stroke-width="1.4"/>'
        '<path d="M173 124 Q184 124 182 132 Q180 138 170 136" fill="none" stroke="#12303f" stroke-width="2.6"/>'
        '<path d="M146 128 Q156 132 166 128" fill="none" stroke="#5fc08a" stroke-width="2.4" stroke-linecap="round"/>'
    ),
)

REPAIR_BILL = ToadArt(
    file="honours/repair-bill",
    label="REPAIR BILL",
    disc=("#e2e6ea", "#7d8894", "#252a32"),
    banner="#7d8894",
    banner_text=INK,
    # Their gold, leaving.
    behind="".join(
        f'<g transform="translate({x} {y})">'
        '<path d="M-7 -2 Q-18 -10 -20 -2 Q-14 0 -7 2Z M7 -2 Q18 -10 20 -2 Q14 0 7 2Z" fill="#fffaf0" '
        'stroke="#3a2410" stroke-width="1.2"/>'
        '<circle r="8" fill="#ffd25a" stroke="#3a2410" stroke-width="1.8"/>'
        '<circle r="4.5" fill="none" stroke="#c58f45" stroke-width="1.4"/></g>'
        for x, y in [(56, 44), (100, 30), (146, 48)]
    ),
    # A broken sword and the receipt for fixing it, which goes on for some time.
    front=(
        '<path d="M28 100 L56 84 L60 90 L32 106Z" fill="#dfe6ec" stroke="#12303f" stroke-width="2" '
        'stroke-linejoin="round"/>'
        '<path d="M52 118 L62 112 L58 104 L48 110Z" fill="#dfe6ec" stroke="#12303f" stroke-width="2" '
        'stroke-linejoin="round"/>'
        '<path d="M46 124 L54 118 L50 112 L42 118Z" fill="url(#bronze)" stroke="#3a2410" stroke-width="1.8"/>'
        '<path d="M140 100 L170 100 L168 186 L138 186Z" fill="#fffaf0" stroke="#12303f" stroke-width="2" '
        'stroke-linejoin="round"/>'
        '<path d="M146 110 h18 M146 118 h14 M146 126 h18 M146 134 h12 M146 142 h18 M146 150 h16" stroke="#9aa6b2" '
        'stroke-width="2" stroke-linecap="round"/>'
        '<path d="M146 160 h18" stroke="#e0402e" stroke-width="3" stroke-linecap="round"/>'
        '<path d="M136 98 h38 v6 h-38Z" fill="url(#bronze)" stroke="#3a2410" stroke-width="1.6"/>'
    ),
)

PET_PULL = ToadArt(
    file="honours/pet-pull",
    label="PET PULL",
    disc=("#e4f5c0", "#7ea84a", "#1f3410"),
    banner="#7ea84a",
    banner_text=INK,
    # Somewhere ahead, the whole room has noticed.
    behind=_bang(150, 64, "#e0402e") + _bang(166, 76, "#e0402e") + _bang(134, 52, "#e0402e"),
    # It is always the pet: a hunter's boar, charging off on its own.
    front=(
        '<g transform="translate(-2 6)">'
        '<path d="M34 142 L32 156 M44 144 L44 158 M60 144 L62 158 M70 142 L74 156" stroke="#2b1a0c" '
        'stroke-width="4" stroke-linecap="round"/>'
        '<ellipse cx="54" cy="132" rx="26" ry="16" fill="#8a5a32" stroke="#2b1a0c" stroke-width="2.4"/>'
        '<path d="M36 120 L40 112 L46 120 L52 110 L58 120 L64 112 L68 122" fill="none" stroke="#2b1a0c" '
        'stroke-width="2.4" stroke-linejoin="round"/>'
        '<path d="M76 126 Q90 126 90 136 Q90 144 78 142Z" fill="#a8744a" stroke="#2b1a0c" stroke-width="2.2"/>'
        '<ellipse cx="88" cy="136" rx="3.6" ry="4.4" fill="#f2a7c3" stroke="#2b1a0c" stroke-width="1.4"/>'
        '<path d="M80 140 Q84 132 90 130" fill="none" stroke="#f3ead0" stroke-width="3" stroke-linecap="round"/>'
        '<circle cx="74" cy="128" r="2.2" fill="#e0402e"/>'
        '<path d="M66 120 L72 112 L74 122Z" fill="#6e4422" stroke="#2b1a0c" stroke-width="1.6"/>'
        '<path d="M22 124 L10 120 M22 132 L8 132 M22 140 L10 144" stroke="#fff4d0" stroke-width="2.6" '
        'stroke-linecap="round"/></g>' + _drop(144, 74)
    ),
)

WRONG_SKULL = ToadArt(
    file="honours/wrong-skull",
    label="WRONG SKULL",
    disc=("#d8ccf4", "#6a4fb8", "#1f1440"),
    banner="#6a4fb8",
    banner_text=CREAM,
    # The skull on the target they were told to kill, and the moon on the one they were told to leave.
    behind=(
        '<g transform="translate(60 44)">'
        '<path d="M-14 4 Q-16 -16 0 -16 Q16 -16 14 4 L10 8 L10 14 L-10 14 L-10 8Z" fill="#fffaf0" stroke="#12303f" '
        'stroke-width="2.2" stroke-linejoin="round"/>'
        '<circle cx="-6" cy="-2" r="4" fill="#12303f"/><circle cx="6" cy="-2" r="4" fill="#12303f"/>'
        '<path d="M-5 14 L-5 9 M0 14 L0 9 M5 14 L5 9" stroke="#12303f" stroke-width="1.6"/></g>'
        '<path d="M150 26 A18 18 0 1 0 156 60 A14 14 0 1 1 150 26Z" fill="#d8e6ff" stroke="#12303f" '
        'stroke-width="2" stroke-linejoin="round"/>'
    ),
    # The sheep. Was a sheep. Is now very cross.
    front=(
        '<g transform="translate(152 138)">'
        + "".join(
            f'<circle cx="{x}" cy="{y}" r="9" fill="#fffaf0" stroke="#12303f" stroke-width="1.8"/>'
            for x, y in [(-12, -4), (0, -10), (12, -4), (-8, 6), (8, 6), (0, 0)]
        )
        + '<ellipse cx="-18" cy="-2" rx="8" ry="7" fill="#3a3f4a" stroke="#12303f" stroke-width="1.8"/>'
        '<path d="M-22 -5 L-16 -3 M-16 -6 L-21 -2" stroke="#e0402e" stroke-width="1.8" stroke-linecap="round"/>'
        '<path d="M-6 14 L-6 22 M6 14 L6 22" stroke="#12303f" stroke-width="3" stroke-linecap="round"/></g>'
        + _star(126, 112, 10, "#ffd25a")
    ),
)

BONE_DRY = ToadArt(
    file="honours/bone-dry",
    label="BONE DRY",
    disc=("#b8dcff", "#2f6fd0", "#0c1d48"),
    banner="#2f6fd0",
    banner_text=CREAM,
    # The mana bar, and the last drop of it.
    behind=(
        '<rect x="58" y="42" width="84" height="14" rx="4" fill="#12303f" stroke="#3a2410" stroke-width="2"/>'
        '<rect x="61" y="45" width="6" height="8" rx="2" fill="#3a8fff"/>'
        '<path d="M58 42 h84 v14 h-84Z" fill="none" stroke="url(#bronze)" stroke-width="2"/>'
    ),
    # An empty mana potion, upended, still being shaken.
    front=(
        '<g transform="translate(134 120) rotate(28)">'
        '<path d="M-8 -10 L8 -10 L8 -20 Q22 -28 20 -44 Q16 -60 0 -60 Q-16 -60 -20 -44 Q-22 -28 -8 -20Z" '
        'fill="#dff0ff" fill-opacity=".7" stroke="#12303f" stroke-width="2.2" stroke-linejoin="round"/>'
        '<rect x="-10" y="-11" width="20" height="9" rx="2" fill="url(#bronze)" stroke="#3a2410" stroke-width="1.8"/>'
        '<path d="M-12 -46 Q-8 -54 0 -54" fill="none" stroke="#fffaf0" stroke-width="2.4" stroke-linecap="round"/>'
        "</g>"
        '<path d="M160 50 L166 44 M170 62 L178 60 M148 46 L150 38" stroke="#fff4d0" stroke-width="2.4" '
        'stroke-linecap="round"/>' + _drop(128, 124, "#3a8fff") + _drop(98, 64)
    ),
)

METER_GAZER = ToadArt(
    file="honours/meter-gazer",
    label="METER GAZER",
    disc=("#b8f0ea", "#1f9aa0", "#0a2e33"),
    banner="#1f9aa0",
    banner_text=INK,
    # The damage meter, watched more closely than the boss.
    behind=(
        '<rect x="58" y="34" width="84" height="42" rx="5" fill="#12303f" stroke="url(#bronze)" stroke-width="3"/>'
        + "".join(
            f'<rect x="63" y="{39 + i * 7}" width="{w * 0.78:.0f}" height="5" rx="1.5" fill="{c}"/>'
            for i, (w, c) in enumerate(
                [(94, "#C79C6E"), (80, "#9482C9"), (70, "#ABD473"), (58, "#FFF569"), (40, "#69CCF0")]
            )
        )
    ),
    # A magnifying glass over one eye, the better to see their own name.
    front=(
        '<path d="M138 104 L160 132" stroke="#3a2410" stroke-width="9" stroke-linecap="round"/>'
        '<path d="M138 104 L160 132" stroke="#7a4f23" stroke-width="5.5" stroke-linecap="round"/>'
        '<circle cx="124" cy="90" r="21" fill="#e4d29a"/>'
        '<circle cx="124" cy="90" r="13" fill="#e7a73c" stroke="#12303f" stroke-width="2.4"/>'
        '<ellipse cx="124" cy="90" rx="10" ry="4.4" fill="#12303f"/>'
        '<circle cx="124" cy="90" r="21" fill="#bfe8ff" fill-opacity=".3" stroke="url(#bronze)" stroke-width="5"/>'
        '<circle cx="124" cy="90" r="21" fill="none" stroke="#3a2410" stroke-width="1.2"/>'
        '<path d="M110 80 Q114 74 120 72" fill="none" stroke="#fffaf0" stroke-width="2.4" stroke-linecap="round"/>'
    ),
)

HONOURS = (
    RAIDER_OF_THE_WEEK,
    SUNDER_KING,
    BEST_INTERRUPT,
    FLOOR_INSPECTOR,
    STOOD_IN_FIRE,
    JUMPED_THE_GUN,
    BREW_BREAK,
    REPAIR_BILL,
    PET_PULL,
    WRONG_SKULL,
    BONE_DRY,
    METER_GAZER,
)

# ---------------------------------------------------------------- Horde races (docs/role-badges.md)
# The member toad, recoloured and dressed as each race the guild can play on the Horde side in WoW Forever.

HORDE_DISC, HORDE_BANNER = ("#f2a088", "#a8281e", "#3a0c08"), "#a8281e"


def _pair(path: str, **attrs: str) -> str:
    """A path and its mirror image across the toad's middle (x = 100)."""
    a = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items())
    return f'<path d="{path}" {a}/><path d="{path}" transform="matrix(-1 0 0 1 200 0)" {a}/>'


ORC = ToadArt(
    file="races/orc",
    label="ORC",
    disc=HORDE_DISC,
    banner=HORDE_BANNER,
    banner_text=CREAM,
    skin=("#9cc865", "#557f2f"),
    recolour=(("#8b7a45", "#4f7a2c"), ("#7d6e3c", "#3f6522")),
    # A warrior's topknot.
    behind=(
        '<path d="M90 98 Q84 70 96 56 Q92 46 100 36 Q108 46 104 56 Q116 70 110 98Z" fill="#2b2420" '
        'stroke="#12100c" stroke-width="2" stroke-linejoin="round"/>'
        '<rect x="93" y="58" width="14" height="7" rx="2" fill="url(#bronze)" stroke="#3a2410" stroke-width="1.6"/>'
    ),
    # A scowl, tusks and a spiked pauldron.
    front=(
        _pair("M64 79 L88 85", stroke="#2b2420", stroke_width="4.5", stroke_linecap="round")
        + _pair(
            "M78 128 Q72 116 78 106 Q86 116 86 130Z",
            fill=IVORY,
            stroke="#12303f",
            stroke_width="2",
            stroke_linejoin="round",
        )
        + '<path d="M134 112 Q156 100 172 114 Q166 128 146 128Z" fill="#6a6f7a" stroke="#12303f" '
        'stroke-width="2.2" stroke-linejoin="round"/>'
        '<path d="M146 108 L150 92 L156 106 M158 108 L166 96 L166 112" fill="#dfe6ec" stroke="#12303f" '
        'stroke-width="2" stroke-linejoin="round"/>'
    ),
)

TROLL = ToadArt(
    file="races/troll",
    label="TROLL",
    disc=("#a8ecd0", "#2f8a6a", "#0f3a2c"),
    banner="#2f8a6a",
    banner_text=CREAM,
    skin=("#86c8da", "#3f7f9a"),
    recolour=(("#8b7a45", "#3a7088"), ("#7d6e3c", "#346a80")),
    # A tall red mohawk and long ears.
    behind=(
        '<path d="M84 98 L78 54 L90 70 L94 36 L102 66 L110 32 L112 68 L124 48 L118 98Z" fill="#e0402e" '
        'stroke="#5a1410" stroke-width="2" stroke-linejoin="round"/>'
        + _pair(
            "M60 112 L20 92 L58 128Z", fill="url(#skin)", stroke="#12303f", stroke_width="2.4", stroke_linejoin="round"
        )
    ),
    # Great curling tusks.
    front=_pair(
        "M72 128 Q54 114 62 92 Q68 112 82 124Z",
        fill=IVORY,
        stroke="#12303f",
        stroke_width="2",
        stroke_linejoin="round",
    ),
)

TAUREN = ToadArt(
    file="races/tauren",
    label="TAUREN",
    disc=("#f0d4a0", "#a8743a", "#3d2410"),
    banner="#a8743a",
    banner_text=CREAM,
    skin=("#c8a070", "#7d5534"),
    recolour=(("#8b7a45", "#6e4a2c"), ("#7d6e3c", "#5d3e22")),
    # Horns and a shaggy forelock.
    behind=(
        _pair(
            "M66 94 Q28 92 28 58 Q44 80 74 84Z",
            fill=IVORY,
            stroke="#3a2410",
            stroke_width="2.2",
            stroke_linejoin="round",
        )
        + _pair("M38 78 L46 72 M32 66 L40 62", stroke="#c58f45", stroke_width="3", stroke_linecap="round")
        + '<path d="M86 98 Q90 74 100 72 Q112 74 114 98Z" fill="#5d3e22" stroke="#2b1a0c" stroke-width="2"/>'
    ),
    # A brass nose ring and a feather tied on a horn.
    front=(
        '<circle cx="100" cy="116" r="7" fill="none" stroke="#3a2410" stroke-width="5"/>'
        '<circle cx="100" cy="116" r="7" fill="none" stroke="url(#bronze)" stroke-width="3"/>'
        '<path d="M168 52 Q178 64 172 80 Q164 66 168 52Z" fill="#fffaf0" stroke="#3a2410" stroke-width="1.6"/>'
        '<path d="M168 52 L172 80" stroke="#e0402e" stroke-width="1.4"/>'
    ),
)

UNDEAD = ToadArt(
    file="races/undead",
    label="UNDEAD",
    disc=("#cdb8ec", "#5a3f8a", "#1f1238"),
    banner="#5a3f8a",
    banner_text=CREAM,
    skin=("#bcc4b2", "#6f7a6a"),
    recolour=(("#8b7a45", "#5f6a5a"), ("#7d6e3c", "#4f5a4a"), ("#e7a73c", "#9be36a")),
    # A tattered cowl.
    behind=(
        '<path d="M44 140 Q36 62 100 46 Q164 62 156 140 L146 128 L140 142 L130 130 L70 130 L60 142 L54 128Z" '
        'fill="#3d2a52" stroke="#1a1028" stroke-width="2.4" stroke-linejoin="round"/>'
    ),
    # Stitches across the cheek, a ghostly glow and a little bone showing.
    front=(
        _pair("M64 82 L60 76", stroke="#9be36a", stroke_width="2", stroke_linecap="round", opacity=".8")
        + '<path d="M112 114 L136 124" stroke="#2b2f38" stroke-width="2"/>'
        '<path d="M116 110 L114 120 M122 112 L120 122 M128 115 L126 125 M134 118 L132 128" stroke="#2b2f38" '
        'stroke-width="1.8" stroke-linecap="round"/>'
        '<path d="M50 102 L36 92" stroke="#efe6cc" stroke-width="5" stroke-linecap="round"/>'
        '<circle cx="34" cy="89" r="4" fill="#efe6cc" stroke="#3a3f4a" stroke-width="1.4"/>'
        '<circle cx="38" cy="86" r="4" fill="#efe6cc" stroke="#3a3f4a" stroke-width="1.4"/>'
    ),
)


def _feather(x: float, y: float, angle: float, fill: str) -> str:
    return (
        f'<g transform="translate({x} {y}) rotate({angle})">'
        f'<path d="M0 0 Q-9 -20 0 -44 Q9 -20 0 0Z" fill="{fill}" stroke="#12303f" stroke-width="1.8"/>'
        '<path d="M0 -2 L0 -40" stroke="#12303f" stroke-width="1.2" opacity=".6"/></g>'
    )


SKYBORNE = ToadArt(
    file="races/skyborne",
    label="SKYBORNE",
    disc=("#e4f6ff", "#4f9ad8", "#132a5a"),
    banner="#2f6fb8",
    banner_text=CREAM,
    skin=("#f0f5fc", "#a8b8d8"),
    recolour=(("#8b7a45", "#8496c0"), ("#7d6e3c", "#7a8cba"), ("#e7a73c", "#5fd0ff")),
    # Windshaper: a crest of sky feathers, long elven ears and the wind itself.
    behind=(
        '<path d="M22 60 Q40 44 58 56 Q66 62 58 68 M142 48 Q162 34 178 50 Q182 60 170 60" fill="none" '
        'stroke="#e4f6ff" stroke-width="3" stroke-linecap="round" opacity=".85"/>'
        + _feather(100, 96, -34, "#4f9ad8")
        + _feather(100, 96, 34, "#4f9ad8")
        + _feather(100, 96, -12, "#fffaf0")
        + _feather(100, 96, 12, "#fffaf0")
        + _pair(
            "M60 104 L16 70 L58 122Z", fill="url(#skin)", stroke="#12303f", stroke_width="2.4", stroke_linejoin="round"
        )
    ),
    # A gold circlet with a sky-blue stone.
    front=(
        '<path d="M86 96 Q100 90 114 96" fill="none" stroke="#3a2410" stroke-width="5" stroke-linecap="round"/>'
        '<path d="M86 96 Q100 90 114 96" fill="none" stroke="url(#bronze)" stroke-width="3" stroke-linecap="round"/>'
        '<circle cx="100" cy="92" r="4" fill="#5fd0ff" stroke="#3a2410" stroke-width="1.4"/>'
    ),
)

RACES = (ORC, TROLL, TAUREN, UNDEAD, SKYBORNE)

ALL = (WEDNESDAY, THURSDAY, SUNDAY, SUPER_ADMIN, *HONOURS, *RACES)


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


def _dress(art: ToadArt, defs: str, body: str) -> tuple[str, str]:
    """The defs and the drawn toad for one piece of art: recoloured, posed, with its props behind and in front."""
    if art.skin:
        top, bottom = art.skin
        defs = re.sub(
            r'<linearGradient id="skin".*?</linearGradient>',
            f'<linearGradient id="skin" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{top}"/>'
            f'<stop offset="1" stop-color="{bottom}"/></linearGradient>',
            defs,
        )
    for old, new in art.recolour:
        body = body.replace(old, new)
    toad = body + art.face
    if art.pose:
        toad = f'<g transform="{art.pose}">{toad}</g>'
    return defs, f"{art.behind}{toad}{art.front}"


def standalone(art: ToadArt, defs: str, body: str) -> str:
    defs, toad = _dress(art, defs, body)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="4 12 192 168" width="192" height="168">\n'
        f"{defs}\n{toad}\n</svg>\n"
    )


def badge(art: ToadArt, defs: str, body: str) -> str:
    ticks = "".join(
        '<rect x="98" y="5" width="4" height="9" rx="1.5" fill="#4a2f14" opacity=".55" '
        f'transform="rotate({a} 100 100)"/>'
        for a in range(0, 360, 15)
    )
    a, b, c = art.disc
    defs, toad = _dress(art, defs, body)
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
        f'<g clip-path="url(#disc)">\n{toad}\n</g>\n'
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
