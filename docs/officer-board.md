# Officers' board

Each raid night has its own Trello-style task board on the Raid page, for that night's officers to assign tasks, set
due dates and track the guild's internal work around the raid: rosters to post, consumables to restock, trials to talk
to, strategy docs to update. Each night's board (Wednesday, Thursday, Sunday) is separate; nothing on one shows on another.

## Who sees it

That raid night's officers, global officers and super admins (`MANAGE_OFFICER_BOARD`, scoped to the raid day in the
URL like every `/api/days/{day}/...` officer route). Raiders and the other night's officers never see the board, and the
API refuses them (403; a sibling-day officer's attempt is on the audit log as `rbac.denied`). Super admins switch
between the nights on the Raid page and see each night's board.

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

A card id from another night's board answers 404 under this night's path. 422 for an empty or long title, an unknown
lane, or an assignee who has never signed in.

The rules live in `toads_api.officer_board.service` over a repository protocol; cards are in hub-db's
`officer_board_cards` table (migration 0019). The web component is `apps/web/src/lib/components/OfficerBoard.svelte`
(logic in `$lib/officer-board.ts`; the preview answers from `$lib/preview/board-fake.ts`).
