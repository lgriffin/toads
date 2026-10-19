# Role badges

Role badges are toads members earn from the Discord roles they hold: the Wednesday Toad and the Sunday Toad for the
raid nights, Tank, Healer and Damage, and a toad per class. A super admin ties each badge to one or more roles in the
Toads server; everyone holding the role wears the badge beside their name on the hub, and loses it when the role is
taken away in Discord (at their next role refresh).

Every signed-in member also wears their rank toad without any setup: the member toad for everyone, plus the officer
toad for officers, the super admin toad for super admins (`TOADS_SUPER_ADMIN_IDS`) and the Archtoad for the guild
master.

## Who ties them

Super admins alone (`MANAGE_ROLE_BADGES`, in `rbac.permissions.SUPER_ADMIN_ONLY`). On the site: Admin → Badges from
Discord roles. Pick the role, pick the badge, and press "Give the badge to this role". Remove takes it off the role
again. Every tie and untie is on the audit log (`role_badge.add`, `role_badge.remove`).

The role list comes from Discord with the bot token, leaving out `@everyone` and roles a bot or integration manages.
While Discord is not answering, the badges already tied keep working but new ones cannot be added.

## API

- `GET /api/me/role-badges`: the badges the caller's roles earn, in catalogue order (any signed-in member).
- `GET /api/admin/role-badges`: the catalogue, every tie, and the server's roles (`roles: null` when Discord is down).
- `POST /api/admin/role-badges` `{discord_role_id, badge_id}`: tie one. 409 if the role already earns it, 422 for an
  unknown badge or a role the server does not have, 503 when Discord is down.
- `DELETE /api/admin/role-badges/{discord_role_id}/{badge_id}`: untie it.

Discord role ids are strings in JSON: they exceed JavaScript's safe integers. Roles are never a source of permissions
here: the hub only reads which roles a member holds (`Principal.discord_role_ids`) to pick their badges.

## Adding a badge

1. Draw it. `scripts/toad_art.py` draws the Wednesday, Sunday and super admin toads on the member toad's body
   (`uv run --with fonttools --with brotli python scripts/toad_art.py`); add a `ToadArt` there for a new one.
2. Add it to `services/api/src/toads_api/role_badges/catalog.py` and `apps/web/src/lib/role-badges.ts`.
   `test_role_badges.py` fails until both lists and the artwork agree.

Retiring a badge: remove it from both lists. Stored ties stay but earn nothing.
