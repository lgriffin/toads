import { describe, expect, it } from 'vitest';
import { raids } from './mock/data';
import { progressionFromRaids } from './progression';

describe('progressionFromRaids', () => {
  it('aggregates kills per zone in tier order', () => {
    expect(progressionFromRaids(raids)).toEqual([
      { zone: 'Karazhan', killed: 8, total: 8 },
      { zone: "Gruul's Lair", killed: 2, total: 2 },
      { zone: "Magtheridon's Lair", killed: 1, total: 1 },
      { zone: 'Serpentshrine Cavern', killed: 5, total: 6 },
      { zone: 'Tempest Keep', killed: 3, total: 4 }
    ]);
  });
  it('counts a boss killed in any raid once', () => {
    const [a, b] = raids.filter((r) => r.zone === 'Serpentshrine Cavern');
    const merged = progressionFromRaids([
      { ...a, bosses: [{ name: 'X', killed: true, wipes: 0, seconds: 1 }] },
      { ...b, bosses: [{ name: 'X', killed: false, wipes: 3, seconds: 0 }, { name: 'Y', killed: false, wipes: 1, seconds: 0 }] }
    ]);
    expect(merged).toEqual([{ zone: 'Serpentshrine Cavern', killed: 1, total: 2 }]);
  });
  it('handles no raids', () => expect(progressionFromRaids([])).toEqual([]));
});
