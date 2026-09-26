import { describe, expect, it } from 'vitest';
import { ageDays, ageLabel, mmss } from './format';
import { MOCK_NOW, raids } from './mock/data';
import { ALL, filterRaids } from './raids';

const any = { zone: ALL, raidDay: ALL, size: ALL, lookbackDays: 365 };

describe('filterRaids', () => {
  it('keeps everything with no filters', () => {
    expect(filterRaids(raids, any, MOCK_NOW)).toHaveLength(raids.length);
  });
  it('filters by zone, day and size together', () => {
    const got = filterRaids(raids, { ...any, zone: 'Serpentshrine Cavern', raidDay: 'Wednesday', size: '25' }, MOCK_NOW);
    expect(got.map((r) => r.id)).toEqual(['ssc-0924', 'ssc-0917']);
  });
  it('drops raids older than the lookback', () => {
    expect(filterRaids(raids, { ...any, size: '10' }, MOCK_NOW)).toHaveLength(1);
    expect(filterRaids(raids, { ...any, lookbackDays: 7 }, MOCK_NOW).every((r) => r.date >= '2026-09-19')).toBe(true);
  });
});

describe('format', () => {
  it('labels snapshot age', () => {
    expect(ageDays('2026-09-15T18:00:00Z', MOCK_NOW)).toBe(11);
    expect(ageLabel('2026-09-26T10:00:00Z', MOCK_NOW)).toBe('today');
    expect(ageLabel('2026-09-25T10:00:00Z', MOCK_NOW)).toBe('1 day ago');
  });
  it('formats fight length', () => {
    expect(mmss(312)).toBe('5:12');
    expect(mmss(60)).toBe('1:00');
  });
});
