# Officers' board

Each raid night has its own Trello-style task board in that night's officer section (`/officers/nights/{day}`), for that night's officers to assign tasks, set
due dates and track the guild's internal work around the raid: rosters to post, consumables to restock, trials to talk
to, strategy docs to update. Each night's board (Wednesday, Thursday, Sunday) is separate; nothing on one shows on another.

## Tonight and the night's links

The night's section opens with a **Tonight** band for the ten minutes before invites: the next raid night's date, who
has said they will miss it (with the spec they play, from the comp builder's roster, and their note), and how many of
each role that leaves the team short. Beside it, **Strategy and roles** holds the night's pinned links. Officers keep
strategy docs and role sheets in Google Drive, so the hub links to them rather than copying them: pin a link with a name
and its https address, and every officer of that night sees it; Unpin takes it off. A night holds up to 12 links, a
name up to 80 characters and an address up to 500. Only https links to a real host are taken. Pinning and unpinning
are on the audit log as `board.link_add` and `board.link_remove`.

## Who sees it

That raid night's officers, global officers and super admins (`MANAGE_OFFICER_BOARD`, scoped to the raid day in the
URL like every `/api/days/{day}/...` officer route). Raiders and the other night's officers never see the board, and the
API refuses them (403; a sibling-day officer's attempt is on the audit log as `rbac.denied`). The Officer console
(`/officers`) links only the nights the viewer runs; global officers and super admins get every night's link and board.
Opening another night's section by its URL shows a refusal and none of its content.

## How it works

- Three lanes, left to right: **To do**, **In progress** and **Done**. New cards go to the bottom of To do.
- A card has a title (up to 200 characters), optional notes (up to 2000), an optional assignee and an optional due date.
  Anyone who has signed in to the hub can be assigned, so an officer can hand a task to a raider (who will not see the
  board, so tell them in Discord).
- A card whose due date has passed (in the guild's timezone, `timezone` in `config/raid_days.yaml`) and that is not in
  Done is marked overdue.
- Move a card by dragging it, with its Start it, Mark done and Back buttons, or with Move up and Move down in its
  editor.
  Click a card's title to edit it or remove it.
- A board holds at most 200 cards; clear Done when it fills up.
- Every change is on the audit log: `board.add`, `board.edit`, `board.move` (the lane in `detail`) and `board.remove`.

## API

- `GET /api/days/{day}/board`: the lanes in order with their cards, and `assignees`, everyone a card can be given to.
- `POST /api/days/{day}/board/cards` `{title, notes?, assignee_member_id?, due_on?, lane?}`: add a card (201).
- `PUT /api/days/{day}/board/cards/{card_id}` `{title, notes, assignee_member_id, due_on}`: rewrite a card.
- `POST /api/days/{day}/board/cards/{card_id}/move` `{lane, position}`: move it; answers the board's lanes as they now
  stand. A position past the lane's end puts the card last.
- `DELETE /api/days/{day}/board/cards/{card_id}`: remove it (204).
- `GET /api/days/{day}/links`: the night's pinned links in the order they were pinned.
- `POST /api/days/{day}/links` `{label, url}`: pin one (201; 422 for an empty name or a link that is not https, 409
  when the night already holds 12).
- `DELETE /api/days/{day}/links/{link_id}`: unpin it (204; 404 for another night's link).

A card id from another night's board answers 404 under this night's path. 422 for an empty or long title, an unknown
lane, or an assignee who has never signed in.

The rules live in `toads_api.officer_board.service` over a repository protocol; cards are in hub-db's
`officer_board_cards` table (migration 0019) and the links in `night_links` (migration 0033). The web component is `apps/web/src/lib/components/OfficerBoard.svelte`
(logic in `$lib/officer-board.ts`; the preview answers from `$lib/preview/board-fake.ts`). The Tonight band is
`NightTonight.svelte` (`$lib/tonight.ts`, `$lib/night-links.ts`; preview `$lib/preview/links-fake.ts`).
