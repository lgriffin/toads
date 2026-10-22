# Raid strategy docs

Officers keep raid strategy in Google Drive. The hub pins Google Docs to the classic raids, for every night or for one
raid night, and each night's Raid page shows the doc for every raid the night is running, so raiders open the right doc
without asking in Discord. The hub only links the docs; it never copies or edits them.

## The raids

MC (Molten Core), BWL (Blackwing Lair), ZG (Zul’Gurub), AQ20 (Ruins of Ahn’Qiraj), AQ40 (Temple of Ahn’Qiraj), Naxx
(Naxxramas), and TBD for a raid not listed yet. The list is `RAIDS` in `services/api/src/toads_api/strategy/service.py`;
the web app reads it from the API (its preview copy is checked against it in `apps/web/src/lib/strategy.test.ts`).

## Pinning a doc

On **Officers > Strategy** (`/officers/strategy`) any officer picks the raid, who it is for ("Every night" or one of the
nights they run; global officers and super admins see every night), pastes the doc's link and, optionally, a name (up to
80 characters; "Naxxramas strategy" when left blank). Only `https://docs.google.com` and `https://drive.google.com`
links are taken (up to 500 characters), so a pinned link always opens a Google Doc, Sheet, Slides deck or Drive file.

- **One doc per raid, per place.** A raid has one pinned doc for every night, and each night may pin its own for the
  raid too (Sunday runs a faster MC, say). Pinning a doc makes it the pinned doc for that raid in that place at once;
  the doc it replaced is listed under it as replaced.
- **A night's own doc wins.** A night running the raid shows its own doc if it pinned one, else the every-night doc.
- **Pinning for a night adds the raid to it.** A doc pinned for Wednesday adds its raid to the raids Wednesday is
  running, if it was not there already, so the Raid page shows it straight away.
- **History.** Each raid keeps its six newest docs in each place: the pinned one and the five it replaced.
- **Take down.** Taking down a pinned doc pins the one it replaced in the same place again; taking down a replaced doc
  just removes it. A night's officers take down that night's docs and the every-night ones, never another night's.
- Share the doc in Drive with the raiders ("Anyone in the guild's group" or "Anyone with the link"); the hub cannot see
  whether they can open it.

## Each night's raids

A night's officers tick the raids their night is running, on the Strategy page or on the night's Raid page (the picker
under Strategy, shown to that night's officers only). A night can run more than one raid (ZG then BWL, say): the Raid
page lists them in the order they were ticked. Unticking every raid clears the night. The night keeps its raids until an
officer changes them, so update them when the night moves on. Global officers and super admins can set any night's
raids.

## The Raid page

Every night's Raid page has a Strategy band: "Wednesday is running Zul'Gurub then Blackwing Lair" and, for each raid, a
button that opens its doc in a new tab, with its name and who pinned it when. Until an officer picks the night's raids,
or while a raid has no doc pinned, it says so.

## Who can do what

| Action | Who | Route |
| --- | --- | --- |
| See every raid's docs and each night's raids | any signed-in member (`view_guild_raids`) | `GET /api/strategy` |
| See a night's raids and their docs | any signed-in member | `GET /api/days/{day}/strategy` |
| Pin a doc for their night or every night, take one down | any night's officers (`manage_strategy`, scoped to their night) | `POST /api/days/{day}/strategy/docs`, `DELETE /api/days/{day}/strategy/docs/{id}` |
| Pin a doc for any night or every night, take one down | global officers and super admins (`manage_strategy`, guild-wide) | `POST /api/admin/strategy`, `DELETE /api/admin/strategy/{id}` |
| Pick a night's raids | that night's officers, global officers, super admins (`manage_strategy`, scoped) | `PUT /api/days/{day}/strategy` |

An every-night doc serves every night running the raid, yet every officer may pin or replace one (Leigh's call, 22 Oct
2026): a night's officers do it through their own night's path, so their power stays scoped to a raid day in the URL and
the audit log names the night they acted for. A night's own docs and raids are that night's alone. Every change is on the
audit log: `strategy.pin` and `strategy.remove` (the night the officer acted through, or none for the global tier;
`detail` names the raid and the night the doc is for, such as "mc for every night") and `strategy.night` (the night and
its raids, comma separated). Pinning a doc for a night adds its raid to that night in the same write, and saves of one
night's raids take turns, so two officers never leave a night running a list neither picked.

## Storage

hub-db tables `strategy_docs` (one row per doc, with `raid_day_id` null for every night; the newest per raid and place
is pinned; migration `0040`, `raid_day_id` from `0042`) and `night_raid_choices` (one row per raid a raid day is
running, with its `position`; migration `0042`, which replaced `night_raids`).
