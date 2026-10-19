# Awards

Awards are the toads the guild gives its members: milestones, achievements and titles. The hub stores who holds
what; the artwork lives in `apps/web/static/logos/` (contact sheet at `/logos/` on the site).

| Kind | Examples | Held |
|---|---|---|
| Milestone | 10, 20, 50 and 100 raids; Raider of the Month; Classic Fresh and TBC Veteran | once; Raider of the Month once per month |
| Achievement | Level 60, Sixty Alt, Epic Mount, Scarab Lord, Dragonslayer, Wipe Veteran, … | once |
| Title | Banker, Developer, Discord Admin | once; shown as a toad beside the member's rank toad |

## Who gives them

Global officers and super admins (`manage_awards`). Awards are guild-wide rather than a raid day's, so a raid-day
officer cannot give them; the routes live under `/api/admin/` like every guild-wide officer route. Every award given
or taken back is on the audit log (`award.give`, `award.take_back`).

On the site: Officers → Awards. Pick the member and the award; Raider of the Month asks for the month. A note is
optional and shows with the award.

## API

- `GET /api/me/awards`: the caller's awards, newest first.
- `GET /api/awards`: every award in the guild, newest first (any signed-in member).
- `POST /api/admin/awards` `{member_id, award_id, period?, note?}`: give one. 409 if already held (for that month).
- `DELETE /api/admin/awards/{id}`: take one back.

## Adding an award

1. Draw it: add the toad to the logo generator and regenerate `static/logos/` and `src/lib/milestones.ts`.
2. Add its id to `services/api/src/toads_api/awards/catalog.py`. `test_awards.py` fails until the hub's catalogue and
   the web app's agree.

Retiring an award: remove it from the catalogue. Stored rows stay but are no longer shown.

## The Archtoad and Discord usernames

The Archtoad, the guild master's toad, goes to the Discord account `_gallagher` (`ARCHTOAD_DISCORD_USERNAME` in
`apps/web/src/lib/toads.ts`). It is matched on the Discord username, which the hub stores on every member and refreshes
at each sign-in, never on the server nickname, which members change often. `/api/session` reports both:
`display_name` (nickname or chosen character name) and `discord_username`. Members who signed in before the hub
stored usernames get theirs at their next sign-in.
