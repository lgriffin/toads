# Design tooling

The hub's web app (`apps/web`, SvelteKit) is designed with [Impeccable](https://impeccable.style), a Claude Code plugin
(Apache 2.0) that gives the agent a design vocabulary and flags generic "AI slop" UI patterns.

## Setup

`.claude/settings.json` registers the `pbakaus/impeccable` marketplace, pinned to a release tag, and enables the
`impeccable` plugin. Claude Code asks to install it the first time you trust this folder; nothing else is needed.
Cloud sessions on claude.ai/code pick it up the same way.

To move to a newer release, change `ref` in `.claude/settings.json` to the new `skill-v…` tag in a pull request.
The plugin's hooks run a bundled detector binary on every edit, so the pin is deliberate: review the release notes
before bumping it.

## First run

Run `/impeccable init` once in `apps/web`. It interviews you about the product and writes `PRODUCT.md` (and
`DESIGN.md` via `/impeccable document`); commit both so every session shares them. Branding is toads and ponds,
never frogs.

## Everyday commands

- `/impeccable critique` or `/impeccable audit` on a page before a UI pull request
- `/impeccable polish`, `typeset`, `layout`, `colorize` to refine a view
- `/impeccable shape` to plan a new page before building it

The plugin's hooks check each UI edit and run a deeper pass when Claude stops; findings come back to the agent, not
to CI. Machine-local choices live in `.impeccable/config.local.json`, which is gitignored.

## Top bar, themes and easier reading

- **Top bar.** A signed-in member sees a Hub menu (Hub home, Raid, Logs, Highlights, Bank, then the public pages
  under "About the guild"), Me, an Officers menu for officers and super admins, and a menu under their name. Visitors
  keep the public nav. The menus are `NavMenu.svelte` (a disclosure: a button and a panel of links, Escape and a click
  outside close it) and their links come from `$lib/nav.ts`. The Officers menu lists only the raid nights the viewer
  runs and adds the Admin console for super admins; every page still checks its own permission. No toads sit in the
  top bar: they greet the member on the hub home and stand on Me.
- **Themes.** `src/lib/theme.css` holds the colour tokens for the dark theme (the pond at dusk, the default) and the
  light theme (the pond by day). Use the tokens, not hex values: `--cream` for strong text, `--bronze-hi` for
  headings, `--teal`/`--accent` for links, `--on-accent`/`--on-bronze` for text on a filled chip or button (never
  `--ink`, which is the page colour and turns pale by day), and `--warn-bg`, `--ok-bg`, `--bad-bg`, `--info-bg` for
  status chips. Text over the night-time key art sits in an `.always-dusk` element, which keeps the dark tokens.
- **Easier reading.** The display settings (in the account menu, or the Display menu for visitors) offer Dark, Light
  or Match my device, and Easier reading: bigger text, roomier lines, one plain typeface without capitals-only
  lettering, and underlined links. `static/display.js` applies the saved choice before the first paint (a file, so the
  CSP's `script-src 'self'` allows it); `$lib/display.ts` changes it afterwards. Keep their keys in step. Both also write a `theme-color` tag (the page
  colour of a picked theme, none for Match my device), which browsers tint their bars with and the desktop app follows
  (docs/desktop.md).
- **Checks.** The e2e suite runs axe on every page in the dark theme, and again in the light theme with easier reading,
  plus on each open top bar menu in both themes.

## Guardrails and touch

- **Ask once more before anything that cannot be undone.** Deleting an absence, unclaiming a character, rejecting an
  applicant or a claim: the first press shows what will happen and a way back (Keep it, or Cancel); only the second
  acts. Follow the same inline pattern (no `confirm()` dialog) for new destructive buttons. REQ-HUB-FRONT-011.
- **Touch targets.** On a coarse pointer every `.btn` is at least 44px tall (`routes/+layout.svelte`). Placeholders use
  `--muted`, so hints stay readable in both themes. REQ-HUB-FRONT-012.
- **Wide tables.** Put `use:scrollable` (`$lib/scrollable.ts`) on a `.scroll` box: it joins the tab order only while
  its table overflows, so keyboard users can scroll it.

