# Toads Hub desktop app

The desktop app is the Toads Hub in its own window, for officers in particular: the live site (<https://toads.gg>)
with native menus, a tray icon and desk alerts around it. Every page, permission and launch hold rule is still the
site's, so nothing ships in the app that the site does not already do, and a site deploy reaches the app at once.
Requirements: `tests/features/hub_app.feature` (REQ-HUB-APP-001..007). Code: `apps/desktop/`.

## For officers

**Install.** Download the installer for your computer from the latest `desktop-v…` release on GitHub:

| Computer | File | First launch |
| --- | --- | --- |
| Windows | `Toads-Hub-<version>-win-x64.exe` | Windows SmartScreen may say it doesn't recognise the app: **More info → Run anyway**. |
| Mac with Apple silicon (M1 and later) | `Toads-Hub-<version>-mac-arm64.dmg` | Drag Toads Hub to Applications. The first time, **right-click → Open**, then **Open**. |
| Intel Mac | `Toads-Hub-<version>-mac-x64.dmg` | As above. |
| Linux | `.AppImage` (any distro) or `.deb` (Debian, Ubuntu) | Make the AppImage executable, or `sudo apt install ./Toads-Hub-….deb`. |

The warnings are there because the builds are not yet signed with a paid Apple or Windows certificate (see
[Signing](#signing)). If macOS says the app "is damaged", run `xattr -cr "/Applications/Toads Hub.app"` once.

**Sign in.** Choose **Me → Log in with Discord**. Discord's own page opens inside the app; sign in there as you would
in a browser, or scan the QR code with the Discord app on your phone. The app keeps you signed in between launches
until you choose **Me → Log out** (or Log out in the site's account menu).

**What the app adds to the site:**

- **Menus.** Hub, Me and Officers are the site's own top bar and account menus, so you see exactly the pages the site
  shows you, and only the raid nights you run. They come from the live site, so a new page or the end of the launch
  hold shows up in the app as soon as the site has it, without a new install. Shortcuts: Ctrl+1… (⌘1… on a Mac) for the Hub pages, Ctrl+Shift+1… for the officer
  tools, Ctrl+0 for Me, Alt+← and Alt+→ (⌘[ and ⌘]) for back and forward.
- **Desk alerts.** For officers, the app checks your raid leader desk (applications, Discord posts to curate, highlights
  and spotlights waiting on you) every two minutes and whenever you switch to it. The count shows on the dock or
  taskbar icon (on Windows as a number, up to 9+), the tray menu lists it under **Raid leader desk** or says nothing
  is waiting, and a notification pops up when something new arrives. Turn the alerts off
  under **File → Notify me about new desk work**.
- **Tray.** The tray icon opens the hub, shows your desk and has shortcuts to the officer console and your nights.
  **File → Keep running in the tray when closed** keeps the alerts coming after you close the window.
- **Links out.** Google Docs, Warcraft Logs, Discord channels and every other site open in your normal browser, so
  you keep your own Google sign-in there. Right-click a link for **Open link in browser** or **Copy link address**, and
  anywhere else on a page for **Back**, **Forward** and **Reload**.
- **Help.** **Help → Desktop app guide** opens this page; **Open Toads Hub in your browser** opens the site there.
- **Updates.** See [Updates](#updates) below: install once, and new versions arrive by themselves.
- **Theme.** The app follows the theme you pick on the site (Display, in the account menu): Dark, Light or Match my
  device. The title bar, the window while a page loads and the offline page match it, and it opens in it next time.
- **Window.** It reopens where you left it. If the hub can't be reached it says so and tries again by itself (after
  10 seconds, then 20, 40 and every 2 minutes, and at once when you're back online), or now with **Try again now**. Opening the app again brings the open window forward instead of starting a second copy.

### Updates

You install the app once. After that it looks for a new version shortly after it starts, every six hours while it
runs, and whenever you choose **Help → Check for updates…**.

- **Windows and Linux.** A new version downloads in the background. When it is ready the app asks to **Restart now**;
  choose **Later** and it installs the next time you quit the app. The AppImage replaces itself; the `.deb` asks for
  your password to install, as any package does.
- **Mac.** Until the app is signed with an Apple Developer ID (see [Signing](#signing)), macOS does not let it replace
  itself. Instead it tells you a new version is out and **Open release page** takes you to the download: drag the new
  Toads Hub into Applications over the old one. Your sign-in and settings are kept. Once the app is signed, Macs update
  like Windows.

Most changes need no update at all: the window shows the live site, and the menus come from it.

## For maintainers

```bash
just setup                         # includes apps/desktop's npm ci
just desktop                       # build and run against the dev stack on http://localhost:8080
just desktop https://toads.gg      # or any https hub
just dev desktop-check desktop-test desktop-smoke   # types, unit tests, smoke run (Linux needs xvfb-run)
```

The app opens `https://toads.gg` unless `--hub=<url>` or `TOADS_HUB_URL` names another hub; it refuses anything but
https, or plain http to localhost.

**How it is built.** `src/main.ts` is the Electron main process; the rest of `src/` is plain logic with vitest tests.
`build.mjs` bundles it with esbuild, and the menus import `apps/web/src/lib/nav.ts`, `launch.ts`, `access.ts` and
`absences.ts` directly, so the rules are the site's own. The desk lines come from the site's `deskLines`.

**Staying in step with the site.** The app takes everything that changes with a site deploy from the live site, and
bundles only the rules and a fallback:

| What | From the site | In the app |
| --- | --- | --- |
| Top bar and account menu lists, launch hold | `GET /desktop.json` (`apps/web/src/lib/desktop.ts`, prerendered with each build) | Read after every page load alongside `/api/session`; the bundled copy (`BUNDLED_SITE`) is used only until the site answers, and a contract it does not know keeps the last good lists |
| Sign-in and Log out | `SIGN_IN`, `SIGN_OUT`, `ACCOUNT_MENU` in `nav.ts` | The Me menu uses the same labels; Log out posts to `/auth/logout` as the site's form does |
| Theme | The `theme-color` tag (`display.ts` `themeColor`, `static/display.js`): the page colour of a picked theme, none for Match my device | `did-change-theme-color` and each page load set `nativeTheme.themeSource` and the window colour (`src/theme.ts`), remembered in `prefs.json` |

Change a field of `/desktop.json` in a way an older app would misread only with a new `DESKTOP_CONTRACT`. The web
app's tests hold every top bar link to a real page (`desktop.test.ts`) and the theme-color values to `theme.css`'s
`--ink` (`display.test.ts`); the smoke run checks the live lists, the theme and Log out against the fake hub.

**Look.** The app's own surfaces wear the site's design. `static/offline.html` uses the colour tokens of
`apps/web/src/lib/theme.css` for both themes (picked by `prefers-color-scheme`, which follows the app's native theme)
and the top bar's mark and Cinzel wordmark, which `build.mjs` copies into `static/shared/` (not committed). In
`resources/`, `icon.png` is the Windows and Linux icon and `icon-mac.png` the same art inset on Apple's icon grid for the
Dock; `tray.png` is 16 px with `@2x` and `@3x`, so it sits right in the macOS menu bar and a Windows tray at any
scaling; `badge-1.png` to `badge-9plus.png` (each with `@2x`) are the numbered Windows taskbar overlays.

**Security.** The window is sandboxed with context isolation, no Node integration, no preload and no webviews. Only
the hub's origin and Discord's sign-in pages (`/oauth2/authorize`, `/login`, `/register`) load in it; other http(s),
`mailto:` and `discord:` links go to the default browser and every other scheme is refused. The hub may ask for
notifications and clipboard writes, and any page for fullscreen; every other permission is refused. The user agent
drops the `Electron/` token so Discord treats the window as Chrome. Discord sign-in needs no change in the Discord
portal: the window loads toads.gg itself, so the redirect URI stays `https://toads.gg/auth/callback`.

**Tests.** `test/*.test.ts` cover the hub address, link and permission rules, the menus for each tier, the desk, the
window position and settings. `test/smoke/smoke.cjs` starts the built app against a fake hub (`fake-hub.cjs`) and
checks the window, links to the browser, sign-in reaching the main process's requests, the officer menus, a desk
notification and the offline page with its mark and countdown. CI's `desktop` job runs all of them, packs the Linux
app and audits the dependencies.

### Releasing

1. Bump `version` in `apps/desktop/package.json` (and `npm install` to update the lock file) in a PR, and merge it.
2. Tag the merge commit `desktop-v<version>` and push the tag:
   `git tag desktop-v0.2.0 && git push origin desktop-v0.2.0`.
3. The **Desktop app** workflow (`.github/workflows/desktop.yml`) builds the Windows, macOS (Apple silicon and Intel)
   and Linux installers and publishes them as a GitHub release. It fails if the tag and the version differ.

Every PR that changes `apps/desktop` builds the same installers as workflow artifacts, so they can be tried before
merge.

**Updates.** electron-builder's `publish` setting (`package.json`, GitHub, `lgriffin/toads`) makes every build write
the update feeds `latest.yml` (Windows), `latest-mac.yml` and `latest-linux.yml` (AppImage and deb), and bakes
`app-update.yml` into the app. The release carries them with the blockmaps (for downloading only what changed) and
the Mac zips that Squirrel.Mac installs from. The installed app (`src/update.ts`, electron-updater) reads the feed from
the repository's **latest** release, so a release of anything else in this repository must be published with
`--latest=false` or every app stops finding its updates. A copy run from source (`just desktop`) never updates.

| Platform | Unsigned (today) | Signed |
| --- | --- | --- |
| Windows (NSIS) | Updates itself. electron-updater checks the publisher only when the running app was signed. | Updates itself, and checks the new installer is signed by the same publisher. |
| Linux AppImage / deb | Updates itself (Linux has no signing to check). The deb asks for a password through `pkexec`. | Same. |
| macOS | Cannot: Squirrel.Mac only installs an update signed by the running app's Developer ID, which an ad-hoc signature never matches. The app says a version is out and links its release page. | Updates itself. `build.mjs` turns this on when `CSC_LINK` is set for the Mac build. |

The first release with updates is the one that has to be installed by hand: a copy from before it has no updater.

When the launch hold is lifted in `apps/web/src/lib/launch.ts`, the app's menus open up for raiders with the site's
deploy, through `/desktop.json`; a desktop release then only refreshes the bundled fallback.

### Signing

Unsigned builds work but warn on first launch. To sign, add these repository secrets; the workflow passes them to
electron-builder, which signs (and on macOS notarizes) when they are set:

| Secret | What |
| --- | --- |
| `DESKTOP_CSC_LINK`, `DESKTOP_CSC_KEY_PASSWORD` | The code-signing certificate (base64 .p12) and its password. On macOS a "Developer ID Application" certificate from an Apple Developer account; on Windows an OV or EV code-signing certificate. |
| `DESKTOP_APPLE_ID`, `DESKTOP_APPLE_APP_SPECIFIC_PASSWORD`, `DESKTOP_APPLE_TEAM_ID` | For notarizing the Mac app. |

Without them, the Mac app is ad-hoc signed so that it starts on Apple silicon at all, and does not update itself.

What each costs and buys:

- **macOS: an Apple Developer Program membership** (US$99 a year, apple.com/developer). It gives the Developer ID
  Application certificate (export it as a .p12 for `DESKTOP_CSC_LINK`) and notarization (`DESKTOP_APPLE_*`, with an
  app-specific password from appleid.apple.com). This is what turns on Mac auto-updates and removes the "right-click →
  Open" and "is damaged" steps.
- **Windows: a code-signing certificate** (OV or EV, from a certificate authority, typically a few hundred dollars a
  year). Since 2023 the key has to live on a hardware token or a cloud HSM, so it cannot go in `DESKTOP_CSC_LINK`
  as a file; signing in CI then means a cloud signing service such as Azure Trusted Signing (a few dollars a month)
  and a change to desktop.yml. It only quiets SmartScreen: Windows updates already work unsigned.
- **Linux:** nothing to buy.
