# Raid strategy docs

Officers keep raid strategy in Google Drive. The hub pins one Google Doc per classic raid as that raid's authoritative
strategy, and each raid night's Raid page shows the doc for the raid the night is running, so raiders open the right
doc without asking in Discord. The hub only links the docs; it never copies or edits them.

## The raids

MC (Molten Core), BWL (Blackwing Lair), ZG (Zul’Gurub), AQ20 (Ruins of Ahn’Qiraj), AQ40 (Temple of Ahn’Qiraj), Naxx
(Naxxramas), and TBD for a raid not listed yet. The list is `RAIDS` in `services/api/src/toads_api/strategy/service.py`;
the web app reads it from the API (its preview copy is checked against it in `apps/web/src/lib/strategy.test.ts`).

## Pinning a doc

On **Officers > Strategy** (`/officers/strategy`) any officer picks the raid, pastes the doc's link
and, optionally, a name (up to 80 characters; "Naxxramas strategy" when left blank). Only `https://docs.google.com` and
`https://drive.google.com` links are taken (up to 500 characters), so a pinned link always opens a Google Doc, Sheet,
Slides deck or Drive file.

- **One doc per raid.** Pinning a doc makes it the raid's pinned doc at once, on every night running that raid. The doc
  it replaced is listed under it as replaced.
- **History.** A raid keeps its six newest docs: the pinned one and the five it replaced. Older ones drop off.
- **Take down.** Taking down the pinned doc pins the one it replaced again; taking down a replaced doc just removes it.
- Share the doc in Drive with the raiders ("Anyone in the guild's group" or "Anyone with the link"); the hub cannot see
  whether they can open it.

## Each night's raid

A night's officers say which raid their night is running, on the Strategy page or on the night's Raid page (the picker
under Strategy, shown to that night's officers only). "Not decided yet" clears it. The night keeps its raid until an
officer changes it, so set it when the night moves on (BWL to AQ40, say). Global officers and super admins can set any
night's raid.

## The Raid page

Every night's Raid page has a Strategy band: "Wednesday is running Blackwing Lair" and a button that opens the pinned
doc in a new tab, with its name and who pinned it when. Until an officer picks the night's raid, or while the raid has no
doc pinned, it says so.

## Who can do what

| Action | Who | Route |
| --- | --- | --- |
| See every raid's docs and each night's raid | any signed-in member (`view_guild_raids`) | `GET /api/strategy` |
| See a night's raid and doc | any signed-in member | `GET /api/days/{day}/strategy` |
| Pin a doc, take one down | any night's officers (`manage_strategy`, scoped to their night) | `POST /api/days/{day}/strategy/docs`, `DELETE /api/days/{day}/strategy/docs/{id}` |
| Pin a doc, take one down | global officers and super admins (`manage_strategy`, guild-wide) | `POST /api/admin/strategy`, `DELETE /api/admin/strategy/{id}` |
| Pick a night's raid | that night's officers, global officers, super admins (`manage_strategy`, scoped) | `PUT /api/days/{day}/strategy` |

A raid's doc serves every night running it, yet every officer may pin or replace one (Leigh's call, 22 Oct 2026): a
night's officers do it through their own night's path, so their power stays scoped to a raid day in the URL and the
audit log names the night they acted for. A night's raid is that night's alone. Every change is on the audit log:
`strategy.pin` and `strategy.remove` (the raid in `detail`, the officer's night or none for the global tier) and
`strategy.night` (the night and the raid).

## Storage

hub-db tables `strategy_docs` (one row per doc; the newest per raid is pinned) and `night_raids` (one row per raid day
that has picked a raid), migration `0040`.
