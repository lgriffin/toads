# Raid comps

Officers plan each raid night's composition on **Officers › Comp builder** (`/officers/comp`), and members say what
they play on **Me** under "Your specs".

## Members' specs

Every signed-in member sets the class they raid as, a primary spec, and optionally a secondary spec of the same class
(`GET`/`PUT`/`DELETE /api/me/specs`, any signed-in member, always their own). Druids pick Feral (cat) or Guardian
(bear) as separate specs, because they take different seats. The class and spec list is
`toads_api.comps.catalog`, mirrored in `apps/web/src/lib/comp.ts`; `test_comps.py` keeps the two in step. Spec ids
are stored, so never rename one.

## The builder

- **Any comp** (the default) seats bare specs with no names, so any composition can be tried. The panel beside the
  groups lists every raid buff, party buff and debuff, who brings it and, when nobody does, which class or spec would.
  Party buffs show the groups they reach.
- **Roster** switches the palette to the raid night's members, by the name they chose on the hub, with their specs.
  Filter by class, spec or role: a spec filter matches a primary or a secondary, and a member dropped in while it is
  set takes that spec. A seated member's ⇄ button swaps them to their other spec. Members without specs are listed
  under "without specs yet" so officers can nudge them.
- Drag a spec or member onto a seat, drag seats onto each other to swap them, or drag a seat back to the palette to
  remove it. On touch screens, tap the spec or member, then the seat. Raids seat 10, 20 or 40 in groups of five.
- A comp can seat anyone in the hub, so a fill-in from the other night can be locked in, but a named member only in a
  spec of the class they set. Switching raid night keeps the comp on the board as an unsaved draft.
- **Lock in** saves the comp under a name for that raid night; officers of the night can open, replace or delete it.
  Saving and deleting are on the audit log (`comp.save`, `comp.delete`).

The buff data is World of Warcraft: Forever's, from the beta client (October 2026), where most class buffs reach the
whole raid. Update `BUFFS` in `comp.ts` as Blizzard confirms changes.

## Who is on a night's roster

A member is on a raid night's roster when their Discord roles put them on that night: the night's trial, raider or
officer roles in `config/raid_days.yaml`, or a role a super admin tied to the night's Toad badge on /admin
(docs/role-badges.md). Nobody has to sign in to the hub first. When an officer opens the roster, the API lists the
Discord server's members with the Toad Bot's token (`GET /guilds/{id}/members`, which needs the Server Members intent
the bot already has) and records each holder's nights on their member row (`members.raid_days`), creating the row for
someone the hub has not met yet. It reads the server at most once per `role_refresh_seconds` across the hub; if Discord
does not answer, the roster stays as last read and the next request tries again. Sign-ins and role refreshes keep a
member's nights current in between. None of this is a source of permissions.

People who have never signed in (`members.signed_in_at` is null, migration 0023) come back with `signed_in: false` and
are listed under "without specs yet" marked **Not signed in**, since only a signed-in member can set specs. Officers
can still seat them in a spec; signing in later keeps the same member, so the seat stays theirs. Losing a night's
roles or leaving the server takes someone off at the next read.

## Importing from Raid-Helper

Raid-Helper (https://raid-helper.dev) is the Discord bot the guild signs up with. Its composition tool and its events
both export JSON, and a night's officers can hand that export to the hub to pre-fill the specs of everyone it seats, so
members already have their class, spec and badges before they first sign in.

- **In Discord**: `/raidhelper import night:<night> export:<file>` on the Toad Bot. The bot only carries the file
  (up to 512 KB); it calls the hub as the officer who ran the command (`X-Toads-Acting-Member` with the hub service
  token, allowed on this one route only), and the hub reads that officer's roles from Discord. The reply, only seen by
  the officer, counts what happened and lists who was skipped and why.
- **API**: `POST /api/days/{day}/comps/raid-helper` with the export as the body, for that night's officers.

The officers' walkthrough and the tables an import writes are in [toad-bot.md](toad-bot.md).

What the import does (`toads_api.comps.raid_helper`, `CompService.import_specs`):

- Members are matched by the Discord user id in each seat; the names in the export do not matter. Someone not in the
  Discord server is skipped. Someone the hub has not met gets a member row, as the roster does, without a sign-in.
- Raid-Helper's "Tank" pseudo-class and its numbered spec names (`Protection1`, `Holy1`, `Restoration1`) are read by
  the class colour it sends with each seat, so a pink `Protection1` tank is a Protection Paladin. Unconfirmed seats,
  open seats, a second seat for the same person, and anything that is not one of our specs are skipped.
- The seat becomes the member's primary spec, marked as imported (`member_specs.imported_from`, migration 0027). A
  newer import updates imported specs; specs a member set themselves are never touched.
- On Me, imported specs say an officer filled them in from the sign-up. The member can change them or confirm them as
  they are; either makes them their own.
- One `specs.import` entry on the audit log per import. Night membership and the night's badge stay with Discord roles.

## Badges from specs

A member's primary spec earns its class badge and the Tank, Healer or Damage badge (`GET /api/me/role-badges`,
`toads_api.comps.catalog.badges_of_spec`), whether they set it or it was imported. These add to the badges Discord roles
earn (docs/role-badges.md).

## Permissions

`build_comps`, held by officers for their own raid night and by global officers for every night
(`/api/days/{day}/comps*`, the Raid-Helper import included). Requirements: `tests/features/hub_comp.feature`.
