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
| `GET /api/bank/me` | `VIEW_BANK` | none: whether the bank is set up, and the caller's officer days |
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
| `POST /api/bank/events` | ToadsBank's service token | none: see Events |

Every guild member holds `VIEW_BANK` and `REQUEST_BANK_ITEMS`. `IMPORT_BANK_SNAPSHOT` and `MANAGE_BANK` are officer
permissions and, like every officer power, are scoped to a raid day: a Wednesday officer works the bank under
`/api/days/wed/bank/...`, a global officer under any day. Registering or editing a source is the global tier's
(ToadsBank's `admin`). ToadsBank still applies a source's `audience` and its `managers` list, so a raid-day officer can
only approve requests on banks they manage.

The URL's day decides who reaches a route; the hub also binds each officer route to the banks of that day (a source's
`raidDay`), so a Wednesday officer cannot work Sunday's bank under `/api/days/wed/...`:

- the request queue lists only requests on that day's banks;
- approve, reject and deliveries first look the request up (`GET /v1/requests?scope=all`) and check its source's day;
- preview and accept check the day of the bank the snapshot matched (`matchedSource`); an unregistered bank needs
  the global tier.

A refusal is `403 not_this_day`. Global officers are not bound: they work every bank, including those with no raid
day, under any day's URL. Opening an import and adding parts touch no bank, so they are not bound either. The bot,
which does not know a request's bank, tries the member's officer days in turn and moves on after `not_this_day`.

### Identity

The hub sends ToadsBank:

- `Authorization: Bearer <TOADS_BANK_SERVICE_TOKEN>`;
- `X-Toads-Member`: the member's Discord user id;
- `X-Toads-Name`: their display name, percent-encoded UTF-8;
- `X-Toads-Roles`: `member`, plus `officer` when they hold officer powers on any raid day, plus `admin` for a global
  officer.

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
3. builds their Principal exactly as a login would, so the route's `require(...)` applies as usual.

So the bot can do nothing the member could not do on the site. Manager actions use the raid days the member is an
officer for (from `GET /api/bank/me`), in turn, until one owns the bank.

## Configuration

`services/api/.env`:

| Variable | Meaning |
| --- | --- |
| `TOADS_BANK_URL` | `toadsbank-api`'s base URL. Empty: the bank is off. |
| `TOADS_BANK_SERVICE_TOKEN` | The token shared with ToadsBank (its `TOADSBANK_SERVICE_TOKEN`). Empty: the bank is off. |
| `TOADS_BANK_BOT_TOKEN` | The bank bot's token for acting as a member; the same value in the bank bot's env. Empty: the bot's commands and buttons are refused. |
| `TOADS_BANK_CHANNEL_ID` | Where accepted snapshots are posted when the source's raid day has no `bank_requests` channel. |
| `TOADS_BANK_FALLBACK_CHANNEL_ID` | Where the bot reports a manager it could not DM. Empty: the bank channel. |

ToadsBank's side needs `TOADSBANK_SERVICE_TOKEN` (the same value) and `TOADSBANK_EVENTS_URL` set to
`<hub>/api/bank/events`.

## Local development with the fake bank

`toads_api.testing.fake_bank` is an in-memory implementation of the v1 contract: imports with the real `TOADSBANK/1`
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
