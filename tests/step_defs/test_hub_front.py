"""REQ-HUB-FRONT: the public homepage's model of how we raid, and the toolkit of what each tier can do."""

import re
from pathlib import Path

from pytest_bdd import given, scenario, then

ROOT = Path(__file__).resolve().parents[2]
FEATURE = ROOT / "tests" / "features" / "hub_front.feature"
WEB = ROOT / "apps" / "web" / "src"
PILLARS = ["prep", "flasks", "consumes", "speed", "badges", "standard"]


def _read(relative: str) -> str:
    return (WEB / relative).read_text(encoding="utf-8")


@scenario(
    str(FEATURE),
    "REQ-HUB-FRONT-001 The public homepage shall explain how a Toads raid night works (prep, flasks and elixirs, "
    "consumes, speed, badges and how the guild measures itself) and shall show only guild-level numbers, never a "
    "player's name",
)
def test_homepage_model() -> None:
    pass


@given("the public homepage", target_fixture="landing")
def landing() -> str:
    return _read("lib/Landing.svelte")


@then("it shows the six pillars of how we raid, each linking to its full write-up on How we raid")
def six_pillars(landing: str) -> None:
    assert "<ModelPillars compact />" in landing
    copy = _read("lib/landing.ts")
    assert re.findall(r"^    id: '(\w+)',$", copy, re.MULTILINE) == PILLARS
    pillars = _read("lib/components/ModelPillars.svelte")
    assert 'href="{base}/how-we-raid/#{p.id}"' in pillars
    assert "<ModelPillars {trend} />" in _read("routes/how-we-raid/+page.svelte")


@then("each pillar says what we expect, how we measure it and what a member sees")
def pillar_parts() -> None:
    copy = _read("lib/landing.ts")
    for field in ("approach", "measure", "youSee"):
        assert len(re.findall(rf"^    {field}:", copy, re.MULTILINE)) == len(PILLARS), field
    pillars = _read("lib/components/ModelPillars.svelte")
    for heading in ("Our approach", "How we measure it", "What you see"):
        assert f"<dt>{heading}</dt>" in pillars


@then("it shows a raid week and the three apps a member gets")
def week_and_apps(landing: str) -> None:
    assert "<RaidWeek />" in landing
    assert "MEMBER_APPS" in landing
    copy = _read("lib/landing.ts")
    assert copy.count("raid: true") == 2
    for app in ("Raid analyzer", "Guild bank", "Discord"):
        assert f"title: '{app}'" in copy


@then("its guild pulse reads only guild totals from the raid sheets")
def guild_totals_only() -> None:
    names = ("low_consumables", "PlayerLine", "players:")
    for source in ("lib/pulse.ts", "lib/components/GuildPulse.svelte", "lib/components/ModelPillars.svelte"):
        text = _read(source)
        assert not any(n in text for n in names), source
    # Only the preview has the sample data; the real site leaves the pulse out until a public summary exists.
    assert "const pulse: GuildPulse | null = __PREVIEW__" in _read("routes/+page.svelte")
