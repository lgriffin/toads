# Toads Hub

Discord-authenticated web app for the Toads guild (Spineshatter EU). It unifies Warcraft Logs reports,
the WCL Analyzer's analysis, raid signups, screenshots and the guild bank, and gives each member a
private performance page (/me). Analysis is not re-implemented here: the worker uses `wcl-core` and
the API reads through `wcl-store`, both published from `lgriffin/warcraftlogs_project`.

## Layout

- `apps/web/` SvelteKit + TypeScript. Talks only to the API.
- `services/api/` FastAPI: auth, RBAC (`toads_api/rbac/`), routes. `toads_api.bank` is the adapter to ToadsBank
  (lgriffin/ToadsBank), which owns the guild bank's data; `toads_api.testing.fake_bank` stands in for it in dev and
  tests. See `docs/bank.md`.
- `services/worker/` RQ jobs; owns all Warcraft Logs traffic.
- `services/bot/` discord.py; no DB credentials, calls the API with a service token. `toads_bot.kit` builds two-way
  bots (a spec of bindings; site actions out, Discord events in) against `toads_api.bots`; see `docs/bots.md`.
- `packages/hub-db/` hub-only SQLAlchemy models (analyzer tables come from wcl-store).
- `infra/` compose, Caddyfile. `config/` raid days and Discord role map (config, not code).
- `tests/features/` EARS requirements as Gherkin, one file per epic. `docs/requirements.md` is generated.

## Commands

```bash
just setup      # uv sync + npm ci
just up         # dev stack on http://localhost:8080
just check      # every CI check that needs no network, Docker or database (scripts/dev.py check)
just dev types test   # any scripts/dev.py tasks, in order; `just fix` applies Ruff's fixes
just reqs       # regenerate docs/requirements.md
```

`scripts/dev.py` is the one list of checks: CI jobs, the justfile and a local run all call its tasks, and
`tests/step_defs/test_dev_gates.py` fails if a CI job stops running its tasks. `ci-success` is the one required check:
it needs every other job and fails if any failed, was cancelled or was skipped (`scripts/ci_gate.py`). A new CI job
goes in its `needs` and in `JOB_TASKS` or `OUTSIDE_DEV` in that test. The coverage floor is `fail_under` in
`pyproject.toml`; it only goes up (`scripts/ratchet.py` fails a PR that lowers it), and `diffcov` holds the lines a PR
changes to 90%.

## Rules

- Features before code: add or edit the scenario in `tests/features/` in the same PR as the code, then
  run `just reqs`. Every scenario needs a `REQ-<repo>-<epic>-<nnn>` id, one `@ears_*` tag and a persona tag.
- The RBAC table in the build spec is the source of truth for `toads_api/rbac/permissions.py` and its
  matrix test. Officer powers are always scoped to a raid day unless the holder is a global officer.
  Raid-day scope comes from the route path only, never from a body or query parameter.
- Every route declares `require(Permission.X)`; the frontend only hides buttons. Tier and RBAC checks stay in the
  route layer (`rbac/`, `community/deps.py`); services such as `community/service.py` hold rules only, over a
  repository protocol. `lint-imports` (contracts in `pyproject.toml`) enforces the layering in CI.
- Python 3.12, ruff (line length 120), mypy strict. No `latest` image tags.
- Config through environment only (pydantic-settings); keep each `.env.example` in sync. Never commit secrets.
- All changes go through PRs; never push directly to main.
- UI work in `apps/web` uses the Impeccable plugin (`.claude/settings.json`); see `docs/design.md`.
