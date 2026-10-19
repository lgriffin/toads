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
    model = copy[copy.index("export const MODEL") :]
    assert re.findall(r"^    id: '(\w+)',$", model.split("\n];", 1)[0], re.MULTILINE) == PILLARS
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


@scenario(
    str(FEATURE),
    "REQ-HUB-FRONT-002 The toolkit page shall show what raiders, officers and super admins can do in the raid "
    "analyzer, the guild bank and Discord with the officers' Google Drive, unlock the rows up to the viewer's tier, "
    "and name only permissions the hub's RBAC table gives that tier",
)
def test_toolkit() -> None:
    pass


@given("the toolkit page", target_fixture="toolkit")
def toolkit() -> str:
    return _read("routes/toolkit/+page.svelte")


@then("it lists the raid analyzer, the guild bank and Discord and Drive, each with a row for every tier")
def three_apps() -> None:
    access = _read("lib/access.ts")
    for app in ("Raid analyzer", "Guild bank", "Discord and Drive"):
        assert f"title: '{app}'" in access
    test = _read("lib/access.test.ts")
    assert "for (const app of APPS) expect(app.rows.map((r) => r.tier)).toEqual([...TIERS]);" in test


@then("it unlocks rows up to the viewer's tier, read from their session")
def unlocks_by_tier(toolkit: str) -> None:
    assert "unlocked(row, tier)" in toolkit
    assert "tierOf(session)" in toolkit


@then("a unit test fails if a row names a permission the RBAC table lacks or gives another tier")
def rbac_drift_test() -> None:
    test = _read("lib/access.test.ts")
    assert "services/api/src/toads_api/rbac/permissions.py" in test
    assert "puts each permission in the tier that first holds it" in test


@then("the top bar's tier chip opens it")
def chip_opens_toolkit() -> None:
    layout = _read("routes/+layout.svelte")
    assert 'href="{base}/toolkit/"' in layout
    assert "TIER_LABEL[tier]" in layout


@scenario(
    str(FEATURE),
    "REQ-HUB-FRONT-003 When a member is new to the hub, it shall offer a welcome checklist, and it shall give super "
    "admins one console for bank grants, officer tokens and the hub's integrations",
)
def test_welcome_and_admin() -> None:
    pass


@given("the welcome checklist", target_fixture="welcome")
def welcome() -> str:
    return _read("lib/welcome.ts")


@then("it walks a new member through claiming characters, their name, how we raid, the bank, the apps and the toolkit")
def welcome_steps(welcome: str) -> None:
    ids = re.findall(r"^    id: '(\w+)',$", welcome, re.MULTILINE)
    assert ids == ["character", "name", "model", "bank", "apps", "toolkit"]
    assert "WELCOME_STEPS" in _read("routes/welcome/+page.svelte")
    assert 'href="{base}/welcome/"' in _read("lib/Landing.svelte")


@then("the admin console shows integrations, scheduled jobs and bank grants to super admins only")
def admin_console() -> None:
    page = _read("routes/admin/+page.svelte")
    assert "const allowed = $derived(__PREVIEW__ || !!session?.super_admin);" in page
    assert "<BankGrants" in page
    for name in ("INTEGRATIONS", "JOBS"):
        assert name in page
    assert "if (under(p, '/admin') && role !== 'admin') return 'admins-only';" in _read("lib/preview/gate.ts")
    assert "{ href: '/admin', label: 'Admin', adminOnly: true }" in _read("lib/nav.ts")


@scenario(
    str(FEATURE),
    "REQ-HUB-FRONT-004 While the launch hold is on, the hub shall show a signed-in raider one coming-soon page for the "
    "guild bank, logs analysis and raid assistance, show officers their tabs with a Forever launch notice in place of "
    "each page, and leave super admins every page",
)
def test_launch_hold() -> None:
    pass


@given("the launch hold", target_fixture="launch")
def launch() -> str:
    return _read("lib/launch.ts")


@then("a raider's members nav is the hub link alone and every member page shows the coming-soon page")
def raider_coming_soon(launch: str) -> None:
    assert "export const LAUNCH_HOLD: boolean = __LAUNCH_HOLD__;" in launch
    for title in ("Guild bank management", "Logs analysis", "Raid assistance"):
        assert f"title: '{title}'" in launch
    layout = _read("routes/+layout.svelte")
    assert "heldNav(memberNav(officer, tier === 'admin'), tier)" in layout
    assert "{:else if hold === 'coming-soon'}\n    <ComingSoon />" in layout
    assert "gives raiders the coming-soon page on every member page" in _read("lib/launch.test.ts")


@then("an officer keeps every tab and each one shows the Forever launch notice")
def officer_notice() -> None:
    assert "{:else if hold === 'forever-notice'}\n    <ForeverNotice {path} />" in _read("routes/+layout.svelte")
    assert "Coming with the Forever launch" in _read("lib/components/ForeverNotice.svelte")
    assert "gives officers the Forever launch notice on every tab" in _read("lib/launch.test.ts")


@then("super admins, visitors and the public pages are never held")
def never_held(launch: str) -> None:
    assert "if (!hold || tier === 'visitor' || tier === 'admin' || !isMemberPath(path)) return 'open';" in launch
    assert "leaves super admins, visitors and the public pages alone" in _read("lib/launch.test.ts")


@then("the real site waits for the session before a held page renders, so it never starts the page's own API calls")
def waits_for_session() -> None:
    layout = _read("routes/+layout.svelte")
    assert "LAUNCH_HOLD && !__PREVIEW__ && session === undefined && isMemberPath(path)" in layout
    assert "__LAUNCH_HOLD__: JSON.stringify(process.env.PREVIEW !== '1' || process.env.LAUNCH_HOLD === '1')" in (
        WEB.parent / "vite.config.ts"
    ).read_text(encoding="utf-8")
