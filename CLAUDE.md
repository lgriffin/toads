# Toads Hub

Discord-authenticated web app for the Toads guild (Spineshatter EU). It unifies Warcraft Logs reports,
the WCL Analyzer's analysis, raid signups, screenshots and the guild bank, and gives each member a
private performance page (/me). Analysis is not re-implemented here: the worker uses `wcl-core` and
the API reads through `wcl-store`, both published from `lgriffin/warcraftlogs_project`.

## Layout

- `apps/web/` SvelteKit + TypeScript. Talks only to the API.
- `services/api/` FastAPI: auth, RBAC (`toads_api/rbac/`), routes.
- `services/worker/` RQ jobs; owns all Warcraft Logs traffic.
- `services/bot/` discord.py; no DB credentials, calls the API with a service token.
- `packages/hub-db/` hub-only SQLAlchemy models (analyzer tables come from wcl-store).
- `infra/` compose, Caddyfile. `config/` raid days and Discord role map (config, not code).
- `tests/features/` EARS requirements as Gherkin, one file per epic. `docs/requirements.md` is generated.

## Commands

```bash
just setup      # uv sync + npm ci
just up         # dev stack on http://localhost:8080
just test       # lint, mypy strict, pytest, svelte-check, vitest, reqs
just reqs       # regenerate docs/requirements.md
```

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
