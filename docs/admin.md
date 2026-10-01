# Super admins, the break-glass admin and officer tokens

The hub's roles come from Discord (REQ-HUB-RBAC-001): members, trials, raiders, a raid day's officers and global
officers. Above them sit a handful of **super admins**, named in the hub's configuration, who hand the bank's upkeep
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
| `break_glass` | the break-glass admin | `{METHOD} {path}` | the permission used |

## Configuration

| Variable | Meaning |
| --- | --- |
| `TOADS_SUPER_ADMIN_IDS` | Super admins' Discord user ids, comma-separated. Empty: none. |
| `TOADS_BREAK_GLASS_ADMIN_ID` | The break-glass admin's Discord user id. Empty: none. |
