# Absences and the Raid page

Raiders tell their officers which raid nights they will miss on the **Calendar** (`/calendar`), and each raid night's
officers see the team's upcoming absences in one place: on the Calendar and on the officer desk of the **Raid** page
(`/raid`).

## Who sees what

| Who | Raid page | Calendar |
| --- | --- | --- |
| Member with no raid role | "not on a raid team yet" | the same, nothing to report |
| Trial or raider | their own team's night (both, if they are on both teams) | report and cancel their own absences |
| Raid-day officer | their night, plus the officer desk with its absences | their own absences, plus their night's team absences |
| Global officer, super admin | every night, with a switcher, and the officer desk on each | every night's team absences, with a switcher |

The web app only chooses what to render; the API checks every call (REQ-HUB-ABSENCE-002, -003).

## API

| Route | Permission | What |
| --- | --- | --- |
| `GET /api/me/absences` | `view_guild_raids` | the caller's absences that have not ended, soonest first |
| `POST /api/days/{day}/absences` | `report_absence` on `{day}` | report one: `first_date`, optional `last_date` and `note` |
| `DELETE /api/me/absences/{id}` | `report_absence` | cancel one of the caller's own; anyone else's answers 404 |
| `GET /api/days/{day}/absences` | `view_absences` on `{day}` | the next 8 nights with who is away, and every upcoming absence |

`report_absence` is held by trials and up on their own raid day, so a member reports only for a team they are on.
`view_absences` is an officer permission, scoped to the raid day in the path like every officer power.
`/api/session` also returns `day_names`, every configured raid day's name, for the Raid page's switcher.

## Rules

- An absence covers a run of dates on one team, both ends included. Its nights are the dates in the run that fall on
  the raid day's weekday, read from the day's `name` in `config/raid_days.yaml` (or `weekdays` in
  `raid_sheets.yaml`). A day whose name names no weekday still takes absences; it just lists no nights.
- It must start today or later, end on or after it starts, span under 92 days, start within a year, and hold at least
  one raid night. A member may hold at most 20 upcoming absences per team, none overlapping on the same team.
- The note (up to 200 characters) is shown only to that night's officers.
- Absences live in hub-db's `member_absences` table (migration 0016). They are a member's own word, so they are not on
  the audit log, and ended ones are kept but no longer listed.

## Launch hold

Raid and Calendar stay open to every signed-in member during the launch hold (`apps/web/src/lib/launch.ts`): the Raid
page is itself "Coming soon" for each night, and absences help the officers plan before launch too.

## Raids & Logs is now Logs

The analysed raids page moved from `/raids` to `/logs`. Old `/raids` and `/raids/{id}` links redirect.
