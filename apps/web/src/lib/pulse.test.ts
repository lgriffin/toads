import { describe, expect, it } from 'vitest';
import { sheetTrend } from './mock/sheets';
import { clearTrend, fastestClear, mainZone, minutes, series, totalProgress } from './pulse';
import type { RaidHeadline } from './sheets';

const raid = (date: string, clears: [string, number][], extra: Partial<RaidHeadline> = {}): RaidHeadline => ({
  raid_day: 'wed',
  raid_date: date,
  title: null,
  zone: null,
  report_code: null,
  log_valid: true,
  characters: 25,
  clear_times: clears.map(([zone, seconds]) => ({ zone, seconds })),
  consumables_avg: null,
  low_consumables: [],
  gear_issues: null,
  players_with_gear_issues: null,
  drums: null,
  potions: null,
  interrupts: null,
  deaths: null,
  avoidable_damage: null,
  ...extra
});

describe('clear times', () => {
  const trend = [raid('2026-09-23', [['BT', 6512]]), raid('2026-09-16', [['MH', 4000]]), raid('2026-09-09', [['BT', 7427]])];

  it('lists one zone oldest first and skips raids without it', () => {
    expect(clearTrend(trend, 'BT')).toEqual([
      { date: '2026-09-09', value: 7427 },
      { date: '2026-09-23', value: 6512 }
    ]);
  });

  it("picks the newest timed raid's first zone", () => {
    expect(mainZone(trend)).toBe('BT');
    expect(mainZone([raid('2026-09-30', []), ...trend.slice(1)])).toBe('MH');
    expect(mainZone([])).toBeNull();
  });

  it('finds the fastest clear and the time saved against the oldest', () => {
    expect(fastestClear(trend)).toEqual({
      zone: 'BT',
      seconds: 6512,
      date: '2026-09-23',
      saved: 915,
      since: '2026-09-09'
    });
    expect(fastestClear([raid('2026-09-23', [['BT', 6000]])])?.saved).toBe(0);
    expect(fastestClear([])).toBeNull();
  });

  it('ignores a zero clear time', () => {
    expect(clearTrend([raid('2026-09-23', [['BT', 0]])], 'BT')).toEqual([]);
  });

  it('reads the sample trend', () => {
    expect(fastestClear(sheetTrend)?.zone).toBe('BT');
  });
});

describe('series', () => {
  it('keeps the newest values, oldest first, and skips gaps', () => {
    const trend = [
      raid('2026-09-23', [], { players_with_gear_issues: 2 }),
      raid('2026-09-16', [], { players_with_gear_issues: null }),
      raid('2026-09-09', [], { players_with_gear_issues: 7 }),
      raid('2026-09-02', [], { players_with_gear_issues: 9 })
    ];
    expect(series(trend, (r) => r.players_with_gear_issues, 2)).toEqual([
      { date: '2026-09-09', value: 7 },
      { date: '2026-09-23', value: 2 }
    ]);
  });
});

describe('progress and wording', () => {
  it('totals bosses', () => {
    expect(
      totalProgress([
        { zone: 'Black Temple', killed: 9, total: 9 },
        { zone: 'Mount Hyjal', killed: 4, total: 5 }
      ])
    ).toEqual({ killed: 13, total: 14 });
  });

  it('says minutes plainly', () => {
    expect(minutes(915)).toBe('15 minutes');
    expect(minutes(60)).toBe('1 minute');
    expect(minutes(10)).toBe('under a minute');
  });
});
