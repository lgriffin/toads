# Logs analysis on the server

How to get the WCL Analyzer's analysis (the Python project, lgriffin/warcraftlogs_project) running on the toads.gg
server, so the hub shows real raid data. Until the launch hold lifts on 4 November 2026 only officers and super admins
see the pages below; raiders see a coming-soon page. It assumes the hub is already deployed
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

So the desktop app's `warcraftlogs_history.db` and `config.json` stay on your PC. The server only needs a Warcraft Logs client
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
| `TOADS_SYNC_REFRESH_MINUTES` | optional; how often the sync looks for new reports (default `15`, `0` turns it off) |
| `TOADS_SYNC_RESERVE_PERCENT` | optional; the share of the guild key's hourly Warcraft Logs points the sync leaves unspent (default `20`) |
| `TOADS_SYNC_BATCH` | optional; a cap on reports per sync run on top of the rate limit (default `0`, no cap) |

Leave `TOADS_HUB_SERVICE_TOKEN` and `TOADS_CREDENTIALS_KEYS` as the setup script wrote them: they must match the
API's. If an older env file has no `TOADS_SYNC_` lines, the defaults apply. An env file written before October 2026
says `TOADS_SYNC_REFRESH_MINUTES=60` and `TOADS_SYNC_BATCH=10`, which hold the sync to ten reports an hour: change them
to `15` and `0`, or delete both lines.

### How much one sync imports

Warcraft Logs gives each API client a number of points an hour, and every query spends some. Before each report the
sync asks Warcraft Logs how many points the guild key has spent this hour (its `rateLimitData`), and it keeps going
while what is left, less the `TOADS_SYNC_RESERVE_PERCENT` reserve, still covers the dearest report it has imported so
far. A run also stops when the hour's points reset, so the publish jobs get their turn; the next run, 15 minutes later,
spends the new hour's points. The scheduler's log line `sync.done` says why each run stopped (`stopped`) and how many
points it left (`points_left`).

## 4. Restart with the new settings

```bash
sudo -iu toads /opt/toads/scripts/deploy.sh
```

The scheduler starts `sync-guild` straight away, then every 15 minutes. Each run analyses the guild's newest reports
that are not stored yet, as many as the rate limit allows, and the publish jobs that follow it put them on the hub. The sync stays off while the client id is empty or the guild id is `0`.

## 5. The first import

The scheduler's sync looks at the guild's newest 350 reports. To import **every** report the guild has on Warcraft
Logs, run the backfill once. It works oldest first (the scheduler takes the newest, so the two do not race), spends the
same rate-limit budget, waits for the hour's points to reset whenever they run out, and finishes on its own once
everything is stored or only reports that never analyse are left. A long history takes hours, so start it in `tmux`
or `screen`:

```bash
tmux new -s backfill
cd /opt/toads
sudo -u toads docker compose -f infra/docker-compose.prod.yml run --rm worker toads-worker backfill
```

It prints each report as it goes and "Waiting N min for the Warcraft Logs points to reset" while it waits; detach with
Ctrl+B then D and come back with `tmux attach -t backfill`. Ctrl+C stops it safely: run it again and it carries on.
At the end it prints how many reports it imported and lists the ones that failed. `toads-worker sync` runs one
scheduler-style pass by hand.

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

Comparing guild raids with another guild's report needs a Warcraft Logs **user** login on the guild's behalf; your own
super admin Warcraft Logs account is fine. It needs a redirect URL on the client:

1. On the Warcraft Logs client, add the redirect URL `https://toads.gg/api/reference/login/callback` (keep the
   localhost one if the desktop app uses it).
2. In `/opt/toads/services/api/.env`, set `TOADS_WCL_CLIENT_ID` and `TOADS_WCL_CLIENT_SECRET` to the same client.
3. Rerun `deploy.sh`, open the officer console, choose **Add reference reports** and connect the login, signing in to
   Warcraft Logs as the account that acts for the guild.

Only the client id and secret go in env files. The login's access and refresh tokens are stored encrypted in the hub's
database (with `TOADS_CREDENTIALS_KEYS`) and the worker refreshes them; Warcraft Logs rotates them, so they cannot live
in env files. Your Warcraft Logs password never reaches the hub.

[Admin guide section 8](../ADMIN_GUIDE.md#8-the-reference-comparison-login) has the details.

## Checking it works

```bash
cd /opt/toads
sudo -u toads docker compose -f infra/docker-compose.prod.yml logs --since 2h scheduler | grep -E 'sync|schedule'
```

`sync.done` lines show how many reports each run imported, failed and left for later, why it stopped and how many
rate-limit points it left; `schedule.job_failed` lines
show a job that broke, with the reason.

## Troubleshooting

| What you see | Why, and the fix |
| --- | --- |
| No `sync-guild` in the scheduler's `schedule.started` line | `TOADS_WCL_CLIENT_ID` is empty, `TOADS_WCL_GUILD_ID` is `0`, or `TOADS_SYNC_REFRESH_MINUTES` is `0` in the worker's env. Fix it and rerun `deploy.sh`. |
| `toads-worker sync` says to set `TOADS_WCL_GUILD_ID` | The guild id is still `0`; step 2. |
| `401` or `invalid_client` from Warcraft Logs | The client id or secret is wrong, or the client was deleted. |
| A report listed under `failed` every run | Warcraft Logs has no fights in it (an empty or trash-only log). It is retried each run and does not hold back older reports: the next one takes its place in the batch. |
| The sync imports nothing, `remaining` is 0, but raids are missing | They are not on the guild's Warcraft Logs page (logged as personal reports). Import each with `toads-worker analyse <URL>`. |
| `/hub` widgets still empty after a sync | The publish jobs have not run since; run them by hand (step 5) or wait up to 30 minutes. If they fail, the worker's `TOADS_HUB_SERVICE_TOKEN` does not match the API's. |
| `429` errors or `sync.rate_limited` in the worker's log | Something else spent the guild key's points (officer imports, a second deployment on the same client). Raise `TOADS_SYNC_RESERVE_PERCENT`. |
| Still about ten reports an hour | The env file still says `TOADS_SYNC_BATCH=10`; set it to `0` (step 3). |
| `sync.rate_limit_unreadable` in the log | Warcraft Logs did not answer the rate-limit query; that run falls back to ten reports. |

## Optional: the analyzer itself on AlmaLinux

The hub never needs this: its worker runs the analyzer's packages inside its container, whatever the host is. But the
WCL Analyzer now runs natively on AlmaLinux 9 (RHEL 9 and Rocky 9 too), so an officer on an EL desktop, or you on the
server for a one-off look at a report, can use the desktop app or its CLI there. Its CI installs and starts it in an
`almalinux:9` container on every pull request.

```bash
git clone https://github.com/lgriffin/warcraftlogs_project.git
cd warcraftlogs_project
scripts/install_linux.sh            # on a server with no display: add --no-desktop
```

The script installs Python 3.12 and Qt's X11 libraries with `dnf` (EL 9's own Python is too old), creates a `.venv` in
the checkout and links `warcraftlogs` and `warcraftlogs-gui` into `~/.local/bin`. Each release also ships a signed
`WarcraftLogsAnalyzer-<tag>-linux.tar.gz`. Update with `git pull` and the script again: the in-app updater is for
Windows and stays off on Linux. Over SSH, use the CLI (`warcraftlogs`); the GUI needs a display.

This install keeps its own `config.json` and `warcraftlogs_history.db` in the checkout. It does not touch the hub's
database or its env files, so it is safe beside the deployed hub. The script is tested on AlmaLinux 9; the toads.gg
server runs AlmaLinux 10, where it has not been tried yet. Details and troubleshooting
are in the analyzer's [Linux install guide](https://github.com/lgriffin/warcraftlogs_project/blob/master/guides/linux_install.md).

## Taking a newer analyzer

When the Python project gains a feature the hub should use, bump the pinned commit as
[admin guide: bumping the analyzer](../ADMIN_GUIDE.md#bumping-the-analyzer) says. The deploy runs wcl-store's
migrations (`analyser-migrate`) before the worker restarts, so new tables appear on their own.
