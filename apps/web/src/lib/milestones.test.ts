import { existsSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { MILESTONES } from './milestones';

describe('milestones', () => {
  it('has unique ids', () => {
    const ids = MILESTONES.map((m) => m.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('has the standalone toad and the badge for every milestone', () => {
    for (const m of MILESTONES) {
      expect(existsSync(`static/logos/${m.file}.svg`), m.id).toBe(true);
      expect(existsSync(`static/logos/${m.file}-badge.svg`), m.id).toBe(true);
    }
  });

  it('covers the attendance tiers and both histories', () => {
    const ids = MILESTONES.map((m) => m.id);
    for (const id of ['raids-10', 'raids-20', 'raids-50', 'raids-100', 'raider-of-the-month', 'veteran-fresh', 'veteran-tbc']) {
      expect(ids).toContain(id);
    }
  });
});
