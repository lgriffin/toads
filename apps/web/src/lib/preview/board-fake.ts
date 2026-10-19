/**
 * The preview's officer boards: sample cards in the browser only, so the Raid page's task board works on GitHub Pages
 * with no hub behind it. Changes last until the page reloads.
 */
import { ApiError } from '$lib/api';
import { LANES, type Board, type BoardBackend, type BoardCard, type BoardLane, type CardIn, type LaneId } from '$lib/officer-board';
import { PREVIEW_MEMBERS } from './awards-fake';

const isoDay = (offset: number) => new Date(Date.now() + offset * 86_400_000).toISOString().slice(0, 10);

type Seed = [string, LaneId, string, number | null, number | null];
const SEEDS: Record<string, Seed[]> = {
  wed: [
    ['Post the Gruul and Magtheridon roster', 'todo', 'Bench order from the absence calendar.', 2, 1],
    ['Restock flasks in the guild bank', 'todo', '', 5, -1],
    ['Message the two trials about their review', 'doing', 'Both had a solid week; set up the chat.', 3, 2],
    ['Update the Kael’thas strategy doc on Drive', 'done', '', 1, null]
  ],
  sun: [['Find a fourth healer for Sunday', 'todo', '', null, 4]]
};

let nextId = 1;
const cards: Record<string, BoardCard[]> = Object.fromEntries(
  Object.entries(SEEDS).map(([day, seeds]) => [
    day,
    seeds.map(([title, lane, notes, assignee, due]) => card(lane, { title, notes, assignee_member_id: assignee, due_on: due === null ? null : isoDay(due) }))
  ])
);

function card(lane: LaneId, body: CardIn, id = nextId++): BoardCard {
  const assignee = body.assignee_member_id ?? null;
  const due = body.due_on ?? null;
  return {
    id,
    lane,
    title: body.title.trim(),
    notes: body.notes?.trim() ?? '',
    assignee_member_id: assignee,
    assignee_name: PREVIEW_MEMBERS.find((m) => m.member_id === assignee)?.display_name ?? null,
    due_on: due,
    overdue: lane !== 'done' && due !== null && due < isoDay(0),
    updated_at: new Date().toISOString()
  };
}

function lanes(day: string): BoardLane[] {
  return LANES.map((l) => ({ ...l, cards: (cards[day] ??= []).filter((c) => c.lane === l.id) }));
}

function find(day: string, id: number): BoardCard {
  const found = (cards[day] ?? []).find((c) => c.id === id);
  if (!found) throw new ApiError(404, 'No such card on this board');
  return found;
}

export const previewBoard: BoardBackend = {
  async board(day): Promise<Board> {
    return { raid_day: day, lanes: lanes(day), assignees: PREVIEW_MEMBERS };
  },
  async add(day, body) {
    if (!body.title.trim()) throw new ApiError(422, 'A card needs a title');
    const c = card(body.lane ?? 'todo', body);
    (cards[day] ??= []).push(c);
    return c;
  },
  async edit(day, id, body) {
    const old = find(day, id);
    const c = card(old.lane, body, id);
    cards[day] = cards[day].map((x) => (x.id === id ? c : x));
    return c;
  },
  async move(day, id, lane, position) {
    const c = find(day, id);
    const rest = cards[day].filter((x) => x.id !== id);
    const inLane = rest.filter((x) => x.lane === lane);
    const at = Math.max(0, Math.min(position, inLane.length));
    const before = inLane[at];
    const updated = card(lane, c, id);
    const index = before ? rest.indexOf(before) : rest.length;
    rest.splice(index, 0, updated);
    cards[day] = rest;
    return lanes(day);
  },
  async remove(day, id) {
    find(day, id);
    cards[day] = cards[day].filter((x) => x.id !== id);
  }
};
