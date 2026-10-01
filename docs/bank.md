# The guild bank: the hub's face of ToadsBank

The bank's data and rules live in [ToadsBank](https://github.com/lgriffin/ToadsBank): a WoW addon that exports a
bank snapshot as `TOADSBANK/1` text parts, and a headless service (`toadsbank-api` and its worker) that reassembles
them, keeps the stock, reservations and requests, and publishes events. ToadsBank's ADR 0002 puts the bank's website
and Discord in this hub, so the hub:

- signs members in with Discord and decides who may reach which bank route (its RBAC);
- calls `toadsbank-api` for them, with a shared service token and the member's identity in `X-Toads-*` headers;
- serves the Bank page (`apps/web/src/routes/bank`);
- runs the `bank` bot (`toads_bot.kit.bank`), which turns ToadsBank's events into DMs and posts and offers `/bank`
  commands.

```
 browser ──/api/bank/*──────────────▶ hub API ──/v1/* + service token + X-Toads-*──▶ toadsbank-api
 bank bot ─/api/bank/* + bank bot ──▶ (RBAC)  ◀──POST /api/bank/events + token───── toadsbank-worker
           token + acting member        │
                                        └─ BotBridge: bank.dm / bank.post ──▶ bank bot ──▶ Discord
```

ToadsBank's HTTP contract (v1) is the source of truth for request and response shapes; the hub passes ToadsBank's
JSON through unchanged and forwards only the body fields the contract names.

## Routes

| Hub route | Permission | ToadsBank call |
| --- | --- | --- |
| `GET /api/bank/me` | `VIEW_BANK` | none: whether the bank is set up, the caller's officer days, the days they may import and work the queue on, whether they see or manage grants, whether they are a super admin or the break-glass admin, and (to the global tier) who the break-glass admin is |
| `GET /api/bank/sources` | `VIEW_BANK` | `GET /v1/sources` |
| `GET /api/bank/sources/{id}/replica` | `VIEW_BANK` | `GET /v1/sources/{id}/replica` |
| `GET /api/bank/inventory?q=&sourceId=` | `VIEW_BANK` | `GET /v1/inventory` |
| `GET /api/bank/requests?status=` | `VIEW_BANK` | `GET /v1/requests?scope=mine` |
| `POST /api/bank/requests` | `REQUEST_BANK_ITEMS` | `POST /v1/requests` |
| `POST /api/bank/requests/{id}/cancel` | `REQUEST_BANK_ITEMS` | `POST /v1/requests/{id}/cancel` |
| `POST /api/days/{day}/bank/imports` | `IMPORT_BANK_SNAPSHOT` (scoped) | `POST /v1/imports` |
| `POST /api/days/{day}/bank/imports/{id}/parts` | `IMPORT_BANK_SNAPSHOT` (scoped) | `POST /v1/imports/{id}/parts` |
| `GET /api/days/{day}/bank/imports/{id}/preview` | `IMPORT_BANK_SNAPSHOT` (scoped) | `GET /v1/imports/{id}/preview` |
| `POST /api/days/{day}/bank/imports/{id}/accept` | `IMPORT_BANK_SNAPSHOT` (scoped) | `POST /v1/imports/{id}/accept` |
| `GET /api/days/{day}/bank/requests?scope=queue\|all` | `MANAGE_BANK` (scoped) | `GET /v1/requests` |
| `POST /api/days/{day}/bank/requests/{id}/approve\|reject\|deliveries` | `MANAGE_BANK` (scoped) | the same on `/v1` |
| `POST /api/admin/bank/sources` | `MANAGE_BANK` (global tier) | `POST /v1/sources` |
| `PATCH /api/admin/bank/sources/{id}` | `MANAGE_BANK` (global tier) | `PATCH /v1/sources/{id}` |
| `GET /api/admin/bank/grants` | `MANAGE_BANK` (global tier) | none: see Grants |
| `POST /api/admin/bank/grants` | `MANAGE_GRANTS` (super admins) | none |
| `DELETE /api/admin/bank/grants/{id}` | `MANAGE_GRANTS` (super admins) | none |
| `GET /api/admin/bank/tokens` | `MANAGE_GRANTS` (super admins) | none: see [admin.md](admin.md) |
| `POST /api/admin/bank/tokens` | `MANAGE_GRANTS` (super admins) | none |
| `DELETE /api/admin/bank/tokens/{id}` | `MANAGE_GRANTS` (super admins) | none |
| `POST /api/bank/redeem` | `VIEW_BANK` | none: redeem an officer token |
| `POST /api/bank/events` | ToadsBank's service token | none: see Events |

Every guild member holds `VIEW_BANK` and `REQUEST_BANK_ITEMS`. `IMPORT_BANK_SNAPSHOT` and `MANAGE_BANK` are officer
permissions and, like every officer power, are scoped to a raid day: a Wednesday officer works the bank under
`/api/days/wed/bank/...`, a global officer under any day. A super admin may also grant either one to another member
(see Grants and [admin.md](admin.md)). Registering or editing a source is the global tier's (ToadsBank's `admin`);
granting is the super admins' alone.
ToadsBank still applies a source's `audience`, so a member who is not an officer does not see an officers-only bank.

The URL's day decides who reaches a route; the hub also binds each officer route to the banks of that day (a source's
`raidDay`), so a Wednesday officer cannot work Sunday's bank under `/api/days/wed/...`:

- the request queue lists only requests on that day's banks;
- approve, reject and deliveries first look the request up (`GET /v1/requests?scope=all`) and check its source's day;
- preview and accept check the day of the bank the snapshot matched (`matchedSource`); an unregistered bank needs
  the global tier.

A refusal is `403 not_this_day`. Global officers are not bound: they work every bank, including those with no raid
day, under any day's URL. A grant with no raid day covers every bank the member can see (a source's `audience` still
applies), under any day's URL. Opening an import and adding parts touch no bank, so they are not bound either. The bot,
which does not know a request's bank, tries the member's officer days in turn and moves on after `not_this_day`.

### Identity

The hub sends ToadsBank:

- `Authorization: Bearer <TOADS_BANK_SERVICE_TOKEN>`;
- `X-Toads-Member`: the member's Discord user id;
- `X-Toads-Name`: their display name, percent-encoded UTF-8;
- `X-Toads-Roles`: `member`, plus `officer` when they hold officer powers on any raid day, plus `admin` for a global
  officer, plus `uploader` on an import route or `manager` on a request queue route the hub has let them reach (by an
  officer role or a grant);
- `X-Toads-Banks`: with `uploader` or `manager`, and for anyone but the global tier, the source ids the call may touch:
  the bank the snapshot matched on accept, the request's bank on approve, reject and deliveries, or the route's banks
  (that day's banks the member can see, or every bank they can see for a grant with no raid day) on the queue.

ToadsBank (TB-BM-17) lets an `uploader` accept a snapshot and a `manager` list and work requests, as a source's manager
could, only on a bank named in `X-Toads-Banks` that the member can already see; the role never widens what they see,
and gives no officer or admin powers. So ToadsBank does not need to know about raid days or grants, and a mistake in
the hub's binding cannot reach an officers-only bank.

### Idempotency keys

Every mutating bank route needs an `Idempotency-Key` header (1 to 128 characters). The web page sends a fresh UUID per
submission and the bot sends one derived from the Discord interaction (manager buttons use the request id and
revision, so a double click is applied once). The hub never forwards the key as sent: it sends ToadsBank
`sha256(discord id, method, path, key)`, so one member's key can never replay another member's answer.

### Errors

A ToadsBank error is passed on with its status (400, 403, 404, 409, 422, 423) and body:
`{"detail": "<message>", "error": {"code", "message", "details", "current"}}`, so `insufficient_stock`'s
`details.canWaitlist` and `stale_revision`'s `current` reach the page and the bot. Two codes are the hub's own:

| Status | Code | When |
| --- | --- | --- |
| 503 | `bank_not_configured` | `TOADS_BANK_URL` or `TOADS_BANK_SERVICE_TOKEN` is empty |
| 502 | `bank_unavailable` | ToadsBank did not answer, answered 5xx, or refused the hub's token (logged as an error) |

## Events

ToadsBank's worker POSTs every outbox event to `TOADSBANK_EVENTS_URL`, which is the hub's `/api/bank/events`, with
the same service token. The hub remembers each event `id` for a week in Redis and acknowledges a repeat without acting
again. If it cannot act on an event (the bank bot's manifest lacks an action, say) it forgets the id and answers 503,
so ToadsBank retries.

Known gap: the DMs and posts an event becomes wait in the bot bridge's queue, which is still in memory
(`InMemoryBridgeStore`, see bots.md "Not yet"). An API restart between acknowledging an event and the bank bot pulling
its actions loses them, and ToadsBank will not resend an event it saw acknowledged. The bridge's table-backed store
closes this for every bot.

| Event | What the hub does |
| --- | --- |
| `request.assigned` | `bank.dm` to each manager, with Approve / Reject / Record delivery buttons for that revision. A DM the bot finally gives up on (five failed attempts) becomes a `bank.post` to the fallback channel (TB-BM-12). |
| `request.updated` | `bank.dm` to the requester, saying what changed. |
| `snapshot.accepted` | `bank.post` to the source's raid day's `channels.bank_requests` (in `config/raid_days.yaml`), else `TOADS_BANK_CHANNEL_ID`; skipped when neither is set. |
| `request.created` and others | Acknowledged; the site's queue reads ToadsBank directly. |

Names in ToadsBank's payloads are raw. The hub escapes Discord markdown and mention syntax in every name before it
asks the bot to say anything, and the bot sends everything with `AllowedMentions.none()` (TB-DM-08).

## The bank bot

`toads_bot.kit.bank.Bank` is a kit binding (see `bots.md`), run as `TOADS_BOT_SPEC=bank toads-botkit` with its own
Discord application.

- Site actions: `bank.dm {user_id, content, manage?, fallback?}` and `bank.post {channel_id, content}`. Posts go only
  to the bot's `TOADS_BOT_CHANNEL_IDS`, so list the bank channel, the fallback channel and any raid day's
  `bank_requests` channel there.
- `/bank import` opens a modal of five paragraph boxes (4,000 characters each, so two 1,800-character parts per box).
  The bot opens an import for the member if they have none open, adds the parts and answers with the parts received
  and missing; once the export is complete it shows the preview with Accept and Cancel buttons.
- `/bank redeem <token>` redeems an officer token ([admin.md](admin.md)) through `POST /api/bank/redeem`.
- `/bank find <item>` searches the inventory. `/bank request <item> <quantity> <character>` resolves the item by name
  and asks the bank holding the most of it; when stock is short it offers a Join the waitlist button.
- Manager buttons carry the request id and revision. A stale revision answers with the request's current state
  (TB-BM-16).

Every answer is ephemeral.

### Acting for a member

The bot has no database credentials and no session. It calls the hub's bank routes with its own token
(`TOADS_BANK_BOT_TOKEN`, the same value on the API and the bank bot) and names the Discord member who used the
command or button in `X-Toads-Acting-Member: <discord user id>`. The hub then:

1. accepts the header only on `/api/bank/...` and `/api/days/{day}/bank/...` (never `/api/bank/events` or any other
   route), and only with `TOADS_BANK_BOT_TOKEN`. The shared `TOADS_HUB_SERVICE_TOKEN`, which the worker and the
   other bots hold, cannot act for anyone;
2. reads that member's roles from Discord with the hub's bot token (`GET /guilds/{guild}/members/{user}`); someone not
   in the server gets 403, and Discord being down gives 503. What Discord said is kept in Redis for
   `TOADS_ROLE_REFRESH_SECONDS` (at most 15 minutes, as for a signed-in session), so a busy bot does not run into
   Discord's rate limits; someone not in the server is not remembered;
3. builds their Principal exactly as a login would (super admins from configuration included), so the route's
   `require(...)` applies as usual. A raid day's bank routes read grants from the database on every call and never
   remember them with the roles, so a revoke stops the bot on the member's next command.

So the bot can do nothing the member could not do on the site. Imports and manager actions use the raid days the
member may work (`import_days` and `manage_days` from `GET /api/bank/me`: their officer days and any day a grant
covers), in turn, until one owns the bank.

## Grants

Officers run the bank's upkeep through their Discord roles: a raid day's officers import snapshots and work the
request queue for that day's banks, global officers for every bank. A super admin ([admin.md](admin.md)) can let one
more member do either without making them an officer, directly or through an officer token the member redeems: a grant is one Discord user id, one permission (`import_bank_snapshot` or
`manage_bank`) and either a raid day (that day's banks) or none (every bank). Officers never need one; a grant only
adds to a member who is not an officer of that day.

- Grants live in hub-db's `bank_grants` table (migration `0011`), with who granted them and when; "every bank" is
  stored as `*`, so a unique constraint on (user, permission, raid day) keeps one row per grant even when two land at
  once. Granting and revoking are written to the audit log. Granting something already held returns the existing grant
  (`200`); a new one is `201`.
- Only someone in the Toads server can be granted anything (`404` otherwise); an unknown raid day is `422`.
- A raid day's bank routes read the member's grants on every call (`rbac.deps.with_grants`, only for routes a grant
  can open) into their Principal, and
  `can(...)` honours them only on a raid day taken from the route's path, never on a guild-wide route. So a grant opens
  the same `/api/days/{day}/bank/...` routes an officer of that day uses, binds them to that day's banks the same way,
  and never reaches `/api/admin/...`.
- ToadsBank learns of a grant only through the per-call `uploader` / `manager` role above: nothing is copied into a
  source's `managers`, so ToadsBank's `request.assigned` DMs still go to the listed managers only. A granted member
  sees the queue on the site and through the bot, for the banks they can see.

The Bank page shows the global tier the grants, and super admins the controls to grant, revoke and mint officer tokens.
Any member can redeem a token there or with `/bank redeem`. The bank bot has no grant or mint commands: its
acting-member token reaches only `/api/bank/...` and `/api/days/{day}/bank/...`, not the admin routes.

## Configuration

`services/api/.env`:

| Variable | Meaning |
| --- | --- |
| `TOADS_BANK_URL` | `toadsbank-api`'s base URL. Empty: the bank is off. |
| `TOADS_BANK_SERVICE_TOKEN` | The token shared with ToadsBank (its `TOADSBANK_SERVICE_TOKEN`). Empty: the bank is off. |
| `TOADS_BANK_BOT_TOKEN` | The bank bot's token for acting as a member; the same value in the bank bot's env. Empty: the bot's commands and buttons are refused. |
| `TOADS_BANK_CHANNEL_ID` | Where accepted snapshots are posted when the source's raid day has no `bank_requests` channel. |
| `TOADS_BANK_FALLBACK_CHANNEL_ID` | Where the bot reports a manager it could not DM. Empty: the bank channel. |
| `TOADS_SUPER_ADMIN_IDS` | Super admins' Discord user ids, comma-separated ([admin.md](admin.md)). |
| `TOADS_BREAK_GLASS_ADMIN_ID` | The break-glass admin's Discord user id ([admin.md](admin.md)). |

ToadsBank's side needs `TOADSBANK_SERVICE_TOKEN` (the same value) and `TOADSBANK_EVENTS_URL` set to
`<hub>/api/bank/events`.

## Local development with the fake bank

`toads_api.testing.fake_bank` is an in-memory implementation of the v1 contract, the `uploader` and `manager` roles
included: imports with the real `TOADSBANK/1`
reader (headers, base64, CRC-32), sources, replica, inventory, requests with idempotency keys and revisions, and the
outbox events, which it POSTs to `FAKE_BANK_EVENTS_URL`. It seeds one bank, "Toads main bank", captured an hour before
it started, managed by the fake Discord's dev user (1001) and assigned to the raid day `FAKE_BANK_RAID_DAY` (`wed`
in the dev stack).

`just up` starts it as `fake-bank` (port 8002 inside the stack), and `services/api/.env.example` points the API at it.
It refuses to start without `FAKE_BANK_I_AM_DEV=1`, as the fake Discord does, because its token opens everything.

To see the officer side, give the dev user an officer role: put a role id in `FAKE_DISCORD_ROLES` and the same id in a
raid day's `officer_roles` in `config/raid_days.yaml`. `toads_api.testing.fake_bank.encode_parts` turns a snapshot into
pasteable parts, and `sample_snapshot` gives one to start from.

The fake is not ToadsBank: raid allocations, expiry, baseline history and movement matching are left out, and nothing
persists.
