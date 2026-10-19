# Logs analysis on the server

How to get the WCL Analyzer's analysis (the Python project, lgriffin/warcraftlogs_project) running on the toads.gg
server, so a super admin sees real raid data in the hub today. It assumes the hub is already deployed
([docs/deploy.md](deploy.md)); every command below runs on the server over SSH.

## How the two projects fit together

Nothing from the desktop app is copied to the server. The hub's worker installs the analyzer's own packages
(`wcl-core`, `wcl-store`, `wcl-app`) from lgriffin/warcraftlogs_project, pinned to one commit in the root
`pyproject.toml`, and runs the same `RaidService` the desktop app runs. It fetches the guild's reports from Warcraft
Logs itself and stores the results in the hub's Postgres database, in wcl-store's tables beside the hub's own.

```
Warcraft Logs ──(guild key)──> worker: sync-guild ──> Postgres (wcl-store tables)
                                scheduler: publish-home, publish-performance, publish-badges, publish-reference
                                        └──(service token)──> API ──> hub home, /me, badges, reference page
```

So the desktop app's `analyzer.db` and `config.json` stay on your PC. The server only needs a Warcraft Logs client
and the guild's id.

## What a super admin sees once it runs

Super admins are global officers too, so they see every officer view.

| Where | What fills in |
| --- | --- |
| `/hub` | The analyzer widgets: guild snapshot, last raid, recent raids, raid activity, healing week on week, top damage and healing, attendance, boss kills, class mix, interrupts, consumables, flasks, and the officers' badge roster. |
| `/me` | Your performance against the role median and your Toads badges, once your character claim is approved. |
| Claim search | Character names to claim, from the raids the sync analysed. |
| `/officers/reference` | The guild raids to compare, and comparisons once the reference login is connected (step 6). |
| `/admin` | The scheduler's jobs, now including `sync-guild`. |

The Raids & Logs table (`/raids`) is still a placeholder; it is a later phase.

## 1. A Warcraft Logs client

Use the client you already have (the one with the `https://localhost:1234` redirect), or create one at
**warcraftlogs.com → your profile → Clients (API) → Create client**. The worker signs in with client credentials, which
need no redirect URL, so the localhost redirect is fine for it.

Keep the client id and secret to yourself: they go into the server's env files in step 3, never into chat or Git.

## 2. The guild's Warcraft Logs id

Open the guild's page on Warcraft Logs (search for Toads on Spineshatter). The id is the number in the address, for
example `https://fresh.warcraftlogs.com/guild/id/123456` means `123456`. If the address shows the guild's name
instead, the desktop app's `config.json` has the same number as `guild_id`.

## 3. Fill in the worker's settings

```bash
sudo -u toads nano /opt/toads/services/worker/.env
```

| Setting | Value |
| --- | --- |
| `TOADS_WCL_CLIENT_ID` | the client id from step 1 |
| `TOADS_WCL_CLIENT_SECRET` | its secret |
| `TOADS_WCL_GUILD_ID` | the number from step 2 |
| `TOADS_WCL_API_URL` | leave the default (`https://fresh.warcraftlogs.com/api/v2/client`) for Anniversary realms |
| `TOADS_SYNC_REFRESH_MINUTES` | optional; how often the sync looks for new reports (default `60`, `0` turns it off) |
| `TOADS_SYNC_BATCH` | optional; the most reports one sync analyses (default `10`) |

Leave `TOADS_HUB_SERVICE_TOKEN` and `TOADS_CREDENTIALS_KEYS` as the setup script wrote them: they must match the
API's. If an older env file has no `TOADS_SYNC_` lines, the defaults apply.

## 4. Restart with the new settings

```bash
sudo -iu toads /opt/toads/scripts/deploy.sh
```

The scheduler starts `sync-guild` straight away, then every hour. Each run analyses up to `TOADS_SYNC_BATCH` of the
guild's newest reports that are not stored yet, oldest of them first, and the publish jobs that follow it put them on
the hub. The sync stays off while the client id is empty or the guild id is `0`.

## 5. The first import

The scheduler will work through the guild's history ten reports an hour. To fill the hub now, run the sync by hand a
few times (each run prints what it imported and how many reports are left):

```bash
cd /opt/toads
sudo -u toads docker compose -f infra/docker-compose.prod.yml run --rm worker toads-worker sync
```

To analyse one particular report, for example an older raid the batches have not reached yet, give its code or URL:

```bash
sudo -u toads docker compose -f infra/docker-compose.prod.yml run --rm worker \
  toads-worker analyse https://fresh.warcraftlogs.com/reports/aBcD1234eFgH5678
```

Then publish straight away instead of waiting for the next half hour:

```bash
for job in publish-home publish-performance publish-badges publish-reference; do
  sudo -u toads docker compose -f infra/docker-compose.prod.yml run --rm worker toads-worker "$job"
done
```

Sign in to https://toads.gg and open `/hub`: the analyzer widgets should show the raids you imported. Claim your
character on `/me/claim` to see your own performance and badges there; a claim matching your Discord nickname is
approved at once, otherwise approve it in the Officers console.

## 6. Optional: the reference comparison login

Comparing guild raids with another guild's report needs a Warcraft Logs **user** login, which needs a redirect URL on
the client:

1. On the Warcraft Logs client, add the redirect URL `https://toads.gg/api/reference/login/callback` (keep the
   localhost one if the desktop app uses it).
2. In `/opt/toads/services/api/.env`, set `TOADS_WCL_CLIENT_ID` and `TOADS_WCL_CLIENT_SECRET` to the same client.
3. Rerun `deploy.sh`, open `/officers/reference` and connect the guild's dedicated Warcraft Logs account.

[Admin guide section 8](../ADMIN_GUIDE.md#8-the-reference-comparison-login) has the details.

## Checking it works

```bash
cd /opt/toads
sudo -u toads docker compose -f infra/docker-compose.prod.yml logs --since 2h scheduler | grep -E 'sync|schedule'
```

`sync.done` lines show how many reports each run imported, failed and left for later; `schedule.job_failed` lines
show a job that broke, with the reason.

## Troubleshooting

| What you see | Why, and the fix |
| --- | --- |
| No `sync-guild` in the scheduler's `schedule.started` line | `TOADS_WCL_CLIENT_ID` is empty, `TOADS_WCL_GUILD_ID` is `0`, or `TOADS_SYNC_REFRESH_MINUTES` is `0` in the worker's env. Fix it and rerun `deploy.sh`. |
| `toads-worker sync` says to set `TOADS_WCL_GUILD_ID` | The guild id is still `0`; step 2. |
| `401` or `invalid_client` from Warcraft Logs | The client id or secret is wrong, or the client was deleted. |
| A report listed under `failed` every run | Warcraft Logs has no fights in it (an empty or trash-only log). It is retried each run and does no harm; it only takes one place in the batch. |
| The sync imports nothing, `remaining` is 0, but raids are missing | They are not on the guild's Warcraft Logs page (logged as personal reports). Import each with `toads-worker analyse <URL>`. |
| `/hub` widgets still empty after a sync | The publish jobs have not run since; run them by hand (step 5) or wait up to 30 minutes. If they fail, the worker's `TOADS_HUB_SERVICE_TOKEN` does not match the API's. |
| `429` errors in the worker's log | Warcraft Logs rate limit. Lower `TOADS_SYNC_BATCH` or raise `TOADS_WCL_THROTTLE_MS`. |

## Taking a newer analyzer

When the Python project gains a feature the hub should use, bump the pinned commit as
[admin guide: bumping the analyzer](../ADMIN_GUIDE.md#bumping-the-analyzer) says. The deploy runs wcl-store's
migrations (`analyser-migrate`) before the worker restarts, so new tables appear on their own.
