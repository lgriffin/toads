import { describe, expect, it } from 'vitest';
import { ApiError, claimError, createClaim, getSession, listClaims, listMembers, statusLabel, unclaim } from './api';

type Call = { url: string; init: RequestInit };

function fakeFetch(status: number, body?: unknown): { f: typeof fetch; calls: Call[] } {
  const calls: Call[] = [];
  const f = (async (url: string, init: RequestInit) => {
    calls.push({ url, init });
    return new Response(body === undefined ? null : JSON.stringify(body), { status });
  }) as unknown as typeof fetch;
  return { f, calls };
}

describe('getSession', () => {
  it('returns the member', async () => {
    const { f } = fakeFetch(200, {
      member_id: 1,
      display_name: 'Hopscotch',
      global_officer: false,
      day_roles: {},
      raid_days: [],
      officer_days: []
    });
    expect((await getSession(f))?.display_name).toBe('Hopscotch');
  });
  it('returns null when signed out', async () => {
    expect(await getSession(fakeFetch(401, { detail: 'Not signed in' }).f)).toBeNull();
  });
  it('throws on other errors', async () => {
    await expect(getSession(fakeFetch(503, { detail: 'Discord is unavailable' }).f)).rejects.toThrow('Discord');
  });
});

describe('claims', () => {
  it('posts the character id only', async () => {
    const { f, calls } = fakeFetch(201, { id: 3, status: 'pending' });
    await createClaim(42, f);
    expect(calls[0].url).toBe('/api/claims');
    expect(calls[0].init.method).toBe('POST');
    expect(JSON.parse(String(calls[0].init.body))).toEqual({ character_id: 42 });
  });
  it('lists members', async () => {
    const { f, calls } = fakeFetch(200, [{ member_id: 1, display_name: 'Hopscotch', discord_user_id: null }]);
    expect((await listMembers(f))[0].display_name).toBe('Hopscotch');
    expect(calls[0].url).toBe('/api/members');
  });
  it('lists and unclaims', async () => {
    expect(await listClaims(fakeFetch(200, []).f)).toEqual([]);
    const { f, calls } = fakeFetch(204);
    await unclaim(7, f);
    expect(calls[0]).toMatchObject({ url: '/api/claims/7', init: { method: 'DELETE' } });
  });
  it('keeps the status text for non-JSON errors', async () => {
    const f = (async () => new Response('oops', { status: 500, statusText: 'Server Error' })) as unknown as typeof fetch;
    await expect(listClaims(f)).rejects.toMatchObject({ status: 500, message: 'Server Error' });
  });
});

describe('messages', () => {
  it('explains each refusal', () => {
    expect(claimError(new ApiError(401, ''))).toMatch(/Sign in/);
    expect(claimError(new ApiError(403, ''))).toMatch(/trial or raider/);
    expect(claimError(new ApiError(404, ''))).toMatch(/No character/);
    expect(claimError(new ApiError(409, ''))).toMatch(/officer/);
    expect(claimError(new ApiError(500, 'boom'))).toBe('boom');
    expect(claimError(new Error('x'))).toMatch(/try again/);
  });
  it('labels claim states', () => {
    expect(statusLabel({ status: 'approved', reason: null })).toBe('Approved');
    expect(statusLabel({ status: 'pending', reason: null })).toMatch(/officer/);
    expect(statusLabel({ status: 'rejected', reason: 'Not yours' })).toBe('Rejected: Not yours');
    expect(statusLabel({ status: 'rejected', reason: null })).toBe('Rejected');
  });
});
