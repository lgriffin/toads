import { describe, expect, it } from 'vitest';
import { ApiError } from './api';
import { LANES, boardError, dueLabel, hubBoard, moved, neighbourLane, type BoardLane } from './officer-board';
import { previewBoard } from './preview/board-fake';

const card = (id: number, lane: 'todo' | 'doing' | 'done', overdue = false) => ({
  id,
  lane,
  title: `Card ${id}`,
  notes: '',
  assignee_member_id: null,
  assignee_name: null,
  due_on: null,
  overdue,
  updated_at: ''
});

const board = (): BoardLane[] => [
  { id: 'todo', name: 'To do', cards: [card(1, 'todo', true), card(2, 'todo'), card(3, 'todo')] },
  { id: 'doing', name: 'In progress', cards: [card(4, 'doing')] },
  { id: 'done', name: 'Done', cards: [] }
];
const ids = (lanes: BoardLane[]) => lanes.map((l) => l.cards.map((c) => c.id));

describe('officer board', () => {
  it('names the same lanes as the hub', () => {
    expect(LANES.map((l) => l.id)).toEqual(['todo', 'doing', 'done']);
    expect(neighbourLane('todo', -1)).toBeNull();
    expect(neighbourLane('todo', 1)).toBe('doing');
    expect(neighbourLane('done', 1)).toBeNull();
  });

  it('moves a card as the hub will, clamped to the lane', () => {
    expect(ids(moved(board(), 3, 'todo', 0))).toEqual([[3, 1, 2], [4], []]);
    expect(ids(moved(board(), 1, 'doing', 9))).toEqual([[2, 3], [4, 1], []]);
    expect(ids(moved(board(), 99, 'done', 0))).toEqual(ids(board()));
  });

  it('is never overdue once done', () => {
    const done = moved(board(), 1, 'done', 0)[2].cards[0];
    expect(done).toMatchObject({ lane: 'done', overdue: false });
  });

  it('labels due dates, with the year only when it differs', () => {
    const today = new Date(2026, 9, 19);
    expect(dueLabel('2026-10-21', today)).toBe('Due Wed 21 Oct');
    expect(dueLabel('2027-01-04', today)).toBe('Due Mon 4 Jan 2027');
  });

  it('explains refusals', () => {
    expect(boardError(new ApiError(403, 'Forbidden'))).toMatch(/officers/);
    expect(boardError(new ApiError(422, 'A card needs a title'))).toBe('A card needs a title');
    expect(boardError(new Error('x'))).toMatch(/try again/);
  });

  it('calls the raid day’s routes', async () => {
    const calls: [string, RequestInit | undefined][] = [];
    const f = (async (path: string, init?: RequestInit) => {
      calls.push([path, init]);
      return new Response(init?.method === 'DELETE' ? null : '{}', { status: init?.method === 'DELETE' ? 204 : 200 });
    }) as typeof fetch;
    const hub = hubBoard(f);
    await hub.board('wed');
    await hub.add('wed', { title: 'Flasks' });
    await hub.edit('wed', 7, { title: 'Flasks' });
    await hub.move('wed', 7, 'done', 0);
    await hub.remove('wed', 7);
    expect(calls.map(([p, i]) => `${i?.method ?? 'GET'} ${p}`)).toEqual([
      'GET /api/days/wed/board',
      'POST /api/days/wed/board/cards',
      'PUT /api/days/wed/board/cards/7',
      'POST /api/days/wed/board/cards/7/move',
      'DELETE /api/days/wed/board/cards/7'
    ]);
  });

  it('keeps the preview’s boards apart per raid night and to the hub’s rules', async () => {
    const wed = await previewBoard.board('wed');
    const sun = await previewBoard.board('sun');
    expect(wed.lanes.flatMap((l) => l.cards).length).toBeGreaterThan(sun.lanes.flatMap((l) => l.cards).length);
    await expect(previewBoard.add('sun', { title: '  ' })).rejects.toMatchObject({ status: 422 });
    const added = await previewBoard.add('sun', { title: 'Book the tank', due_on: '2000-01-01' });
    expect(added.overdue).toBe(true);
    const lanes = await previewBoard.move('sun', added.id, 'done', 0);
    expect(lanes[2].cards[0]).toMatchObject({ id: added.id, overdue: false });
    await previewBoard.remove('sun', added.id);
    await expect(previewBoard.remove('sun', added.id)).rejects.toMatchObject({ status: 404 });
  });
});
