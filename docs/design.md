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
