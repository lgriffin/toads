# The Toad Bot

The Toad Bot is the guild's one Discord bot for the hub. It runs on the hub's own Discord application (the one members
sign in with), so there is one bot to invite, one token to keep and one place files and information come in. The bank
bot (docs/bank.md) is a separate application only because ToadsBank owns the bank's data.

## What it does

| | How | Who |
| --- | --- | --- |
| Interview rooms | Opens `#interview-<character>` when someone applies on /recruit, and locks it when the application closes | Automatic (docs/recruitment.md) |
| Officer posts | Posts officer announcements marked "also post to Discord" (`TOADS_POST_TO_CHANNELS`) | Automatic |
| Mirrored channels | Offers messages in chosen channels to the hub for officers to curate (`TOADS_MIRROR_CHANNEL_IDS`) | Automatic |
| Raid-Helper sign-ups | `/raidhelper import`: pre-fills members' specs and badges from a Raid-Helper export | That night's officers |

Setup (invite link, permissions, intents, env) is in ADMIN_GUIDE.md, "Getting the Toad Bot onto the server" and
"Toad Bot". `/raidhelper` needs nothing more: slash commands come with the `applications.commands` scope the invite
already has.

## Importing a Raid-Helper sign-up

[Raid-Helper](https://raid-helper.dev) is the bot the guild signs up with. Its composition tool and its events can
export the sign-up as a JSON file, and that file is what the Toad Bot takes.

1. In Raid-Helper, export the night's composition (or the event's sign-ups) and save the file. Its name and extension
   don't matter (`.txt` or `.json`); its content is JSON with a `slots` list (composition tool) or `signUps` list
   (event).
2. In any channel the Toad Bot can see, type `/raidhelper import`, pick the **night** (the list comes from the hub),
   and attach the file as **export**.
3. The bot answers only to you, with what happened: how many members were pre-filled, updated from an earlier import,
   already up to date, or kept because they set their own specs on Me, then who was skipped and why.

Run it again whenever the sign-up changes: a newer import updates what an earlier one set and leaves everything else
alone.

### Who can run it

The night's officers, global officers and super admins. The bot does not decide this: it passes the file to the hub as
the person who ran the command, and the hub reads that person's roles from Discord, exactly as when they sign in to the
site. Anyone else gets "Only that night's officers can import its sign-ups." The same import is open on the API
(`POST /api/days/{day}/comps/raid-helper`) for a signed-in officer.

### What members see

On **Me**, "Your specs" shows the imported class and primary spec with a note that an officer filled them in from the
Raid-Helper sign-up. They can change them or press **Confirm my specs**; either makes the specs their own, and no later
import touches them. Their class badge and Tank, Healer or Damage badge show beside their name from the moment of the
import, including for members who have never signed in. The night's badge (Sunday Toad and so on) still comes only from
their Discord role.

### How a seat is read

| Raid-Helper sends | The hub reads |
| --- | --- |
| `userId` | The member, by Discord user id. The name in the export is ignored, so renames don't matter. |
| `className` "Tank" with a colour | The class by its colour: `#C69B6D` Warrior, `#F48CBA` Paladin, `#FF7C0A` Druid |
| `specName` with a number (`Protection1`, `Holy1`, `Restoration1`) | The same spec name without the number, for the class the colour gives |
| `Beastmastery` | Beast Mastery |
| `isConfirmed` other than "confirmed", or an event status other than primary | Skipped: not confirmed |
| A seat with no `userId` ("Holy (Spot to be filled)") | Skipped: an open seat |
| The same person twice | The first seat counts |
| A class or spec we don't have | Skipped, naming what Raid-Helper sent |
| Someone not in the Discord server | Skipped |

## Where an import lands

```
Discord                 Toad Bot                       Hub API                                   hub-db (Postgres)
/raidhelper import ──▶  reads the file (≤512 KB)  ──▶  POST /api/days/{day}/comps/raid-helper
  night, file           as JSON                        X-Toads-Acting-Member: <your user id>
                                                       │ roles from Discord → build_comps for {day}?
                                                       │ read_export(): seats → (user id, class, spec)
                                                       │ Discord member list: who is in the server
                                                       ├──────────────────────────────────────▶  members        (row per person, created if new)
                                                       ├──────────────────────────────────────▶  member_specs   (class, primary, imported_from)
                                                       └──────────────────────────────────────▶  audit          (one specs.import row)
                         ◀── summary for you ────────── counts + skipped rows
```

The tables, as an import writes them:

- **`members`**, one row per Discord user (`discord_user_id`, unique). Someone the hub has not met gets a row with their
  server name and Discord username and no `signed_in_at`, the same rows the comp builder's roster creates. When they
  sign in later they keep that row, so everything already attached to it stays theirs.
- **`member_specs`**, one row per member (`member_id` is the key): `wow_class` (`paladin`), `primary_spec`
  (`paladin-protection`), `secondary_spec` (kept from an earlier import when it still fits, else null),
  `imported_from` (`raid-helper`; null once the member saves their own) and `updated_at`. Ids are the catalogue's in
  `toads_api.comps.catalog`.
- **`audit`**, one row per import: action `specs.import`, the officer as actor, the night as `raid_day_id`, and
  `raid-helper <n> members` as the target.

Not stored: the file itself, the seat's group and slot numbers, Raid-Helper's names, emote ids, or the comp's layout.
The import keeps only what the hub uses today.

## Building the next import

Every file or command the Toad Bot takes follows the same path, so a new one is four pieces:

1. **A cog** in `services/bot/src/toads_bot/cogs/` with the slash command. It reads the attachment, checks it is
   roughly the right shape and size, and calls the hub through `HubClient`. It decides nothing about permissions and
   never touches the database (an import contract in `pyproject.toml` forbids it).
2. **A hub route** under the night (`/api/days/{day}/...`) with the permission the site uses for the same job. If the
   bot calls it for a member, add the path to `TOAD_BOT_ACTING_PATHS` in `toads_api/rbac/deps.py`; that list is the
   only place the hub service token may act for someone, so keep it to the routes that need it.
3. **A reader and a service method**: a pure function that turns the file into the hub's own ids (like
   `toads_api.comps.raid_helper`), and a service method with the rules (overwrite or not, what to skip).
4. **A table or column** in `packages/hub-db`, with a numbered migration, and an audit row for the import.

If a later feature needs the raw sign-up (who signed up for which raid, benched, late, absent), that is a new table of
sign-ups per raid date rather than more columns on `member_specs`, which holds one current answer per member. The
reader already sees each seat's status, group and slot, so storing them is a change to the service and a migration,
not to the bot.
