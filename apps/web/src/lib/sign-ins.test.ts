import { describe, expect, it } from 'vitest';
import { ApiError } from './api';
import { dayLabel, hubSignIns, isoDay, quiet, shiftDay, signInError, sinceLabel } from './sign-ins';

describe('sign-in audit', () => {
  it('asks a night’s route, or the no-night route, for the chosen day', async () => {
    const seen: string[] = [];
    const f = (async (url: string) => {
      seen.push(url);
      return new Response(JSON.stringify({ raid_day: null, date: '2026-11-25', sign_ins: [], members: [], recent: [] }), {
        status: 200,
        headers: { 'content-type': 'application/json' }
      });
    }) as unknown as typeof fetch;
    const hub = hubSignIns(f);
    await hub.day('wed', '2026-11-24');
    await hub.day(null);
    expect(seen).toEqual(['/api/days/wed/sign-ins?on=2026-11-24', '/api/admin/sign-ins']);
  });

  it('steps days across month ends', () => {
    expect(shiftDay('2026-11-30', 1)).toBe('2026-12-01');
    expect(shiftDay('2026-03-01', -1)).toBe('2026-02-28');
    expect(isoDay(new Date(2026, 0, 5))).toBe('2026-01-05');
    expect(dayLabel('2026-11-24')).toMatch(/Tue/);
  });

  it('says how long ago a member last signed in', () => {
    const now = new Date(2026, 10, 25, 20, 0);
    expect(sinceLabel(null, now)).toBe('Never');
    expect(sinceLabel(new Date(2026, 10, 25, 8).toISOString(), now)).toBe('Today');
    expect(sinceLabel(new Date(2026, 10, 24, 23).toISOString(), now)).toBe('Yesterday');
    expect(sinceLabel(new Date(2026, 10, 20).toISOString(), now)).toBe('5 days ago');
    expect(sinceLabel(new Date(2026, 9, 20).toISOString(), now)).toBe('5 weeks ago');
    expect(sinceLabel(new Date(2026, 5, 1).toISOString(), now)).toBe('5 months ago');
  });

  it('marks members who have gone quiet', () => {
    const now = new Date(2026, 10, 25);
    expect(quiet(null, 14, now)).toBe(true);
    expect(quiet(new Date(2026, 10, 1).toISOString(), 14, now)).toBe(true);
    expect(quiet(new Date(2026, 10, 20).toISOString(), 14, now)).toBe(false);
  });

  it('words a refusal for the officer', () => {
    expect(signInError(new ApiError(403, 'Forbidden'))).toMatch(/officers/);
    expect(signInError(new ApiError(422, 'That day has not happened yet'))).toBe('That day has not happened yet');
    expect(signInError(new Error('boom'))).toMatch(/could not be loaded/);
  });
});
