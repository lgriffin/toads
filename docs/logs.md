# Logs

`/logs` is the hub's version of the desktop app's raid browser and raid view: every guild raid the sync has analysed,
the desktop app's analysis for each one, and a boss history. Officers use it to compare nights, for example Wednesday
against Thursday.

## Where the data comes from

The worker's `publish-logs` job (every `TOADS_HUB_REFRESH_MINUTES`, or `toads-worker publish-logs`) builds the pages
with the analyzer's `RaidPageService` from the raids wcl-store holds, so it never calls Warcraft Logs. The payloads are
the analyzer's contract, `guides/raid_pages.md` in lgriffin/warcraftlogs_project, version 1.

1. `PUT /api/worker/logs` sends the raid list, the boss history and a sha256 of each raid's analysis (`hashes`). The
   API keeps exactly those raids (a raid gone from the analyzer leaves with its analysis) and answers with the raids
   whose analysis it does not hold in that build yet (none held, or a rebuilt one after an analyzer fix or a
   re-imported report), newest first, at most 100 a turn so a first run fills in over a few turns. A raid the worker
   could not read back is listed without a hash and keeps the analysis the hub holds. An older list never replaces a
   newer one (409); the check and the replacement are one transaction.
2. `PUT /api/worker/logs/{report}` sends one raid's analysis with its hash. A hash other than the one the latest list
   named is a late upload from an older run, refused with 409; the worker skips it and carries on.

Both need the worker's service token. The hub-db tables are `log_raids` and `log_index` (migrations 0018 and 0020).

## Who sees what

Every signed-in member reads the list, each raid's makeup by role, each boss's kill time and raid totals, and the boss
history's kills and times. Each raider's own numbers are per-raid detail (REQ-HUB-PRIV-001), so only officers see them
(REQ-HUB-RAID-004):

| Who | Raids in full | Boss history per raider |
| --- | --- | --- |
| Global officers and super admins | every raid (`GET /api/logs/{report}`) | every weekday |
| A raid day's officers | raids held on that day's weekday (`GET /api/days/{day}/logs/{report}`) | that weekday |
| Everyone else | none: the overview | none |

A raid day's weekday comes from `weekdays` in `raid_sheets.yaml`, else the weekday in the day's `name` in
`raid_days.yaml`. A raid on another weekday (an alt run on a Thursday, say) is in full for global officers only.
`GET /api/logs` tells the page, per raid, whether the caller sees it in full and under which raid day to read it.

## Each night at a glance

The analyzer's raid widgets (guild at a glance, last raid, recent raids, raid activity, weekly healing, healers week on
week, top damage and healing, attendance, boss kills, class mix, interrupts, consumables, flasks, and the roster's
badges for officers) used to sit only on the hub home, with every raid night mixed together. Logs now shows them per
night (REQ-HUB-RAID-005):

1. The worker's `publish-home` job puts the guild-wide page (`PUT /api/worker/home-page`) as before. The API's answer
   names each raid day's weekday (`nights`, the same weekdays the list uses, above).
2. For each night the job builds the same widgets from that night's raids only (wcl-store's
   `RaidScope(weekdays=...)`) and puts them to `PUT /api/worker/home-page/nights/{day}`. The hub-db table is
   `night_home_pages` (migration 0026). A night that fails does not stop the others; the job reports it after.
3. `GET /api/home/nights` lists the nights with a page and each one's weekday, which the page's tabs and weekday
   chips follow (a raid day whose weekday the API cannot tell has no tab). `GET /api/home/nights/{day}` serves a
   night's page to any signed-in member, with the same rule as the hub home:
   the roster's badges are for officers only.

Logs opens on the night of the viewer's Toad badge (the night their Discord role ties them to on /admin). Super
admins, global officers, members of several nights and members of none open on every raid, which shows the guild-wide
page. Picking a night also sets the weekday chips below to that night's weekday.

## The page

- Night tabs (each raid night, or every raid) pick the widgets above the list and start the weekday chips.
- Weekday chips (Mon to Sun, each with its raid count) pick any mix of days; none picked shows every day. A zone
  picker and a title search narrow it further, as the desktop raid list's day checkboxes and search do
  (REQ-HUB-RAID-002).
- Boss history sums the picked weekdays: kills, average kill time, raid DPS and HPS, and for officers each raider's
  damage and healing per kill.
- A raid opens on its encounters. In full it has the desktop raid view's tabs: Composition, Healers, Tanks, Melee,
  Ranged, Consumables, Boss vs trash, Interrupts, Cast efficiency, Debuff and Totem uptime, Engineering
  (REQ-HUB-RAID-001). Tabs with nothing logged are left out.

The desktop app's deep dive (cast timelines, wasted resources, cooldown synergy) calls Warcraft Logs live, so it is
not on the hub.

Under the launch hold `/logs` is officers' only, like the other analyzer pages.
