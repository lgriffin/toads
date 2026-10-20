# Absences and the Raid page

Raiders add, change and delete the raid nights they will miss on their **Me** page (`/me`, the Your absences section),
each with a note, and each raid night's officers see the team's upcoming absences in one place: the officers'
**Calendar** (`/officers/calendar`) and the officer desk of the **Raid** page (`/raid`). Old `/calendar` links land on
Me.

## Who sees what

| Who | Raid page | Me, Your absences | Officers, Calendar |
| --- | --- | --- | --- |
| Member with no raid role | "not on a raid team yet" | nothing to report | not shown |
| Trial or raider | their own team's night (both, if on both teams) | add, change and delete their own | not shown |
| Raid-day officer | their night, plus the officer desk with its absences | the same | their night's team absences |
| Global officer, super admin | every night, with a switcher, and the officer desk on each | the same | every night's, with a switcher |

The web app only chooses what to render; the API checks every call (REQ-HUB-ABSENCE-002, -003).

## API

| Route | Permission | What |
| --- | --- | --- |
| `GET /api/me/absences` | `view_guild_raids` | the caller's absences that have not ended, soonest first |
| `POST /api/days/{day}/absences` | `report_absence` on `{day}` | report one: `first_date`, optional `last_date`, and `note` |
| `PUT /api/days/{day}/absences/{id}` | `report_absence` on `{day}` | change the dates or note of one of the caller's own on that team; anyone else's, or one already over, answers 404 |
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
- Every absence carries a note (up to 200 characters, not blank), shown only to that night's officers. A change
  follows the same rules, and an absence never overlaps itself.
- Absences live in hub-db's `member_absences` table (migration 0016). They are a member's own word, so they are not on
  the audit log, and ended ones are kept but no longer listed.

## Launch hold

Raid and Me stay open to every signed-in member during the launch hold (`apps/web/src/lib/launch.ts`): the Raid page
is itself "Coming soon" for each night, and a raider's Me shows only their absences until launch, since absences help
the officers plan before launch too. Me's claim and settings pages stay held.

## Raids & Logs is now Logs

The analysed raids page moved from `/raids` to `/logs`. Old `/raids` and `/raids/{id}` links redirect.
