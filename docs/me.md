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

A member with more than one character with guild raids switches between them (REQ-HUB-ME-005). The characters are the
ones "Your performance" picks: the character they chose, then approved claims, then their server nickname when nobody
else claims or shares it. Asking for anyone else's name shows their own main character; nobody sees another member's
page.

## How it is built

`toads-worker publish-characters` (and the scheduler, every `TOADS_HUB_REFRESH_MINUTES`):

1. `GET /api/worker/character-pages/wanted` returns every name a member may go by (approved claims and nicknames).
2. The worker builds a page for each name with guild raids, in one storage session that reads each raid once.
3. `PUT /api/worker/character-pages` replaces the stored pages (`analyzer_character_pages`, migration 0028). An older
   build never replaces a newer one, and every chart is checked against the chart contract.

`GET /api/me/character-page` (`?name=` picks another of the member's characters) answers the signed-in member only.
