"""REQ-HUB-APP: the officers' desktop app (apps/desktop, docs/desktop.md).

The app's behaviour is tested by its own vitest suite and a smoke run of the built app against a fake hub (CI's
`desktop` job); these steps check those tests and the app's wiring exist and say what the scenarios promise.
"""

import json
import re
from pathlib import Path
from typing import Any

import yaml
from pytest_bdd import given, scenario, then

ROOT = Path(__file__).resolve().parents[2]
FEATURE = ROOT / "tests" / "features" / "hub_app.feature"
APP = ROOT / "apps" / "desktop"


def _read(relative: str) -> str:
    return (APP / relative).read_text(encoding="utf-8")


@scenario(
    str(FEATURE),
    "REQ-HUB-APP-001 The desktop app shall open the live hub in its own window, sign in with Discord inside that "
    "window and keep the member signed in between launches",
)
def test_window_and_sign_in() -> None:
    pass


@scenario(
    str(FEATURE),
    "REQ-HUB-APP-002 The desktop app's Hub, Me and Officers menus shall be the website's own top bar for the "
    "signed-in member, so an officer sees only the raid nights they run and a raider sees what the launch hold shows "
    "them",
)
def test_menus() -> None:
    pass


@scenario(
    str(FEATURE),
    "REQ-HUB-APP-003 If a page links away from the hub or Discord's sign-in, then the desktop app shall open it in the "
    "default browser, never in the app, and the app window shall have no Node access and grant the hub only "
    "notifications, clipboard writes and fullscreen",
)
def test_links_and_sandbox() -> None:
    pass


@scenario(
    str(FEATURE),
    "REQ-HUB-APP-004 When new work reaches an officer's raid leader desk, the desktop app shall raise one native "
    "notification and count what waits on the dock or taskbar, from the tray as well when the window is closed",
)
def test_desk_alerts() -> None:
    pass


@scenario(
    str(FEATURE),
    "REQ-HUB-APP-005 When a desktop-v tag matching the app's version is pushed, the desktop workflow shall build the "
    "Windows, macOS and Linux installers and publish them as a GitHub release",
)
def test_release() -> None:
    pass


@scenario(
    str(FEATURE),
    "REQ-HUB-APP-006 The desktop app shall stay consistent with the website it shows: the live site's top bar lists "
    "and launch hold, its account menu and Log out, and the reader's theme",
)
def test_consistent_with_the_site() -> None:
    pass


@given("the desktop app", target_fixture="main")
def main() -> str:
    return _read("src/main.ts")


@then("it opens https://toads.gg, or a hub given with --hub or TOADS_HUB_URL that is https or plain http to localhost")
def opens_the_hub() -> None:
    hub = _read("src/hub.ts")
    assert "export const LIVE_HUB = 'https://toads.gg';" in hub
    assert "'--hub='" in hub and "env.TOADS_HUB_URL" in hub
    tests = _read("test/hub.test.ts")
    assert "refuses plain http elsewhere" in tests and "fails on a bad override" in tests


@then("Discord's authorize and login pages stay in the window and the hub's session lives in one persistent partition")
def sign_in_in_window(main: str) -> None:
    assert "const DISCORD_SIGN_IN = ['/oauth2/authorize', '/login', '/register'];" in _read("src/links.ts")
    assert "const PARTITION = 'persist:toads';" in main
    assert main.count("partition: PARTITION") == 1


@then("a smoke run of the built app signs in against a fake hub and its own requests carry the session cookie")
def smoke_signs_in() -> None:
    smoke = _read("test/smoke/smoke.cjs")
    assert "await click('login');" in smoke
    assert "await until('the officer menus'" in smoke
    assert "credentials: 'include'" in _read("src/main.ts")
    assert "test/smoke/smoke.cjs" in json.loads(_read("package.json"))["scripts"]["smoke"]


@then(
    "the window comes back where it was, shows an offline page with a retry when the hub cannot be reached, and a "
    "second launch focuses the first"
)
def native_window(main: str) -> None:
    assert "restore(" in main and "window-state.json" in main
    assert "loadFile(staticFile('offline.html')" in main
    assert 'id="retry"' in _read("static/offline.html")
    assert "await until('the offline page'" in _read("test/smoke/smoke.cjs")
    assert "requestSingleInstanceLock()" in main and "app.on('second-instance', showWindow);" in main


@then("its menus are built from the web app's nav, launch hold and access modules, compiled in rather than copied")
def menus_from_the_site() -> None:
    menus = _read("src/menus.ts")
    for module in ("nav", "launch", "access", "absences"):
        assert f"from '../../web/src/lib/{module}';" in menus, module
    for fn in ("hubMenu(", "officerMenu(", "heldNav(", "tierOf("):
        assert fn in menus, fn
    assert "only the nights they run" in _read("test/menus.test.ts")


@then(
    "they follow the member's /api/session after every page load, with keyboard shortcuts for the hub pages and the "
    "officer tools"
)
def menus_follow_session(main: str) -> None:
    assert "contents.on('did-navigate', () => void refresh());" in main
    assert "getJson('/api/session')" in main and "menusFor(parseSession(answer), site)" in main
    menus = _read("src/menus.ts")
    assert "`CmdOrCtrl+${n + 1}`" in menus and "`CmdOrCtrl+Shift+${n + 1}`" in menus


@then(
    "links to other sites, the rest of Discord and new windows open in the default browser, and other schemes are "
    "refused"
)
def links_to_browser(main: str) -> None:
    assert "setWindowOpenHandler" in main and "return { action: 'deny' };" in main
    assert "contents.on('will-navigate'" in main and "contents.on('will-redirect'" in main
    tests = _read("test/links.test.ts")
    assert "https://discord.com/channels/1/2" in tests and "file:///etc/passwd" in tests
    assert "await until('links in the browser'" in _read("test/smoke/smoke.cjs")


@then("the window runs sandboxed with context isolation, no Node integration and no webviews")
def sandboxed(main: str) -> None:
    prefs = main[main.index("webPreferences: {") :].split("}", 1)[0]
    for setting in ("contextIsolation: true", "sandbox: true", "nodeIntegration: false", "webviewTag: false"):
        assert setting in prefs, setting
    assert "preload" not in prefs
    assert "will-attach-webview" in main


@then("every other permission request is refused, even from the hub")
def permissions(main: str) -> None:
    links = _read("src/links.ts")
    allowed = re.search(r"const HUB_PERMISSIONS = new Set\(\[(.*?)\]\);", links)
    assert allowed and allowed.group(1) == "'notifications', 'clipboard-sanitized-write', 'fullscreen'"
    assert "setPermissionRequestHandler" in main and "setPermissionCheckHandler" in main


@then(
    "it reads the officer's desk every two minutes and on focus, counts it on the badge and lists it in the tray in "
    "the hub's words"
)
def reads_the_desk(main: str) -> None:
    assert "const DESK_POLL_MS = 2 * 60 * 1000;" in main
    assert "window.on('focus'" in main and "getJson('/api/desk')" in main
    assert "app.setBadgeCount(count);" in main and "setOverlayIcon" in main
    assert "import { deskLines, type DeskSummary } from '../../web/src/lib/community-api';" in _read("src/desk.ts")


@then(
    "it notifies only about what grew, never on the first look, and an officer can turn that off or keep the app in "
    "the tray"
)
def notifies_on_growth(main: str) -> None:
    assert "stays quiet on the first look" in _read("test/desk.test.ts")
    assert "await until('a desk notification'" in _read("test/smoke/smoke.cjs")
    assert "if (news && prefs.deskNotifications) notify(news);" in main
    assert "if (prefs.keepInTray && !quitting)" in main


@given("the desktop workflow", target_fixture="workflow")
def workflow() -> dict[Any, Any]:
    data = yaml.safe_load((ROOT / ".github" / "workflows" / "desktop.yml").read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


@then(
    "it builds on Windows, macOS and Linux, checks the tag against the app's version, and publishes the installers on "
    "a tag only"
)
def builds_everywhere(workflow: dict[Any, Any]) -> None:
    on = workflow[True]  # PyYAML reads the bare `on:` key as True
    assert on["push"]["tags"] == ["desktop-v*"]
    build = workflow["jobs"]["build"]
    assert {m["platform"] for m in build["strategy"]["matrix"]["include"]} == {"win", "mac", "linux"}
    assert any('"desktop-v${version}"' in str(s.get("run", "")) for s in build["steps"])
    release = workflow["jobs"]["release"]
    assert release["if"] == "startsWith(github.ref, 'refs/tags/desktop-v')"
    assert release["permissions"] == {"contents": "write"}
    assert workflow["permissions"] == {"contents": "read"}


@then("CI's desktop job runs the app's types, tests, smoke run, packaging and audit on every PR")
def ci_job() -> None:
    ci = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))
    runs = " ".join(str(s.get("run", "")) for s in ci["jobs"]["desktop"]["steps"])
    for task in ("desktop-check", "desktop-test", "desktop-smoke", "desktop-pack", "desktop-audit"):
        assert task in runs, task
    assert "desktop" in ci["jobs"]["ci-success"]["needs"]


WEB = ROOT / "apps" / "web"


def _web(relative: str) -> str:
    return (WEB / relative).read_text(encoding="utf-8")


@then(
    "it reads the site's /desktop.json after every page load and draws its menus from it, keeping the bundled lists "
    "only until the site answers"
)
def reads_the_site(main: str) -> None:
    assert "export const DESKTOP_PATH = '/desktop.json';" in _web("src/lib/desktop.ts")
    endpoint = _web("src/routes/desktop.json/+server.ts")
    assert "export const prerender = true;" in endpoint and "json(desktopSite())" in endpoint
    assert "getJson(DESKTOP_PATH)" in main and "site = parseDesktopSite(siteAnswer) ?? site;" in main
    assert "export const BUNDLED_SITE: DesktopSite = desktopSite();" in _read("src/menus.ts")
    assert "lifts the launch hold, without a new release" in _read("test/menus.test.ts")
    assert "the live site's lists win over the bundled ones" in _read("test/smoke/smoke.cjs")


@then(
    "its Me menu is the site's account menu, with the site's sign-in wording and a Log out that posts to the hub as "
    "the site does"
)
def account_menu(main: str) -> None:
    layout = _web("src/routes/+layout.svelte")
    assert "accountMenu(tier)" in layout and "{SIGN_IN.label}" in layout and "action={SIGN_OUT.href}" in layout
    menus = _read("src/menus.ts")
    assert "accountMenu(tier, site.launch_hold, site.nav.accountMenu)" in menus and "SIGN_IN.label" in menus
    assert "hubUrl(hub, SIGN_OUT.href), { method: 'POST'" in main
    assert "await until('signed out'" in _read("test/smoke/smoke.cjs")


@then(
    "it takes the reader's theme from the site's theme-color tag for its window, title bar and offline page, and "
    "remembers it for the next launch"
)
def follows_the_theme(main: str) -> None:
    assert "contents.on('did-change-theme-color'" in main and "nativeTheme.themeSource = prefs.theme;" in main
    assert "import { THEME_COLOR } from '../../web/src/lib/display';" in _read("src/theme.ts")
    assert "theme: ThemeSource;" in _read("src/prefs.ts")
    assert 'name="theme-color"' in _web("src/lib/display.ts") and "meta.name = 'theme-color';" in _web(
        "static/display.js"
    )
    assert "await until('the remembered theme'" in _read("test/smoke/smoke.cjs")


@then(
    "the web app's tests hold every top bar link to a page on the site and the theme-color values to theme.css's page "
    "colours"
)
def drift_tests() -> None:
    assert "is a page on the site" in _web("src/lib/desktop.test.ts")
    assert "keeps the theme-color values on theme.css's page colour" in _web("src/lib/display.test.ts")
