# Sign-in audit

Each time a member signs in to the hub through Discord, the hub records it (table `sign_ins`, migration 0044) with the
raid nights the member's Discord roles put them on at that moment. Officers read it on **Officers > Sign-ins**
(`/officers/sign-ins`): for a day they pick, who signed in and when, a fortnight of daily counts to jump between days,
and when each member of their night last signed in (`members.signed_in_at`), most recent first and "Never" last.

## Who sees what

| Who | Sign-ins page |
| --- | --- |
| Trial, raider, member | not shown; the API refuses (403) |
| Raid-night officer | their own night's members only: a Sunday officer never sees Wednesday's |
| Global officer, super admin | every night's, plus members on no raid night |

A night's day view holds the sign-ins of members who were on that night when they signed in, so moving a member to
another night does not carry their past sign-ins with them. The "Last sign-in" list holds the members on the night
now, including people the hub knows from their Discord roles who have never signed in. The no-night view holds only
members who have signed in at least once.

The web app only chooses what to render; the API checks every call (REQ-HUB-SIGNIN-001, -002, -003).

## API

| Route | Permission | What |
| --- | --- | --- |
| `GET /api/days/{day}/sign-ins?on=YYYY-MM-DD` | `view_sign_ins` on `{day}` | that night's sign-ins on the day, its members' last sign-ins, and the 14 days of counts up to it |
| `GET /api/admin/sign-ins?on=YYYY-MM-DD` | `view_sign_ins` (global tier) | the same for members on no raid night |

`on` defaults to today in the guild's time zone (`raid_days.yaml` `timezone`); a day after today, or more than a year
back, answers 422. Reading the audit is not itself audited. Sign-ins are kept with the member and deleted with them.

## Code

- `packages/hub-db/src/hub_db/sign_ins.py` the `SignIn` table; `toads_api.identity.upsert_member` writes a row on each
  sign-in.
- `services/api/src/toads_api/sign_ins/` the service (rules over a repository protocol), its SQL repository and routes.
- `apps/web/src/lib/sign-ins.ts`, `SignInAudit.svelte` and `routes/officers/sign-ins/`; the preview answers from
  `preview/sign-ins-fake.ts`.
