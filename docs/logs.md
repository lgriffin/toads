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

## The page

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
