import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { badgeIcon, newWork, parseDesk, trayDesk, trayLines, waiting, type Desk } from '../src/desk';

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

describe('trayDesk', () => {
  it("heads the tray's desk lines with the hub's name for the desk", () => {
    expect(trayDesk(desk(2, 0, 1))).toEqual(['Raid leader desk', 'Applications waiting: 2', 'Highlight submissions: 1']);
  });

  it('says a read desk is clear, and shows nothing when there is no desk to read', () => {
    expect(trayDesk(desk())).toEqual(['Raid leader desk', 'Nothing waiting']);
    expect(trayDesk(null)).toEqual([]);
  });
});

describe('badgeIcon', () => {
  it('numbers the overlay up to nine, then 9+', () => {
    expect(badgeIcon(0)).toBeNull();
    expect(badgeIcon(1)).toBe('badge-1.png');
    expect(badgeIcon(9)).toBe('badge-9.png');
    expect(badgeIcon(10)).toBe('badge-9plus.png');
  });

  it('has an icon, and its 2x, for every count it names', () => {
    for (let count = 1; count <= 10; count++) {
      const name = badgeIcon(count) ?? '';
      for (const file of [name, name.replace('.png', '@2x.png')]) {
        expect(existsSync(join(__dirname, '..', 'resources', file)), file).toBe(true);
      }
    }
  });
});
