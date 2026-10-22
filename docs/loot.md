# Loot priority

Each raid night's officer section (`/officers/nights/{day}`) has a **Loot priority** list: the big-ticket items that
night's officers decide on ahead of time, and who is first, second and third in line for each. When the first in line
gets the item, an officer marks them received and the next one in line is up for the next drop. Each night's list
(Wednesday, Thursday, Sunday) is separate.

## Who sees it

That raid night's officers, global officers and super admins (`MANAGE_LOOT`, scoped to the raid day in the URL like
every `/api/days/{day}/...` officer route). Raiders and the other nights' officers never see the list, and the API
refuses them (403; a sibling-day officer's attempt is on the audit log as `rbac.denied`). Nothing to set up: a night's
list appears with the night in `config/raid_days.yaml`.

## How it works

- **Find an item** by name ("thunderfury", "head of onyxia"; at least two letters). Matches come best first: the whole
  name, then names that start with what was typed, then the rest, epics and legendaries ahead of lesser items. Each
  result shows its quality, slot, item level and item id, and links to its Wowhead page. **Add** puts it on the list.
- An item is stored by its game **item id** and the **canonical name** it had when it was added, so a later catalogue
  update never renames an item already on a list. An item can be on a night's list once.
- **Add to line** puts one of the night's raid group in line, after whoever is there already. The raid group is the
  night's roster: everyone holding that night's Discord raid role, the same pool as the comp builder. The arrows move
  someone up or down, and ✕ takes them out of line. A line holds up to 10 people.
- **Mark received** when someone has the item. The first one in line who has not received it is shown as **Next up**.
  Undo received puts them back.
- A note on each item (up to 500 characters) holds the officers' reasoning: "bindings first", "tanks before DPS".
- **Take off** removes an item and its line once it is settled. A list holds up to 100 items.
- Someone who leaves the night's raid group keeps their place in any line they were in until an officer takes them
  out; only the night's raid group can be added.
- Every change is on the audit log: `loot.add` (the item's name in `detail`), `loot.note`, `loot.line` (the member
  ids in rank order), `loot.received`, `loot.unreceived` (the member id) and `loot.remove`.

## Item data

The catalogue is [LibItemDB](https://www.curseforge.com/wow/addons/libitemdb) by Pimptasty, an offline WoW item
database addon, used under its MIT licence (`services/api/src/toads_api/loot/data/NOTICE`). It ships data for every WoW
flavour, including WoW Forever (23,596 items from a walk of the Forever beta client) and Classic Era.

The hub takes **Forever first, then Classic**. Forever's beta data lacks much of the raid loot (most of Molten Core,
for one), and the two games share item ids, so Classic fills those gaps while Forever's names win where the two
differ. Test, placeholder and removed items (LibItemDB's `Hidden.lua`) are left out. That gives about 23,800 items,
English names only. Search results from Classic's data say "Classic data".

Links go to `https://www.wowhead.com/classic/item={id}`, since Forever shares Classic's item ids. An item only Forever
has (a few thousand, mostly cosmetics and new recipes) has no Classic Wowhead page.

The data is a gzipped TSV, `services/api/src/toads_api/loot/data/items.tsv.gz` (about 290 KB), read once when the API
first needs it and searched in memory. To refresh it from a newer LibItemDB release:

1. Download the release zip from CurseForge and unzip it; the addon folder is `ItemDB/`.
2. `uv run python scripts/import_items.py path/to/ItemDB` (add `--flavour Forever --flavour Vanilla` to choose the
   flavours and their order, `--locale` for another language).
3. Commit the new `items.tsv.gz` in a PR. Its first line names the LibItemDB version and the item counts.

## API

- `GET /api/days/{day}/loot`: the night's `items` (each with `item_id`, `item_name`, `quality`, `item_level`, `slot`,
  `note` and `recipients` in rank order, each with `rank`, `name`, `received_at` and `next_up`), the `roster` who can be
  put in line, and `catalogue`, the data's source line.
- `GET /api/days/{day}/loot/items?q=&limit=`: search the catalogue (up to 25 results; 422 for fewer than 2 letters).
- `POST /api/days/{day}/loot` `{item_id, note?}`: add an item (201; 422 for an id the catalogue lacks, 409 when the
  item is already on the list or the list is full).
- `PUT /api/days/{day}/loot/{entry_id}` `{note}`: rewrite the note.
- `PUT /api/days/{day}/loot/{entry_id}/line` `{member_ids}`: the whole line, first to last. Members who stay keep their
  received mark; 422 for someone twice, more than 10, or someone outside the night's raid group who was not already in
  line.
- `PUT /api/days/{day}/loot/{entry_id}/line/{member_id}/received` `{received}`: mark or unmark (404 if they are not in
  line).
- `DELETE /api/days/{day}/loot/{entry_id}`: take the item off (204).

An entry id from another night's list answers 404 under this night's path.

The rules live in `toads_api.loot.service` over a repository protocol, the catalogue in `toads_api.loot.catalogue`;
lists are in hub-db's `loot_items` and `loot_recipients` tables (migration 0041). The web component is
`apps/web/src/lib/components/LootPriority.svelte` (logic in `$lib/loot.ts`; the preview answers from
`$lib/preview/loot-fake.ts`).
