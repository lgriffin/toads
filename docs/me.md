# Your raids on Me

Me shows a member their own raids as the WCL Analyzer's character profile shows them, built by the analyzer's
`wcl_app.character_pages` (contract in `guides/character_pages.md` in lgriffin/warcraftlogs_project). Nothing is
re-implemented in the hub: the worker builds the pages from wcl-store and the API stores and serves them.

## What a member sees

- A summary: the character, their class, how many guild raids since their first, and the roles they played.
- One chart per role played: their headline number (healing, damage, or damage taken for a tank) against the raid's
  median for the same role, never against all players (REQ-HUB-ME-002). Under three guild raids the card says the
  history is building instead of drawing trends (REQ-HUB-ME-004).
- Personal bests per role (tanks have none: less damage taken is no record).
- Raid by raid: each raid's number, the role median, how far above or below it they were, and their place in the role.
  Each raid opens its page under Logs.
- Across their raids: the lowest, average and highest of each number (overheal %, mitigation %, casts, consumables,
  and the share of raids with a flask or elixir pair), their most cast spells and their consumables.

A member with more than one character with guild raids switches between them from one dropdown (REQ-HUB-ME-005,
REQ-HUB-ME-006). The characters are the ones "Your performance" picks: their main, then the character they chose to go
by, then their other approved claims, then their server nickname when nobody else claims or shares it. Asking for
anyone else's name shows their own main character; nobody sees another member's page.

## Main character

Me opens on the member's main, and the dropdown labels it "(main)". The main is the first character an officer
approved for them (their oldest approved claim) until an officer approves a swap (`members.main_character_id`,
migration 0031). The name a member chooses to go by in settings does not change it. Unclaiming the main, or an officer
reassigning it, falls back to the oldest approved claim left. "Your performance" and badges follow the main too.

Looking at an approved alt, the member can press **Make <alt> my main**; alts with no guild raids, which the dropdown
cannot show, get the same button under it. The ask (`main_swap_requests`) waits for an officer of the member's raid
nights on the same panels as claims (REQ-HUB-CLAIM-006), and the member can withdraw it while it waits. A new ask
replaces the pending one. A rejection's reason shows on Me until the member asks again or the alt leaves them.

- `GET /api/me/main`: the main, the other approved characters, and the latest ask.
- `POST /api/me/main` `{character_id}`: ask; 422 unless it is one of their approved characters, 409 if it is the
  main already. `#officers` gets a `main_swap_pending` event.
- `DELETE /api/me/main/request`: withdraw the pending ask.
- Officers: `GET /api/days/{day}/main-swaps`, `POST /api/days/{day}/main-swaps/{id}/approve|reject` (reject takes a
  reason), and for the global tier `/api/admin/main-swaps` (members on no night) plus approve/reject on any night's.
  Approving an alt the member no longer holds answers 409.

## How it is built

`toads-worker publish-characters` (and the scheduler, every `TOADS_HUB_REFRESH_MINUTES`):

1. `GET /api/worker/character-pages/wanted` returns every name a member may go by (approved claims and nicknames).
2. The worker builds a page for each name with guild raids, in one storage session that reads each raid once.
3. `PUT /api/worker/character-pages` replaces the stored pages (`analyzer_character_pages`, migration 0028). An older
   build never replaces a newer one, and every chart is checked against the chart contract.

`GET /api/me/character-page` (`?name=` picks another of the member's characters) answers the signed-in member only.

New members name their main, specs and alts on the first sign-in setup first (docs/setup.md).
