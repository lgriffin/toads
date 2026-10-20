# Toads admin guide

How to configure, run and look after everything the Toads guild runs: the Toads hub (this repository), the guild bank
service and addon ([ToadsBank](https://github.com/lgriffin/ToadsBank), whose own guide is
[docs/operations.md](https://github.com/lgriffin/ToadsBank/blob/main/docs/operations.md)), the Discord bots, the access
model, member settings, the reference comparison login and the community layer.

This guide is the map. The detailed rules live next to the code and are linked from each section:
[docs/admin.md](docs/admin.md) (super admins, break-glass, officer tokens), [docs/bank.md](docs/bank.md) (the hub's
side of the bank), [docs/bots.md](docs/bots.md) (the bot kit) and ToadsBank's
[docs/api.md](https://github.com/lgriffin/ToadsBank/blob/main/docs/api.md).

Never write a secret into this repository, an issue or a chat. Every secret below goes into the deployment's
environment or secret store only.

## Contents

1. [What runs where](#1-what-runs-where)
2. [Accounts and applications to create](#2-accounts-and-applications-to-create)
3. [First-time setup, in order](#3-first-time-setup-in-order)
4. [Settings reference](#4-settings-reference)
5. [Config files](#5-config-files)
6. [Access control](#6-access-control)
7. [Member settings and members' own Warcraft Logs keys](#7-member-settings-and-members-own-warcraft-logs-keys)
8. [The reference comparison login](#8-the-reference-comparison-login)
9. [The community layer](#9-the-community-layer)
10. [The guild bank](#10-the-guild-bank)
11. [Routine operations](#11-routine-operations)
12. [Rotating secrets](#12-rotating-secrets)
13. [Backups and restore](#13-backups-and-restore)
14. [Troubleshooting](#14-troubleshooting)
15. [Known limitations](#15-known-limitations)

## 1. What runs where

| Piece | Code | Process | Talks to |
| --- | --- | --- | --- |
| Web app | `apps/web` (SvelteKit) | `web` | the hub API only |
| Hub API | `services/api` (FastAPI) | `api` | Postgres, Redis, Discord, ToadsBank, Warcraft Logs (only the reference login's code exchange) |
| Worker | `services/worker` (RQ) | `worker` (jobs from Redis), `scheduler` (`toads-worker schedule`) | Warcraft Logs, Postgres, the hub API |
| Toad Bot | `services/bot` (`toads-bot`) | `bot` | Discord, the hub API (`/api/bot/*`) |
| Kit bots | `services/bot` (`toads-botkit`) | `bank-bot` (`TOADS_BOT_SPEC=bank`), optionally `relay` | Discord, the hub API (`/api/bots/*`, and `/api/bank/*` for the bank bot) |
| Migrations | `packages/hub-db` (`hub-db-migrate`), wcl-store (`toads-worker-migrate`) | `migrate`, `analyser-migrate` (one-shot) | Postgres |
| Reverse proxy | `infra/Caddyfile` | `caddy` | `/api/*` and `/auth/*` to the API, everything else to the web app |
| Guild bank | lgriffin/ToadsBank | `toadsbank-api`, `toadsbank-worker`, its own Postgres | the hub's `/api/bank/events` |
| Bank addon | lgriffin/ToadsBank `addon/` | in the WoW client | nothing: officers paste its export |

One Postgres database holds both the hub's tables (hub-db, migrations `0001` to `0013`) and the analyzer's tables
(wcl-store, from lgriffin/warcraftlogs_project). Redis holds sessions, logins in progress, the bank event dedup and the
RQ queues. Nothing in the code uses object storage yet (MinIO in the dev stack is a stand-in for later screenshot
uploads).

Only the worker imports the analyzer packages (`wcl-core`, `wcl-store`, `wcl-app`). They are pinned to one commit of
lgriffin/warcraftlogs_project in the root `pyproject.toml`; see [Bumping the analyzer](#bumping-the-analyzer).

### What the repository ships for deployment

`infra/docker-compose.yml` is the **dev** stack (`just up`): it signs in through a fake Discord, talks to a fake bank,
uses dev passwords, publishes Postgres and Redis ports and serves plain HTTP on port 8080.

`infra/docker-compose.prod.yml` is the **production** stack for one server, and [docs/deploy.md](docs/deploy.md) walks
through setting it up on a VPS. It drops the fakes and MinIO, keeps Postgres and Redis off the host's ports, reads the
Postgres password, domain and ACME email from `infra/.env`, serves the domain over HTTPS from `infra/Caddyfile.prod`
(Let's Encrypt, HSTS), and gives the bank bot its own `services/bot/.env.bank`. `scripts/server-setup.sh` prepares an
AlmaLinux 10 server and generates the internal secrets; `scripts/deploy.sh` deploys one commit of main, running both
migrations before any container is replaced; `.github/workflows/deploy.yml` runs it over SSH after CI passes on main
(off until the `DEPLOY_ENABLED` variable is `true`). Images are built on the server; CI still publishes none. ToadsBank
is deployed separately, next to the hub (its guide covers that).

## 2. Accounts and applications to create

| What | Where | Used by |
| --- | --- | --- |
| Discord application for the hub (OAuth2 login) with a bot user | Discord developer portal | API login (`TOADS_DISCORD_CLIENT_ID/SECRET`), the API's role reads (`TOADS_DISCORD_BOT_TOKEN`), the Toad Bot |
| A second Discord application for the bank bot | Discord developer portal | `bank-bot` (its `TOADS_DISCORD_BOT_TOKEN`) |
| A Warcraft Logs API client | warcraftlogs.com, client management | the worker's guild key (`TOADS_WCL_CLIENT_ID/SECRET` in the worker) and the reference login (the same values in the API) |
| Hosting for the hub stack and ToadsBank | your host | everything |
| Google Sheets shared "Anyone with the link: Viewer" | Google Drive | raid sheets import (`config/raid_sheets.yaml`) |

Discord application details:

- **Hub application.** Add the redirect `https://<hub>/auth/callback` under OAuth2 (it must equal
  `TOADS_DISCORD_REDIRECT_URI` exactly). The login asks for the scopes `identify guilds.members.read`. Invite its bot
  to the Toads server. The Toad Bot reads mirrored channels and members, so turn on the **Server Members** and
  **Message Content** privileged intents. It creates private interview rooms under the interview category, so it needs
  to manage channels there, and it needs to post in the `post_channels` of `config/community.yaml`. The exact
  permissions are in "Discord permissions for interview rooms" below.
- **Bank bot application.** Invite it with the `bot` and `applications.commands` scopes. It needs to send messages in
  the bank channels and DM members. It needs no privileged intents.
- One process per kit bot, each with its own application token ([docs/bots.md](docs/bots.md)). The Toad Bot and the
  API share the hub application's bot token.

### Discord permissions for interview rooms

**You**, to set this up: **Manage Server** on the Toads server (Discord only lets server managers add a bot), and
**Manage Channels** plus **Manage Roles** to make the interview category and set who sees it. Turn on Developer Mode
(User Settings > Advanced) so you can right-click a category and copy its id.

**The Toad Bot**, invited with the `bot` and `applications.commands` scopes and these permissions (permissions integer
`268520464`, so the invite link is
`https://discord.com/oauth2/authorize?client_id=<hub application id>&scope=bot+applications.commands&permissions=268520464`):

| Permission | Why |
| --- | --- |
| View Channels, Send Messages, Read Message History | Read mirrored channels, post the room's welcome |
| Embed Links | The applicant's answers are an embed in the room's first message |
| Manage Channels | Create `#interview-<character>` under the interview category |
| Manage Roles (shown as Manage Permissions on a channel) | Hide each room from everyone and let in only the applicant and the interviewers, then lock it when the application closes |

You can grant Manage Channels and Manage Permissions on the interview category alone instead of server-wide. If rooms
also let in officer roles (no `interviewers` set), the bot's own role must sit above those roles in Server Settings >
Roles. Privileged intents in the developer portal: **Server Members** (find the interviewers by username, and list each
raid night's role holders for the comp builder) and **Message Content** (mirrored channels).

The hub checks, when someone presses "Send application", that their Discord account is in the server (a bot-token
member lookup, which needs no extra permission); someone who is not gets a link to `discord_invite` instead.

### Getting the Toad Bot onto the server

The server admin's half is [docs/discord-setup.md](docs/discord-setup.md): a click-by-click guide for someone who is
not technical. Send it to them together with the invite link from step 3. The website side is:

1. **Use the hub's Discord application** at <https://discord.com/developers/applications>; its bot is the Toad Bot.
   Under **Bot**, switch on **Server Members Intent** and **Message Content Intent**. The bot token goes only into
   `TOADS_DISCORD_BOT_TOKEN` in the API's and the bot's env on the server.
2. **Name it.** Under **General Information**, name the application `Toad Bot` and give it the toad avatar. This is
   the name the server admin sees.
3. **Build the invite link** from the Application ID on **General Information**:
   `https://discord.com/oauth2/authorize?client_id=<APPLICATION ID>&scope=bot+applications.commands&permissions=268520464`.
   Open it yourself and check that the list shows View Channels, Send Messages, Embed Links, Read Message History,
   Manage Channels and Manage Roles, then send it to the server admin.
   The Toads application's link (Application ID `1561652680768626688`, not a secret) is
   <https://discord.com/oauth2/authorize?client_id=1561652680768626688&permissions=268520464&integration_type=0&scope=bot+applications.commands>,
   and docs/discord-setup.md already carries it.
4. **Put the admin's three numbers into `config/community.yaml`**: the category id, plus user ids rather than
   usernames, so a renamed account can't take an interviewer's place. These interviewers are the fallback: once a
   night's officers set its panel on **Officers > Recruitment** (docs/recruitment.md), that night's applicants meet
   the panel instead, with no restart:

   ```yaml
   interview_category_id: 1187654321098765432
   interviewers:
     - "123456789012345678"   # _gallagher
     - "234567890123456789"   # hadur117
   ```

5. **Restart the API and the Toad Bot**, check that the bot shows as online, and tell the admin to run the test (their
   Step 5). If no room appears, the bot's log names interviewers it couldn't find and any "Missing Permissions" from
   Discord.

## 3. First-time setup, in order

1. **Create the Discord applications and the Warcraft Logs client** (section 2). Note the Toads server's id, and the
   role and channel ids you need (Discord: Settings, Advanced, Developer Mode, then right-click to copy ids).
2. **Generate the shared secrets** (section 4, "Values that must match"): `TOADS_HUB_SERVICE_TOKEN`,
   `TOADS_BANK_SERVICE_TOKEN`, `TOADS_BANK_BOT_TOKEN` and `TOADS_CREDENTIALS_KEYS`. For the tokens use a long random
   value, for example `openssl rand -base64 32`. For the credentials key run `just credentials-key`.
3. **Write the config files** from their examples: `config/raid_days.yaml` (raid days, their Discord roles and
   channels, `global_officer_roles`), `config/community.yaml`, `config/raid_sheets.yaml` (section 5). The API refuses
   to start if a role id in `raid_days.yaml` is not a role in the server.
4. **Fill in each service's env** from `services/api/.env.example`, `services/worker/.env.example` and
   `services/bot/.env.example`, plus a separate env for the bank bot (section 4).
5. **Name the super admins and the break-glass admin**: `TOADS_SUPER_ADMIN_IDS` and `TOADS_BREAK_GLASS_ADMIN_ID` in the
   API's env (section 6).
6. **Deploy ToadsBank** (its guide), with `TOADSBANK_SERVICE_TOKEN` equal to the hub's `TOADS_BANK_SERVICE_TOKEN` and
   `TOADSBANK_EVENTS_URL=https://<hub>/api/bank/events`. Then set the hub's `TOADS_BANK_URL` to where the hub reaches
   `toadsbank-api` on the private network.
7. **Start Postgres and Redis, then the two migration jobs** (`hub-db-migrate` with the API's env,
   `toads-worker-migrate` with the worker's env), then the API, worker, scheduler, web and Caddy.
8. **Check**: `GET /healthz` on the API's own port (8000; Caddy forwards only `/api/*` and `/auth/*`) answers, signing in with Discord lands on `/hub`, and `/api/session` shows the
   raid days and officer days you expect. A super admin should see `super_admin: true` there.
9. **Start the bots**: the Toad Bot (`toads-bot`) and the bank bot (`toads-botkit` with `TOADS_BOT_SPEC=bank`).
10. **Register the guild bank** as a global officer or super admin: on the Bank page, or by importing the first
    snapshot (an `admin` accepting an export from an unknown bank registers it). Give each bank its `raidDay` (or none
    for a guild-wide bank) and its managers (section 10).
11. **Connect the reference comparison login** if officers want it (section 8).
12. **Hand out bank powers** to non-officers with grants or officer tokens (section 6).

## 4. Settings reference

All hub settings are environment variables with the `TOADS_` prefix, read by pydantic-settings. A missing required one
stops the process before it opens a port. The `.env.example` files are kept in sync with the code and carry comments.

### Values that must match

| Value | Where it must be identical |
| --- | --- |
| Hub service token | API, worker and every bot: `TOADS_HUB_SERVICE_TOKEN` |
| Bank service token | API `TOADS_BANK_SERVICE_TOKEN`, ToadsBank `TOADSBANK_SERVICE_TOKEN` (or `TOADSBANK_SERVICE_TOKEN_FILE`) |
| Bank bot token | API `TOADS_BANK_BOT_TOKEN`, bank bot `TOADS_BANK_BOT_TOKEN` |
| Credentials keys | API and worker: `TOADS_CREDENTIALS_KEYS` |
| Warcraft Logs client | worker `TOADS_WCL_CLIENT_ID/SECRET`, API `TOADS_WCL_CLIENT_ID/SECRET` (for the reference login) |
| Discord server | API, Toad Bot, bank bot: `TOADS_DISCORD_GUILD_ID` |
| Hub Discord application | API `TOADS_DISCORD_CLIENT_ID/SECRET` and `TOADS_DISCORD_BOT_TOKEN`, Toad Bot `TOADS_DISCORD_BOT_TOKEN`: all from the Toad Bot's application (checked at API startup) |
| Database | API and worker: `TOADS_DATABASE_URL` (the same database) |
| Redis | API and worker: `TOADS_REDIS_URL` |

The bank bot's token must differ from the hub service token: only the bank bot may act for a member.

### Hub API (`services/api/.env`)

| Variable | Required | Default | Meaning |
| --- | --- | --- | --- |
| `TOADS_DATABASE_URL` | yes | | Postgres URL, `postgresql+psycopg://...`. Secret. |
| `TOADS_REDIS_URL` | yes | | Redis URL. |
| `TOADS_DISCORD_CLIENT_ID` | yes | | Hub Discord application's client id (the Toad Bot's Application ID). If the bot token is from another application, the API logs a `discord_application_misconfigured` error (the site stays up). |
| `TOADS_DISCORD_CLIENT_SECRET` | yes | | Its client secret. Secret. |
| `TOADS_DISCORD_BOT_TOKEN` | yes | | The hub application's bot token: lists the server's roles at startup, reads members' roles when the bank bot acts for them, reads scheduled events for the next raid. Secret. |
| `TOADS_DISCORD_GUILD_ID` | yes | | The Toads server id. |
| `TOADS_DISCORD_REDIRECT_URI` | yes | | `https://<hub>/auth/callback`, registered on the Discord application exactly. |
| `TOADS_DISCORD_AUTHORIZE_URL` | no | `https://discord.com/oauth2/authorize` | Dev only: points at the fake Discord. Delete in production. |
| `TOADS_DISCORD_API_BASE` | no | `https://discord.com/api/v10` | Dev only, as above. |
| `TOADS_PUBLIC_BASE_URL` | yes | | The hub's public URL, `https://<hub>`. |
| `TOADS_RAID_DAYS_CONFIG` | no | `config/raid_days.yaml` | Path to the raid days file (`/config/raid_days.yaml` in compose). |
| `TOADS_COMMUNITY_CONFIG` | no | `config/community.yaml` | Path to the community file. |
| `TOADS_RAID_SHEETS_CONFIG` | no | `config/raid_sheets.yaml` | Path to the raid sheets file. |
| `TOADS_HUB_SERVICE_TOKEN` | yes | | Shared with the worker and bots. Secret. |
| `TOADS_CREDENTIALS_KEYS` | yes | | Fernet keys, comma-separated, newest first (section 7). Secret. |
| `TOADS_SESSION_TTL_SECONDS` | no | `604800` (7 days) | How long a sign-in lasts. |
| `TOADS_ROLE_REFRESH_SECONDS` | no | `900` | How often Discord roles are re-read; at most 900. |
| `TOADS_LOGIN_TTL_SECONDS` | no | `600` | How long a started login stays usable. |
| `TOADS_SUPER_ADMIN_IDS` | no | empty | Super admins' Discord user ids, comma-separated (section 6). |
| `TOADS_BREAK_GLASS_ADMIN_ID` | no | empty | The break-glass admin's Discord user id (section 6). |
| `TOADS_WCL_CLIENT_ID` | no | empty | Warcraft Logs client for the reference login. Empty turns the login off. |
| `TOADS_WCL_CLIENT_SECRET` | no | empty | Its secret. Secret. |
| `TOADS_WCL_SITE_URL` | no | `https://fresh.warcraftlogs.com` | The Warcraft Logs site the login goes through. |
| `TOADS_WCL_REDIRECT_URI` | no | `{TOADS_PUBLIC_BASE_URL}/api/reference/login/callback` | Must be registered on the Warcraft Logs client. |
| `TOADS_BANK_URL` | no | empty | `toadsbank-api`'s base URL. Empty: bank routes answer 503. |
| `TOADS_BANK_SERVICE_TOKEN` | no | empty | Shared with ToadsBank. Empty: bank off. Secret. |
| `TOADS_BANK_BOT_TOKEN` | no | empty | The bank bot's token for acting as a member. Empty: the bank bot's commands are refused. Secret. |
| `TOADS_BANK_CHANNEL_ID` | no | empty | Where accepted snapshots are posted when a bank's raid day has no `bank_requests` channel. |
| `TOADS_BANK_FALLBACK_CHANNEL_ID` | no | empty | Where the bot reports a manager it could not DM. Empty: the bank channel. |

### Worker and scheduler (`services/worker/.env`)

| Variable | Required | Default | Meaning |
| --- | --- | --- | --- |
| `TOADS_DATABASE_URL` | yes | | The same database as the API. Secret. |
| `TOADS_REDIS_URL` | yes | | The same Redis as the API. |
| `TOADS_WCL_CLIENT_ID` | yes | | The guild's Warcraft Logs client id (the guild key). |
| `TOADS_WCL_CLIENT_SECRET` | yes | | Its secret. Secret. |
| `TOADS_WCL_GUILD_ID` | yes | | The guild's Warcraft Logs id. |
| `TOADS_WCL_API_URL` | no | `https://fresh.warcraftlogs.com/api/v2/client` | Warcraft Logs GraphQL endpoint. |
| `TOADS_WCL_THROTTLE_MS` | no | `250` | Pause between Warcraft Logs calls. |
| `TOADS_WCL_MAX_RETRIES` | no | `3` | Retries per Warcraft Logs call. |
| `TOADS_CREDENTIALS_KEYS` | yes | | The same value as the API's. Secret. |
| `TOADS_HUB_API_URL` | no | `http://api:8000` | Where the worker posts results. |
| `TOADS_HUB_SERVICE_TOKEN` | no | empty | The shared service token; the publish jobs need it. Secret. |
| `TOADS_RAID_SHEETS_CONFIG` | no | `config/raid_sheets.yaml` | Raid sheets file. |
| `TOADS_HUB_REFRESH_MINUTES` | no | `30` | Scheduler: publish-home, publish-performance, publish-badges, publish-reference and publish-logs. `0` turns them off. |
| `TOADS_SHEETS_REFRESH_MINUTES` | no | `360` | Scheduler: import-sheets, only when the sheets file exists. `0` turns it off. |
| `TOADS_SYNC_REFRESH_MINUTES` | no | `15` | Scheduler: sync-guild, which analyses the guild's new Warcraft Logs reports. Off until `TOADS_WCL_CLIENT_ID` and `TOADS_WCL_GUILD_ID` are set; `0` turns it off. [docs/logs-analysis.md](docs/logs-analysis.md) |
| `TOADS_SYNC_RESERVE_PERCENT` | no | `20` | The share of the guild key's hourly Warcraft Logs points the sync leaves unspent for officer imports and anything else on the key. Each run imports new reports, newest first, until the next one would eat into it. |
| `TOADS_SYNC_BATCH` | no | `0` | An optional cap on reports per sync run on top of the rate limit; failed ones do not count. `0` means no cap. Used as the cap (`10` when `0`) if Warcraft Logs does not report the rate limit. |

### Toad Bot (`services/bot/.env`, `toads-bot`)

| Variable | Required | Default | Meaning |
| --- | --- | --- | --- |
| `TOADS_DISCORD_BOT_TOKEN` | yes | | The hub application's bot token. Secret. |
| `TOADS_DISCORD_GUILD_ID` | yes | | The Toads server id. |
| `TOADS_HUB_API_URL` | yes | | The API, e.g. `http://api:8000`. |
| `TOADS_HUB_SERVICE_TOKEN` | yes | | The shared service token. Secret. |
| `TOADS_POST_TO_CHANNELS` | no | `false` | Whether officer posts marked "also post to Discord" are really posted. |
| `TOADS_MIRROR_CHANNEL_IDS` | no | `[]` | JSON list of channels offered to the hub for curation. The API keeps its own allowlist (`mirrored_channels`). |

### Kit bots and the bank bot (`toads-botkit`)

A kit bot reads the four required Toad Bot variables above (with its own `TOADS_DISCORD_BOT_TOKEN`) plus:

| Variable | Default | Meaning |
| --- | --- | --- |
| `TOADS_BOT_SPEC` | `relay` | Which bot to run: `bank` or `relay`. |
| `TOADS_BOT_CHANNEL_IDS` | `[]` | JSON list of channels the bot may post in. For the bank bot: `TOADS_BANK_CHANNEL_ID`, `TOADS_BANK_FALLBACK_CHANNEL_ID` and every raid day's `bank_requests` channel. |
| `TOADS_BOT_POLL_SECONDS` | `15` | How often it pulls actions from the hub (at least 1). |
| `TOADS_BANK_BOT_TOKEN` | empty | Bank bot only: the same value as the API's. Secret. |

### Dev and test only

`FAKE_DISCORD_*` and `FAKE_BANK_*` configure the fake Discord and fake bank in the dev stack; both refuse to start
without `FAKE_DISCORD_I_AM_DEV=1` / `FAKE_BANK_I_AM_DEV=1`. Never run them in production. `TOADS_TEST_DATABASE_URL`
points the SQL tests at a real Postgres. `PREVIEW=1` and `BASE_PATH` build the GitHub Pages preview.

## 5. Config files

Raid days, roles, channels and sheets are configuration, not code. Copy each `config/*.example.yaml` to its name
without `.example` (git-ignored) and mount `config/` read-only into the API, worker and scheduler at `/config`.
Restart the API after editing a file.

**`config/raid_days.yaml`** (API)

- `timezone`: server time for raid start times (default `Europe/Paris`); members see their own time.
- `global_officer_roles`: Discord role ids whose holders are global officers on every raid day.
- `raid_days`: one entry per raid day, with `id` (lowercase, used in URLs such as `/api/days/wed/...`), `name`,
  optional `start_time` (`HH:MM`, the fallback for "Next raid" when Discord has no scheduled event), `trial_roles`,
  `raider_roles`, `officer_roles` and `channels` (`raid_logs`, `signups`, `bank_requests`).
- "Next raid" on the hub home is the soonest raid on the member's own nights: a Discord scheduled event counts for the
  night whose weekday it falls on. Global officers and members of no night see the guild's soonest raid, and an event
  on a weekday that is no raid night (a one-off) shows to everyone.
- Every role id must exist in the server. One that does not (a role deleted or recreated in Discord) grants nothing, and
  the API logs a `discord_role_missing` error naming the day and role; put the role's new id in the config.
- **Adding a raid night** (Thursday joined Wednesday and Sunday in October 2026): make the night's roles in Discord
  (for example `Thursday Toads` for raiders, `Thursday Trials` and `Thursday Officers`), copy each role's id (Developer
  Mode, right-click the role, Copy Role ID), add an entry to `raid_days` with its `id` (`thu`), `name` (`Thursday`),
  `start_time` and those ids in `trial_roles` (and `raider_roles` and `officer_roles`, or tie the raider role to the
  night's Toad badge and the officer role to its Officer badge on the Admin page instead), then restart the API. Role
  ids go in square brackets, as numbers: `officer_roles: [1300000000000000001]`; a bare number, a role name or a pasted
  `<@&...>` mention stops the API from starting. Members with
  the officer role get that night's officer powers and pages (Raid page desk and board, Calendar, comp builder, logs,
  recruitment panel, bank) at their next role refresh; nothing else gives them sight of it. Then on the Admin page tie
  the raider role to the night's badge (Thursday Toad). A night whose badge art, preview data or homepage wording is
  new also needs `apps/web/src/lib/nights.ts`, `scripts/toad_art.py` and both badge catalogues in a PR.

**`config/community.yaml`** (API): guild name and realm for the `/story` page (its tagline and story live in the repo,
`services/api/src/toads_api/community/story.py`, and change with a deploy), `discord_invite`
(discord.gg or discord.com/invite links only; the Story page hides its Discord button without one),
`mirrored_channels` (channel id plus `raid_day`, `null` for guild-wide), `post_channels` (`guild` plus one per raid
day), `interview_category_id` and `interviewers` (who interviews applicants for a night with no interview panel:
Discord user ids, or usernames such as `[_gallagher, hadur117]`; prefer ids, since a username someone gives up can be
claimed by another member). Each night's panel is set by its officers on Officers > Recruitment, not here
(docs/recruitment.md). The homepage's own words are site text, not configuration: they live in `apps/web/src/lib/landing.ts` and
change through a PR.

**`config/raid_sheets.yaml`** (worker, API): the CBA and RPB spreadsheets, which tabs to keep, `follows: cba` for RPB,
and `weekdays` per raid day. Sheets must be shared "Anyone with the link: Viewer". Setup tabs (Instructions, `trans`,
`*config*`) are never stored, and webhooks and e-mails elsewhere are blanked.

## 6. Access control

Roles come from Discord, re-read at least every 15 minutes. Full rules: [docs/admin.md](docs/admin.md) and the RBAC
section of [docs/bank.md](docs/bank.md).

| Tier | Comes from | Can |
| --- | --- | --- |
| Member, trial, raider | a raid day's `trial_roles` / `raider_roles` (anyone in the server is a member) | their own pages; raiders upload and submit highlights; everyone may view the bank and request items |
| Raid-day officer | a raid day's `officer_roles`, or an officer grant for that night on the Admin page | officer powers **for that raid day only**: `/api/days/{day}/...` routes, that day's banks, claims, applications, curation |
| Global officer | `global_officer_roles`, or an "Every night" officer grant on the Admin page | officer powers on every raid day, bank sources, recruitment, highlights, spotlights; sees the grants list |
| Super admin | `TOADS_SUPER_ADMIN_IDS` | everything a global officer can, plus `MANAGE_GRANTS`: grant and revoke bank grants, mint and revoke officer tokens; `MANAGE_ROLE_BADGES`: tie badges to Discord roles; and `MANAGE_OFFICER_GRANTS`: grant and revoke officer powers |
| Break-glass admin | `TOADS_BREAK_GLASS_ADMIN_ID` | always a super admin; visible to everyone in the global tier; every change is audited as `break_glass` |

Rules worth knowing:

- **Raid-day scoping.** An officer power is always for one raid day, and the day comes from the URL path only, never
  from a body or query. Bank officer routes are also bound to the banks whose `raidDay` matches; a bank with no raid
  day is the global tier's.
- **Super admins are configuration only.** No route, table or Discord role makes someone a super admin. To change the
  list, change the env and restart the API. Keep it to two or three people.
- **Break-glass** widens what one person may do, not who can sign in: they still sign in with Discord and must be in
  the server. It is visible on purpose (`/api/session`, `/api/bank/me`, the Bank page).
- **Grants** give one non-officer `import_bank_snapshot` or `manage_bank`, for one raid day or every bank. They are read
  from the database on every call, so a revoke works on the member's next action. A grant never opens `/api/admin/...`,
  never reaches an officers-only bank and never allocates raid stock.
- **Officer grants** ([docs/admin.md](docs/admin.md#officer-grants)): on the Admin page a super admin makes one Discord
  member an officer of a raid night, or of every night (a global officer), on top of their Discord roles. Read on every
  request, so a revoke works on their next action. A grant never makes a super admin, and its holder cannot grant
  anything. Audited as `officer.grant` and `officer.revoke`.
- **Officer tokens** are the self-service way to hand out grants: a super admin mints one on the Bank page or the Admin
  page, passes it on privately, and the member redeems it on the Bank page or with `/bank redeem <token>`. 7 days and one use by
  default (at most 30 days and 25 uses). Only a hash is stored; the token is shown once.
- **Audit log** (`audit` table): `officer.grant`, `officer.revoke`, `bank.grant`, `bank.revoke`, `bank.token_minted`, `bank.token_redeemed`,
  `bank.token_revoked`, `break_glass`, plus officer actions such as claim decisions and board changes (`board.*`).
- **Role badges** ([docs/role-badges.md](docs/role-badges.md)): on the Admin page, under "Badges from Discord roles",
  pick a server role and the badge it earns (Wednesday Toad, Thursday Toad, Sunday Toad, each night's Officer, Tank,
  Healer, Damage or a class). Everyone holding the role wears the badge beside their name. Start by tying the Wednesday, Thursday and
  Sunday raider roles.
  A raid night's badge also sets its team: everyone holding a role tied to the Thursday Toad badge is a Thursday raider
  (on its roster and calendar), with no `raider_roles` entry needed in `raid_days.yaml`. Untie it and they leave the
  team at once. The comp builder's roster reads the server's role holders with the Toad Bot's token whenever an
  officer opens it (at most every 15 minutes), so it lists people who have never signed in too, marked "Not signed
  in" ([docs/comps.md](docs/comps.md)). A night's Officer badge does the same for its officers: tie Thursday Officer
  to the `Thursday Officers` role and its holders run Thursday, and only Thursday. The rank
  toads (member, officer, super admin, Archtoad) need no setup. Audited as `role_badge.add` and `role_badge.remove`.
- **Raid page and absences** ([docs/absences.md](docs/absences.md)): `/raid` is each raid night's page. Members see
  their own team's night, its officers also get an officer desk linking to the night's officer section, and super
  admins and global officers switch between every night. On their Me page a raid day's trials and raiders add, change and
  delete the nights they will miss, each with a note (`report_absence`, checked against the raid day in the path), and
  that day's officers see them all in the night's officer section and under Officers, Calendar (`/officers/calendar`, `view_absences`). Nothing to
  configure: nights follow each raid day's `name` in `raid_days.yaml` (a day named "Wednesday" raids on Wednesdays).
  Notes are seen only by that night's officers. Not audited: an absence is a member's own word, not an officer action.
- **Officer sections**: `/officers` is the shared Officer console every officer uses (calendar, comp builder,
  recruitment, reference reports, awards). Each raid night also has its own section, `/officers/nights/{day}`, with that
  night's absences, task board and interview panel. An officer sees only the sections of the nights they run: a
  Sunday officer never sees Wednesday's. Global officers and super admins see every night.
- **Officers' board** ([docs/officer-board.md](docs/officer-board.md)): each raid night has its own task board in
  its officer section (To do, In progress, Done), seen and worked only by that night's officers, global officers and super
  admins (`MANAGE_OFFICER_BOARD`). Nothing to set up: a night's board appears with the night in
  `config/raid_days.yaml`. Audited as `board.add`, `board.edit`, `board.move` and `board.remove`.
- **Logs** ([docs/logs.md](docs/logs.md)): `/logs` lists every raid the sync has analysed, filtered by any mix of
  weekdays, zone and title, with the desktop app's raid analysis per raid and a boss history over the picked days.
  Each raider's own numbers are officers' only: a raid day's officers see the raids held on that day's weekday in full,
  global officers and super admins every raid, and everyone else each boss's totals and the raid's makeup. The
  scheduler's `publish-logs` keeps it current; nothing to configure beyond the sync.
- **The Admin page** (`/admin`, shown in the nav to super admins only) gathers role badges, bank grants and officer tokens, the
  scheduler's jobs and where each integration is set up. It reads `/api/session` and changes nothing the Bank page
  cannot; the grant routes still check `MANAGE_GRANTS`. Every member can see what their tier allows on `/toolkit`.
- **The launch hold** (until the World of Warcraft: Forever launch on 4 November 2026). A raider who signs in sees one
  coming-soon page (guild bank management, logs analysis, raid assistance) on every member page except Raid and
  Me, and the Members nav shows only Hub, Raid and Me, so raiders can report absences now (their Me shows only their
  absences until launch). Officers see every member page as it is being built (the hub fills in from the historic TBC raids
  the worker synced), except Bank, which shows what is coming with the Forever launch and a mockup until the bank has
  data. Super admins see exactly what officers see, plus the Admin console. The hold is in the web app
  only (`apps/web/src/lib/launch.ts`); the API's permissions are unchanged. To lift it, set `LAUNCH_HOLD` to `false`
  there in a PR and let it deploy.

## 7. Member settings and members' own Warcraft Logs keys

Signed-in members open `/me/settings` to:

- **Choose the name shown**: their Discord nickname or an approved claimed character (the character holds only while
  the claim stays approved).
- **Save their own Warcraft Logs key** (client id and secret). Work done for that member then uses their key and its
  rate limit instead of the guild's. Keys are write-only through the API (the page shows only the last four characters
  of the client id), are not checked when saved, and fall back to the guild key if Warcraft Logs refuses them (status
  `rejected`; the member saves a new one).

Admin side:

- Keys are encrypted at rest with `TOADS_CREDENTIALS_KEYS` (Fernet, in the `wcl_credentials` table), each bound to its
  member id. The API encrypts, the worker decrypts, so **both must hold the same value**.
- The guild key is the worker's `TOADS_WCL_CLIENT_ID/SECRET`. Guild-wide jobs (the guild sync, the scheduler's publish jobs,
  sheet imports) always use it.
- Losing every key in `TOADS_CREDENTIALS_KEYS` makes stored member keys and the reference login unreadable. Members
  then fall back to the guild key and must save their keys again, and an officer must reconnect the reference login.
  Keep the keys with the other secrets and back them up. Rotation: [section 12](#12-rotating-secrets).

## 8. The reference comparison login

Officers compare a guild raid with another guild's report on `/officers/reference/` (needs `VIEW_INSIGHTS`, so
officers only, per raid day). The officer console links to it from its **Reference reports** card ("Add reference
reports"). Reading other guilds' reports needs a Warcraft Logs **user** login on the guild's behalf: a dedicated account
or a super admin's own Warcraft Logs account both work.

Setup:

1. On the Warcraft Logs client (the same one as the worker's), register the redirect URI
   `https://<hub>/api/reference/login/callback` (or whatever `TOADS_WCL_REDIRECT_URI` says).
2. Set `TOADS_WCL_CLIENT_ID` and `TOADS_WCL_CLIENT_SECRET` in the **API's** env (the worker already has them).
   Optionally `TOADS_WCL_SITE_URL` and `TOADS_WCL_REDIRECT_URI`.
3. Restart the API. An officer opens the officer console, chooses **Add reference reports**, connects the login and
   signs in to Warcraft Logs as the account that acts for the guild.

What lives where:

| What | Where | Why |
| --- | --- | --- |
| Client id and secret | env (`TOADS_WCL_CLIENT_ID`, `TOADS_WCL_CLIENT_SECRET`) | Fixed per deployment; the secret never reaches the database. |
| `TOADS_CREDENTIALS_KEYS` | env, same value on the API and worker | Encrypts the stored token. |
| The account's access and refresh tokens | hub-db, Fernet-encrypted, written by the login | Warcraft Logs issues and rotates them; they change on every refresh, so env vars cannot hold them. |
| The account's password | nowhere | The hub never sees it; Warcraft Logs' own sign-in page takes it. |

How it runs: the API does only the OAuth code exchange and queues jobs. The worker refreshes the token and runs imports
and comparisons. `publish-reference` refreshes the list of raids to pick from every `TOADS_HUB_REFRESH_MINUTES`. A job
untouched for an hour shows as failed.

Disconnect with the page's disconnect button (`DELETE /api/days/{day}/reference/login`). Leaving
`TOADS_WCL_CLIENT_ID` empty in the API turns the feature off and the page says so.

## 9. The community layer

Recruitment with private Discord interview rooms, officer posts curated both ways with Discord, highlight reels and
consent-gated spotlights, and the public pages (`/` landing, `/story`, `/recruit`).

- **Nothing from Discord is shown until an officer publishes it.** Messages in `mirrored_channels` reach the curation
  queue; raid-day officers curate their day's channels, global officers the guild-wide ones.
- **Only the global tier posts to the public Story.** An edit made in Discord sends a public post back to review.
- **Applications** ask six questions (character, class, primary and secondary role, raid night, why Toads; no age,
  e-mail or real name), need a Discord account that is in the server when the applicant presses send, and have a
  30-day reapply cooldown. The Toad Bot opens the interview room under `interview_category_id` the moment someone
  applies, with only the applicant and the chosen night's interview panel in it, and posts their answers there. Each
  night's officers pick their panel from the Discord on **Officers > Recruitment**; a night without one uses
  `interviewers` from the config (docs/recruitment.md). With neither, an officer opens the room from the officer
  console and the officers of the days applied for see it. Officers move
  applications through their states either way, and the room is locked (never deleted) when one closes.
- **Highlights**: raiders submit clips (YouTube, Twitch and Streamable only, loaded on click); global officers review
  them. **Spotlights** need the member's consent before they are published.
- **Recruitment needs** are set by global officers.
- Posting to Discord needs both `post_channels` in `config/community.yaml` and `TOADS_POST_TO_CHANNELS=true` on the
  Toad Bot.

## 10. The guild bank

The bank's data and rules live in ToadsBank; the hub signs members in, applies its RBAC and calls ToadsBank for them.
Hub side: [docs/bank.md](docs/bank.md). Service, addon and their operations:
[ToadsBank's guide](https://github.com/lgriffin/ToadsBank/blob/main/docs/operations.md).

To set it up on the hub side:

1. `TOADS_BANK_URL`, `TOADS_BANK_SERVICE_TOKEN` and `TOADS_BANK_BOT_TOKEN` in the API env; the matching values on
   ToadsBank and the bank bot (section 4).
2. ToadsBank's `TOADSBANK_EVENTS_URL` set to `https://<hub>/api/bank/events`.
3. Bank channels: `TOADS_BANK_CHANNEL_ID`, optionally `TOADS_BANK_FALLBACK_CHANNEL_ID`, and per raid day
   `channels.bank_requests` in `raid_days.yaml`. List every one of them in the bank bot's `TOADS_BOT_CHANNEL_IDS`.
4. Register each bank with its `raidDay` (or none) and its `managers` (Discord user ids; they get the request DMs),
   and `audience` (`members` or `officers`).

Who does what:

| Task | Who |
| --- | --- |
| View the bank, request items, cancel own requests | every member |
| Import a snapshot (addon export pasted on the Bank page or with `/bank import`) | that day's officers, global officers, super admins, holders of an import grant |
| Work the request queue (approve, reject, record deliveries) | that day's officers, global officers, super admins, holders of a manage grant; ToadsBank also lets a bank's listed `managers` act |
| Register or edit a bank | global officers and super admins |
| Grant, revoke, mint and revoke tokens | super admins |

Defaults in ToadsBank's code: a bank warns after 24 hours without a snapshot and blocks new reservations after 72;
open requests expire after 14 days.

## 11. Routine operations

### Add or remove a super admin

Edit `TOADS_SUPER_ADMIN_IDS` (comma-separated Discord user ids) in the API env and restart the API. Changing the
break-glass admin is the same with `TOADS_BREAK_GLASS_ADMIN_ID`. Removing someone takes effect on their next request.

### Make someone an officer, or change raid days

Give or take the Discord role. The hub re-reads roles within `TOADS_ROLE_REFRESH_SECONDS` (15 minutes), or at once
when the member signs in again. To add a raid day or role, edit `config/raid_days.yaml` and restart the API.

### Grant bank powers to a non-officer

On the Bank page, as a super admin: grant `import_bank_snapshot` or `manage_bank` to a member, for one raid day or
every bank. Or mint an officer token (choose permissions, raid day, lifetime, uses, a note), send it to the member
privately, and let them redeem it on the Bank page or with `/bank redeem <token>`.

### Revoke

- A grant: the grants list on the Bank page (`DELETE /api/admin/bank/grants/{id}`). Works on the member's next call.
- A token not yet used up: the tokens list (`DELETE /api/admin/bank/tokens/{id}`). This does not take back grants it
  already gave; revoke those too.
- An officer role: remove the Discord role.

### Import a bank snapshot

An officer (or grant holder) scans the bank in game with the ToadsBank addon, exports it, and pastes the parts on the
Bank page or into `/bank import` in Discord, then checks the preview and accepts it. Details in ToadsBank's guide.

### Pre-fill specs from a Raid-Helper sign-up

Export the night's sign-ups from Raid-Helper (the composition tool or the event), then run
`/raidhelper import night:<night> export:<file>` on the Toad Bot as one of that night's officers. Everyone the export
seats gets their class and primary spec, and the class and role badges that come with it, before they sign in; members
can correct them on Me. Specs a member set themselves are kept. Details, and where the data lands, in
[docs/toad-bot.md](docs/toad-bot.md).

### Approve bank requests

Managers get a DM with Approve, Reject and Record delivery buttons when a request is assigned. The same queue is on the
Bank page under the raid day. A stale button answers with the request's current state.

### Approve character claims

Members find their character by name on `/me/claim`; the hub knows who they are from their Discord sign-in. The
names come from wcl-store's character list, which the worker fills as it analyses the guild's raids, so a character
shows up after its first logged raid. Raid-day officers approve, reject or reassign claims under
`/api/days/{day}/claims` (the Officers console).

### Refresh hub data by hand

The scheduler does this every 30 minutes, and imports new guild reports every 15 minutes, as many as the guild key's
Warcraft Logs rate limit allows. To run a job now, in the worker image: `toads-worker sync`, `backfill`,
`analyse <report code or URL>`, `publish-home`, `publish-performance`, `publish-badges`,
`publish-reference`, `publish-logs` or `import-sheets`
(for example `docker compose -f infra/docker-compose.yml run --rm worker toads-worker publish-home`).

### Import the guild's whole history

The scheduler's sync looks at the guild's newest 350 reports. To import every report the guild has on Warcraft Logs,
run the backfill once on the server; it works oldest first, waits out the rate limit when the hour's points are spent,
and finishes on its own (it can take hours for a long history, so run it in `tmux` or `screen`):

```bash
cd /opt/toads
sudo -u toads docker compose -f infra/docker-compose.prod.yml run --rm worker toads-worker backfill
```

It shares the guild key's points with the scheduler and keeps to the same `TOADS_SYNC_RESERVE_PERCENT`, so both can
run at once. Stopping it (Ctrl+C) is safe: run it again and it carries on from what is stored.
[docs/logs-analysis.md](docs/logs-analysis.md#5-the-first-import) has the details.

### Deploy an update

Merge to main: once CI passes, the Deploy workflow runs `scripts/deploy.sh` on the server, which checks out the commit,
rebuilds the images, runs both migration jobs (`hub-db-migrate`, `toads-worker-migrate`) and then restarts the API,
worker, scheduler, web and bots. Services whose image did not change keep running, except that the API, worker and scheduler
restart whenever a file in `config/` changed since the last deploy, since they read it only at startup. Run the script by hand (`sudo -iu toads /opt/toads/scripts/deploy.sh [sha]`) after
changing an env file, or from Actions → Deploy → Run workflow to roll back ([docs/deploy.md](docs/deploy.md#8-day-to-day)).
Migrations are numbered Alembic revisions; they run forwards only in normal operation.

### Bumping the analyzer

Getting the analysis running on the server the first time: [docs/logs-analysis.md](docs/logs-analysis.md).

The worker's analysis comes from lgriffin/warcraftlogs_project. To take a new analyzer version, change the `rev` of
`wcl-core`, `wcl-store` and `wcl-app` in the root `pyproject.toml` together, run `uv lock`, open a PR, and run
`toads-worker-migrate` on deploy (wcl-store may bring new tables).

## 12. Rotating secrets

Rotate a secret when someone who knew it leaves, when it may have leaked, or on a schedule. After each change, restart
every process that reads it.

| Secret | How |
| --- | --- |
| `TOADS_HUB_SERVICE_TOKEN` | New value in the API, worker and every bot env at once; restart all of them. Calls fail with 401 until all agree. |
| `TOADS_BANK_SERVICE_TOKEN` | New value in the hub API and ToadsBank (`service_token` secret) together; restart the API, `toadsbank-api` and `toadsbank-worker`. Events fail meanwhile and are retried for 24 hours, so none are lost if both sides change within that window. |
| `TOADS_BANK_BOT_TOKEN` | New value in the API and bank bot; restart both. |
| `TOADS_CREDENTIALS_KEYS` | Generate a key (`just credentials-key`) and put it **first**: `new,old`. Restart the API and worker. New writes use the new key and old rows still decrypt. A row is re-encrypted only when it is written again (a member saves their key, or the worker refreshes the reference login). Drop the old key only once you accept that members who have not re-saved must save their key again. |
| Discord client secret or bot tokens | Reset in the Discord developer portal, update the env of the API and the bot that uses it, restart. |
| Warcraft Logs client secret | Reset on warcraftlogs.com, update the worker and API env, restart. The reference login may need reconnecting. |
| Database password | Change the role's password in Postgres first (`\password <user>` in `psql`; the secret files alone do not change it), then update `TOADS_DATABASE_URL` in the API and worker, restart. |
| Super admins or break-glass | Edit the env and restart the API (section 11). |
| Officer tokens | Revoke unused tokens; they expire on their own after at most 30 days. |

Sign-ins live in Redis: flushing Redis signs everyone out (and drops queued jobs and the bank event dedup).

## 13. Backups and restore

| What | Holds | Back up |
| --- | --- | --- |
| Hub Postgres | members, claims, settings, encrypted keys, reference login, community, layouts, grants, tokens, audit, sheets, and the analyzer's tables | yes: `pg_dump -Fc` daily (with `docker compose exec -T`, so no TTY corrupts the dump), keep several days, copy off the host |
| ToadsBank Postgres | banks, snapshots, requests, deliveries, raid allocations | yes, see ToadsBank's guide |
| `TOADS_CREDENTIALS_KEYS` and the other secrets | needed to read encrypted rows and run the stack | yes, in your secret store, never next to the database dump |
| `config/*.yaml` | raid days, roles, channels, community copy, sheets | yes (they are git-ignored) |
| Redis | sessions, queues, event dedup | no: losing it signs people out and drops queued jobs |

A restore without the matching `TOADS_CREDENTIALS_KEYS` brings everything back except members' saved keys and the
reference login. Restore with the API, worker and scheduler stopped, using `pg_restore --clean --if-exists --no-owner`
into the same database. After restoring the hub database, run `hub-db-migrate` and `toads-worker-migrate` before starting the
API and worker.

## 14. Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| API exits at startup naming a variable | A required setting is missing or invalid (section 4). |
| API exits at startup saying the bot token "belongs to application" another id | `TOADS_DISCORD_CLIENT_ID` and `TOADS_DISCORD_BOT_TOKEN` come from different Discord applications; take both, and the client secret, from the Toad Bot's application ([docs/deploy.md](docs/deploy.md#turn-on-discord-sign-in)). |
| API exits at startup naming a raid day and role | A role id in `raid_days.yaml` is not a role in the server, or the bot token cannot see the server. |
| Discord login says the redirect is invalid | `TOADS_DISCORD_REDIRECT_URI` does not match the redirect registered on the Discord application exactly. |
| Someone signed in but has no officer powers | Their role is not in that day's `officer_roles` or in `global_officer_roles`, or roles have not refreshed yet (up to 15 minutes, or sign in again). |
| Bank page or routes answer 503 `bank_not_configured` | `TOADS_BANK_URL` or `TOADS_BANK_SERVICE_TOKEN` is empty. |
| 502 `bank_unavailable` | ToadsBank is down, unreachable, or the two service tokens differ. |
| 403 `not_this_day` on a bank action | The bank's `raidDay` differs from the URL's day; a global officer or a grant for every bank is needed. |
| The bank bot's commands are refused | `TOADS_BANK_BOT_TOKEN` is empty or differs between the API and bot, or the member is not in the server. |
| No DMs or posts after bank events | The bank bot is not running, its channels are missing from `TOADS_BOT_CHANNEL_IDS`, or the API restarted and the in-memory queue was lost (issue #25). |
| Members' keys all show as not working | `TOADS_CREDENTIALS_KEYS` differs between the API and worker, or the key that wrote them was removed. |
| Reference page says the login is not set up | `TOADS_WCL_CLIENT_ID` is empty in the API. |
| Warcraft Logs refuses the reference login callback | The redirect URI is not registered on the Warcraft Logs client. |
| Logs widgets or performance never update | The scheduler is not running, `TOADS_HUB_REFRESH_MINUTES=0`, or the worker's `TOADS_HUB_SERVICE_TOKEN` is wrong. |
| Raid sheets not imported | The sheet is not shared by link, `config/raid_sheets.yaml` is missing in the scheduler, or `TOADS_SHEETS_REFRESH_MINUTES=0`. |
| Claim search finds nobody | The worker has not analysed a raid yet, so wcl-store's character list is empty. |
| `429` when redeeming a token | Five refused tries in 15 minutes; wait for the window to pass. |

## 15. Known limitations

- **Bot bridge queue is in memory** ([#25](https://github.com/lgriffin/toads/issues/25)). Actions waiting for a kit bot
  (bank DMs and posts) are lost if the API restarts before the bot pulls them, and ToadsBank will not resend an event
  the hub already acknowledged. Restart the API when the queue is quiet.
- **Single-server deploys build images on the server** ([docs/deploy.md](docs/deploy.md)); CI publishes none and
  production images are not signed yet (REQ-DEV-REL-001).
- **Bot permissions**: kit bots other than the bank bot run with an open gate and the site trusts the Discord user id
  they send (REQ-HUB-BOT-005 pending). The Toad Bot still uses its own outbox at `/api/bot/*`.
- **Super-admin tier** is not yet in the build spec's RBAC table.
- **WoW Forever addon**: its interface number is a placeholder until the probe runs on the Forever client
  ([ToadsBank#2](https://github.com/lgriffin/ToadsBank/issues/2)); see ToadsBank's guide.
- **Open hosting and settings items** are tracked in [#24](https://github.com/lgriffin/toads/issues/24) and
  [ToadsBank#3](https://github.com/lgriffin/ToadsBank/issues/3); defaults still awaiting confirmation in
  [ToadsBank#4](https://github.com/lgriffin/ToadsBank/issues/4).
