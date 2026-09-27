import { describe, expect, it } from 'vitest';
import { ApiError, raidSummary, raidTrend, recentRaidSheets } from './api';
import { sheetTrend } from './mock/sheets';
import {
  DASH,
  change,
  clearTime,
  clearTimes,
  count,
  gearLabel,
  newestFirst,
  percent,
  points,
  previousRaid,
  reportUrl,
  sheetsError,
  type RaidHeadline
} from './sheets';

type Call = { url: string; init: RequestInit };

function fakeFetch(status: number, body?: unknown): { f: typeof fetch; calls: Call[] } {
  const calls: Call[] = [];
  const f = (async (url: string, init: RequestInit) => {
    calls.push({ url, init });
    return new Response(body === undefined ? null : JSON.stringify(body), { status });
  }) as unknown as typeof fetch;
  return { f, calls };
}

const blank = (raid_day: string, raid_date: string): RaidHeadline => ({
  raid_day,
  raid_date,
  title: null,
  zone: null,
  report_code: null,
  log_valid: null,
  characters: null,
  clear_times: [],
  consumables_avg: null,
  low_consumables: [],
  gear_issues: null,
  players_with_gear_issues: null,
  drums: null,
  potions: null,
  interrupts: null,
  deaths: null,
  avoidable_damage: null
});

describe('clearTime', () => {
  it('formats h:mm:ss', () => {
    expect(clearTime(6512)).toBe('1:48:32');
    expect(clearTime(4120)).toBe('1:08:40');
  });
  it('handles the edges', () => {
    expect(clearTime(0)).toBe('0:00:00');
    expect(clearTime(59)).toBe('0:00:59');
    expect(clearTime(3600)).toBe('1:00:00');
    expect(clearTime(3599)).toBe('0:59:59');
    expect(clearTime(36_000 + 61)).toBe('10:01:01');
    expect(clearTime(59.6)).toBe('0:01:00');
  });
  it('shows a dash for missing or nonsense values', () => {
    expect(clearTime(null)).toBe(DASH);
    expect(clearTime(undefined)).toBe(DASH);
    expect(clearTime(-1)).toBe(DASH);
    expect(clearTime(Number.NaN)).toBe(DASH);
    expect(clearTime(Number.POSITIVE_INFINITY)).toBe(DASH);
  });
});

describe('clearTimes', () => {
  it('joins zones', () => {
    expect(
      clearTimes([
        { zone: 'BT', seconds: 6512 },
        { zone: 'MH', seconds: 4120 }
      ])
    ).toBe('BT 1:48:32 · MH 1:08:40');
  });
  it('shows a dash when there are none', () => {
    expect(clearTimes([])).toBe(DASH);
    expect(clearTimes(null)).toBe(DASH);
  });
});

describe('count and percent', () => {
  it('formats numbers', () => {
    expect(count(2431905)).toBe('2,431,905');
    expect(count(0)).toBe('0');
    expect(count(null)).toBe(DASH);
  });
  it('formats shares', () => {
    expect(percent(0.9372)).toBe('94%');
    expect(percent(0.9372, 1)).toBe('93.7%');
    expect(percent(1)).toBe('100%');
    expect(percent(0)).toBe('0%');
    expect(percent(null)).toBe(DASH);
    expect(percent(undefined)).toBe(DASH);
  });
});

describe('gearLabel', () => {
  it('names the players', () => {
    expect(gearLabel({ gear_issues: 40, players_with_gear_issues: 21 })).toBe('40 across 21 players');
    expect(gearLabel({ gear_issues: 2, players_with_gear_issues: 1 })).toBe('2 across 1 player');
  });
  it('handles zero and nulls', () => {
    expect(gearLabel({ gear_issues: 0, players_with_gear_issues: 0 })).toBe('0');
    expect(gearLabel({ gear_issues: 5, players_with_gear_issues: null })).toBe('5');
    expect(gearLabel({ gear_issues: null, players_with_gear_issues: 3 })).toBe(DASH);
  });
});

describe('reportUrl', () => {
  it('links a well-formed code', () => {
    expect(reportUrl('hOpPy7ToAdFr0g25')).toBe('https://classic.warcraftlogs.com/reports/hOpPy7ToAdFr0g25');
  });
  it('refuses anything else', () => {
    for (const bad of [null, undefined, '', 'short', 'hOpPy7ToAdFr0g25x', 'hOpPy7ToAdFr0g2/', '../../evil/path1', 'javascript:alert1']) {
      expect(reportUrl(bad)).toBeNull();
    }
  });
  it('accepts every mock report code', () => {
    for (const r of sheetTrend) if (r.report_code) expect(reportUrl(r.report_code)).not.toBeNull();
  });
});

describe('change', () => {
  it('reads fewer deaths as better', () => {
    expect(change(157, 169)).toEqual({ delta: -12, label: 'down 12', tone: 'better' });
    expect(change(170, 157)).toEqual({ delta: 13, label: 'up 13', tone: 'worse' });
  });
  it('reads more potions as better when asked', () => {
    expect(change(318, 301, { lowerIsBetter: false })).toEqual({ delta: 17, label: 'up 17', tone: 'better' });
  });
  it('reports no change', () => {
    expect(change(10, 10)?.label).toBe('same');
    expect(change(0.9372, 0.9361, { format: points })?.tone).toBe('same');
  });
  it('formats shares as points', () => {
    const c = change(0.9372, 0.9214, { lowerIsBetter: false, format: points });
    expect(c?.label).toBe('up 2 pts');
    expect(c?.tone).toBe('better');
    expect(points(0.01)).toBe('1 pt');
  });
  it('is null when either side is missing', () => {
    expect(change(null, 3)).toBeNull();
    expect(change(3, null)).toBeNull();
    expect(change(3, undefined)).toBeNull();
  });
});

describe('newestFirst and previousRaid', () => {
  const raids = [blank('wed', '2026-09-09'), blank('sun', '2026-09-20'), blank('wed', '2026-09-23'), blank('wed', '2026-09-16')];
  it('sorts newest first without changing the input', () => {
    expect(newestFirst(raids).map((r) => r.raid_date)).toEqual(['2026-09-23', '2026-09-20', '2026-09-16', '2026-09-09']);
    expect(raids[0].raid_date).toBe('2026-09-09');
  });
  it('compares with the previous raid on the same day', () => {
    expect(previousRaid(raids, raids[2])?.raid_date).toBe('2026-09-16');
    expect(previousRaid(raids, raids[1])).toBeNull();
    expect(previousRaid(raids, raids[0])).toBeNull();
  });
});

describe('sheetsError', () => {
  it('explains each failure', () => {
    expect(sheetsError(new ApiError(401, 'x'))).toMatch(/Sign in/);
    expect(sheetsError(new ApiError(403, 'x'))).toMatch(/role on a raid day/);
    expect(sheetsError(new ApiError(502, 'Bad Gateway'))).toMatch(/unavailable/);
    expect(sheetsError(new ApiError(404, 'No sheets for that raid'))).toBe('No sheets for that raid');
    expect(sheetsError(new TypeError('network'))).toMatch(/could not be loaded/);
  });
});

describe('raid sheet calls', () => {
  it('fetches the trend with optional filters', async () => {
    const { f, calls } = fakeFetch(200, sheetTrend);
    expect(await raidTrend(undefined, undefined, f)).toHaveLength(sheetTrend.length);
    await raidTrend('wed', 4, f);
    expect(calls.map((c) => c.url)).toEqual(['/api/raid-sheets/trend', '/api/raid-sheets/trend?day=wed&limit=4']);
    expect(calls[0].init.credentials).toBe('same-origin');
  });
  it('encodes summary path parts', async () => {
    const { f, calls } = fakeFetch(200, { headline: blank('wed', '2026-09-23'), players: [] });
    const s = await raidSummary('wed', '2026-09-23', f);
    expect(s.players).toEqual([]);
    await raidSummary('a/b', '2026-09-23?x', f);
    expect(calls.map((c) => c.url)).toEqual([
      '/api/days/wed/raids/2026-09-23/sheets/summary',
      '/api/days/a%2Fb/raids/2026-09-23%3Fx/sheets/summary'
    ]);
  });
  it('fetches the recent sheets', async () => {
    const { f, calls } = fakeFetch(200, []);
    await recentRaidSheets('sun', undefined, f);
    expect(calls[0].url).toBe('/api/raid-sheets/recent?day=sun');
  });
  it('raises ApiError for 403', async () => {
    const { f } = fakeFetch(403, { detail: 'Forbidden' });
    await expect(raidTrend(undefined, undefined, f)).rejects.toMatchObject({ status: 403 });
  });
});
