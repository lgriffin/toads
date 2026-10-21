# Professions and guild crafters

Members say which professions they have on **Me** under "Your professions", and officers see them and name the
guild's crafters on **Officers › Professions** (`/officers/professions`). A guild crafter is the member we send a
profession's top end recipes to.

## Members' professions

Any signed-in member picks the professions they have, on their main or their alts, each with an optional skill (1 to
375) and, where the profession has them, a specialisation such as Transmutation Master or Spellfire Tailoring
(`GET`/`PUT /api/me/professions`, always the caller's own; a `PUT` replaces the whole list). Primary professions and the
secondary skills (Cooking, First Aid, Fishing) are listed apart; there is no cap on how many a member lists, since they
cover alts too. The list is `toads_api.professions.catalog`, mirrored in `apps/web/src/lib/professions.ts`;
`test_professions.py` keeps the two in step. Ids are stored, so never rename one.

## Guild crafters

The guild's crafters are guild-wide, one list for every night. An officer names a member for one profession, with an
optional note on what to send them ("Flasks and transmutes"), and can take it back.

- A raid night's officers see the professions of everyone on their night (`GET /api/days/{day}/professions`, the same
  roster as the comp builder: everyone whose Discord roles put them on the night) and name or un-name only those members
  (`PUT`/`DELETE /api/days/{day}/crafters/{profession}/{member_id}`).
- Global officers and super admins also see every member who lists a profession (`GET /api/admin/professions`) and
  name anyone (`PUT`/`DELETE /api/admin/crafters/{profession}/{member_id}`).
- Both views carry the full list of the guild's crafters, so every officer sees who to send recipes to.
- A member can only be named for a profession they list on Me. If they drop it, the naming ends with it, and Me tells
  them so.
- The member sees "Guild Alchemy crafter" and the note on their Me.

The permission is `MANAGE_CRAFTERS`, held by officers for their own nights and by the global tier everywhere. Naming
and un-naming are on the audit log (`crafter.name`, `crafter.unname`), and a naming that ends because the member dropped the profession as
`crafter.unlisted`.

## Later

Listing who crafts what to every member, from the bank's loot and recipe data, builds on these two tables
(`member_professions`, `guild_crafters`): the public side reads them, nothing here changes.
