import { describe, expect, it } from 'vitest';
import { ApiError } from './api';
import { referenceComparison, referenceOverview } from './mock/data';
import {
  comparedRaidLine,
  compactNumber,
  deleteReference,
  deltaTone,
  disconnectReferenceLogin,
  durationLabel,
  formatDelta,
  getComparison,
  getReferenceOverview,
  hasPendingJobs,
  importReference,
  loginLabel,
  loginNotice,
  metricTone,
  pickDay,
  raidLabel,
  raidLength,
  referenceError,
  reportCode,
  requestComparison,
  scopeNote,
  setReferenceLabel,
  startReferenceLogin,
  type StoredRaid
} from './reference';

type Call = { url: string; init: RequestInit };

function fakeFetch(status: number, body?: unknown): { f: typeof fetch; calls: Call[] } {
  const calls: Call[] = [];
  const f = (async (url: string, init: RequestInit) => {
    calls.push({ url, init });
    return new Response(body === undefined ? null : JSON.stringify(body), { status });
  }) as unknown as typeof fetch;
  return { f, calls };
}

const job = { id: 'j1', kind: 'import', status: 'queued', message: '', report: 'x', created_at: '', updated_at: '' };

describe('reference client', () => {
  it('reads the overview for the day in the path', async () => {
    const { f, calls } = fakeFetch(200, referenceOverview);
    expect((await getReferenceOverview('wed', f)).references).toHaveLength(2);
    expect(calls[0].url).toBe('/api/days/wed/reference');
  });
  it('escapes the day and report ids', async () => {
    const { f, calls } = fakeFetch(202, job);
    await deleteReference('we d', 'a/b', f);
    expect(calls[0]).toMatchObject({ url: '/api/days/we%20d/reference/references/a%2Fb', init: { method: 'DELETE' } });
  });
  it('starts and ends the login', async () => {
    const { f, calls } = fakeFetch(200, { authorize_url: 'https://www.warcraftlogs.com/oauth/authorize?x=1' });
    expect((await startReferenceLogin('wed', f)).authorize_url).toContain('warcraftlogs');
    const del = fakeFetch(204);
    await disconnectReferenceLogin('wed', del.f);
    expect([calls[0].url, calls[0].init.method]).toEqual(['/api/days/wed/reference/login', 'POST']);
    expect([del.calls[0].url, del.calls[0].init.method]).toEqual(['/api/days/wed/reference/login', 'DELETE']);
  });
  it('posts imports, comparisons and labels as JSON', async () => {
    const { f, calls } = fakeFetch(202, job);
    await importReference('wed', 'Rf5GkT2pWm8hQz3C', null, f);
    await requestComparison('wed', 'Tq8mZr2VbX4kLp7N', 'Rf5GkT2pWm8hQz3C', f);
    await setReferenceLabel('wed', 'Rf5GkT2pWm8hQz3C', 'EU speed clear', f);
    expect(calls.map((c) => [c.url, c.init.method, JSON.parse(String(c.init.body))])).toEqual([
      ['/api/days/wed/reference/imports', 'POST', { report: 'Rf5GkT2pWm8hQz3C', label: null }],
      [
        '/api/days/wed/reference/comparisons',
        'POST',
        { guild_report: 'Tq8mZr2VbX4kLp7N', reference_report: 'Rf5GkT2pWm8hQz3C' }
      ],
      ['/api/days/wed/reference/references/Rf5GkT2pWm8hQz3C/label', 'PUT', { label: 'EU speed clear' }]
    ]);
  });
  it('reads a built comparison, and null when it is not built', async () => {
    const { f, calls } = fakeFetch(200, referenceComparison);
    expect((await getComparison('wed', 'a', 'b', f))?.comparison.version).toBe(1);
    expect(calls[0].url).toBe('/api/days/wed/reference/comparisons/a/b');
    expect(await getComparison('wed', 'a', 'b', fakeFetch(404, { detail: 'Not built' }).f)).toBeNull();
  });
  it('passes on the API detail', async () => {
    const { f } = fakeFetch(422, { detail: 'That is not a Warcraft Logs report' });
    await expect(importReference('wed', 'nope', null, f)).rejects.toMatchObject({ status: 422 });
    await expect(getComparison('wed', 'a', 'b', fakeFetch(500, {}).f)).rejects.toBeInstanceOf(ApiError);
  });
});

describe('referenceError', () => {
  it('explains refusals', () => {
    expect(referenceError(new ApiError(401, ''))).toMatch(/sign in/);
    expect(referenceError(new ApiError(403, ''))).toMatch(/officers/);
    expect(referenceError(new ApiError(400, 'Report codes are 16 characters'))).toBe('Report codes are 16 characters');
    expect(referenceError(new Error('x'))).toMatch(/try again/);
  });
});

describe('pickDay', () => {
  const officer = { officer_days: ['wed'], raid_days: ['wed', 'sun'], global_officer: false };
  it('uses the requested day when the member is its officer', () => {
    expect(pickDay({ ...officer, officer_days: ['wed', 'sun'] }, 'sun')).toBe('sun');
  });
  it('falls back to the first officer day', () => {
    expect(pickDay(officer, 'sun')).toBe('wed');
    expect(pickDay(officer, null)).toBe('wed');
  });
  it('lets a global officer open any day', () => {
    const global = { officer_days: [], raid_days: ['wed', 'sun'], global_officer: true };
    expect(pickDay(global, 'sun')).toBe('sun');
    expect(pickDay(global)).toBe('wed');
  });
  it('gives a non-officer nothing', () => {
    expect(pickDay({ officer_days: [], raid_days: ['wed'], global_officer: false }, 'wed')).toBeNull();
  });
});

describe('labels', () => {
  const raid: StoredRaid = {
    report_id: 'Rf5GkT2pWm8hQz3C',
    title: "Gruul's Lair",
    raid_date: '2026-09-21 20:00:00',
    zone: 'Karazhan',
    raid_size: 25,
    label: 'EU speed clear',
    owner: null
  };
  it('labels a raid for a picker', () => {
    expect(raidLabel(raid)).toBe("2026-09-21 · Gruul's Lair (Karazhan, 25-man) [EU speed clear]");
    expect(raidLabel({ ...raid, zone: null, raid_size: null, label: null })).toBe("2026-09-21 · Gruul's Lair");
  });
  it('describes the login', () => {
    const base = { configured: true, connected: false, status: null, connected_by: null, connected_at: null };
    expect(loginLabel({ ...base, configured: false })).toMatch(/no Warcraft Logs app/);
    expect(loginLabel(base)).toMatch(/Not connected/);
    expect(loginLabel({ ...base, connected: true, status: 'expired' })).toMatch(/expired/);
    expect(loginLabel({ ...base, connected: true, status: 'working' })).toMatch(/working/);
  });
  it('turns the login redirect into a notice', () => {
    expect(loginNotice('ok')).toMatch(/connected/);
    expect(loginNotice('failed')).toMatch(/did not/);
    expect(loginNotice(null)).toBe('');
    expect(loginNotice('<script>')).toBe('');
  });
  it('describes a compared raid', () => {
    expect(comparedRaidLine(referenceComparison.comparison.guild)).toBe("2026-09-23 · Gruul's Lair · 25-man · 52m");
  });
});

describe('jobs', () => {
  it('knows when the worker is still busy', () => {
    expect(hasPendingJobs([{ status: 'done' }, { status: 'running' }])).toBe(true);
    expect(hasPendingJobs([{ status: 'queued' }])).toBe(true);
    expect(hasPendingJobs([{ status: 'done' }, { status: 'failed' }])).toBe(false);
    expect(hasPendingJobs([])).toBe(false);
  });
});

describe('numbers', () => {
  it('formats deltas', () => {
    expect(formatDelta(12.46)).toBe('+12.5%');
    expect(formatDelta(-3)).toBe('−3.0%');
    expect(formatDelta(0.04)).toBe('0.0%');
    expect(formatDelta(null)).toBe('—');
    expect(formatDelta(Number.NaN)).toBe('—');
  });
  it('colours metrics by the API verdict', () => {
    expect(metricTone({ better: true })).toBe('positive');
    expect(metricTone({ better: false })).toBe('negative');
    expect(metricTone({ better: null })).toBe('neutral');
  });
  it('colours raw differences by direction', () => {
    expect(deltaTone(5)).toBe('positive');
    expect(deltaTone(-5)).toBe('negative');
    expect(deltaTone(5, false)).toBe('negative');
    expect(deltaTone(0.01)).toBe('neutral');
    expect(deltaTone(null)).toBe('neutral');
  });
  it('formats durations', () => {
    expect(durationLabel(214_000)).toBe('3:34');
    expect(durationLabel(59_600)).toBe('1:00');
    expect(durationLabel(null)).toBe('—');
    expect(raidLength(11_760_000)).toBe('3h 16m');
    expect(raidLength(null)).toBe('—');
  });
  it('shortens big totals', () => {
    expect(compactNumber(6_020_000)).toBe('6.0M');
    expect(compactNumber(845_300)).toBe('845.3k');
    expect(compactNumber(950)).toBe('950');
    expect(compactNumber(null)).toBe('—');
  });
});

describe('reportCode', () => {
  it('accepts a code or a report link', () => {
    expect(reportCode(' Rf5GkT2pWm8hQz3C ')).toBe('Rf5GkT2pWm8hQz3C');
    expect(reportCode('https://classic.warcraftlogs.com/reports/Rf5GkT2pWm8hQz3C#fight=3')).toBe('Rf5GkT2pWm8hQz3C');
    expect(reportCode('https://fresh.warcraftlogs.com/reports/Rf5GkT2pWm8hQz3C')).toBe('Rf5GkT2pWm8hQz3C');
  });
  it('rejects anything else', () => {
    expect(reportCode('short')).toBeNull();
    expect(reportCode('https://example.com/reports/Rf5GkT2pWm8hQz3C')).toBeNull();
    expect(reportCode('https://classic.warcraftlogs.com/reports/Rf5GkT2pWm8hQz3CX')).toBeNull();
  });
});

describe('scope note', () => {
  it('names the bosses left out', () => {
    expect(scopeNote(referenceComparison.comparison.scope)).toBe(
      'Consumables and encounters cover only the 2 shared bosses. Not counted: Magtheridon.'
    );
    expect(scopeNote({ scoped: false, shared_encounters: 3, guild_extra_encounters: [] })).toBe('');
  });
});
