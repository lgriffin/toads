# First sign-in setup

`/setup` gathers what the officers need about a member as soon as they reach the hub (REQ-HUB-ME-007): their main,
their primary and secondary spec, their alts and their professions.

## Who sees it

- Sign-in sends a trial or raider (anyone who may claim characters) to `/setup` instead of the hub home until they
  press **Finish and hop in** (`members.setup_done_at`). A sign-in that asked to return somewhere (`/recruit`) still
  returns there, and members with no raid night role go to the hub as before. `/api/session` says `needs_setup`.
- Everyone meets it once, existing members included: migration 0035 leaves `setup_done_at` empty for all.
- Anyone can rerun it from the account menu (**Your setup**) or the link at the foot of Me.
- It is open to raiders during the launch hold (`OPEN_TO_MEMBERS_EXACT` in `apps/web/src/lib/launch.ts`).

## The welcome

The page opens with Gail, the bank toad, beside a note signed by Gally (_gallagher) and the officers. The wording is `WELCOME` in
`apps/web/src/lib/setup.ts`; officers change it there in a PR. Toads and the Pond, never frogs.

## Characters

- A character the guild's logs know is claimed through the ordinary claim routes, with the usual rules: a name that
  matches the member's Discord nickname is approved at once, anything else waits on the claims panel of their raid
  nights.
- A character the logs have not seen (a new alt, or a main that has not raided with us) is named by name and class
  (`POST /api/me/setup/characters`, table `declared_characters`). Each later visit to setup turns any of those the
  logs now know into a claim, then drops the row. One someone else already holds stays named, for an officer to sort
  out.
- **The first main is the member's to name** (`POST /api/me/setup/main`, or `main: true` on a named character) while
  they hold no approved character but that one. It sets `members.main_character_id`, which Me honours once the claim is
  approved, so an alt approved first by nickname never becomes the main by accident. After that, the main changes only
  by a main swap the officers approve (docs/me.md).
- Specs and professions are the same cards as on Me (`SpecsCard`, `/api/me/specs`; `ProfessionsCard`,
  `/api/me/professions`).

## Routes

| Route | What it does |
| --- | --- |
| `GET /api/me/setup` | done, the main as setup shows it, named characters, whether the first main is still open |
| `POST /api/me/setup/characters` | name a character by name and class: claimed at once if the logs know it |
| `DELETE /api/me/setup/characters/{id}` | drop a named character |
| `POST /api/me/setup/main` | make a character just claimed the first main |
| `POST /api/me/setup/done` | finish setup |

All need `claim_character` and act on the caller's own member id.
