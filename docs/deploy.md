# Deploying the Toads hub to a VPS

Step by step from a bare server to "merge to main and the site updates itself". Written for a **GoDaddy VPS running
AlmaLinux 10** with a domain registered at GoDaddy; [what changes elsewhere](#what-changes-on-a-different-server) is at
the end. The [admin guide](../ADMIN_GUIDE.md) explains every setting; this page is only the server and the pipeline.

What you end up with:

```
push / merge to main ──> CI (GitHub Actions) ──green──> Deploy workflow ──SSH──> scripts/deploy.sh on the VPS
                                                                                   │ git checkout <sha>
                                                                                   │ docker compose build
                                                                                   │ run both migrations
                                                                                   └ restart the stack
https://<your domain> ──> Caddy (ports 80/443, Let's Encrypt certificate) ──> web app / API
```

- Everything runs in Docker from `infra/docker-compose.prod.yml`. Postgres and Redis are not reachable from outside.
- Caddy gets and renews the HTTPS certificate on its own (Let's Encrypt, free). No certbot or nginx needed. If you
  already paid GoDaddy for a certificate, [step 9](#9-optional-use-a-certificate-bought-from-godaddy) uses it instead.
- A deploy only happens after CI passes on main. If a database migration fails, the running site is left alone.
- SELinux stays **enforcing**; the compose file labels its mounts for it.

Never paste a password, token or private key into a chat, issue or commit. They go only on the server or in GitHub's
secret settings.

## 1. Point your GoDaddy domain at the server

1. In the GoDaddy dashboard open your VPS and note its **public IPv4 address**.
2. Go to **My Products → Domains → your domain → DNS → DNS Records**.
3. Delete the existing `A` record for `@` whose value says **Parked** (or any other `A` record for `@`).
4. Add, or edit, these records (TTL 1/2 hour is fine):

   | Type | Name | Value |
   | --- | --- | --- |
   | A | `@` | your VPS IP |
   | CNAME | `www` | `@` |

   To use a subdomain instead (say `hub.example.com`), add one `A` record with Name `hub` and leave `@` alone.
5. If there is an `AAAA` record and your VPS has no IPv6 address, delete it: Let's Encrypt tries IPv6 first.
6. If there is a `CAA` record, it must allow `letsencrypt.org` (or delete it).

Check from your own computer (it can take a few minutes):

```bash
nslookup toads.example.com    # should print your VPS IP
```

If GoDaddy's VPS dashboard has its own firewall, allow inbound TCP 22, 80 and 443 (and UDP 443) there too.

## 2. First login and your own password

SSH in with the details GoDaddy gave you (Windows: PowerShell or PuTTY; Mac/Linux: Terminal):

```bash
ssh <user>@<VPS IP>
passwd            # change your password to one only you know
```

Recommended: log in with a key instead of a password. On **your own computer**:

```bash
ssh-keygen -t ed25519            # once; press Enter for the defaults
ssh-copy-id <user>@<VPS IP>      # Windows has no ssh-copy-id: append id_ed25519.pub to ~/.ssh/authorized_keys on the server
ssh <user>@<VPS IP>              # should not ask for the server password now
```

Step 10 turns password logins off once keys work.

## 3. Run the setup script

On the server:

```bash
curl -fsSL https://raw.githubusercontent.com/lgriffin/toads/main/scripts/server-setup.sh -o server-setup.sh
less server-setup.sh                                   # read what it does first
sudo bash server-setup.sh toads.example.com you@example.com
```

Use your real domain and an email address for Let's Encrypt's expiry warnings. The script
([scripts/server-setup.sh](../scripts/server-setup.sh)):

- updates the system and installs Docker CE (from Docker's RHEL repository) with the compose plugin;
- turns on Docker's SELinux support and log rotation (`/etc/docker/daemon.json`);
- opens SSH, HTTP and HTTPS in firewalld;
- adds 2 GB of swap if the server has under 4 GB of RAM (image builds need it);
- creates a `toads` user (member of the `docker` group) and clones the hub to `/opt/toads`;
- writes `infra/.env` and every `services/*/.env` with fresh random secrets: the Postgres password, the hub service
  token, the credentials key and the bank bot token. It points the API at the real Discord and at your domain and
  turns the guild bank off until ToadsBank is deployed;
- makes the SSH key GitHub will deploy with. That key can only run `scripts/deploy.sh`: no shell, no forwarding.

It ends by printing the four GitHub secrets for [step 7](#7-let-github-deploy-on-every-push). Keep that window open, or
run it again later: it never replaces a secret that is already set.

## 4. Discord and Warcraft Logs applications

Sign-in, the API's role reads and the Toad Bot all use **one Discord application**: the Toad Bot's. For Toads that is
application **1561652680768626688**, the `client_id` in the bot's invite link. Its id is public; its **client
secret** and **bot token** are not, and go only into the server's env files in [step 5](#5-fill-in-the-values-only-you-have).
The API checks at startup that the bot token belongs to `TOADS_DISCORD_CLIENT_ID`. If they come from different
applications, or Discord rejects the token, it still starts (so the site stays up) and logs a
`discord_application_misconfigured` error naming both settings; a failed deploy shows that line in its log.

### Turn on Discord sign-in

1. Open <https://discord.com/developers/applications> and sign in with the Discord account that made the Toad Bot.
2. Click the **Toad Bot** application. **General Information** shows its **Application ID**; for Toads it is
   `1561652680768626688`. That is the value of `TOADS_DISCORD_CLIENT_ID`.
3. In the left menu click **OAuth2**.
4. Under **Redirects** click **Add Redirect** and paste exactly this, with no slash at the end:

   ```
   https://toads.gg/auth/callback
   ```

   (On another domain use `https://<your domain>/auth/callback`. It must equal `TOADS_DISCORD_REDIRECT_URI`, which the
   setup script already wrote.) Click **Save Changes** in the bar that appears at the bottom.
5. Still on **OAuth2**, under **Client Secret** click **Reset Secret**, confirm, and click **Copy**. Paste it straight
   into `TOADS_DISCORD_CLIENT_SECRET` in step 5. Discord shows it only once; if you lose it, reset it again.
6. In the left menu click **Bot**. Under **Privileged Gateway Intents** switch on **Server Members Intent** and
   **Message Content Intent**, then **Save Changes**. If you do not have the bot token on the server yet, click
   **Reset Token**, copy it, and paste it into `TOADS_DISCORD_BOT_TOKEN` in step 5 (the API's env and
   `services/bot/.env`). Resetting it logs out a running Toad Bot until its env has the new token.
7. Nothing else is ticked on the application: the hub asks for the `identify` and `guilds.members.read` scopes itself
   each time someone signs in, so you do not use the OAuth2 URL Generator for sign-in. (The generator is only for the
   bot's invite link, [admin guide](../ADMIN_GUIDE.md#getting-the-toad-bot-onto-the-server).)

Only members of the Toads Discord server can sign in. Anyone else who tries lands on a "members only" page and gets
no session, so the bot must be in the server and `TOADS_DISCORD_GUILD_ID` must be the Toads server's id.

### Warcraft Logs

Follow [admin guide section 2](../ADMIN_GUIDE.md#2-accounts-and-applications-to-create) to create the Warcraft Logs
client. Once the site is up, [docs/logs-analysis.md](logs-analysis.md) turns on the guild's raid analysis.

## 5. Fill in the values only you have

Edit with `sudo -u toads nano <file>` (Ctrl-O saves, Ctrl-X quits). The setup script already filled everything that
is not listed here.

`/opt/toads/services/api/.env`

| Setting | Value |
| --- | --- |
| `TOADS_DISCORD_CLIENT_ID` | the Toad Bot's Application ID (`1561652680768626688` for Toads) |
| `TOADS_DISCORD_CLIENT_SECRET` | Toad Bot application → OAuth2 → Reset Secret (step 4) |
| `TOADS_DISCORD_BOT_TOKEN` | Toad Bot application → Bot → Reset Token (step 4) |
| `TOADS_DISCORD_GUILD_ID` | Discord: right-click the server → Copy Server ID (needs Developer Mode) |
| `TOADS_SUPER_ADMIN_IDS`, `TOADS_BREAK_GLASS_ADMIN_ID` | your Discord user id, and the other super admins ([docs/admin.md](admin.md)) |
| `TOADS_WCL_CLIENT_ID`, `TOADS_WCL_CLIENT_SECRET` | Warcraft Logs client (leave the id empty to turn the reference login off) |

`/opt/toads/services/worker/.env`: `TOADS_WCL_CLIENT_ID`, `TOADS_WCL_CLIENT_SECRET`, `TOADS_WCL_GUILD_ID`.

`/opt/toads/config/raid_days.yaml`, `community.yaml`, `raid_sheets.yaml`: real Discord role and channel ids, as
[admin guide section 5](../ADMIN_GUIDE.md#5-config-files) describes. The API checks the raid-day roles against Discord
when it starts, so it will not start with the example ids.

Bots are optional at first, and each starts on its own. For the Toad Bot (interview rooms, posts), fill in
`services/bot/.env` (its token, `TOADS_DISCORD_GUILD_ID`, and `TOADS_HUB_SERVICE_TOKEN` as in the API's env) and set
`COMPOSE_PROFILES=bot` in `/opt/toads/infra/.env`. For the bank bot, put the **bank bot's own** application token in
`services/bot/.env.bank` and make it `COMPOSE_PROFILES=bot,bank`. The deploy script builds and starts only the bots
named there, so a bot left out keeps running its old build.

## 6. First deploy, by hand

```bash
sudo -iu toads /opt/toads/scripts/deploy.sh
```

The first build takes a while. When it prints `... is live`, open `https://toads.example.com`: Caddy fetches the
certificate on the first request, so the very first page can take a few seconds. Sign in with Discord and you should
land on `/hub` (the first time, Discord asks you to authorize **Toad Bot**; that is the sign-in). If something fails, see [troubleshooting](#troubleshooting).

## 7. Let GitHub deploy on every push

In GitHub: **lgriffin/toads → Settings → Environments → New environment**, name it `production`, then add these
**environment secrets** (the setup script printed them; run it again to see them):

| Secret | Value |
| --- | --- |
| `DEPLOY_HOST` | your domain (or the VPS IP) |
| `DEPLOY_USER` | `toads` |
| `DEPLOY_KNOWN_HOSTS` | the two `... ssh-ed25519 AAAA...` lines it printed (pins the server's identity) |
| `DEPLOY_SSH_KEY` | the whole output of `sudo cat /root/toads-deploy-key`, including the BEGIN and END lines |

Then delete the private key from the server: `sudo rm /root/toads-deploy-key /root/toads-deploy-key.pub`.

Optional: under the environment's **Deployment branches**, allow only `main`.

Finally, **Settings → Secrets and variables → Actions → Variables → New repository variable**: `DEPLOY_ENABLED` =
`true`. Until this exists the Deploy workflow skips itself.

Test it: **Actions → Deploy → Run workflow** (leave the sha empty). The run's log shows the server's output.

## 8. Day to day

- **Ship a change**: merge a PR into main. CI runs; when it is green, the Deploy workflow rolls that commit out. Only
  one deploy runs at a time; a later one waits.
- **Roll back**: Actions → Deploy → Run workflow, and paste the full sha of an earlier main commit. Migrations only run
  forwards, so rolling back past a migration needs [admin guide section 11](../ADMIN_GUIDE.md#11-routine-operations).
- **Pause deploys**: set `DEPLOY_ENABLED` to `false`.
- **What's live**: `sudo -iu toads tail /opt/toads/.git/deploy.log`.
- **Logs**: `cd /opt/toads && sudo -u toads docker compose -f infra/docker-compose.prod.yml logs -f api` (or `web`,
  `worker`, `caddy`).
- **Change a setting**: edit the `.env` file, then run the deploy script by hand (step 6) to restart with it.
- **Backups**: [admin guide section 13](../ADMIN_GUIDE.md#13-backups-and-restore). At minimum, a nightly
  `docker compose -f infra/docker-compose.prod.yml exec -T postgres pg_dump -U toads toads` copied off the server.

### Analyzer releases

The site runs a **release** of the analyzer (lgriffin/warcraftlogs_project), never its master, so experimental work
there stays off toads.gg. The **Analyzer release** workflow (`.github/workflows/analyzer-release.yml`) runs nightly at
03:17 UTC: when the analyzer's latest release is newer than the pin in `pyproject.toml`, it opens a PR named "Take
analyzer release vX.Y.Z" that changes only `pyproject.toml` and `uv.lock`. When CI passes on that PR, the same workflow
merges it, and Deploy ships it as usual (with the analyzer's migrations). A red PR stays open for you; so does one with
anything else pushed to it.

It skips pre-releases and any tag that is not plain `vX.Y.Z`, and it never moves to a release that lacks commits the
current pin has. To ship analyzer changes, publish a release there (push a `vX.Y.Z` tag); to hold one back, mark it as
a pre-release.

Setup, once:

1. Make a fine-grained token: GitHub → **Settings → Developer settings → Personal access tokens → Fine-grained tokens →
   Generate new token**. Resource owner `lgriffin`, **Only select repositories** → `lgriffin/toads`, repository
   permissions **Contents: Read and write** and **Pull requests: Read and write**. Pick an expiry and diarise it: when
   the token expires the workflow fails until you replace it.
2. In this repository: **Settings → Secrets and variables → Actions → Secrets → New repository secret**:
   `ANALYZER_BUMP_TOKEN` = the token. (The workflow needs its own token because PRs and merges made with GitHub's
   default token start neither CI nor Deploy.)
3. **Variables → New repository variable**: `ANALYZER_RELEASES_ENABLED` = `true`. Until this exists the workflow skips
   itself; set it to `false` to pause.

Test it: **Actions → Analyzer release → Run workflow**. If the pin is already the latest release, the log says so.

## 9. Optional: use a certificate bought from GoDaddy

Skip this unless you have already paid for one: Let's Encrypt is free and renews itself, while a GoDaddy certificate
must be re-downloaded and installed by hand each year.

1. On the server, make a key and signing request:
   ```bash
   cd /opt/toads/infra/certs
   sudo -u toads openssl req -new -newkey rsa:2048 -nodes -keyout privkey.pem -out request.csr \
     -subj "/CN=toads.example.com"
   cat request.csr
   ```
2. In GoDaddy: **SSL Certificates → your certificate → Manage → Re-key & Manage**, paste the CSR, submit, and wait for
   it to be issued.
3. **Download**, server type **Other**. Unzip; you get `<random>.crt` and `gd_bundle-g2-g1.crt`. Copy them to the
   server (e.g. `scp`) and join them, your certificate first:
   ```bash
   cat <random>.crt gd_bundle-g2-g1.crt | sudo -u toads tee /opt/toads/infra/certs/fullchain.pem >/dev/null
   sudo chmod 600 /opt/toads/infra/certs/privkey.pem
   ```
4. Tell Caddy to use them (this file is git-ignored, so deploys keep it):
   ```bash
   echo 'tls /certs/fullchain.pem /certs/privkey.pem' | sudo -u toads tee /opt/toads/infra/certs/tls.caddy
   ```
5. Run the deploy script (step 6). Set a reminder to repeat steps 1 to 3 before the certificate expires.

## 10. Lock the server down

Once key logins work (step 2) and the site is up:

```bash
sudo tee /etc/ssh/sshd_config.d/50-toads.conf >/dev/null <<'EOF'
PasswordAuthentication no
PermitRootLogin no
EOF
sudo sshd -t && sudo systemctl reload sshd
```

Keep your current SSH session open and check that a **new** one still gets in before closing it. If GoDaddy only gave
you `root`, create your own admin user first (`sudo useradd -m -G wheel <name>`, `sudo passwd <name>`, copy your key
into its `~/.ssh/authorized_keys`).

Automatic security updates:

```bash
sudo dnf -y install dnf-automatic
sudo sed -i 's/^upgrade_type.*/upgrade_type = security/; s/^apply_updates.*/apply_updates = yes/' /etc/dnf/automatic.conf
sudo systemctl enable --now dnf-automatic.timer
```

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Browser says the certificate is invalid, or the site never loads | `logs caddy`. Usually DNS not pointing here yet (`nslookup`), port 80 or 443 closed in GoDaddy's panel, or a stray `AAAA`/`CAA` record (step 1). Caddy retries on its own once fixed. |
| Deploy stops at a migration | The old site keeps running. `logs migrate` or run `docker compose -f infra/docker-compose.prod.yml run --rm migrate` to see the error. |
| `api is unhealthy` | `logs api`. Most often a Discord value or a role id in `config/raid_days.yaml`. "belongs to application" means the client id and bot token are from different Discord applications (step 4). |
| Discord says `Invalid OAuth2 redirect_uri` | The redirect on the Toad Bot's OAuth2 page is not exactly `https://<your domain>/auth/callback` (step 4). |
| Signing in lands on "members only" | That Discord account is not in the Toads server, or `TOADS_DISCORD_GUILD_ID` is another server's id. |
| Permission denied reading `/config` or the Caddyfile | SELinux: `sudo ausearch -m avc -ts recent`. The mounts carry `z` labels; check `/etc/docker/daemon.json` has `"selinux-enabled": true` and Docker was restarted. |
| Deploy workflow fails at SSH | `DEPLOY_KNOWN_HOSTS` must match the server (re-run the setup script to print it); `DEPLOY_SSH_KEY` must include the BEGIN/END lines. |
| Setup stops at Docker: `failed to add jump rules` or `Extension addrtype ... missing kernel module` | The kernel lacks `xt_addrtype`. `sudo dnf -y install kernel-modules-extra`, `sudo reboot`, then run the setup script again. |
| Build killed / out of memory | `free -h`; the setup script adds swap below 4 GB of RAM. A 2 GB VPS is the practical minimum. |
| `another deploy is running` | Wait; one deploy at a time. |

`logs X` above means `cd /opt/toads && sudo -u toads docker compose -f infra/docker-compose.prod.yml logs X`.

## What changes on a different server

- **Ubuntu or Debian**: replace the `dnf` and Docker repository steps in the setup script with Docker's apt
  instructions, and `firewalld` with `ufw allow 80,443/tcp`. There is no SELinux; the `z` labels are harmless.
- **Podman instead of Docker**: not supported by these files; the stack relies on compose's
  `service_completed_successfully` ordering. Keep Docker CE.
- **No root access** (GoDaddy shared hosting rather than a VPS): this setup needs a VPS.
- **ToadsBank**: deploy it next to the hub ([its operations guide](https://github.com/lgriffin/ToadsBank/blob/main/docs/operations.md)),
  then set `TOADS_BANK_URL` and `TOADS_BANK_SERVICE_TOKEN` in `services/api/.env` (admin guide section 10).
