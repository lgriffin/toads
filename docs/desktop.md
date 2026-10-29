# Toads Hub desktop app

The desktop app is the Toads Hub in its own window, for officers in particular: the live site (<https://toads.gg>)
with native menus, a tray icon and desk alerts around it. Every page, permission and launch hold rule is still the
site's, so nothing ships in the app that the site does not already do, and a site deploy reaches the app at once.
Requirements: `tests/features/hub_app.feature` (REQ-HUB-APP-001..005). Code: `apps/desktop/`.

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
  taskbar icon, the tray menu lists it, and a notification pops up when something new arrives. Turn the alerts off
  under **File → Notify me about new desk work**.
- **Tray.** The tray icon opens the hub, shows your desk and has shortcuts to the officer console and your nights.
  **File → Keep running in the tray when closed** keeps the alerts coming after you close the window.
- **Links out.** Google Docs, Warcraft Logs, Discord channels and every other site open in your normal browser, so
  you keep your own Google sign-in there. Right-click a link for **Open link in browser** or **Copy link address**.
- **Theme.** The app follows the theme you pick on the site (Display, in the account menu): Dark, Light or Match my
  device. The title bar, the window while a page loads and the offline page match it, and it opens in it next time.
- **Window.** It reopens where you left it. If the hub can't be reached it says so and retries when you're back
  online. Opening the app again brings the open window forward instead of starting a second copy.

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

**Security.** The window is sandboxed with context isolation, no Node integration, no preload and no webviews. Only
the hub's origin and Discord's sign-in pages (`/oauth2/authorize`, `/login`, `/register`) load in it; other http(s),
`mailto:` and `discord:` links go to the default browser and every other scheme is refused. The hub may ask for
notifications and clipboard writes, and any page for fullscreen; every other permission is refused. The user agent
drops the `Electron/` token so Discord treats the window as Chrome. Discord sign-in needs no change in the Discord
portal: the window loads toads.gg itself, so the redirect URI stays `https://toads.gg/auth/callback`.

**Tests.** `test/*.test.ts` cover the hub address, link and permission rules, the menus for each tier, the desk, the
window position and settings. `test/smoke/smoke.cjs` starts the built app against a fake hub (`fake-hub.cjs`) and
checks the window, links to the browser, sign-in reaching the main process's requests, the officer menus, a desk
notification and the offline page. CI's `desktop` job runs all of them, packs the Linux app and audits the
dependencies.

### Releasing

1. Bump `version` in `apps/desktop/package.json` (and `npm install` to update the lock file) in a PR, and merge it.
2. Tag the merge commit `desktop-v<version>` and push the tag:
   `git tag desktop-v0.2.0 && git push origin desktop-v0.2.0`.
3. The **Desktop app** workflow (`.github/workflows/desktop.yml`) builds the Windows, macOS (Apple silicon and Intel)
   and Linux installers and publishes them as a GitHub release. It fails if the tag and the version differ.

Every PR that changes `apps/desktop` builds the same installers as workflow artifacts, so they can be tried before
merge. The app does not update itself yet: officers download the new installer from the release.

When the launch hold is lifted in `apps/web/src/lib/launch.ts`, the app's menus open up for raiders with the site's
deploy, through `/desktop.json`; a desktop release then only refreshes the bundled fallback.

### Signing

Unsigned builds work but warn on first launch. To sign, add these repository secrets; the workflow passes them to
electron-builder, which signs (and on macOS notarizes) when they are set:

| Secret | What |
| --- | --- |
| `DESKTOP_CSC_LINK`, `DESKTOP_CSC_KEY_PASSWORD` | The code-signing certificate (base64 .p12) and its password. On macOS a "Developer ID Application" certificate from an Apple Developer account; on Windows an OV or EV code-signing certificate. |
| `DESKTOP_APPLE_ID`, `DESKTOP_APPLE_APP_SPECIFIC_PASSWORD`, `DESKTOP_APPLE_TEAM_ID` | For notarizing the Mac app. |

Without them, the Mac app is ad-hoc signed so that it starts on Apple silicon at all.
