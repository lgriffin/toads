"""REQ-HUB-FRONT: the public homepage's model of how we raid, Hub features, and the launch hold's previews."""

import re
from pathlib import Path

from pytest_bdd import given, scenario, then

ROOT = Path(__file__).resolve().parents[2]
FEATURE = ROOT / "tests" / "features" / "hub_front.feature"
WEB = ROOT / "apps" / "web" / "src"
PILLARS = ["prep", "flasks", "consumes", "speed", "loot", "standard"]
HOME_PILLARS = ["prep", "flasks", "speed", "standard"]


def _read(relative: str) -> str:
    return (WEB / relative).read_text(encoding="utf-8")


@scenario(
    str(FEATURE),
    "REQ-HUB-FRONT-001 The public homepage shall explain how a Toads raid night works (prep, flasks and consumes, "
    "speed and how the guild measures itself) and shall show only guild-level numbers, never a player's name",
)
def test_homepage_model() -> None:
    pass


@given("the public homepage", target_fixture="landing")
def landing() -> str:
    return _read("lib/Landing.svelte")


@then("it shows the raid-night pillars, each linking to its full write-up on How we raid")
def home_pillars(landing: str) -> None:
    assert "<ModelPillars compact />" in landing
    copy = _read("lib/landing.ts")
    home = copy[copy.index("export const HOME_PILLARS") :].split("\n];", 1)[0]
    assert re.findall(r"id: '(\w+)'", home) == HOME_PILLARS
    assert set(HOME_PILLARS) <= set(PILLARS)
    pillars = _read("lib/components/ModelPillars.svelte")
    assert 'href="{base}/how-we-raid/#{p.id}"' in pillars
    assert "<ModelPillars {trend} />" in _read("routes/how-we-raid/+page.svelte")


@then(
    "How we raid says for each of its six pillars what we expect, how we measure it and what a member sees, with the "
    "Loot Council in place of badges"
)
def pillar_parts() -> None:
    copy = _read("lib/landing.ts")
    model = copy[copy.index("export const MODEL") :].split("\n];", 1)[0]
    assert re.findall(r"^    id: '(\w+)',$", model, re.MULTILINE) == PILLARS
    for field in ("approach", "measure", "youSee"):
        assert len(re.findall(rf"^    {field}:", model, re.MULTILINE)) == len(PILLARS), field
    assert "Loot Council" in model
    # thatsmybis.com keeps a table per raid day, not one per guild, so there is no single page to link.
    assert "thatsmybis.com" in model and "https://thatsmybis.com" not in copy
    pillars = _read("lib/components/ModelPillars.svelte")
    for heading in ("Our approach", "How we measure it", "What you see"):
        assert f"<dt>{heading}</dt>" in pillars


@then("it shows the three apps a member gets and that they open through the hub at the Forever launch")
def apps_at_launch(landing: str) -> None:
    assert "MEMBER_APPS" in landing
    assert "RaidWeek" not in landing
    assert "FOREVER_LAUNCH" in landing and '<p class="opens">' in landing
    copy = _read("lib/landing.ts")
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
    "REQ-HUB-FRONT-002 The public Hub features page shall show what everyone, raiders and officers can do in the raid "
    "analyzer, the guild bank and Discord with the officers' Google Drive, mark the steps up to the viewer's tier, and "
    "name only permissions the hub's RBAC table gives that tier",
)
def test_hub_features() -> None:
    pass


@given("the Hub features page", target_fixture="features")
def features() -> str:
    return _read("routes/features/+page.svelte")


@then("it lists the raid analyzer, the guild bank and Discord and Drive, each with a step for every tier")
def three_apps() -> None:
    access = _read("lib/access.ts")
    for app in ("Raid analyzer", "Guild bank", "Discord and Drive"):
        assert f"title: '{app}'" in access
    test = _read("lib/access.test.ts")
    assert "for (const app of APPS) expect(app.rows.map((r) => r.tier)).toEqual([...FEATURE_TIERS]);" in test


@then("it marks the steps up to the viewer's tier, read from their session, and shows super admins the officers' steps")
def marks_by_tier(features: str) -> None:
    assert "unlocked(row, shownAs)" in features
    assert "tierOf(session)" in features
    assert "let shownAs = $derived(featureTier(tier));" in features


@then("a unit test fails if a step names a permission the RBAC table lacks or gives another tier")
def rbac_drift_test() -> None:
    test = _read("lib/access.test.ts")
    assert "services/api/src/toads_api/rbac/permissions.py" in test
    assert "puts each permission in the tier that first holds it" in test


@then("it is in the public nav, the top bar's tier chip opens it and the old toolkit address redirects to it")
def discoverable() -> None:
    assert "{ href: '/features', label: 'Hub features' }" in _read("lib/nav.ts")
    layout = _read("routes/+layout.svelte")
    assert 'href="{base}/features/"' in layout
    assert "TIER_LABEL[tier]" in layout
    assert "goto(`${base}/features/`, { replaceState: true })" in _read("routes/toolkit/+page.svelte")


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


@then(
    "it walks a new member through claiming characters, their name, how we raid, the bank, the apps and the hub's "
    "features"
)
def welcome_steps(welcome: str) -> None:
    ids = re.findall(r"^    id: '(\w+)',$", welcome, re.MULTILINE)
    assert ids == ["character", "name", "model", "bank", "apps", "features"]
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
    "guild bank, logs analysis and raid assistance on every member page but Raid and Calendar, show officers every "
    "page as it is being built except the bank, which shows a Forever launch notice, and show super admins exactly "
    "the officers' view plus the Admin console",
)
def test_launch_hold() -> None:
    pass


@given("the launch hold", target_fixture="launch")
def launch() -> str:
    return _read("lib/launch.ts")


@then(
    "a raider's members nav is the hub, Raid and Calendar links and every other member page shows the coming-soon page"
)
def raider_coming_soon(launch: str) -> None:
    assert "export const LAUNCH_HOLD: boolean = __LAUNCH_HOLD__;" in launch
    for title in ("Guild bank management", "Logs analysis", "Raid assistance"):
        assert f"title: '{title}'" in launch
    layout = _read("routes/+layout.svelte")
    assert "heldNav(memberNav(officer, tier === 'admin'), tier)" in layout
    assert "{:else if hold === 'coming-soon'}\n    <ComingSoon {...me} />" in layout
    assert "const OPEN_TO_MEMBERS = ['/raid', '/calendar'];" in launch
    assert "gives raiders the coming-soon page on every member page" in _read("lib/launch.test.ts")
    assert "opens the Raid page and the Calendar to every signed-in tier" in _read("lib/launch.test.ts")


@then("an officer opens every page but the bank, which shows the Forever launch notice")
def officer_notice(launch: str) -> None:
    layout = _read("routes/+layout.svelte")
    assert "{:else if hold === 'forever-notice'}\n    <ForeverNotice {path} {...me} />" in layout
    assert "Coming with the Forever launch" in _read("lib/components/ForeverNotice.svelte")
    assert "const HELD_FOR_OFFICERS = ['/bank'];" in launch
    assert "opens every page to officers but the bank" in _read("lib/launch.test.ts")


@then("super admins see exactly what officers see, plus the Admin console")
def super_admin_as_officer(launch: str) -> None:
    assert "if (tier === 'officer' || tier === 'admin') return" in launch
    assert "gives super admins exactly the officers\\' view, with the Admin console open" in _read("lib/launch.test.ts")
    assert "heldNav(memberNav(officer, tier === 'admin'), tier)" in _read("routes/+layout.svelte")


@then("visitors and the public pages are never held")
def never_held(launch: str) -> None:
    assert "if (!hold || tier === 'visitor' || !isMemberPath(path)) return 'open';" in launch
    assert "leaves visitors and the public pages alone" in _read("lib/launch.test.ts")


@then("the real site waits for the session before a held page renders, so it never starts the page's own API calls")
def waits_for_session() -> None:
    layout = _read("routes/+layout.svelte")
    assert "LAUNCH_HOLD && !__PREVIEW__ && isMemberPath(path) && (session === undefined || sessionFailed)" in layout
    assert "__LAUNCH_HOLD__: JSON.stringify(process.env.PREVIEW !== '1' || process.env.LAUNCH_HOLD === '1')" in (
        WEB.parent / "vite.config.ts"
    ).read_text(encoding="utf-8")


@scenario(
    str(FEATURE),
    "REQ-HUB-FRONT-005 While the launch hold is on, the Bank tab shall show officers its intent, the features coming "
    "to it and a labelled mockup of stock, Discord requests, a ledger and a fairness view, and every signed-in member "
    "shall meet their own toad",
)
def test_tab_previews() -> None:
    pass


@given("the tab previews", target_fixture="previews")
def previews() -> str:
    return _read("lib/launch.ts")


@then("the Bank tab states its intent and lists what is coming")
def tabs_previewed(previews: str) -> None:
    assert "  '/bank': {\n    intent:" in previews
    notice = _read("lib/components/ForeverNotice.svelte")
    assert "TAB_PREVIEW[tab.href]" in notice
    assert "previews the bank tab with its intent" in _read("lib/launch.test.ts")


@then("the Bank tab shows the bankers' features to officers and a mockup labelled as sample data")
def bank_mockup(previews: str) -> None:
    assert "title: 'For bankers, and visible to officers'" in previews
    assert "{#if preview.mockup === 'bank'}<BankMockup />{/if}" in _read("lib/components/ForeverNotice.svelte")
    mockup = _read("lib/components/BankMockup.svelte")
    for part in ("In the bank", "Requests", "/bank request", "Ledger: who got what, and when", "Fairness:"):
        assert part in mockup, part
    assert '<span class="tag">Mockup</span>' in mockup


@then("every signed-in member has a rank toad, raiders the member toad")
def member_toad() -> None:
    toads = _read("lib/toads.ts")
    assert "raider: { id: 'ranks/member', label: 'Member' }" in toads
    for name in ("member", "member-badge"):
        assert (WEB.parent / "static" / "logos" / "ranks" / f"{name}.svg").is_file()


@then("raiders meet their toad on the coming-soon page, officers on the held bank tab, and everyone on the hub home")
def toad_greeting() -> None:
    for component in ("ComingSoon", "ForeverNotice"):
        assert "<ToadGreeting {name} {...facts} />" in _read(f"lib/components/{component}.svelte"), component
    layout = _read("routes/+layout.svelte")
    assert "{#if signedIn && isHubHome}\n      <ToadGreeting {...me} />" in layout


@scenario(
    str(FEATURE),
    "REQ-HUB-FRONT-006 The public Story page's tagline and story shall come from the repository, so a merge and the "
    "deploy that follows change them without editing the server",
)
def test_story_in_repo() -> None:
    pass


@given("the Story page's words", target_fixture="story")
def story() -> str:
    return (ROOT / "services" / "api" / "src" / "toads_api" / "community" / "story.py").read_text(encoding="utf-8")


@then("the API serves the tagline and story from the repository, not from config/community.yaml")
def served_from_repo(story: str) -> None:
    assert "TAGLINE = (" in story and "STORY: tuple[str, ...] = (" in story
    service = (ROOT / "services" / "api" / "src" / "toads_api" / "community" / "service.py").read_text(encoding="utf-8")
    assert "tagline=story.TAGLINE," in service and "story=list(story.STORY)," in service
    config = (ROOT / "services" / "api" / "src" / "toads_api" / "community" / "config.py").read_text(encoding="utf-8")
    assert "tagline:" not in config and "story:" not in config
    assert "tagline:" not in (ROOT / "config" / "community.example.yaml").read_text(encoding="utf-8")


@then("the static preview shows the same words")
def preview_matches() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "story", ROOT / "services" / "api" / "src" / "toads_api" / "community" / "story.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    mock = _read("lib/mock/community.ts").replace("\\'", "'")
    for words in (module.TAGLINE, *module.STORY):
        assert f"'{words}'" in mock, words


@scenario(
    str(FEATURE),
    "REQ-HUB-FRONT-007 While the launch hold is on, the story page shall show our story alone: the hero, the Discord "
    "link and the story, without recruiting, progression, highlights or news",
)
def test_public_hold() -> None:
    pass


@given("the public launch hold", target_fixture="story_route")
def story_route() -> str:
    return _read("routes/story/+page.svelte")


@then("the story page shows only the story while the hold is on and the full story page after it")
def story_only(story_route: str) -> None:
    assert "<LiveStory storyOnly={LAUNCH_HOLD} />" in story_route
    page = _read("lib/StoryPage.svelte")
    assert "{#if !storyOnly}" in page and "storyOnly = false" in page


@then("the homepage and every public tab stay open to visitors")
def public_site_open() -> None:
    assert "<Landing " in _read("routes/+page.svelte")
    layout = _read("routes/+layout.svelte")
    assert "{#each PUBLIC_NAV as item}" in layout
    assert "isHeldPublic" not in layout


@scenario(
    str(FEATURE),
    "REQ-HUB-FRONT-008 Every page shall show The Regular toad as its browser tab icon, as an SVG with an ICO fallback "
    "and a home-screen icon",
)
def test_tab_icon() -> None:
    pass


@given("the page shell", target_fixture="shell")
def shell() -> str:
    return _read("app.html")


@then("it links the toad as an SVG icon, an ICO icon and an Apple touch icon under the site's asset path")
def icon_links(shell: str) -> None:
    assert '<link rel="icon" href="%sveltekit.assets%/favicon.ico" sizes="32x32" />' in shell
    assert '<link rel="icon" href="%sveltekit.assets%/favicon.svg" type="image/svg+xml" />' in shell
    assert '<link rel="apple-touch-icon" href="%sveltekit.assets%/apple-touch-icon.png" />' in shell


@then("the SVG icon is The Regular toad from the logo set and the icon files are in the web app's static folder")
def icon_files() -> None:
    static = WEB.parent / "static"
    assert (static / "favicon.svg").read_bytes() == (static / "logos" / "01-the-regular.svg").read_bytes()
    assert (static / "favicon.ico").read_bytes()[:4] == b"\x00\x00\x01\x00"
    assert (static / "apple-touch-icon.png").read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
