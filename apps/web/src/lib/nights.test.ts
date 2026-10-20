import { describe, expect, it } from 'vitest';
import { NIGHT_IDS, NIGHT_NAMES, NIGHTS_IN_WORDS, NIGHTS_OR, RAID_NIGHTS, TEAM_COUNT, inWords, raidNight } from './nights';
import { ROLE_BADGES } from './role-badges';

describe('raid nights', () => {
  it('runs three teams, Wednesday, Thursday and Sunday, in week order', () => {
    expect(NIGHT_IDS).toEqual(['wed', 'thu', 'sun']);
    expect(NIGHT_NAMES.thu).toBe('Thursday');
    expect(NIGHTS_IN_WORDS).toBe('Wednesday, Thursday and Sunday');
    expect(NIGHTS_OR).toBe('Wednesday, Thursday or Sunday');
    expect(TEAM_COUNT).toBe('three');
  });
  it('finds a night by id or name', () => {
    expect(raidNight('thu')?.name).toBe('Thursday');
    expect(raidNight(' Thursday ')?.id).toBe('thu');
    expect(raidNight('fri')).toBeUndefined();
    expect(raidNight('')).toBeUndefined();
  });
  it('gives every night a role badge with its toad', () => {
    for (const n of RAID_NIGHTS) expect(ROLE_BADGES.find((b) => b.file === n.toad)?.name).toBe(`${n.name} Toad`);
  });
  it('lists in words', () => {
    expect(inWords([])).toBe('');
    expect(inWords(['a'])).toBe('a');
    expect(inWords(['a', 'b'])).toBe('a and b');
    expect(inWords(['a', 'b', 'c'])).toBe('a, b and c');
  });
});
