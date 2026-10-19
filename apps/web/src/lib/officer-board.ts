/**
 * The officers' task board (docs/officer-board.md): one Trello-style board per raid night on the Raid page, for that
 * night's officers to assign tasks, set due dates and track the guild's internal work. The hub's routes are under
 * /api/days/{day}/board and only that night's officers (and the global tier) may call them; this page only hides the
 * board from everyone else.
 */
import { ApiError, call, type Fetch } from './api';

export type LaneId = 'todo' | 'doing' | 'done';

/** The board's lanes, left to right, as services/api/src/toads_api/officer_board/service.py lists them. */
export const LANES: readonly { id: LaneId; name: string }[] = [
  { id: 'todo', name: 'To do' },
  { id: 'doing', name: 'In progress' },
  { id: 'done', name: 'Done' }
];

export const TITLE_LIMIT = 200;
export const NOTES_LIMIT = 2000;

export interface BoardCard {
  id: number;
  lane: LaneId;
  title: string;
  notes: string;
  assignee_member_id: number | null;
  assignee_name: string | null;
  /** "YYYY-MM-DD", or null with no due date. */
  due_on: string | null;
  /** Due before today (in the guild's timezone) and not yet done. */
  overdue: boolean;
  updated_at: string;
}

export interface BoardLane {
  id: LaneId;
  name: string;
  cards: BoardCard[];
}

export interface Assignee {
  member_id: number;
  display_name: string;
}

export interface Board {
  raid_day: string;
  lanes: BoardLane[];
  assignees: Assignee[];
}

export interface CardIn {
  title: string;
  notes?: string;
  assignee_member_id?: number | null;
  due_on?: string | null;
}

/** What the board component talks to: the hub, or the preview's in-browser fake. */
export interface BoardBackend {
  board(day: string): Promise<Board>;
  add(day: string, card: CardIn & { lane?: LaneId }): Promise<BoardCard>;
  edit(day: string, id: number, card: CardIn): Promise<BoardCard>;
  move(day: string, id: number, lane: LaneId, position: number): Promise<BoardLane[]>;
  remove(day: string, id: number): Promise<void>;
}

const base = (day: string) => `/api/days/${encodeURIComponent(day)}/board`;

export function hubBoard(f: Fetch = fetch): BoardBackend {
  return {
    board: (day) => call<Board>(f, base(day)),
    add: (day, card) => call<BoardCard>(f, `${base(day)}/cards`, { method: 'POST', body: JSON.stringify(card) }),
    edit: (day, id, card) =>
      call<BoardCard>(f, `${base(day)}/cards/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify(card) }),
    move: (day, id, lane, position) =>
      call<BoardLane[]>(f, `${base(day)}/cards/${encodeURIComponent(id)}/move`, {
        method: 'POST',
        body: JSON.stringify({ lane, position })
      }),
    remove: (day, id) => call<void>(f, `${base(day)}/cards/${encodeURIComponent(id)}`, { method: 'DELETE' })
  };
}

/** The lane to the left (-1) or right (+1) of `lane`, or null at the board's edge. */
export function neighbourLane(lane: LaneId, step: -1 | 1): LaneId | null {
  const i = LANES.findIndex((l) => l.id === lane) + step;
  return i >= 0 && i < LANES.length ? LANES[i].id : null;
}

/**
 * The board after moving card `id` to `position` in `lane`, as the hub will arrange it, so a drag or a move button
 * shows at once; the hub's answer replaces it.
 */
export function moved(lanes: BoardLane[], id: number, lane: LaneId, position: number): BoardLane[] {
  const card = lanes.flatMap((l) => l.cards).find((c) => c.id === id);
  if (!card) return lanes;
  const without = lanes.map((l) => ({ ...l, cards: l.cards.filter((c) => c.id !== id) }));
  return without.map((l) => {
    if (l.id !== lane) return l;
    const cards = [...l.cards];
    cards.splice(Math.max(0, Math.min(position, cards.length)), 0, { ...card, lane, overdue: lane === 'done' ? false : card.overdue });
    return { ...l, cards };
  });
}

/** "Due Wed 21 Oct", for a card's footer; the year only when it is not this year. */
export function dueLabel(due: string, today: Date = new Date()): string {
  const [y, m, d] = due.split('-').map(Number);
  const when = new Date(Date.UTC(y, m - 1, d));
  const opts: Intl.DateTimeFormatOptions = { weekday: 'short', day: 'numeric', month: 'short', timeZone: 'UTC' };
  if (y !== today.getFullYear()) opts.year = 'numeric';
  return `Due ${when.toLocaleDateString('en-GB', opts).replace(',', '')}`;
}

/** What to tell an officer when a board call fails. */
export function boardError(e: unknown): string {
  if (!(e instanceof ApiError)) return 'Something went wrong; try again.';
  switch (e.status) {
    case 401:
      return 'Sign in again to use the board.';
    case 403:
      return 'Only this raid night’s officers can use its board.';
    case 404:
      return 'That card is gone; someone may have removed it. The board has been refreshed.';
    default:
      return e.message || 'Something went wrong; try again.';
  }
}
