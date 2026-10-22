# Raid strategy docs

Officers keep raid strategy in Google Drive. In the hub they add Google Docs to each classic raid, then each raid night
pins the docs its raiders need, so the night's Raid page links them without anyone asking in Discord. The hub only links
the docs; it never copies or edits them.

## The raids

MC (Molten Core), BWL (Blackwing Lair), ZG (Zul’Gurub), AQ20 (Ruins of Ahn’Qiraj), AQ40 (Temple of Ahn’Qiraj), Naxx
(Naxxramas), and TBD for a raid not listed yet. The list is `RAIDS` in `services/api/src/toads_api/strategy/service.py`;
the web app reads it from the API (its preview copy is checked against it in `apps/web/src/lib/strategy.test.ts`).

## Adding a doc to a raid

On **Officers > Strategy** (`/officers/strategy`) any officer picks the raid, pastes the doc's link and, optionally, a
name (up to 80 characters; "Naxxramas strategy" when left blank), then presses **Add the doc**. Only
`https://docs.google.com` and `https://drive.google.com` links are taken (up to 500 characters), so a link always opens a
Google Doc, Sheet, Slides deck or Drive file. If something is wrong the reason shows under the button.

- A raid holds every doc its officers add, newest first, up to 20; take an old one down to add more.
- An added doc is not shown to raiders until a night pins it. Each doc on the Strategy page says which nights pin it.
- Share the doc in Drive with the raiders ("Anyone in the guild's group" or "Anyone with the link"); the hub cannot see
  whether they can open it.

## Pinning docs for a night's raiders

A night's officers pick the docs their raiders see, from every raid's docs, on the night's **Raid page** (the picker
under Strategy, shown to that night's officers only) or on the Strategy page under "What each night's raiders see". The
picker is a list of tick boxes: tick one doc per raid the night runs (ZG then BWL, say), or more. The Raid page lists
them in the order they were ticked. Unticking every doc clears the night. Global officers and super admins can pin any
night's docs. A night pins up to 10.

## Taking a doc down

Taking a doc down removes it from the raid and from every night that pins it. A night's officers can take down a doc
that no other night pins; a doc another night pins is for that night's officers or the global tier to take down.

## The Raid page

Every night's Raid page has a Strategy band: a button for each doc the night pins ("Open the BWL strategy") that opens it
in a new tab, with its name, its raid and who added it when. Until the night's officers pin a doc, it says so.

## Who can do what

| Action | Who | Route |
| --- | --- | --- |
| See every raid's docs and each night's pins | any signed-in member (`view_guild_raids`) | `GET /api/strategy` |
| See a night's pinned docs | any signed-in member | `GET /api/days/{day}/strategy` |
| Add a doc to a raid, take one down | any night's officers (`manage_strategy`, scoped to their night) | `POST /api/days/{day}/strategy/docs`, `DELETE /api/days/{day}/strategy/docs/{id}` |
| Add a doc to a raid, take any down | global officers and super admins (`manage_strategy`, guild-wide) | `POST /api/admin/strategy`, `DELETE /api/admin/strategy/{id}` |
| Pin a night's docs | that night's officers, global officers, super admins (`manage_strategy`, scoped) | `PUT /api/days/{day}/strategy` |

Every officer may add docs (Leigh's call, 22 Oct 2026): a night's officers do it through their own night's path, so their
power stays scoped to a raid day in the URL and the audit log names the night they acted for. A night's pins are that
night's alone. Every change is on the audit log: `strategy.add` and `strategy.remove` (the night the officer acted
through, or none for the global tier; the raid in `detail`) and `strategy.night` (the night and its pinned doc ids,
comma separated). Saves of one night's pins take turns, so two officers never leave a night with a list neither picked.

## Storage

hub-db tables `strategy_docs` (one row per doc added to a raid; migration `0040`) and `night_strategy_docs` (one row per
doc a raid day pins, with its `position`; migration `0043`, which replaced `night_raid_choices` and kept each night
showing the docs it showed before).
