import { describe, expect, it } from 'vitest';
import { newWork, parseDesk, trayLines, waiting, type Desk } from '../src/desk';

const desk = (a = 0, p = 0, h = 0, s = 0): Desk => ({
  applications_waiting: a,
  posts_to_curate: p,
  highlights_to_review: h,
  spotlights_awaiting_consent: s
});

describe('parseDesk', () => {
  it('reads the desk and drops anything else the API adds', () => {
    expect(parseDesk({ ...desk(1, 2, 3, 4), extra: 'x' })).toEqual(desk(1, 2, 3, 4));
  });

  it('refuses what is not a desk', () => {
    expect(parseDesk(null)).toBeNull();
    expect(parseDesk({ detail: 'Not signed in' })).toBeNull();
    expect(parseDesk({ ...desk(), posts_to_curate: -1 })).toBeNull();
    expect(parseDesk({ ...desk(), posts_to_curate: 1.5 })).toBeNull();
    expect(parseDesk({ ...desk(), posts_to_curate: '2' })).toBeNull();
  });
});

it('waiting adds everything up for the badge', () => {
  expect(waiting(desk(1, 2, 3, 4))).toBe(10);
  expect(waiting(null)).toBe(0);
});

it("trayLines words the desk as the hub does, skipping what is empty", () => {
  expect(trayLines(desk(2, 0, 1))).toEqual(['Applications waiting: 2', 'Highlight submissions: 1']);
  expect(trayLines(desk())).toEqual([]);
  expect(trayLines(null)).toEqual([]);
});

describe('newWork', () => {
  it('says what grew', () => {
    expect(newWork(desk(1), desk(2, 1))).toBe('Applications waiting: 2 (1 new)\nDiscord posts to curate: 1 (1 new)');
  });

  it('stays quiet on the first look, when work only shrinks, or when the desk is unreadable', () => {
    expect(newWork(null, desk(5))).toBeNull();
    expect(newWork(desk(3, 2), desk(1, 2))).toBeNull();
    expect(newWork(desk(3), null)).toBeNull();
  });
});
