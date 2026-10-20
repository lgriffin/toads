# Super admins, the break-glass admin and officer tokens

The hub's roles come from Discord (REQ-HUB-RBAC-001): members, trials, raiders, a raid day's officers and global
officers. A super admin may also make one member an officer through an **officer grant** (REQ-HUB-RBAC-005). Above them sit a handful of **super admins**, named in the hub's configuration, who hand the bank's upkeep
to other members: directly, as a grant, or through an **officer token** the member redeems themselves. One of them may
be the **break-glass admin**, who is always a super admin and is never hidden.

For every other setting, first-time setup and routine operations, see the [admin guide](../ADMIN_GUIDE.md).

## Super admins

- `TOADS_SUPER_ADMIN_IDS` in `services/api/.env`: Discord user ids, comma-separated. Empty: none.
- Nothing in the app makes someone a super admin: no route, no table, no Discord role. Changing the list means
  changing the environment and restarting the API.
- `rbac.deps.elevate` marks the caller's Principal on every request, on the site and through the bank bot alike. A
  super admin is a global officer too, so they hold every global-tier power whatever their Discord roles: they import
  snapshots and work the request queue on every raid day's banks, and ToadsBank hears them as `admin`, with no role
  or grant needed and nobody else to wait for. Global officers likewise hold every bank power without a grant.
- `Permission.MANAGE_GRANTS` is theirs alone (`rbac.permissions.SUPER_ADMIN_ONLY`): no officer role or grant carries
  it. It opens granting and revoking bank grants, and minting, listing and revoking officer tokens. Global officers
  still see the grants list (`GET /api/admin/bank/grants`).
- `Permission.MANAGE_ROLE_BADGES` is theirs alone too: tying badges to Discord roles ([role-badges.md](role-badges.md)).
- `Permission.MANAGE_OFFICER_GRANTS` is theirs alone too: granting and revoking officer grants (below).
- `/api/session` and `/api/bank/me` say `super_admin: true`.

## The break-glass admin

- `TOADS_BREAK_GLASS_ADMIN_ID`: one Discord user id that is always a super admin, whatever their Discord roles or
  `TOADS_SUPER_ADMIN_IDS` say. Empty: none. No id is written into the code.
- It is visible, not a back door:
  - `/api/session` and `/api/bank/me` say `break_glass: true` to that person;
  - `/api/bank/me` names the break-glass admin's Discord user id (`break_glass_admin`) to the global tier, and the
    Bank page's grants section shows it;
  - every change they make (any `POST`, `PATCH`, `PUT` or `DELETE` past a `require(...)` guard) writes an audit row
    with action `break_glass`, the method and path as its target and the permission used as its detail, before the
    route runs. Reads are not marked.
- They still sign in with Discord and must be in the Toads server: break-glass widens what they may do, not who can
  sign in.

## Officer grants

Officers normally come from Discord roles in `config/raid_days.yaml`. When someone needs officer powers without a
Discord role (cover for a night, a trusted helper), a super admin grants them on the Admin page, under "Officer
grants": find the member in the Toads Discord by username or nickname, pick a raid night or "Every night", and grant.

- A night's grant makes them an officer of that raid day, exactly as that day's `officer_roles` would: its officer
  section, claims, applications, banks, board. "Every night" makes them a global officer, as `global_officer_roles`
  would.
- A grant adds to their Discord roles and never takes from them. Revoking it leaves whatever their roles give.
- **It never makes anyone a super admin**, and a global officer from a grant cannot grant anything: officer grants,
  bank grants, tokens and badges stay `SUPER_ADMIN_ONLY`. Super admins come from `TOADS_SUPER_ADMIN_IDS` alone.
- Grants are read from the database on every request (`Services.principal_for`), on the site and through the bank
  bot, so a grant or revoke counts on the member's next call, with no sign-in or role refresh needed.
- Only someone in the Toads server can be granted. Their Discord username and server name are kept for the list.
- A grant for a raid day later removed from `raid_days.yaml` opens nothing.
- Discord channel permissions are not touched: interview rooms still open to the officer roles, so a granted officer
  who should sit interviews goes on that night's interview panel too ([recruitment.md](recruitment.md)).
- Stored in hub-db's `officer_grants` table (migration `0022`): the Discord user id, names, the raid day (`*` for every
  night), who granted it and when.

Routes (super admins only): `GET /api/admin/officer-grants` (the grants and the nights one can cover),
`GET /api/admin/officer-grants/discord-members?q=` (search the server), `POST /api/admin/officer-grants`
(`{discord_user_id, raid_day}`, `raid_day` null for every night; `201`, or `200` when already held) and
`DELETE /api/admin/officer-grants/{id}`.

## Officer tokens

A super admin mints a token on the Bank page (`POST /api/admin/bank/tokens`), naming:

- the permissions it grants: `import_bank_snapshot`, `manage_bank` or both;
- a raid day (that day's banks), or none (every bank the redeemer can see);
- how long it lasts: 7 days by default, at most 30;
- how often it may be redeemed: once by default, at most 25;
- an optional note, such as who it is for.

The token (`toads-bank-` and 43 random URL-safe characters) is in the answer once and never again: hub-db's
`bank_grant_tokens` table (migration `0012`) keeps its SHA-256 hash, the permissions, the raid day, who minted it and
when, its expiry, its uses, who redeemed it last and when, and when it was revoked. The super admin passes it on
outside the hub (a DM, say).

A member redeems it on the Bank page or with `/bank redeem <token>` in Discord (an ephemeral reply; the bank bot calls
`POST /api/bank/redeem` as that member, see [bank.md](bank.md)). In one transaction the hub looks the hash up, checks
the token is still usable, counts the use and adds the grants it names, as from the super admin who minted it.

- A wrong, expired, used-up or revoked token all get the same `400` answer, and the redeemer gains nothing.
- After 5 refused tries in 15 minutes a member gets `429` until the window passes. With 256 random bits a guess cannot
  succeed anyway; the limit keeps guessing noisy.
- Redeeming what the member already holds keeps the existing grant.
- Super admins list tokens (`GET /api/admin/bank/tokens`: never the token, with a status of `active`, `used`,
  `expired` or `revoked`) and revoke one that could still be redeemed (`DELETE /api/admin/bank/tokens/{id}`; a used,
  expired or revoked one is `409`). Revoking a token does not take back grants already given from it: revoke those in
  the grants list.

## Audit log

| Action | Actor | Target | Detail |
| --- | --- | --- | --- |
| `bank.grant` | the super admin | `bank grant {id}: {permission} for discord user {id}` | |
| `bank.revoke` | the super admin | the same | |
| `bank.token_minted` | the super admin | `bank token {id}` | the permissions |
| `bank.token_redeemed` | the redeemer | `bank token {id}` | the grants it gave, by id |
| `bank.token_revoked` | the super admin | `bank token {id}` | |
| `officer.grant` | the super admin | `officer grant {id}: officer for discord user {id}` (`global officer` for every night) | |
| `officer.revoke` | the super admin | the same | |
| `break_glass` | the break-glass admin | `{METHOD} {path}` | the permission used |

## Configuration

| Variable | Meaning |
| --- | --- |
| `TOADS_SUPER_ADMIN_IDS` | Super admins' Discord user ids, comma-separated. Empty: none. |
| `TOADS_BREAK_GLASS_ADMIN_ID` | The break-glass admin's Discord user id. Empty: none. |
